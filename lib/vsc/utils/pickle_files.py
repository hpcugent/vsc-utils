#
# Copyright 2012-2016 Ghent University
#
# This file is part of vsc-utils,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
# the Flemish Research Foundation (FWO) (http://www.fwo.be/en)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# https://github.com/hpcugent/vsc-utils
#
# vsc-utils is free software: you can redistribute it and/or modify
# it under the terms of the GNU Library General Public License as
# published by the Free Software Foundation, either version 2 of
# the License, or (at your option) any later version.
#
# vsc-utils is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU Library General Public License
# along with vsc-utils. If not, see <http://www.gnu.org/licenses/>.
#
"""
Various types of pickle files that can be used to store non-component specific information.

- TimestampPickle: stores a simple timestamp in a pickled fashion.

                   This should be altered to truly become a base class we can use to store other stuff together with a
                   timestamp.

@author: Andy Georges (Ghent University)
@author: Stijn De Weirdt (Ghent University)
"""

import cPickle as pickle
import os
import stat

from vsc.utils import fancylogger


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
        except Exception:
            self.log.exception("Failed to dump timestamp %s to pickle in filename %s" % (timestamp, self.filename))
            raise

        try:
            os.chmod(self.filename, stat.S_IRWXU)
        except Exception:
            self.log.exception("Failed to set permissions on filename %s" % (self.filename))
            raise
