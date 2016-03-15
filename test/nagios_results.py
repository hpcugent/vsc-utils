# encoding: utf-8
#
# Copyright 2012-2016 Ghent University
#
# This file is part of vsc-utils,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://vscentrum.be/nl/en),
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

@author: Luis Fernando Muñoz Mejías (Ghent University)
"""
from vsc.install.testing import TestCase

from vsc.utils.nagios import NagiosResult, NagiosRange


class TestNagiosResult(TestCase):
    """Test for the nagios result class."""

    def test_no_perfdata(self):
        """Test what is generated when no performance data is given"""
        n = NagiosResult('hello')
        self.assertEqual(n.message, 'hello', 'Class correctly filled in')
        self.assertEqual(len(n.__dict__.keys()), 1, 'Nothing gets added with no performance data')
        self.assertEqual(n.__str__(), n.message, 'Correct stringification with no performance data')

    def test_perfdata_no_thresholds(self):
        """Test what is generated when performance data with no thresholds is given"""
        n = NagiosResult('hello', a_metric=1)
        self.assertEqual(n.message, 'hello', 'Class message correctly filled in')
        self.assertEqual(n.a_metric, 1, "Performance data correctly filled in")
        self.assertEqual(len(n.__dict__.keys()), 2, "No extra fields added")
        self.assertEqual(n.__str__(), 'hello | a_metric=1;;;',
                         'Performance data with no thresholds correctly stringified')

    def test_perfdata_with_thresholds(self):
        """Test what is generated when performance AND thresholds are given"""
        n = NagiosResult('hello', a_metric=1, a_metric_critical=2)
        self.assertEqual(n.a_metric_critical, 2, "Threshold for a perfdata is a normal key")
        self.assertEqual(len(n.__dict__.keys()), 3, "All keys correctly stored in the object")
        self.assertTrue(n.__str__().endswith('a_metric=1;;2;'),
                        "Critical threshold in correct position")
        n.a_metric_warning = 5
        self.assertTrue(n.__str__().endswith('a_metric=1;5;2;'),
                        "Warning threshold in correct position")

    def test_nagios_range(self):
        """Test the nagios range parser"""
        # using the example range from  https://www.nagios-plugins.org/doc/guidelines.html#AEN200

        # end only: alert if < 0 or > 10, (outside the range of {0 .. 10})
        n = NagiosRange("10")
        self.assertTrue(n.alert(11))
        self.assertTrue(n.alert(-1))
        # strict
        self.assertFalse(n.alert(10))
        self.assertFalse(n.alert(0))
        self.assertFalse(n.alert(2))

        # allow int as end with no start string
        n = NagiosRange(10)
        self.assertTrue(n.alert(11))
        self.assertTrue(n.alert(-1))
        self.assertFalse(n.alert(2))

        # start only: alert if  < 10, (outside {10 .. +inf})
        n = NagiosRange("10:")
        self.assertTrue(n.alert(9))
        self.assertTrue(n.alert(-20))
        # strict
        self.assertFalse(n.alert(10))
        self.assertFalse(n.alert(11))

        # alert if > 10, (outside the range of {-∞ .. 10})
        n = NagiosRange("~:10")
        self.assertTrue(n.alert(11))
        # strict
        self.assertFalse(n.alert(10))
        self.assertFalse(n.alert(-100))

        # alert if < 10 or > 20, (outside the range of {10 .. 20})
        n = NagiosRange("10:20")
        self.assertTrue(n.alert(9))
        self.assertTrue(n.alert(21))
        # strict
        self.assertFalse(n.alert(10))
        self.assertFalse(n.alert(15))
        self.assertFalse(n.alert(20))

        # alert if >= 10 and <= 20, (inside the range of {10 .. 20})
        n = NagiosRange("@10:20")
        self.assertTrue(n.alert(10))
        self.assertTrue(n.alert(15))
        self.assertTrue(n.alert(20))
        # strict
        self.assertFalse(n.alert(9))
        self.assertFalse(n.alert(21))
