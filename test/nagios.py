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
Tests for the vsc.utils.nagios module.

@author: Andy Georges (Ghent University)
"""
import logging
import os
import tempfile
import time
import sys
import random
import shutil
import string
import tempfile
from pwd import getpwuid
from io import StringIO

from pathlib import PurePath
from vsc.install.testing import TestCase

from vsc.utils.nagios import NagiosReporter, SimpleNagios
from vsc.utils.nagios import NAGIOS_EXIT_OK, NAGIOS_EXIT_WARNING, NAGIOS_EXIT_CRITICAL, NAGIOS_EXIT_UNKNOWN


class TestNagios(TestCase):
    """Test for the nagios reporter class."""

    def setUp(self):
        user = getpwuid(os.getuid())
        self.nagios_user = user.pw_name
        super(TestNagios, self).setUp()

    def test_eval(self):
        """Test the evaluation of the warning/critical level."""

        nagios = SimpleNagios(
            foo=100,
            foo_critical=90,
            bar=20,
        )

        nagios._eval()

    def test_cache(self):
        """Test the caching mechanism in the reporter."""
        message = "huppeldepup a test string"

        threshold = None
        filename = PurePath(next(tempfile._get_candidate_names()))

        logging.info(f"Reporter using file {filename}")
        reporter = NagiosReporter('test_cache', filename, threshold, self.nagios_user)

        for exit_code in range(0, 4):

            nagios_exit = [NAGIOS_EXIT_OK, NAGIOS_EXIT_WARNING, NAGIOS_EXIT_CRITICAL, NAGIOS_EXIT_UNKNOWN][exit_code]
            logging.info("Caching the exit: %s", nagios_exit)
            reporter.cache(nagios_exit, message)

            old_stdout = sys.stdout
            buffer = StringIO()
            sys.stdout = buffer

            try:
                reporter_test = NagiosReporter('test_cache', filename, threshold, self.nagios_user)
                reporter_test.report_and_exit()
            except SystemExit as err:
                line = buffer.getvalue().rstrip()
                logging.info("Retrieved buffer value: %s", line)
                logging.info("Retrieved exit code: %s", err.code)
                logging.info("Expected exit value: %s", nagios_exit)
                self.assertTrue(err.code == exit_code)
                self.assertTrue(line == "%s %s" % (nagios_exit[1], message))

            sys.stdout = old_stdout
            buffer.close()

        shutil.rmtree(filename)

    def test_threshold(self, message="Hello"):
        """Test the threshold borking mechanism in the reporter."""
        message = message.rstrip()
        threshold = 2
        if message == '':
            return

        filename = PurePath(next(tempfile._get_candidate_names()))
        reporter = NagiosReporter('test_cache', filename, threshold, self.nagios_user)

        # redirect stdout
        old_stdout = sys.stdout
        buff = StringIO()
        sys.stdout = buff

        nagios_exit = NAGIOS_EXIT_OK
        reporter.cache(nagios_exit, message)

        raised_exception = None
        reporter_test = NagiosReporter('test_cache', filename, threshold, self.nagios_user)
        try:
            reporter_test.report_and_exit()
        except SystemExit as err:
            raised_exception = err
        self.assertEqual(raised_exception.code, NAGIOS_EXIT_OK[0],
                         "Exit with status when the cached data is recent")
        # restore stdout
        buff.close()

        time.sleep(threshold + 1)
        buff = StringIO()
        sys.stdout = buff
        raised_exception = None
        reporter_test = NagiosReporter('test_cache', filename, threshold, self.nagios_user)
        try:
            reporter_test.report_and_exit()
        except SystemExit as err:
            raised_exception = err

        line = buff.getvalue().rstrip()
        # restore stdout
        buff.close()
        sys.stdout = old_stdout
        self.assertEqual(raised_exception.code, NAGIOS_EXIT_UNKNOWN[0],
                         "Too old caches lead to unknown status")
        self.assertTrue(line.startswith("%s test_cache nagios exit info expired" % (NAGIOS_EXIT_UNKNOWN[1])))

        shutil.rmtree(filename)

