
# -*- encoding: utf-8 -*-
#
# Copyright 2012-2023 Ghent University
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

from vsc.utils.cache import FileCache
from vsc.utils.fancylogger import getLogger

log = getLogger(__name__)

NAGIOS_CACHE_DIR = '/var/cache'
NAGIOS_CACHE_FILENAME_TEMPLATE = '%s.nagios.json.gz'

NAGIOS_OK = 'OK'
NAGIOS_WARNING = 'WARNING'
NAGIOS_CRITICAL = 'CRITICAL'
NAGIOS_UNKNOWN = 'UNKNOWN'

NAGIOS_EXIT_OK = (0, NAGIOS_OK)
NAGIOS_EXIT_WARNING = (1, NAGIOS_WARNING)
NAGIOS_EXIT_CRITICAL = (2, NAGIOS_CRITICAL)
NAGIOS_EXIT_UNKNOWN = (3, NAGIOS_UNKNOWN)
NAGIOS_MAX_MESSAGE_LENGTH = 8192


def _real_exit(message, code, metrics=''):
    """Prints the code and first  message and exits accordingly.

    @type message: string
    @type code: tuple
    @type metrics: string

    @param message: Useful message for nagios, will be truncated to NAGIOS_MAX_MESSAGE_LENGTH
    @param code: the exit code of the application using the nagios utility
    @param metrics: Metrics for nagios, used to create graphs
    """
    (exit_code, exit_text) = code
    message = message.split('|')
    msg = message[0]
    if len(message) > 1:
        metrics = f'|{message[1]}'
    if len(msg) > NAGIOS_MAX_MESSAGE_LENGTH:
        # log long message but print truncated message
        log.info("Nagios report %s: %s%s", exit_text, msg, metrics)
        msg = msg[:NAGIOS_MAX_MESSAGE_LENGTH-3] + '...'

    print(f"{exit_text} {msg}{metrics}")
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


def real_exit(exit_code, message):
    """A public function, with arguments in the same order as NagiosReporter.cache"""
    _real_exit(message, exit_code)


NAGIOS_DEFAULT_ERRORCODE_MAP = {
    0: NAGIOS_OK,
    1: NAGIOS_WARNING,
    2: NAGIOS_CRITICAL,
    3: NAGIOS_UNKNOWN,
}

NAGIOS_EXIT_MAP = {
    NAGIOS_OK: ok_exit,
    NAGIOS_WARNING: warning_exit,
    NAGIOS_CRITICAL: critical_exit,
    NAGIOS_UNKNOWN: unknown_exit,
}


def exit_from_errorcode(errorcode, msg, error_map=None):
    """Call the correct exit function based on the error code and the mapping"""
    e_map = error_map or NAGIOS_DEFAULT_ERRORCODE_MAP
    try:
        NAGIOS_EXIT_MAP[e_map[errorcode]](msg)
    except (IndexError, KeyError):
        unknown_exit(f"{msg} (errorcode {errorcode} not found in {e_map}")


