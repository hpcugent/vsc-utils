#
# Copyright 2016-2020 Ghent University
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
Tests for the classes and functions in vsc.utils.scrip_tools

@author: Andy Georges
"""
import mock
import logging
import random
import sys

from vsc.install.testing import TestCase
from vsc.utils.script_tools import ExtendedSimpleOption, DEFAULT_OPTIONS, CLI


class TestExtendedSimpleOption(TestCase):
    """
    Tests for the ExtendedSimpleOption class.
    """
    def setUp(self):
        """Backup sys.argv"""
        super(TestCase, self).setUp()
        # make a copy of sys.argv
        self._old_argv = sys.argv[:]
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
        self.assertEqual(opts.nagios_reporter._cache_user, 'nagios')
        self.assertEqual(opts.options.nagios_user, 'nagios')
        self.assertFalse(opts.nagios_reporter._world_readable)
        self.assertFalse(opts.options.nagios_world_readable_check)

    @mock.patch('vsc.utils.script_tools.TimestampedPidLockfile')
    @mock.patch('vsc.utils.script_tools.lock_or_bork')
    @mock.patch('vsc.utils.script_tools.proceed_on_ha_service')
    def test_threshold_custom_setting(self, mock_proceed, mock_lock, mock_lockfile):
        """Test if a custom value is passed on correctly"""
        mock_proceed.return_value = True
        mock_lockfile.return_value = mock.MagicMock()

        threshold = random.uniform(1, 1000)

        opts = ExtendedSimpleOption({'nagios-check-interval-threshold': threshold,
                                     'nagios-user': 'nrpe',
                                     'nagios-world-readable-check': True})
        self.assertEqual(opts.options.nagios_check_interval_threshold, threshold)
        self.assertEqual(opts.options.nagios_user, 'nrpe')
        self.assertEqual(opts.nagios_reporter._cache_user, 'nrpe')
        self.assertTrue(opts.nagios_reporter._world_readable)
        self.assertTrue(opts.options.nagios_world_readable_check)


magic = mock.MagicMock(name='magic')

class MyCLI(CLI):
    TIMESTAMP_MANDATORY = False  # mainly for testing, you really should need this in production
    CLI_OPTIONS = {
        'magic': ('some magic', None, 'store', 'magicdef'),
    }
    def do(self, dry_run):
        return magic.go()


class TestCLI(TestCase):
    """Tests for the CLI base class"""

    @mock.patch('vsc.utils.script_tools.ExtendedSimpleOption.prologue')
    def test_opts(self, prol):
        sys.argv = ['abc']
        ms = MyCLI()

        logging.debug("options %s %s %s", ms.options, dir(ms.options), vars(ms.options))

        extsimpopts = {
            'configfiles': None,
            'debug': False,
            'disable_locking': False,
            'dry_run': False,
            'ha': None,
            'help': None,
            'ignoreconfigfiles': None,
            'info': False,
            'locking_filename': '/var/lock/setup.lock',
            'nagios_check_filename': '/var/cache/setup.nagios.json.gz',
            'nagios_check_interval_threshold': 0,
            'nagios_report': False,
            'nagios_user': 'nagios',
            'nagios_world_readable_check': False,
            'quiet': False,
        }

        myopts = {
            'magic': 'magicdef',
            'start_timestamp': None,
            'timestamp_file': '/var/cache/abc.timestamp',
        }
        myopts.update(extsimpopts)
        self.assertEqual(ms.options.__dict__, myopts)

        myopts = {
            'magic': 'magicdef',
        }
        myopts.update(extsimpopts)
        ms = MyCLI(default_options={})
        logging.debug("options wo default sync options %s", ms.options)
        self.assertEqual(ms.options.__dict__, myopts)

