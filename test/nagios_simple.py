#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# #
#
# Copyright 2012-2013 Ghent University
#
# This file is part of vsc-base,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://vscentrum.be/nl/en),
# the Hercules foundation (http://www.herculesstichting.be/in_English)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# http://github.com/hpcugent/vsc-base
#
# vsc-base is free software: you can redistribute it and/or modify
# it under the terms of the GNU Library General Public License as
# published by the Free Software Foundation, either version 2 of
# the License, or (at your option) any later version.
#
# vsc-base is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU Library General Public License
# along with vsc-base. If not, see <http://www.gnu.org/licenses/>.
# #
"""
Tests for the NagiosResult class in the vsc.utils.nagios module

@author: Stijn De Weirdt (Ghent University)
"""
import os
import tempfile
import time
import StringIO
import sys

from unittest import TestCase, TestLoader, main

from vsc.utils.nagios import SimpleNagios, NAGIOS_EXIT_OK, NAGIOS_EXIT_CRITICAL
from vsc.utils.nagios import NAGIOS_EXIT_WARNING, NAGIOS_EXIT_UNKNOWN


class TestSimpleNagios(TestCase):
    """Test for the SimpleNagios class."""

    def _basic_test_single_instance(self, kwargs, message, nagios_exit):
        """Basic test"""
        # redirect stdout
        old_stdout = sys.stdout
        buffo = StringIO.StringIO()
        sys.stdout = buffo

        try:
            SimpleNagios(**kwargs)
        except SystemExit, e:
            pass
        bo = buffo.getvalue().rstrip()

        # restore stdout
        buffo.close()
        sys.stdout = old_stdout

        self.assertEqual(bo, message)
        self.assertEqual(e.code, nagios_exit[0])

    def _basic_test_single_instance_and_exit(self, fn, msg, message, nagios_exit):
        """Basic test"""
        # redirect stdout
        old_stdout = sys.stdout
        buffo = StringIO.StringIO()
        sys.stdout = buffo

        n = SimpleNagios()
        f = getattr(n, fn)
        try:
            f(msg)
        except SystemExit, e:
            pass
        bo = buffo.getvalue().rstrip()

        # restore stdout
        buffo.close()
        sys.stdout = old_stdout

        self.assertEqual(bo, message)
        self.assertEqual(e.code, nagios_exit[0])

    def test_simple_single_instance(self):
        """Test what is generated when performance data is given, but not critical/warning"""
        kwargs = {
                'message':'hello',
                'value1':3,
                'value1_warning':5,
                'value1_critical':10,
                }
        self._basic_test_single_instance(kwargs, 'OK hello | value1=3;5;10;', NAGIOS_EXIT_OK)
        # greater or equal
        kwargs['value1'] = 5
        self._basic_test_single_instance(kwargs, 'WARNING hello | value1=5;5;10;', NAGIOS_EXIT_WARNING)
        # greater
        kwargs['value1'] = 7
        self._basic_test_single_instance(kwargs, 'WARNING hello | value1=7;5;10;', NAGIOS_EXIT_WARNING)
        # greater or equal
        kwargs['value1'] = 10
        self._basic_test_single_instance(kwargs, 'CRITICAL hello | value1=10;5;10;', NAGIOS_EXIT_CRITICAL)
        # greater
        kwargs['value1'] = 15
        self._basic_test_single_instance(kwargs, 'CRITICAL hello | value1=15;5;10;', NAGIOS_EXIT_CRITICAL)

        # mixed
        kwargsmore = {
                'value0':3,
                'value0_warning':5,
                'value0_critical':10,
                'value2':7,
                'value2_warning':5,
                'value2_critical':10,
                }
        kwargs.update(kwargsmore)
        self._basic_test_single_instance(kwargs, 'CRITICAL hello | value0=3;5;10; value1=15;5;10; value2=7;5;10;',
                                         NAGIOS_EXIT_CRITICAL)

    def test_simple_nagios_instance_and_nagios_exit(self):
        """Test the basic ok/warning/critical/unknown"""
        self._basic_test_single_instance_and_exit('ok', 'hello', 'OK hello', NAGIOS_EXIT_OK)
        self._basic_test_single_instance_and_exit('warning', 'hello', 'WARNING hello', NAGIOS_EXIT_WARNING)
        self._basic_test_single_instance_and_exit('critical', 'hello', 'CRITICAL hello', NAGIOS_EXIT_CRITICAL)
        self._basic_test_single_instance_and_exit('unknown', 'hello', 'UNKNOWN hello', NAGIOS_EXIT_UNKNOWN)


def suite():
    """ return all the tests"""
    return TestLoader().loadTestsFromTestCase(TestSimpleNagios)


if __name__ == '__main__':
    main()  # unittest.main
