#!/usr/bin/python
##
#
# Copyright 2009-2011 Ghent University
#
# This file is part of the tools originally by the HPC team of
# Ghent University (http://ugent.be/hpc).
#
# This is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation v2.
##
"""Utilities for locks."""
import sys

from lockfile import LockFailed, NotLocked, NotMyLock, LockFileReadError
from vsc.utils.fancylogger import getLogger

logger = getLogger('vsc.utils.lock')


def lock_or_bork(lockfile, nagios_reporter):
    """Take the lock on the given lockfile.

    @type lockfile: A LockFile instance
    @type nagios_reporter: SimpleNagios instance

    If the lock cannot be obtained:
        - log a critical error
        - store a critical failure in the nagios cache file
        - exit the script
    """
    try:
        lockfile.acquire()
    except LockFailed, _:
        logger.critical('Unable to obtain lock: lock failed')
        nagios_reporter.critical("failed to take lock on %s" % (lockfile.path,))
    except LockFileReadError, _:
        logger.critical("Unable to obtain lock: could not read previous lock file %s" % (lockfile.path,))
        nagios_reporter.critical("failed to read lockfile %s" % (lockfile.path,))
        sys.exit(1)


def release_or_bork(lockfile, nagios_reporter):
    """ Release the lock on the given lockfile.

    @type lockfile: A LockFile instance
    @type nagios_reporter: SimpleNagios instance

    If the lock cannot be released:
        - log a critcal error
        - store a critical failure in the nagios cache file
        - exit the script
    """

    try:
        lockfile.release()
    except NotLocked, err:
        logger.critical('Lock release failed: was not locked.')
        nagios_reporter.critical("Lock release failed on %s" % (lockfile.path,))
    except NotMyLock, err:
        logger.error('Lock release failed: not my lock')
        nagios_reporter.critical("Lock release failed on %s" % (lockfile.path,))


