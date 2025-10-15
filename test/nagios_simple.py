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
Tests for the NagiosResult class in the vsc.utils.nagios module

@author: Stijn De Weirdt (Ghent University)
"""
import logging
import os
import tempfile
import shutil
import sys
import stat
from pwd import getpwuid
from io import StringIO
from pathlib import PurePath

from vsc.install.testing import TestCase

from vsc.utils.nagios import SimpleNagios, NAGIOS_EXIT_OK, NAGIOS_EXIT_CRITICAL
from vsc.utils.nagios import NAGIOS_EXIT_WARNING, NAGIOS_EXIT_UNKNOWN, NagiosReporter
from vsc.utils.nagios import exit_from_errorcode


class TestSimpleNagios(TestCase):
    """Test for the SimpleNagios class."""

    def setUp(self):
        """redirect stdout"""
        self.old_stdout = sys.stdout
        self.buffo = StringIO()
        sys.stdout = self.buffo
        user = getpwuid(os.getuid())
        self.nagios_user = user.pw_name

    def tearDown(self):
        """Restore stdout"""
        self.buffo.close()
        sys.stdout = self.old_stdout

    def _basic_test_single_instance(self, kwargs, message, nagios_exit):
        """Basic test"""

        self.buffo.seek(0)
        self.buffo.truncate(0)

        raised_exception = None
        try:
            SimpleNagios(**kwargs)
        except SystemExit as err:
            raised_exception = err

        bo = self.buffo.getvalue().rstrip()

        self.assertEqual(bo, message)
        self.assertEqual(raised_exception.code, nagios_exit[0])

    def _basic_test_single_instance_and_exit(self, fn, msg, message, nagios_exit):
        """Basic test"""

        self.buffo.seek(0)
        self.buffo.truncate(0)

        nagios = SimpleNagios()
        func = getattr(nagios, fn)

        raised_exception = None
        try:
            func(msg)
        except SystemExit as err:
            raised_exception = err

        bo = self.buffo.getvalue().rstrip()

        self.assertEqual(bo, message)
        self.assertEqual(raised_exception.code, nagios_exit[0])

    def test_simple_single_instance(self):
        """Test what is generated when performance data is given, but not critical/warning"""
        kwargs = {
            'message': 'hello',
            'value1': 3,
            'value1_warning': 5,
            'value1_critical': 10,
        }
        self._basic_test_single_instance(kwargs, 'OK hello | value1=3;5;10;', NAGIOS_EXIT_OK)
        # outside warning range
        kwargs['value1'] = 5
        self._basic_test_single_instance(kwargs, 'OK hello | value1=5;5;10;', NAGIOS_EXIT_OK)
        # goutside warning range, perfdata with warning in message
        kwargs['value1'] = 7
        self._basic_test_single_instance(kwargs, 'WARNING value1, hello | value1=7;5;10;', NAGIOS_EXIT_WARNING)
        # outside critical range?
        kwargs['value1'] = 10
        self._basic_test_single_instance(kwargs, 'WARNING value1, hello | value1=10;5;10;', NAGIOS_EXIT_WARNING)
        # greater
        kwargs['value1'] = 15
        self._basic_test_single_instance(kwargs, 'CRITICAL value1, hello | value1=15;5;10;', NAGIOS_EXIT_CRITICAL)

        # mixed
        kwargsmore = {
            'value0': 3,
            'value0_warning': 5,
            'value0_critical': 10,
            'value2': 7,
            'value2_warning': 5,
            'value2_critical': 10,
        }
        kwargs.update(kwargsmore)

        # critical value in message
        self._basic_test_single_instance(kwargs, 'CRITICAL value1, hello | value0=3;5;10; value1=15;5;10; value2=7;5;10;',
                                         NAGIOS_EXIT_CRITICAL)

        # all warning values in message
        kwargs['value1'] = 7
        self._basic_test_single_instance(
            kwargs, 'WARNING value1, value2, hello | value0=3;5;10; value1=7;5;10; value2=7;5;10;', NAGIOS_EXIT_WARNING)

        # warning in message
        kwargs['value1'] = 5
        self._basic_test_single_instance(kwargs, 'WARNING value2, hello | value0=3;5;10; value1=5;5;10; value2=7;5;10;',
                                         NAGIOS_EXIT_WARNING)

        # no warning/critical; so regular message
        kwargs['value2'] = 5
        self._basic_test_single_instance(kwargs, 'OK hello | value0=3;5;10; value1=5;5;10; value2=5;5;10;',
                                         NAGIOS_EXIT_OK)


    def test_simple_nagios_instance_and_nagios_exit(self):
        """Test the basic ok/warning/critical/unknown"""
        self._basic_test_single_instance_and_exit('ok', 'hello', 'OK hello', NAGIOS_EXIT_OK)
        self._basic_test_single_instance_and_exit('warning', 'hello', 'WARNING hello', NAGIOS_EXIT_WARNING)
        self._basic_test_single_instance_and_exit('critical', 'hello', 'CRITICAL hello', NAGIOS_EXIT_CRITICAL)
        self._basic_test_single_instance_and_exit('unknown', 'hello', 'UNKNOWN hello', NAGIOS_EXIT_UNKNOWN)

    def test_cache(self):
        """Test the caching"""
        message = "huppeldepup a test string"

        threshold = None
        filename = PurePath(next(tempfile._get_candidate_names()))

        logging.info(f"Reporter using file {filename}")
        simple_nagios = SimpleNagios(_cache=filename, _cache_user=self.nagios_user)
        message = "mywarning"
        simple_nagios.warning(message)

        old_stdout = sys.stdout
        buffer = StringIO()
        sys.stdout = buffer

        reporter_test = NagiosReporter('test_cache', filename, threshold, self.nagios_user)
        try:
            reporter_test.report_and_exit()
        except SystemExit as err:
            line = buffer.getvalue().rstrip()
            logging.info("Retrieved buffer value: %s", line)
            logging.info("Retrieved exit code: %s", err.code)
            logging.info("Expected exit value: %s", (NAGIOS_EXIT_WARNING[0], NAGIOS_EXIT_WARNING[1]))
            self.assertTrue(err.code == 1)
            self.assertTrue(line == "%s %s" % ("WARNING", message))

        sys.stdout = old_stdout
        buffer.close()

        shutil.rmtree(filename)


    def test_world_readable(self):
        """Test world readable cache"""
        (handle, filename) = tempfile.mkstemp()
        os.unlink(filename)

        n = SimpleNagios(_cache=filename, _cache_user=self.nagios_user, _world_readable=True)
        n.ok("test")
        os.close(handle)

        try:
            reporter_test = NagiosReporter('test_cache', filename, -1, self.nagios_user)
            reporter_test.report_and_exit()
        except SystemExit:
            pass

        statres = os.stat(filename)

        self.assertTrue(statres.st_mode & stat.S_IROTH)


class TestNagiosExits(TestCase):
    """Test for all things exiting with nagios results."""

    def setUp(self):
        """redirect stdout"""
        self.old_stdout = sys.stdout
        self.buffo = StringIO()
        sys.stdout = self.buffo
        user = getpwuid(os.getuid())
        self.nagios_user = user.pw_name

    def tearDown(self):
        """Restore stdout"""
        self.buffo.close()
        sys.stdout = self.old_stdout

    def test_exit_from_errorcode(self):
        """test calling the correct exit function."""

        for (ec, expected) in [
                (0, NAGIOS_EXIT_OK),
                (1, NAGIOS_EXIT_WARNING),
                (2, NAGIOS_EXIT_CRITICAL),
                (3, NAGIOS_EXIT_UNKNOWN),
                (101, NAGIOS_EXIT_UNKNOWN),
                ]:
            try:
                exit_from_errorcode(ec, "boem")
            except SystemExit as err:
                print(err)
                self.assertTrue(err.code == expected[0])