class NagiosRange(object):
    """Implement Nagios ranges"""
    DEFAULT_START = 0
    def __init__(self, nrange):
        """Initialisation
            @param nrange: nrange in [@][start:][end] format. If it is not a string, it is converted to
                          string and that string should allow conversion to float.
        """
        self.log = getLogger(self.__class__.__name__, fname=False)

        if not isinstance(nrange, str):
            newnrange = str(nrange)
            self.log.debug("nrange %s of type %s, converting to string (%s)", str(nrange), type(nrange), newnrange)
            try:
                float(newnrange)
            except ValueError as exc:
                msg = (
                    f"nrange {str(nrange)} (type {type(nrange)}) is not valid after"
                    f" conversion to string (newnrange {newnrange})"
                    )
                self.log.exception(msg)
                raise ValueError(msg) from exc
            nrange = newnrange

        self.range_fn = self.parse(nrange)

    def parse(self, nrange):
        """Convert nrange string into nrange function.
            range_fn tests if a value is inside the nrange
        """
        reg = re.compile(r"^\s*(?P<neg>@)?((?P<start>(~|[0-9.-]+)):)?(?P<end>[0-9.-]+)?\s*$")
        r = reg.search(nrange)
        if r:
            res = r.groupdict()
            self.log.debug("parse: nrange %s gave %s", nrange, res)

            start_txt = res['start']
            if start_txt is None:
                start = 0
            elif start_txt == '~':
                start = None  # -inf
            else:
                try:
                    start = float(start_txt)
                except ValueError as exc:
                    msg = f"Invalid start txt value {start_txt}"
                    self.log.exception(msg)
                    raise ValueError(msg) from exc

            end = res['end']
            if end is not None:
                try:
                    end = float(end)
                except ValueError as exc:
                    msg = f"Invalid end value {end}"
                    self.log.exception("msg")
                    raise ValueError(msg) from exc

            neg = res['neg'] is not None
            self.log.debug("parse: start %s end %s neg %s", start, end, neg)
        else:
            msg = f"parse: invalid nrange {nrange}."
            self.log.Error(msg)
            raise ValueError(nrange)

        def range_fn(test):
            # test inside nrange?
            try:
                test = float(test)
            except ValueError as exc:
                msg = f"range_fn: can't convert test {test} (type {type(test)}) to float"
                self.log.exception(msg)
                raise ValueError(msg) from exc

            start_res = True  # default: -inf < test
            if start is not None:
                # start <= test
                start_res = operator.le(start, test)

            end_res = True  # default: test < +inf
            if end is not None:
                # test <= end
                end_res = operator.le(test, end)

            tmp_res = operator.and_(start_res, end_res)
            if neg:
                tmp_res = operator.not_(tmp_res)

            self.log.debug("range_fn: test %s start_res %s end_res %s result %s (neg %s)",
                           test, start_res, end_res, tmp_res, neg)
            return tmp_res

        return range_fn

    def alert(self, test):
        """Return the inverse evaluation of the range function with value test.
            Returns True if an alert should be raised, i.e. if test is outside nrange.
        """
        return not self.range_fn(test)


