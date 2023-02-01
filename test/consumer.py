#
# Copyright 2021-2023 Ghent University
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
xdmod tests
"""
import logging
import mock
import sys
import json
import os

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)


from collections import namedtuple

from vsc.install.testing import TestCase
from vsc.utils.consumer import ConsumerCLI



class TestConsumer(TestCase):
    def setUp(self):
        """Prepare test case."""
        super(TestConsumer, self).setUp()
        self.spool = os.path.join(self.tmpdir, 'spool')
        os.mkdir(self.spool)

        sys.argv = [
            'name', '--debug',
            '--spool='+self.spool,
            '--brokers=serv1,serv2',
            '--ssl=ssl1=sslv1,ssl2=sslv2',
            '--sasl=sasl1=saslv1,sasl2=sslv2',
            ]
    def mk_event(self, typ, resource, day, payload):
        return {
            "type": typ,
            "resource": resource,
            "payload": payload,
            "day": day,
        }

    @mock.patch('vsc.utils.script_tools.ExtendedSimpleOption.prologue')
    def test_update_shred(self, mock_prologue):
        consumer = ConsumerCLI()

        # directories are created, but no file, this is dry-run
        consumer.update_shred_file(self.mk_event('slurm', 'cluster1', '12345678', 'some|data'), True)
        sl1 = os.path.join(self.spool, 'slurm', 'cluster1')
        sl1_ev1 = os.path.join(sl1, '12345678')
        self.assertTrue(os.path.isdir(sl1))
        self.assertFalse(os.path.exists(sl1_ev1))

        consumer.update_shred_file(self.mk_event('slurm', 'cluster1', '12345678', 'some|data'), False)
        self.assertEqual(open(sl1_ev1).read(), "some|data\n")
        consumer.update_shred_file(self.mk_event('slurm', 'cluster1', '12345678', 'some|data2'), False)
        self.assertEqual(open(sl1_ev1).read(), "some|data\nsome|data2\n")

        consumer.update_shred_file(self.mk_event('cloudresourcespecs', 'cloud2', '22345679', {"some": "data", "ts": "123"}), False)
        clr1 = os.path.join(self.spool, 'cloudresourcespecs', 'cloud2')
        clr1_ev1 = os.path.join(clr1, '22345679')
        self.assertEqual(open(clr1_ev1).read(), '{"hypervisors": [{"some": "data"}], "ts": "123"}')
        consumer.update_shred_file(self.mk_event('cloudresourcespecs', 'cloud2', '22345679', {"some": "otherdata", "ts": "456"}), False)
        self.assertEqual(open(clr1_ev1).read(), '{"hypervisors": [{"some": "data"}, {"some": "otherdata"}], "ts": "456"}')

        consumer.update_shred_file(self.mk_event('cloud', 'cloud1', '22345678', {"some": "data"}), False)
        cl1 = os.path.join(self.spool, 'cloud', 'cloud1')
        cl1_ev1 = os.path.join(cl1, '22345678')
        self.assertEqual(open(cl1_ev1).read(), '[{"some": "data"}]')
        consumer.update_shred_file(self.mk_event('cloud', 'cloud1', '22345678', {"some": "otherdata"}), False)
        self.assertEqual(open(cl1_ev1).read(), '[{"some": "data"}, {"some": "otherdata"}]')

    @mock.patch('vsc.utils.script_tools.ExtendedSimpleOption.prologue')
    @mock.patch('vsc.utils.cli.KafkaConsumer', autospec=True)
    @mock.patch('vsc.utils.consumer.ConsumerCLI.update_shred_file')
    def test_consume(self, mock_update_shred, mock_consumer, mock_prologue):

        cl1_1 = "test1_1|message1_1|cluster1|4|5|6|7|8|9|10|11|12|2020-02-28T01:02:03|14|15|16|17|18|19|20|21|22|23|24|25|26"
        cl1_2 = "test1_2|message1_1|cluster1|4|5|6|7|8|9|10|11|12|2020-02-28T11:02:03|14|15|16|17|18|19|20|21|22|23|24|25|26"
        cl2_1 = "test2_1|message2_1|cluster2|4|5|6|7|8|9|10|11|12|2020-02-29T04:05:06|14|15|16|17|18|19|20|21|22|23|24|25|26"

        def mk_msg(typ, resource, day, payload):
            return KafkaMsg(value=json.dumps(self.mk_event(typ, resource, day, payload), sort_keys=True).encode('utf8'))

        KafkaMsg = namedtuple("KafkaMsg", ["value"])

        args = [
            ('slurm', 'cluster1', '20200228', cl1_1),
            ('slurm', 'cluster1', '20200228', cl1_2),
            ('slurm', 'cluster2', '20200229', cl2_1),
        ]

        events = [self.mk_event(*arg) for arg in args]

        msgs = [mk_msg(*arg) for arg in args]

        m_iter = mock.MagicMock()
        m_iter.__iter__.return_value = msgs
        mock_consumer.return_value = m_iter

        consumer = ConsumerCLI()
        consumer.do(dry_run=False)

        logging.debug("consumer calls: %s", mock_consumer.mock_calls)
        self.assertEqual(len(mock_consumer.mock_calls), 2 + len(msgs) + 1)

        # init of consumer
        name, args, kwargs = mock_consumer.mock_calls[0]
        logging.debug("%s %s %s", name, args, kwargs)
        self.assertEqual(name, '')
        self.assertEqual(args, ('xdmod',))  # topic
        self.assertEqual(kwargs, {
            'group_id': 'xdmod',
            'security_protocol': 'PLAINTEXT',
            'bootstrap_servers': ['serv1', 'serv2'],
            'ssl1': 'sslv1',
            'ssl2': 'sslv2',
            'sasl1': 'saslv1',
            'sasl2': 'sslv2',
            'enable_auto_commit': False,
        })

        # next call is the __iter__ call for the loop
        name, args, kwargs = mock_consumer.mock_calls[1]
        logging.debug("%s %s %s", name, args, kwargs)
        self.assertEqual(name, '().__iter__')
        self.assertEqual(args, ())
        self.assertEqual(kwargs, {})

        # next are the message commits
        for idx in range(len(msgs)):
            name, args, kwargs = mock_consumer.mock_calls[2+idx]
            logging.debug("%s %s %s", name, args, kwargs)
            self.assertEqual(name, '().commit')
            self.assertEqual(args, ())
            self.assertEqual(kwargs, {})

        logging.debug("update shred calls: %s", mock_update_shred.mock_calls)
        self.assertEqual(len(mock_update_shred.mock_calls), len(events))
        for idx, ev in enumerate(events):
            name, args, kwargs = mock_update_shred.mock_calls[idx]
            logging.debug("%s %s %s", name, args, kwargs)
            self.assertEqual(name, '')
            self.assertEqual(args, (ev, False))
            self.assertEqual(kwargs, {})

        # last call is the close call
        name, args, kwargs = mock_consumer.mock_calls[-1]
        logging.debug("%s %s %s", name, args, kwargs)
        self.assertEqual(name, '().close')
        self.assertEqual(args, ())
        self.assertEqual(kwargs, {'autocommit': False})
