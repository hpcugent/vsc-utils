#
# Copyright 2016-2024 Ghent University
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

import logging
import random
import sys
import tempfile
import getpass
import mock

from mock import MagicMock, patch
from vsc.install.testing import TestCase

from vsc.install.testing import TestCase
from vsc.utils.nagios import NAGIOS_EXIT_WARNING, NagiosStatusMixin
from vsc.utils.script_tools import (
    ExtendedSimpleOption, DEFAULT_OPTIONS, NrpeCLI, CLI,
    CLIBase, LockMixin, HAMixin, TimestampMixin)


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
    def test_threshold_default_setting(self, mock_proceed, _, mock_lockfile):
        """Test if the default value is set"""
        mock_proceed.return_value = True
        mock_lockfile.return_value = mock.MagicMock()

        opts = ExtendedSimpleOption(options={})
        self.assertEqual(opts.options.nagios_check_interval_threshold,
                         DEFAULT_OPTIONS['nagios-check-interval-threshold'][3])
        self.assertEqual(opts.nagios_reporter._threshold,
                         DEFAULT_OPTIONS['nagios-check-interval-threshold'][3])
        self.assertEqual(opts.nagios_reporter._cache_user, 'nrpe')
        self.assertEqual(opts.options.nagios_user, 'nrpe')
        self.assertFalse(opts.nagios_reporter._world_readable)
        self.assertFalse(opts.options.nagios_world_readable_check)

    @mock.patch('vsc.utils.script_tools.TimestampedPidLockfile')
    @mock.patch('vsc.utils.script_tools.lock_or_bork')
    @mock.patch('vsc.utils.script_tools.proceed_on_ha_service')
    def test_threshold_custom_setting(self, mock_proceed, _, mock_lockfile):
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

class MyNrpeCLI(NrpeCLI):
    TIMESTAMP_MANDATORY = False  # mainly for testing, you really should need this in production
    CLI_OPTIONS = {
        'magic': ('some magic', None, 'store', 'magicdef'),
    }
    def do(self,dryrun):
        return magic.go()


class MyCLI(CLI):
    TIMESTAMP_MANDATORY = False  # mainly for testing, you really should need this in production
    TESTFILE = tempfile.mkstemp()[1]
    TESTFILE2 = tempfile.mkstemp()[1]

    CLI_OPTIONS = {
        'magic': ('some magic', None, 'store', 'magicdef'),
        'nagios_check_filename': ('bla', None, 'store', TESTFILE),
        'locking_filename': ('test', None, 'store', TESTFILE2),
        'nagios_user': ('user nagios runs as', 'str', 'store', getpass.getuser()),
    }
    def do(self, _):
        return magic.go()

class TestNrpeCLI(TestCase):
    """Tests for the CLI base class"""

    @mock.patch('vsc.utils.script_tools.ExtendedSimpleOption.prologue')
    def test_opts(self, _):
        sys.argv = ['abc']
        ms = MyNrpeCLI()

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
            'nagios_user': 'nrpe',
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
        ms = MyNrpeCLI(default_options={})
        logging.debug("options wo default sync options %s", ms.options)
        self.assertEqual(ms.options.__dict__, myopts)

    @mock.patch('vsc.utils.script_tools.ExtendedSimpleOption.prologue')
    def test_exit(self, _):

        self.original_argv = sys.argv
        sys.argv = ["somecli"]

        cli = MyNrpeCLI()

        fake_exit = mock.MagicMock()
        with mock.patch('vsc.utils.nagios._real_exit', fake_exit):
            cli.warning("be warned")
            fake_exit.assert_called_with("be warned", NAGIOS_EXIT_WARNING)


class TestCLI(TestCase):
    """Tests for the CLI base class"""

    @mock.patch('vsc.utils.script_tools.ExtendedSimpleOption.prologue')
    def test_opts(self, _):
        sys.argv = ['abc']
        ms = MyCLI(name="MyCLI")

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
            'locking_filename': ms.TESTFILE2,
            'nagios_check_filename': ms.TESTFILE,
            'nagios_check_interval_threshold': 0,
            'nagios_report': False,
            'nagios_user': getpass.getuser(),
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
        ms = MyCLI(name="mycli", default_options={})
        logging.debug("options wo default sync options %s", ms.options)
        self.assertEqual(ms.options.__dict__, myopts)

    @mock.patch('vsc.utils.script_tools.lock_or_bork')
    @mock.patch('vsc.utils.script_tools.release_or_bork')
    def test_exit(self, locklock, releaselock):
        original_argv = sys.argv
        sys.argv = ["mycli"]

        cli = MyCLI(
            name="MyCLI",
        )

        fake_exit = mock.MagicMock()
        with mock.patch('vsc.utils.script_tools.sys.exit', fake_exit):
            cli.warning("be warned")
            fake_exit.assert_called_with(1)


