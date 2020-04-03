# -*- coding: latin-1 -*-
#
# Copyright 2009-2020 Ghent University
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
from vsc.utils.py2vs3 import is_string

LDAP_DATETIME_TIMEFORMAT = "%Y%m%d%H%M%SZ"

DEFAULT_TIMESTAMP = "20140101000000Z"


def convert_to_datetime(timestamp=None):
    """
    Convert a string or datetime.datime instance to a datetime.datetime with UTC tzinfo

    If no timestamp is given return current time

    if timestamp is a string we can convert following formats:
    Parse a datestamp according to its length
        * YYYYMMDD       (8 chars)
        * unix timestamp (10 chars or any int)
        * YYYYMMDDHHMM   (12 chars)
        * LDAP_DATETIME_TIMEFORMAT
    """
    if timestamp is None:
        # utcnow is time tuple with valid utc time without tzinfo
        #   replace(tzinfo=utc) fixes the tzinfo
        return datetime.datetime.utcnow().replace(tzinfo=utc)

    if isinstance(timestamp, int):
        timestamp = "%010d" % timestamp
    if isinstance(timestamp, datetime.datetime):
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=utc)
    elif is_string(timestamp):
        if len(timestamp) == 10:
            # Unix timestamp
            timestamp = datetime.datetime.fromtimestamp(int(timestamp), utc)
        else:
            if len(timestamp) == 12:
                date_format = "%Y%m%d%H%M"
            elif len(timestamp) == 15:  # len(LDAP_DATETIME_FORMAT doesn't work here
                date_format = LDAP_DATETIME_TIMEFORMAT
            elif len(timestamp) == 8:
                date_format = "%Y%m%d"
            else:
                raise Exception("invalid format provided %s" % timestamp)
            timestamp = datetime.datetime.strptime(timestamp, date_format)

    return timestamp.replace(tzinfo=utc)


def convert_to_unix_timestamp(timestamp=None):
    """
    Convert a string or datetime.datetime instance
    to an integer representing unix timestamp (seconds since epoch)
    """
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

    @returns: a timestamp in whatever format it was stored in (string LDAP timestamp, unix epoch, ...)
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


def retrieve_timestamp_with_default(filename, start_timestamp=None, default_timestamp=DEFAULT_TIMESTAMP, delta=-10):
    """
    Return a tuple consisting of the following values:
    - the unix timestamp (in int) from the given file if the start_timestamp is not provided
      and fall back on default_timestamp if needed.
    - the current time (datetime instance) based on the given delta (offset compared to now(tz=utc) in seconds),
      defaulting to -10s.
    """
    timestamp = start_timestamp
    if start_timestamp is None:
        timestamp = read_timestamp(filename)

    if timestamp is None:
        timestamp = convert_to_unix_timestamp(default_timestamp)
    else:
        timestamp = convert_to_unix_timestamp(timestamp)

    logging.info("Using timestamp %s", timestamp)

    current_time = datetime.datetime.now(tz=utc) + datetime.timedelta(seconds=delta)
    return (timestamp, current_time)
