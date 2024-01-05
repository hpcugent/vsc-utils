#
# Copyright 2012-2024 Ghent University
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
import os
import tempfile
import time
import sys
import random
import string
from pwd import getpwuid
from io import StringIO

from vsc.install.testing import TestCase

from vsc.utils.nagios import NagiosReporter, SimpleNagios
from vsc.utils.nagios import NAGIOS_EXIT_OK, NAGIOS_EXIT_WARNING, NAGIOS_EXIT_CRITICAL, NAGIOS_EXIT_UNKNOWN


class TestNagios(TestCase):
    """Test for the nagios reporter class."""

    def setUp(self):
        user = getpwuid(os.getuid())
        self.nagios_user = user.pw_name
        super().setUp()

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
        length = random.randint(1, 30)
        exit_code = random.randint(0, 3)
        threshold = random.randint(0, 10)

        message = ''.join(random.choice(string.printable) for x in range(length))
        message = message.rstrip()

        (handle, filename) = tempfile.mkstemp()
        os.unlink(filename)
        os.close(handle)
        reporter = NagiosReporter('test_cache', filename, threshold, self.nagios_user)

        nagios_exit = [NAGIOS_EXIT_OK, NAGIOS_EXIT_WARNING, NAGIOS_EXIT_CRITICAL, NAGIOS_EXIT_UNKNOWN][exit_code]

        reporter.cache(nagios_exit, message)

        (handle, _) = tempfile.mkstemp()
        os.close(handle)

        old_stdout = sys.stdout
        try:
            buffer = StringIO()
            sys.stdout = buffer
            reporter_test = NagiosReporter('test_cache', filename, threshold, self.nagios_user)
            reporter_test.report_and_exit()
        except SystemExit as err:
            line = buffer.getvalue().rstrip()
            sys.stdout = old_stdout
            buffer.close()
            self.assertTrue(err.code == nagios_exit[0])
            self.assertTrue(line == f"{nagios_exit[1]} {message}")

        os.unlink(filename)

    def test_threshold(self, message="Hello"):
        """Test the threshold borking mechanism in the reporter."""
        message = message.rstrip()
        threshold = 1
        if message == '':
            return

        (handle, filename) = tempfile.mkstemp()
        os.unlink(filename)
        reporter = NagiosReporter('test_cache', filename, threshold, self.nagios_user)

        # redirect stdout
        old_stdout = sys.stdout
        buff = StringIO()
        sys.stdout = buff

        nagios_exit = NAGIOS_EXIT_OK
        reporter.cache(nagios_exit, message)
        os.close(handle)

        raised_exception = None
        try:
            reporter_test = NagiosReporter('test_cache', filename, threshold, self.nagios_user)
            reporter_test.report_and_exit()
        except SystemExit as err:
            raised_exception = err
        self.assertEqual(raised_exception.code, NAGIOS_EXIT_OK[0],
                         "Exit with status when the cached data is recent")
        # restore stdout
        buff.close()
        sys.stdout = old_stdout

        reporter = NagiosReporter('test_cache', filename, threshold, self.nagios_user)
        reporter.cache(nagios_exit, message)
        time.sleep(threshold + 1)
        # redirect stdout
        old_stdout = sys.stdout
        buff = StringIO()
        sys.stdout = buff

        raised_exception = None
        try:
            reporter_test = NagiosReporter('test_cache', filename, threshold, self.nagios_user)
            reporter_test.report_and_exit()
        except SystemExit as err:
            raised_exception = err

        line = buff.getvalue().rstrip()
        # restore stdout
        buff.close()
        sys.stdout = old_stdout
        self.assertEqual(raised_exception.code, NAGIOS_EXIT_UNKNOWN[0],
                         "Too old caches lead to unknown status")
        self.assertTrue(line.startswith(f"{NAGIOS_EXIT_UNKNOWN[1]} test_cache gzipped JSON file too old (timestamp ="))

        os.unlink(filename)
