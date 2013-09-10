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
This module provides functions to run at the beginning and end of commonly used scripts
    - nagios checking and reporting if requested
    - locking if required
    - checking for high-availability and bailing if required

@author: Andy Georges
"""
import os
import sys

from copy import deepcopy

from vsc.utils.availability import proceed_on_ha_service
from vsc.utils.generaloption import simple_option, SimpleOption
from vsc.utils.lock import lock_or_bork, release_or_bork, LOCKFILE_DIR, LOCKFILE_FILENAME_TEMPLATE
from vsc.utils.nagios import SimpleNagios, NAGIOS_CACHE_DIR, NAGIOS_CACHE_FILENAME_TEMPLATE
from vsc.utils.timestamp_pid_lockfile import TimestampedPidLockfile


def _script_name(full_name):
    """Return the script name without .py extension if any. This assumes that the script name does not contain a
    dot in case of lacking an extension.
    """
    (name, _) = os.path.splitext(full_name)
    return os.path.basename(name)


DEFAULT_OPTIONS = {
        'nagios_report': ('print out nagios information', None, 'store_true', False, 'n'),
        'nagios_check_filename': ('filename of where the nagios check data is stored', str, 'store',
                                  os.path.join(NAGIOS_CACHE_DIR,
                                               NAGIOS_CACHE_FILENAME_TEMPLATE % (_script_name(sys.argv[0]),))),
        'nagios_check_interval_threshold': ('threshold of nagios checks timing out', None, 'store', 0),
        'ha': ('high-availability master IP address', None, 'store', None),
        'locking': ('protect this script by a file-based lock', None, 'store_true', False),
        'locking_filename': ('file that will serve as a lock', None, 'store',
                             os.path.join(LOCKFILE_DIR,
                                          LOCKFILE_FILENAME_TEMPLATE % (_script_name(sys.argv[0]),))),
        'dry-run': ('do not make any updates whatsoever', None, 'store_true', False),
}


def _merge_options(options):
    """Merge the given set of options with the default options, updating default values where needed.

    @type options: dict. keys should be strings, values are multi-typed.
                       value is a simple scalar if the key represents an update to DEFAULT_OPTIONS\
                       value is a SimpleOption tuple otherwise
    """

    opts = deepcopy(options)
    for (k, v) in DEFAULT_OPTIONS.items():
        if k in opts:
            v_ = v[:3] + (opts[k],) + v[4:]
            opts[k] = v_
        else:
            opts[k] = v

    return opts


class ExtendedSimpleOption(SimpleOption):
    """
    Extends the SimpleOption class to allow other checks to occur at script prologue and epilogue.

    - nagios reporting
    - checking if running on the designated HA host
    - locking on a file

    The prologue should be called at the start of the script; the epilogue at the end.
    """

    def __init__(self, options):
        """Initialise"""

        options_ = _merge_options(options)
        super(ExtendedSimpleOption, self).__init__(options_)

        self.nagios_reporter = None
        self.lockfile = None

    def prologue(self):
        """Checks the options given for settings and takes appropriate action.

        See _merge_options for the format.

        - if nagios_report is set, creates a SimpleNagios instance and prints the report.
        - if ha is set, checks if running on the correct host, set the appropriate nagios message and bail if not.
        - if locking_filename is set, take a lock. If the lock fails, bork and set the nagios exit accordingly.
        """

        # bail if nagios report is requested
        self.nagios_reporter = SimpleNagios(_cache=self.options.nagios_check_filename,
                                            _report_and_exit=self.options.nagios_report)

        # check for HA host
        if self.options.ha and not proceed_on_ha_service(self.options.ha):
            self.log.warning("Not running on the target host %s in the HA setup. Stopping." % (self.options.ha,))
            self.nagios_reporter.ok("Not running on the HA master.")

        if self.options.locking:
            self.lockfile = TimestampedPidLockfile(self.options.locking_filename)
            lock_or_bork(self.lockfile, self.nagios_reporter)

    def epilogue(self, nagios_message, nagios_thresholds={}):
        """Run at the end of a script, quitting gracefully if possible."""

        if self.options.locking:
            release_or_bork(self.lockfile, self.nagios_reporter)

        nagios_thresholds['message'] = nagios_message
        self.nagios_reporter._eval_and_exit(**nagios_thresholds)
