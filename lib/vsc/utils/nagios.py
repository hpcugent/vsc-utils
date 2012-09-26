#!/usr/bin/env python
##
#
# Copyright 2012 Andy Georges
#
# This file is part of the tools originally by the HPC team of
# Ghent University (http://ugent.be/hpc).
#
# This is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation v2.
"""
This file contains functions to print out nagios messages and bail.

@author Andy Georges

@created May 22, 2012
"""

__author__ = 'ageorges'
__date__ = 'May 8, 2012'

import cPickle
import os
import pwd
import stat
import sys
import time


import vsc.fancylogger as fancylogger

nagios_exits = {
    'ok':0,
    'warning': 1,
    'critical': 2,
    'unknown': 3,
}

logger = fancylogger.getLogger(__name__)

def ok_exit(message):
    print "OK %s" % (message)
    logger.info("Nagios OK: %s" % message)
    sys.exit(nagios_exits['ok'])


def warning_exit(message):
    print "WARNING %s" % (message)
    logger.info("Nagios WARNING: %s" % message)
    sys.exit(nagios_exits['warning'])


def unknown_exit(message):
    print "UNKNOWN %s" % (message)
    logger.info("Nagios UNKNOWN: %s" % message)
    sys.exit(nagios_exits['unknown'])


def critical_exit(message):
    print "CRITICAL %s" % (message)
    logger.info("Nagios CRITICAL: %s" % message)
    sys.exit(nagios_exits['critical'])


class NagiosReporter(object):
    NAGIOS_EXIT_OK = 0
    NAGIOS_EXIT_WARNING = 1
    NAGIOS_EXIT_CRITICAL = 2
    NAGIOS_EXIT_UNKNOWN = 3

    def __init__(self, header, filename, threshold):
        ## Constants

        self.header = header
        self.filename = filename
        self.threshold = threshold

        self.logger = fancylogger.getLogger(self.__class__.__name__)

    def report_and_exit(self):
        ## unpickle the nagios check cache
        ## if older than 30 minutes, then produce a CRITICAL message
        try:
            f = open(self.filename, 'r')
        except Exception, err:
            self.logger.critical("cannot open nagios pickled file %s for reading [%s]" % (self.filename, err))
            print "UNKNOWN %s: pickled file unavailable (%s)" % (self.header, self.filename)
            sys.exit(self.__class__.NAGIOS_EXIT_UNKNOWN)

        (timestamp, nagios_exit_code, nagios_message) = cPickle.load(f)
        if time.time() - timestamp < self.threshold:
            self.logger.info("Nagios check cache file %s contents delivered: %s" % (self.filename, nagios_message))
            print "%s" % (nagios_message)
            sys.exit(nagios_exit_code)
        else:
            self.logger.critical("Nagios check cache file %s contents older than threshold - cache file timestamp = %s" % (self.filename, time.ctime(timestamp)))
            print "UNKNOWN %s: pickled file too old (timestamp = %s)" % (self.header, time.ctime(timestamp))
            sys.exit(self.__class__.NAGIOS_EXIT_UNKNOWN)

    def cache(self, nagios_exit_code, nagios_message):
        ## pickle result to the nagios check cache
        f = open(self.filename, 'w')
        if not f:
            self.logger.critical("cannot open the nagios pickled file %s for writing" % (self.filename))
            return False
        else:
            t = time.time()
            cPickle.dump((t, nagios_exit_code, nagios_message), f)
            f.close()
            self.logger.info("wrote nagios check cache file %s at %s" % (self.filename, time.ctime(t)))
            try:
                p = pwd.getpwnam("nagios")
                os.chmod(self.filename, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP)
                os.chown(self.filename, p.pw_uid, p.pw_gid)
            except Exception, err:
                self.logger.error("cannot chown of the nagios check file %s to the nagios user" % (self.filename))
        return True