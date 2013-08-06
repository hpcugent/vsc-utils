#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# #
# Copyright 2012-2013 Ghent University
#
# This file is part of vsc-utils,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://vscentrum.be/nl/en),
# the Hercules foundation (http://www.herculesstichting.be/in_English)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# http://github.com/hpcugent/vsc-utils
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
# #
"""
This module provides functionality to cache and report results of script executions that can readily be
interpreted by nagios/icinga.

 - simple exit messages that can directly be picked up by an icingna check
    - ok
    - warning
    - critical
    - unknown
 - NagiosReporter class that provides cache functionality, writing and reading the nagios/icinga result string to a
  gzipped JSON file.

@author: Andy Georges (Ghent University)
@author: Luis Fernando Muñoz Mejías (Ghent University)
"""

import operator
import os
import pwd
import re
import stat
import sys
import time

from vsc.utils.fancylogger import getLogger
from vsc.utils.cache import FileCache

log = getLogger(__name__)

NAGIOS_EXIT_OK = (0, 'OK')
NAGIOS_EXIT_WARNING = (1, 'WARNING')
NAGIOS_EXIT_CRITICAL = (2, 'CRITICAL')
NAGIOS_EXIT_UNKNOWN = (3, 'UNKNOWN')


def _real_exit(message, code):
    """Prints the code and message and exitas accordingly.

    @type message: string
    @type code: tuple

    @param message: Useful message for nagios
    @param code: the, ah, erm, exit code of the application using the nagios utility
    """
    (exit_code, text) = code
    print "%s %s" % (text, message)
    log.info("Nagios report %s: %s" % (text, message))
    sys.exit(exit_code)


def ok_exit(message):
    """Prints OK message and exits the program with an OK exit code."""
    _real_exit(message, NAGIOS_EXIT_OK)


def warning_exit(message):
    """Prints WARNING message and exits the program with an WARNING exit code."""
    _real_exit(message, NAGIOS_EXIT_WARNING)


def unknown_exit(message):
    """Prints UNKNOWN message and exits the program with an UNKNOWN exit code."""
    _real_exit(message, NAGIOS_EXIT_UNKNOWN)


def critical_exit(message):
    """Prints CRITICAL message and exits the program with an CRITICAL exit code."""
    _real_exit(message, NAGIOS_EXIT_CRITICAL)


def nagios_exit(state, message):
    """Print message according to state: supported states:
        - defined nagios constants NAGIOS_EXIT_
        - string: OK,WARNING,CRITICAL and UNKNOWN
        - integer: 0,1,2,3
    """
    nagios_states = [NAGIOS_EXIT_OK, NAGIOS_EXIT_WARNING, NAGIOS_EXIT_CRITICAL, NAGIOS_EXIT_UNKNOWN]
    for x in nagios_states:
        if state == x or state == x[0]  or state == x[1]:
            # this exits, no break or return needed
            _real_exit(message, x)
    log.raiseException('Unsupported state %s.' % (state))

class NagiosReporter(object):
    """Reporting class for Nagios/Icinga reports.

    Can cache the result in a gzipped JSON file and print the result out at some later point.
    """

    def __init__(self, header, filename, threshold, nagios_username="nagios"):
        """Initialisation.

        @type header: string
        @type filename: string
        @type threshold: positive integer

        @param header: application specific part of the message, used to denote what program/script is using the
                       reporter.
        @param filename: the filename of the gzipped JSON cache file
        @param threshold: Seconds to determines how old the gzipped JSON data may be
                         before reporting an unknown result. This can be used to check if the script that uses the
                         reporter has run the last time and succeeded in writing the cache data. If the threshold <= 0,
                         this feature is not used.
        """
        self.header = header
        self.filename = filename
        self.threshold = threshold

        self.nagios_username = nagios_username

        self.log = getLogger(self.__class__.__name__, fname=False)

    def report_and_exit(self):
        """Unzips the cache file and reads the JSON data back in, prints the data and exits accordingly.

        If the cache data is too old (now - cache timestamp > self.threshold), a critical exit is produced.
        """
        try:
            nagios_cache = FileCache(self.filename, True)
        except:
            self.log.critical("Error opening file %s for reading" % (self.filename))
            unknown_exit("%s nagios gzipped JSON file unavailable (%s)" % (self.header, self.filename))

        (timestamp, ((nagios_exit_code, nagios_exit_string), nagios_message)) = nagios_cache.load('nagios')
        nagios_cache.close()

        if self.threshold < 0 or time.time() - timestamp < self.threshold:
            self.log.info("Nagios check cache file %s contents delivered: %s" % (self.filename, nagios_message))
            print "%s %s" % (nagios_exit_string, nagios_message)
            sys.exit(nagios_exit_code)
        else:
            unknown_exit("%s gzipped JSON file too old (timestamp = %s)" % (self.header, time.ctime(timestamp)))

    def cache(self, nagios_exit, nagios_message):
        """Store the result in the cache file with a timestamp.

        @type nagios_exit: one of NAGIOS_EXIT_OK, NAGIOS_EXIT_WARNING, NAGIOS_EXIT_CRTITCAL or NAGIOS_EXIT_UNKNOWN
        @type nagios_message: string

        @param nagios_exit: a valid nagios exit code.
        @param nagios_message: the message to print out when the actual check runs.
        """
        try:
            nagios_cache = FileCache(self.filename)
            nagios_cache.update('nagios', (nagios_exit, nagios_message), 0)  # always update
            nagios_cache.close()
            self.log.info("Wrote nagios check cache file %s at about %s" % (self.filename, time.ctime(time.time())))
        except:
            # raising an error is ok, since we usually do this as the very last thing in the script
            self.log.raiseException("Cannot save to the nagios gzipped JSON file (%s)" % (self.filename))

        try:
            p = pwd.getpwnam(self.nagios_username)
            os.chmod(self.filename, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP)
            os.chown(self.filename, p.pw_uid, p.pw_gid)
        except:
            self.log.raiseException("Cannot chown the nagios check file %s to the nagios user" % (self.filename))

        return True


