# #
#
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
Tests for the NagiosResult class in the vsc.utils.nagios module

@author: Stijn De Weirdt (Ghent University)
"""
import os
import tempfile
import StringIO
import sys

from unittest import TestCase, TestLoader

from vsc.utils.nagios import SimpleNagios, NAGIOS_EXIT_OK, NAGIOS_EXIT_CRITICAL
from vsc.utils.nagios import NAGIOS_EXIT_WARNING, NAGIOS_EXIT_UNKNOWN, NagiosReporter
from pwd import getpwuid


class TestSimpleNagios(TestCase):
    """Test for the SimpleNagios class."""

    def setUp(self):
        """redirect stdout"""
        self.old_stdout = sys.stdout
        self.buffo = StringIO.StringIO()
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

        try:
            SimpleNagios(**kwargs)
        except SystemExit, e:
            pass
        bo = self.buffo.getvalue().rstrip()

        self.assertEqual(bo, message)
        self.assertEqual(e.code, nagios_exit[0])

    def _basic_test_single_instance_and_exit(self, fn, msg, message, nagios_exit):
        """Basic test"""

        self.buffo.seek(0)
        self.buffo.truncate(0)

        n = SimpleNagios()
        f = getattr(n, fn)
        try:
            f(msg)
        except SystemExit, e:
            pass
        bo = self.buffo.getvalue().rstrip()

        self.assertEqual(bo, message)
        self.assertEqual(e.code, nagios_exit[0])

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
        self._basic_test_single_instance(kwargs, 'WARNING value1 | value1=7;5;10;', NAGIOS_EXIT_WARNING)
        # outside critical range?
        kwargs['value1'] = 10
        self._basic_test_single_instance(kwargs, 'WARNING value1 | value1=10;5;10;', NAGIOS_EXIT_WARNING)
        # greater
        kwargs['value1'] = 15
        self._basic_test_single_instance(kwargs, 'CRITICAL value1 | value1=15;5;10;', NAGIOS_EXIT_CRITICAL)

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
        self._basic_test_single_instance(kwargs, 'CRITICAL value1 | value0=3;5;10; value1=15;5;10; value2=7;5;10;',
                                         NAGIOS_EXIT_CRITICAL)

        # all warning values in message
        kwargs['value1'] = 7
        self._basic_test_single_instance(kwargs, 'WARNING value1, value2 | value0=3;5;10; value1=7;5;10; value2=7;5;10;',
                                         NAGIOS_EXIT_WARNING)

        # warning in message
        kwargs['value1'] = 5
        self._basic_test_single_instance(kwargs, 'WARNING value2 | value0=3;5;10; value1=5;5;10; value2=7;5;10;',
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
        (handle, filename) = tempfile.mkstemp()
        os.unlink(filename)

        n = SimpleNagios(_cache=filename, _cache_user=self.nagios_user)
        message = "mywarning"
        n.warning(message)
        os.close(handle)

        self.buffo.seek(0)
        self.buffo.truncate(0)

        try:
            reporter_test = NagiosReporter('test_cache', filename, -1, self.nagios_user)
            reporter_test.report_and_exit()
        except SystemExit, e:
            pass
        bo = self.buffo.getvalue().rstrip()

        self.assertEqual(bo, "WARNING %s" % message)
        self.assertEqual(e.code, NAGIOS_EXIT_WARNING[0])

        os.unlink(filename)


def suite():
    """ return all the tests"""
    return TestLoader().loadTestsFromTestCase(TestSimpleNagios)
