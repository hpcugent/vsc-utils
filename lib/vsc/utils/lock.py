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
Utilities for locks.

@author Andy Georges (Ghent University)
"""
import sys

from lockfile import LockFailed, NotLocked, NotMyLock, LockError
from vsc.utils.fancylogger import getLogger
from vsc.utils.nagios import NAGIOS_EXIT_CRITICAL

logger = getLogger('vsc.utils.lock')

LOCKFILE_DIR = '/var/lock'
LOCKFILE_FILENAME_TEMPLATE = "%s.lock"


def lock_or_bork(lockfile, simple_nagios):
    """Take the lock on the given lockfile.

    @type lockfile: A LockFile instance
    @type simple_nagios: SimpleNagios instance

    If the lock cannot be obtained:
        - log a critical error
        - store a critical failure in the nagios cache file
        - exit the script
    """
    try:
        lockfile.acquire()
    except LockFailed:
        logger.critical('Unable to obtain lock: lock failed')
        simple_nagios.critical("failed to take lock on %s" % (lockfile.path,))
        sys.exit(NAGIOS_EXIT_CRITICAL)
    except LockError:
        logger.critical("Unable to obtain lock: could not read previous lock file %s" % (lockfile.path,))
        simple_nagios.critical("failed to read lockfile %s" % (lockfile.path,))
        sys.exit(NAGIOS_EXIT_CRITICAL)


def release_or_bork(lockfile, simple_nagios):
    """ Release the lock on the given lockfile.

    @type lockfile: A LockFile instance
    @type simple_nagios: SimpleNagios instance

    If the lock cannot be released:
        - log a critcal error
        - store a critical failure in the nagios cache file
        - exit the script
    """

    try:
        lockfile.release()
    except NotLocked:
        logger.critical('Lock release failed: was not locked.')
        simple_nagios.critical("Lock release failed on %s" % (lockfile.path,))
        sys.exit(NAGIOS_EXIT_CRITICAL)
    except NotMyLock:
        logger.error('Lock release failed: not my lock')
        simple_nagios.critical("Lock release failed on %s" % (lockfile.path,))
        sys.exit(NAGIOS_EXIT_CRITICAL)