class NagiosResult(object):
    """Class representing the results of an Icinga/Nagios check.

    It will contain a field with the message to be printed.  And the
    rest of its fields will be the performance data, including
    thresholds for each aspect.

    It provides an C{__str__} method, so that when the results are
    printed, they are rendered correctly and we don't wonder why
    Icinga is doing weird things with its plots.

    For example:

    >>> n = NagiosResult('msg', a=1)
    >>> print n
    msg | a=1;;;
    >>> n = NagiosResult('msg', a=1, a_critical=2, a_warning=3)
    >>> print n
    msg | a=1;3;2;
    >>> n = NagiosResult('msg')
    >>> print n
    msg
    >>> n.a = 5
    >>> print n
    msg | a=5;;;
    >>> n.b = 5
    >>> n.b_critical = 7
    >>> print n
    msg | a=5;;; b=5;;7;

    For more information about performance data and output strings in
    Nagios checks, please refer to
    U{http://docs.icinga.org/latest/en/perfdata.html}
    """
    RESERVED_WORDS = set(['message'])
    NAME_REG = re.compile(r'^(?P<name>.*?)(?:_(?P<option>warning|critical))?$')

    def __init__(self, message, **kwargs):
        """Class constructor.  Takes a message and an optional
        dictionary with each relevant metric and (perhaps) its
        critical and warning thresholds

        @type message: string
        @type kwargs: dict

        @param message: Output of the check.
        @param kwargs: Each value is a number or a string which is
        expected to be a number plus a unit.  Each key is the name of
        a performance datum, optionally with the suffixes "_critical"
        and "_warning" for marking the respective thresholds.
        """
        self.__dict__ = kwargs
        self.message = message

    def _process_data(self):
        """Convert the self.__dict__ in list of dictionaries with value/ok/warning/critical"""
        processed_dict = dict()

        for key, value in self.__dict__.iteritems():
            if key in self.RESERVED_WORDS or key.startswith('_'):
                continue
            processed_key = self.NAME_REG.search(key).groupdict()
            t_name = processed_key.get('name')
            t_key = processed_key.get('option', 'value') or 'value'
            f = processed_dict.setdefault(t_name, dict())
            f[t_key] = value

        return processed_dict

    def __str__(self):
        """Turns the result object into a string suitable for being
        printed by an Icinga check."""
        processed_dict = self._process_data()
        if not processed_dict:
            return self.message

        perf = ["%s=%s;%s;%s;" % (k, v.get('value', ''), v.get('warning', ''), v.get('critical', ''))
                for k, v in sorted(processed_dict.iteritems())]

        return "%s | %s" % (self.message, ' '.join(perf))


class SimpleNagios(NagiosResult):
    """Class to allow easy interaction with the above Nagios-related code
    2 main supported cases:
        a. SimpleNagios().ok("All fine")
        will produce
        OK - All fine and exit with NAGIOS_EXIT_OK
    
        b. SimpleNagios('test a', a=2,a_critical=1)
        will produce 
        CRITICAL test a | a=2;;1; and exit with NAGIOS_EXIT_CRITICAL
    
    Main differences with NagiosResult:
    - __init__: named arguments only
    - reserved words as kwargs: 
        message: a message
        ok, warning, unknown, critical: these are functions
    """

    USE_HEADER = True
    RESERVED_WORDS = set(['message', 'ok', 'warning', 'critical', 'unknown'])
    EVAL_OPERATOR = operator.ge

    def __init__(self, **kwargs):
        """Initialise message and perfdata"""
        self.__dict__ = {}
        self.message = None

        self.__dict__.update(kwargs)

        if self.message:
            self._eval_and_exit()

    def ok(self, msg):
        ok_exit(msg)

    def warning(self, msg):
        warning_exit(msg)

    def critical(self, msg):
        critical_exit(msg)

    def unknown(self, msg):
        unknown_exit(msg)

    def _eval_and_exit(self, **kwargs):
        """Based on provided performance data, exit with proper message and exitcode"""
        self.__dict__.update(kwargs)

        processed_dict = self._process_data()

        warn = True in [self.EVAL_OPERATOR(v['value'], v['warning'])
                for v in processed_dict.values() if 'warning' in v]
        crit = True in [self.EVAL_OPERATOR(v['value'], v['critical'])
                for v in processed_dict.values() if 'critical' in v]

        if crit:
            self.critical(self)
        elif warn:
            self.warning(self)
        else:
            self.ok(self)
