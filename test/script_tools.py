# #
#
# Copyright 2016-2016 Ghent University
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
Tests for the classes and functions in vsc.utils.scrip_tools

@author: Andy Georges
"""
import mock
import random
import sys

from vsc.install.testing import TestCase
from vsc.utils.script_tools import ExtendedSimpleOption, DEFAULT_OPTIONS


class TestExtendedSimpleOption(TestCase):
    """
    Tests for the ExtendedSimpleOption class.
    """
    def setUp(self):
        """Backup sys.argv"""
        super(TestCase, self).setUp()
        self._old_argv = sys.argv
        sys.argv = sys.argv[:1]

    def tearDown(self):
        """restore sys.argv"""
        super(TestCase, self).tearDown()
        sys.argv = self._old_argv

    @mock.patch('vsc.utils.script_tools.TimestampedPidLockfile')
    @mock.patch('vsc.utils.script_tools.lock_or_bork')
    @mock.patch('vsc.utils.script_tools.proceed_on_ha_service')
    def test_threshold_default_setting(self, mock_proceed, mock_lock, mock_lockfile):
        """Test if the default value is set"""
        mock_proceed.return_value = True
        mock_lockfile.return_value = mock.MagicMock()

        opts = ExtendedSimpleOption(options={})
        self.assertEqual(opts.options.nagios_check_interval_threshold,
                         DEFAULT_OPTIONS['nagios-check-interval-threshold'][3])
        self.assertEqual(opts.nagios_reporter._threshold,
                         DEFAULT_OPTIONS['nagios-check-interval-threshold'][3])

    @mock.patch('vsc.utils.script_tools.TimestampedPidLockfile')
    @mock.patch('vsc.utils.script_tools.lock_or_bork')
    @mock.patch('vsc.utils.script_tools.proceed_on_ha_service')
    def test_threshold_custom_setting(self, mock_proceed, mock_lock, mock_lockfile):
        """Test if a custom value is passed on correctly"""
        mock_proceed.return_value = True
        mock_lockfile.return_value = mock.MagicMock()

        threshold = random.uniform(1, 1000)

        opts = ExtendedSimpleOption({'nagios-check-interval-threshold': threshold})
        self.assertEqual(opts.options.nagios_check_interval_threshold, threshold)
