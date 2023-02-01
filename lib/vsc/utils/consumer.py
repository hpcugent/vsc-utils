#
# Copyright 2020-2023 Ghent University
#
# This file is part of vsc-reporting,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
# the Flemish Research Foundation (FWO) (http://www.fwo.be/en)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# https://github.ugent.be/hpcugent/vsc-reporting
#
# All rights reserved.
#
"""
Consumer class
 - consume kafka topic
 - write files to be shredded
"""

import json
import logging
import os

from vsc.reporting.xdmod.cli import KafkaCLI, Ingestor


class ConsumerCLI(KafkaCLI):
    """Consume data from kafka topics and prepare it as xdmod shred file input"""

    CONSUMER_CLI_OPTIONS = {
        'group': ("Kafka consumer group", None, "store", "xdmod"),
        'timeout': ('Kafka consumer timeout in ms. If not set, loops forever', int, "store", None),
        'spool': ("Location to place the files for xdmod-shredder", str, "store", None),
    }

    def make_options(self, defaults=None):
        self.CLI_OPTIONS.update(self.CONSUMER_CLI_OPTIONS)
        return super(ConsumerCLI, self).make_options(defaults=defaults)


    def get_kafka_kwargs(self):
        """Generate the kafka producer or consumer args"""

        kwargs = super(ConsumerCLI, self).get_kafka_kwargs()

        if self.options.timeout is not None:
            kwargs["consumer_timeout_ms"] = self.options.timeout

        # disable auto commit, so dry-run doesn't commit
        kwargs.setdefault('enable_auto_commit', False)

        return kwargs

    def process_msg(self, msg):
        """
        Process msg as JSON.
        Return None on failure.
        """
        value = msg.value
        if value:
            try:
                event = json.loads(value)
            except ValueError:
                logging.error("Failed to load as JSON: %s", value)
                return None

            if 'payload' in event:
                return event
            else:
                logging.error("Payload missing from event %s", event)
                return None
        else:
            logging.error("msg has no value %s (%s)", msg, type(msg))
            return None

    def update_shred_file(self, event, dry_run):
        # need nested structure: eg cloud and storage can only update directory only per resource
        type_dir = os.path.join(self.options.spool, event['type'], event['resource'])
        if not os.path.exists(type_dir):
            os.makedirs(type_dir)

        # add resource/type too?
        #    only day in filename for shredding per directory
        fn = os.path.join(type_dir, event['day'])

        if os.path.exists(fn + '.gz'):
            logging.error("Can't add event %s to %s. Found gzipped file.", event, fn)
            raise Exception("Gzipped destination found")

        logging.debug("Writing event for day %s and resource %s", event['day'], event['resource'])
        if dry_run:
            logging.debug("Dry run, not actually updating anything")
        else:
            #
            # Changes here must be kept in sync with the archive update code
            #
            payload = event['payload']
            if event["type"] == Ingestor.slurm.value:
                with open(fn, "a") as day_shred_file:
                    day_shred_file.write(payload.rstrip() + "\n")
            else:
                # update list of json events
                #   the reading part can be cached to avoid IO issues
                if os.path.exists(fn):
                    with open(fn, 'r') as day_shred_file:
                        events = json.load(day_shred_file)
                else:
                    if event["type"] == Ingestor.cloudresourcespecs.value:
                        events = {'hypervisors': []}
                    else:
                        events = []

                if event["type"] == Ingestor.cloudresourcespecs.value:
                    # this is a status rather than events collection
                    #   timestamp of status is that of latest "update"
                    events['ts'] = payload.pop('ts')
                    events['hypervisors'].append(payload)
                else:
                    events.append(payload)

                with open(fn, 'w') as day_shred_file:
                    json.dump(events, day_shred_file, sort_keys=True)

    def do(self, dry_run):
        """Consume data from kafka"""
        consumer = self.make_consumer(self.options.group)

        # we do not expect this loop to end, i.e., we keep polling
        stats = {}

        def update_stats(event):
            """update of stats for event"""
            typ = stats.setdefault(event['type'], {})
            resource = typ.setdefault(event['resource'], {})
            day = event['day']
            if day in resource:
                resource[day] += 1
            else:
                resource[day] = 1

        def consumer_close():
            # default is autocommit=True, which is not ok wrt dry_run
            consumer.close(autocommit=False)

            total = sum([sum(d.values()) for r in stats.values() for d in r.values()])
            logging.info("All %s messages retrieved (dry_run=%s): %s", total, dry_run, stats)

        logging.debug("Starting to iterate over messages")
        for msg in consumer:
            event = self.process_msg(msg)

            if event is not None:
                try:
                    self.update_shred_file(event, dry_run)
                    if not dry_run:
                        # this is essentially one past the post ack, but we already have that message as well
                        consumer.commit()
                    update_stats(event)
                except Exception:
                    logging.exception("Something went wrong while processing event %s", event)
                    consumer_close()
                    raise

        consumer_close()