class TestCLIBase(TestCase):
    def setUp(self):
        """
        Set up mock instances and common configurations.
        """
        super().setUp()

        # Redirect stdout/stderr to prevent TestCase conflicts
        self.orig_sys_stdout = sys.stdout
        self.orig_sys_stderr = sys.stderr
        sys.stdout = MagicMock()
        sys.stderr = MagicMock()

        self.original_argv = sys.argv
        sys.argv = ["somecli"]

        # Create a dummy subclass of CLIBase for testing
        class TestCLI(CLIBase):
            CLI_OPTIONS = {
                'test-option': ('Test description', None, 'store_true', False),
            }

            def do(self, dryrun=False):
                if dryrun:
                    return ["Dry run mode active."]
                return []

        self.cli = TestCLI(name="Test CLI")

    @patch('vsc.utils.script_tools.ArgParser.parse_args', return_value=MagicMock(dry_run=False))
    @patch('vsc.utils.script_tools.logging.info')
    def test_main_basic(self, mock_logging_info, mock_parse_args):
        """
        Test the main method without any mixins.
        """
        self.cli.main()
        self.assertEqual(self.cli.name, "Test CLI")
        #mock_logging_info.assert_any_call("Test CLI started.")

    def test_get_options(self):
        """
        Test the get_options method aggregates CLI options.
        """
        options = self.cli.get_options()
        self.assertIn('test-option', options)

    @patch('vsc.utils.script_tools.logging.error')
    @patch('vsc.utils.script_tools.sys.exit')
    def test_critical_no_nagios(self, mock_sys_exit, mock_logging_error):
        """
        Test critical method behavior without NagiosStatusMixin.
        """
        self.cli.critical("Critical error")
        mock_logging_error.assert_called_with("Critical error")
        mock_sys_exit.assert_called_with(1)

    @patch('vsc.utils.script_tools.logging.info')
    @patch('vsc.utils.script_tools.ArgParser.parse_args', return_value=MagicMock(dry_run=False))
    def test_main_with_dry_run(self, mock_parse_args, mock_logging_info):
        """
        Test the main method in dry-run mode.
        """
        self.cli.main()
        #mock_logging_info.assert_any_call("Test CLI (dry-run) started.")

    @patch('vsc.utils.script_tools.logging.info')
    @patch('vsc.utils.script_tools.ArgParser.parse_args', return_value=MagicMock(dry_run=False))
    def test_main_with_mixins(self, mock_parse_args, mock_logging_info):
        """
        Test the main method with mixins applied.
        """
        # Extend TestCLI with mixins
        class TestCLIMixins(CLIBase, NagiosStatusMixin, LockMixin):
            CLI_OPTIONS = {'test-mixin-option': ('Mixin test description', None, 'store_true', False)}

            def do(self, dryrun=False):
                return []

            def nagios_prologue(self):
                self.nagios_prologue_called = True

            def lock_prologue(self):
                self.lock_prologue_called = True

            def nagios_epilogue(self):
                self.nagios_epilogue_called = True

            def lock_epilogue(self):
                self.lock_epilogue_called = True

        cli = TestCLIMixins(name="Test CLI with Mixins")
        cli.nagios_prologue_called = False
        cli.lock_prologue_called = False
        cli.nagios_epilogue_called = False
        cli.lock_epilogue_called = False

        cli.main()

        self.assertTrue(cli.nagios_prologue_called)
        self.assertTrue(cli.lock_prologue_called)
        self.assertTrue(cli.nagios_epilogue_called)
        self.assertTrue(cli.lock_epilogue_called)

    @patch('vsc.utils.script_tools.logging.error')
    @patch('vsc.utils.script_tools.sys.exit')
    def test_main_critical_exception(self, mock_sys_exit, mock_logging_error):
        """
        Test the main method when a critical exception is raised.
        """
        class FailingCLI(CLIBase):
            def do(self, dryrun=False):
                raise Exception("Unrecoverable error!")

        cli = FailingCLI("Failing CLI")

        cli.main()
        mock_logging_error.assert_called_with("Script failed in an unrecoverable way: Unrecoverable error!")
        mock_sys_exit.assert_called_with(1)
