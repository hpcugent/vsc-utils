#!/usr/bin/env python
# -*- coding: latin-1 -*-
##
# Copyright 2009-2013 Ghent University
#
# This file is part of vsc-utils,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://vscentrum.be/nl/en),
# the Hercules foundation (http://www.herculesstichting.be/in_English)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# All rights reserved.
#
##
"""Various types of pickle files that can be used to store non-component specific information.

- TimestampPickle: stores a simple timestamp in a pickled fashion.

                   This should be altered to truly become a base class we can use to store other stuff together with a
                   timestamp.

@author: Andy Georges (Ghent University)
@author: Stijn De Weirdt (Ghent University)
"""

import cPickle as pickle
import os
import stat

from vsc import fancylogger


class TimestampPickle(object):
    """Stores a timestamp in some format in a file."""

    def __init__(self, filename):
        self.filename = filename
        self.log = fancylogger.getLogger(self.__class__.__name__)

    def read(self):
        """Read a timestamp value from a pickled file.

        @type filename: string representing the filename of the file to read from.

        @returns: the timestamp in the same format it was stored in.

        @raise
        """

        try:
            timestamp = pickle.load(open(self.filename, "rb"))
        except:
            self.log.exception("Failed to load timestamp pickle from filename %s." % (self.filename))
            return None

        return timestamp

    def write(self, timestamp):
        """Write the given timestamp to a pickled file.
        @type timestamp: datetime.datetime timestamp
        @type filename: string representing the filename of the file to write to. Defaults to None, and then it tries
                        the location provided by the configuration, if any, i.e.,
                        self.vsc.cfg['ldap_timestamp_filename']

        @raise: KeyError if the configuration data was used but no filename information was found
        """

        try:
            pickle.dump(timestamp, open(self.filename, "wb"))
        except Exception, _:
            self.log.exception("Failed to dump timestamp %s to pickle in filename %s" % (timestamp, self.filename))
            raise

        try:
            os.chmod(self.filename, stat.S_IRWXU)
        except Exception, _:
            self.log.exception("Failed to set permissions on filename %s" % (self.filename))
            raise
