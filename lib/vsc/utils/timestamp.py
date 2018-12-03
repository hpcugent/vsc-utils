# -*- coding: latin-1 -*-
#
# Copyright 2009-2018 Ghent University
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
"""Timestamp tools for cache files.

moved here from vsc-ldap vsc.ldap.timestamp
@author: Andy Georges
@author: Stijn De Weirdt
"""

import datetime
import logging

from vsc.utils.cache import FileCache
from vsc.utils.dateandtime import utc

LDAP_DATETIME_TIMEFORMAT = "%Y%m%d%H%M%SZ"



def convert_to_datetime(timestamp=None):
    """
    Convert a string or datetime.datime instance to a datetime.datetime with local tzinfo

    If no timestamp is given return current time

    if timestamp is a string we can convert following formats:
    Parse a datestamp according to its length
        * YYYYMMDD       (8 chars)
        * unix timestamp (10 chars or any int)
        * YYYYMMDDHHMM   (12 chars)
        * LDAP_DATETIME_TIMEFORMAT
    """
    if timestamp is None:
        timestamp = datetime.datetime.today()
    if isinstance(timestamp, int):
        timestamp = "%010d" % timestamp
    if isinstance(timestamp, datetime.datetime):
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=utc)
    elif isinstance(timestamp, basestring):
        if len(timestamp) == 10:
            # Unix timestamp
            timestamp = datetime.datetime.fromtimestamp(int(timestamp), utc)
        else:
            if len(timestamp) == 12:
                date_format = "%Y%m%d%H%M"
            elif len(timestamp) == 15:  # len(LDAP_DATETIME_FORMAT doesn't work here
                date_format =  LDAP_DATETIME_TIMEFORMAT
            elif len(timestamp) == 8:
                date_format = "%Y%m%d"
            else:
                raise Exception("invalid format provided %s" % timestamp)
            timestamp = datetime.datetime.strptime(timestamp, date_format)

    return timestamp.replace(tzinfo=utc)


def convert_to_unix_timestamp(timestamp=None):
    """Convert a string or datetime.datetime instance to a unix timestamp (Seconds since epoch)"""
    timestamp = convert_to_datetime(timestamp)
    return int((timestamp - datetime.datetime(1970, 1, 1, tzinfo=utc)).total_seconds())


def convert_timestamp(timestamp=None):
    """Convert a timestamp, yielding a string and a datetime.datetime instance.

    @type timestamp: either a string or a datetime.datetime instance. Default value is None, in which case the
                     local time is returned.

    @returns: tuple with the timestamp as a
                - LDAP formatted timestamp on GMT in the yyyymmddhhmmssZ format
                - A datetime.datetime instance representing the timestamp
    """
    timestamp = convert_to_datetime(timestamp)
    return (timestamp, timestamp.astimezone(utc).strftime(LDAP_DATETIME_TIMEFORMAT))


def read_timestamp(filename):
    """Read the stored timestamp value from a pickled file.

    @returns: string representing a timestamp in the proper LDAP time format

    """
    cache = FileCache(filename)
    try:
        (_, timestamp) = cache.load('timestamp')
    except TypeError:
        logging.warning('could not load timestamp from cache file %s', filename)
        timestamp = None

    return timestamp


def write_timestamp(filename, timestamp):
    """Write the given timestamp to a pickled file.

    @type timestamp: datetime.datetime timestamp
    """

    if isinstance(timestamp, datetime.datetime) and timestamp.tzinfo is None:
        # add local timezoneinfo
        timestamp_ = timestamp.replace(tzinfo=utc)
        (_, timestamp_) = convert_timestamp(timestamp)
    else:
        timestamp_ = timestamp

    cache = FileCache(filename)
    cache.update('timestamp', timestamp_, 0)
    cache.close()


def retrieve_timestamp_with_default(filename, start_timestamp=None, default_timestamp="2014010100000Z", delta=10):
    """
    Return a tuple consisting of the following values:
    - the timestamp from the given file if the start_timestamp is not provided 
      and fall back on the default if needed.
    - the current time based on the given delta, defaulting to 10s.
    """
    if not start_timestamp:
        timestamp = convert_to_unix_timestamp(read_timestamp(filename))

    timestamp = timestamp or default_timestamp
    logging.info("Using timestamp %s", start_timestamp)

    current_time = datetime.datetime.now(tz=utc) + datetime.timedelta(seconds=-10)
    return (timestamp, current_time)