class NagiosReporter(object):
    """Reporting class for Nagios/Icinga reports.

    Can cache the result in a gzipped JSON file and print the result out at some later point.
    """

    def __init__(self, header, filename, threshold, nagios_username="nagios", world_readable=False):
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

        self.world_readable = world_readable

        self.nagios_username = nagios_username

        self.log = getLogger(self.__class__.__name__, fname=False)

    def report_and_exit(self):
        """Unzips the cache file and reads the JSON data back in, prints the data and exits accordingly.

        If the cache data is too old (now - cache timestamp > self.threshold), a critical exit is produced.
        """
        try:
            nagios_cache = FileCache(self.filename, True)
        except (IOError, OSError):
            self.log.critical("Error opening file %s for reading", self.filename)
            unknown_exit(f"{self.header} nagios gzipped JSON file unavailable ({self.filename})")

        (timestamp, ((nagios_exit_code, nagios_exit_string), nagios_message)) = nagios_cache.load('nagios')

        if self.threshold <= 0 or time.time() - timestamp < self.threshold:
            self.log.info("Nagios check cache file %s contents delivered: %s", self.filename, nagios_message)
            print(f"{nagios_exit_string} {nagios_message}")
            sys.exit(nagios_exit_code)
        else:
            unknown_exit(f"{self.header} gzipped JSON file too old (timestamp = {time.ctime(timestamp)})")

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
            self.log.info("Wrote nagios check cache file %s at about %s", self.filename, time.ctime(time.time()))
        except (IOError, OSError) as exc:
            # raising an error is ok, since we usually do this as the very last thing in the script
            msg = f"Cannot save to the nagios gzipped JSON file ({self.filename})"
            self.log.exception(msg)
            raise OSError(msg) from exc

        try:
            p = pwd.getpwnam(self.nagios_username)
            if self.world_readable:
                os.chmod(self.filename, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH)
            else:
                os.chmod(self.filename, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP)

            # only change owner/group when run as root
            if os.geteuid() == 0:
                os.chown(self.filename, p.pw_uid, p.pw_gid)
            else:
                self.log.warning("Not running as root: Cannot chown the nagios check file %s to %s",
                              self.filename, self.nagios_username)
        except (OSError, FileNotFoundError) as exc:
            msg = f"Cannot chown the nagios check file {self.filename} to the nagios user"
            self.log.exception(msg)
            raise(OSError(msg)) from exc

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

        for key, value in self.__dict__.items():
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

        perf = []
        for k, v in sorted(processed_dict.items()):
            if ' ' in k:
                k = f"'{k}'"
            perf.append(f"{k}={v.get('value', '')}{v.get('unit', '')};{v.get('warning', '')};{v.get('critical', '')};")

        return f"{self.message} | {' '.join(perf)}"


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
        _cache: a filename, if it is set, exit will use NagsioReporter.cache to this file instead of real_exit
        _cache_user: a user that will become owner of the cachefile
    """

    USE_HEADER = True
    RESERVED_WORDS = set(['message', 'ok', 'warning', 'critical', 'unknown',
                         '_exit', '_cache', '_cache_user', '_final', '_final_state', '_report', '_threshold'])

    def __init__(self, **kwargs):
        """Initialise message and perfdata"""
        self.__dict__ = {}
        self.message = None  # the message

        self._cache = None  # the filename of the cache file, will use cache instead of real_exit
        self._cache_user = None

        self._final = None
        self._final_state = None

        self._threshold = 0
        self._report_and_exit = False

        self._world_readable = False

        self.__dict__.update(kwargs)

        if self._cache:
            # make a NagiosReporter instance that can be used for caching
            if self._cache_user:
                cache = NagiosReporter('no header', self._cache, self._threshold, nagios_username=self._cache_user,
                                       world_readable=self._world_readable)
            else:
                cache = NagiosReporter('no header', self._cache, self._threshold, world_readable=self._world_readable)
            if self._report_and_exit:
                cache.report_and_exit()
            else:
                self._final = cache.cache
        else:
            # default exit with real_exit
            self._final = real_exit

        if self.message:
            self._eval_and_exit()

    def _exit(self, nagios_exitcode, msg):
        """Save the last state before performing actual exit.
            In case of caching, this allows to eg generate log message without rereading the cache file.
            In case of regular exit, this code is not/cannot be used.
        """
        self._final_state = (nagios_exitcode, msg)
        self._final(nagios_exitcode, msg)

    def ok(self, msg):
        self._exit(NAGIOS_EXIT_OK, msg)

    def warning(self, msg):
        self._exit(NAGIOS_EXIT_WARNING, msg)

    def critical(self, msg):
        self._exit(NAGIOS_EXIT_CRITICAL, msg)

    def unknown(self, msg):
        self._exit(NAGIOS_EXIT_UNKNOWN, msg)

    def _eval(self, **kwargs):
        """Evaluate the overall critical and warning level.
            warning is not checked if critical is reached
            returns warn,crit,msg
                msg is the name of the perfdata that caused the
                critical/warning level
        """
        self.__dict__.update(kwargs)

        processed_dict = self._process_data()

        msg = []

        warn, crit = None, None
        for k, v in sorted(processed_dict.items()):
            if "critical" in v and NagiosRange(v['critical']).alert(v['value']):
                crit = True
                msg.append(k)

        if not crit:
            for k, v in sorted(processed_dict.items()):
                if "warning" in v and NagiosRange(v['warning']).alert(v['value']):
                    warn = True
                    msg.append(k)

        return warn, crit, ', '.join(msg)

    def _eval_and_exit(self, **kwargs):
        """Based on provided performance data, exit with proper message and exitcode"""
        warn, crit, msg = self._eval(**kwargs)

        if crit:
            self.message = msg
            self.critical(str(self))
        elif warn:
            self.message = msg
            self.warning(str(self))
        else:
            self.ok(str(self))
