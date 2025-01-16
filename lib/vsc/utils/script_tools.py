#
# Copyright 2012-2025 Ghent University
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
This module provides functions to run at the beginning and end of commonly used scripts
    - nagios checking and reporting if requested
    - locking if required
    - checking for high-availability and bailing if required

@author: Andy Georges
"""
import os
import sys

from configargparse import ArgParser
from copy import deepcopy
from vsc.utils import deprecated_class, _script_name

import logging
from lockfile.linklockfile import LockFailed
from vsc.utils import fancylogger
from vsc.utils.availability import proceed_on_ha_service
from vsc.utils.generaloption import SimpleOption
from vsc.utils.lock import lock_or_bork, release_or_bork, LOCKFILE_DIR, LOCKFILE_FILENAME_TEMPLATE
from vsc.utils.nagios import (
    NAGIOS_CRITICAL, SimpleNagios, NAGIOS_CACHE_DIR, NAGIOS_CACHE_FILENAME_TEMPLATE, exit_from_errorcode,
    NAGIOS_EXIT_OK, NAGIOS_EXIT_WARNING, NAGIOS_EXIT_CRITICAL, NAGIOS_EXIT_UNKNOWN,
    NagiosStatusMixin
)
from vsc.utils.timestamp import (
    convert_timestamp, write_timestamp, retrieve_timestamp_with_default, TIMESTAMP_DIR,
    TIMESTAMP_FILENAME_TEMPLATE
)
from vsc.utils.timestamp_pid_lockfile import TimestampedPidLockfile

DEFAULT_TIMESTAMP = "20140101000000Z"
TIMESTAMP_FILE_OPTION = "timestamp_file"

DEFAULT_CLI_OPTIONS = {
    "start_timestamp": ("The timestamp form which to start, otherwise use the cached value", None, "store", None),
    TIMESTAMP_FILE_OPTION: ("Location to cache the start timestamp", None, "store", None),
}
MAX_DELTA = 3
MAX_RTT = 2 * MAX_DELTA + 1


DEFAULT_OPTIONS = {
    'disable-locking': ('do NOT protect this script by a file-based lock', None, 'store_true', False),
    'dry-run': ('do not make any updates whatsoever', None, 'store_true', False),
    'ha': ('high-availability master IP address', None, 'store', None),
    'locking-filename': (
        'file that will serve as a lock', None, 'store',
            os.path.join(
                LOCKFILE_DIR,
                LOCKFILE_FILENAME_TEMPLATE % (_script_name(sys.argv[0])),
            )
    ),
    'nagios-report': ('print out nagios information', None, 'store_true', False, 'n'),
    'nagios-check-filename': ('filename of where the nagios check data is stored', 'str', 'store',
                              os.path.join(NAGIOS_CACHE_DIR,
                                           NAGIOS_CACHE_FILENAME_TEMPLATE % (_script_name(sys.argv[0]),))),
    'nagios-check-interval-threshold': ('threshold of nagios checks timing out', 'int', 'store', 0),
    'nagios-user': ('user nagios runs as', 'str', 'store', 'nrpe'),
    'nagios-world-readable-check': ('make the nagios check data file world readable', None, 'store_true', False),
}


def populate_config_parser(parser, options):
    """
    Populates or updates a ConfigArgParse parser with options from a dictionary.

    Args:
        parser (configargparse.ArgParser): The parser to populate or update.
        options (dict): A dictionary of options where each key is the argument name and the value is a tuple
                        containing (help, type, action, default, optional short flag).

    Returns:
        configargparse.ArgParser: The populated or updated parser.
    """
    existing_args = {action.dest: action for action in parser._actions}

    for arg_name, config in options.items():
        # Extract the tuple components with fallback to None for optional elements
        help_text = config[0]
        type_ = config[1] if len(config) > 1 else None
        action = config[2] if len(config) > 2 else None
        default = config[3] if len(config) > 3 else None
        short_flag = f"-{config[4]}" if len(config) > 4 else None

        # Prepare argument details
        kwargs = {
            "help": help_text,
            "default": default,
        }
        if type_:
            kwargs["type"] = eval(type_)
        if action:
            kwargs["action"] = action

        long_flag = f"--{arg_name.replace('_', '-')}"

        # Check if the argument already exists
        if arg_name in existing_args:
            # Update existing argument
            action = existing_args[arg_name]
            if "help" in kwargs:
                action.help = kwargs["help"]
            if "default" in kwargs:
                action.default = kwargs["default"]
            if "type" in kwargs:
                action.type = kwargs["type"]
            if "action" in kwargs:
                action.action = kwargs["action"]
        else:
            # Add new argument
            if short_flag:
                parser.add_argument(short_flag, long_flag, **kwargs)
            else:
                parser.add_argument(long_flag, **kwargs)

    return parser

class HAException(Exception):
    pass

class LockException(Exception):
    pass

class NagiosException(Exception):
    pass

class TimestampException(Exception):
    pass

class HAMixin:
    """
    A mixin class providing methods for high-availability check.
    """
    HA_MIXIN_OPTIONS = {
        'ha': ('high-availability master IP address', None, 'store', None),
    }

    def ha_prologue(self):
        """
        Check if we are running on the HA master
        """
        if not proceed_on_ha_service(self.options.ha):
            raise HAException(f"Not running on the target host {self.options.ha} in the HA setup")

    def ha_epilogue(self):
        """
        Nothing to do here
        """


class LockMixin:
    """
    A mixin class providing methods for file locking.
    """
    LOCK_MIXIN_OPTIONS = {
        'disable-locking': ('do NOT protect this script by a file-based lock', None, 'store_true', False),
        'locking-filename':
            ( 'file that will serve as a lock', None, 'store',
                os.path.join(
                    LOCKFILE_DIR,
                    LOCKFILE_FILENAME_TEMPLATE % (_script_name(sys.argv[0]),)
                )
            ),
    }

    def lock_prologue(self):
        """
        Take a lock on the file
        """
        self.lockfile = TimestampedPidLockfile(
            self.options.locking_filename, threshold=self.options.nagios_check_interval_threshold * 2
        )
        try:
            self.lockfile.acquire()
        except LockFailed as err:
            raise LockException(f"Failed to acquire lock on {self.options.locking_filename}") from err

    def lock_epilogue(self):
        """
        Release the lock on the file
        """
        try:
            self.lockfile.release()
        except Exception as err:
            raise LockException("Failed to release lock") from err


class TimestampMixin:
    """
    A mixin class providing methods for timestamp handling.

    Requires:
        - The inheriting class must provide `self.options` with attributes:
            - `start_timestamp`
            - `TIMESTAMP_FILE_OPTION`
    """
    TIMESTAMP_MIXIN_OPTIONS = {
        "start_timestamp": ("The timestamp form which to start, otherwise use the cached value", None, "store", None),
        "timestamp_file": (
            "Location to cache the start timestamp", None, "store",
            os.path.join(
                TIMESTAMP_DIR,
                TIMESTAMP_FILENAME_TEMPLATE % (_script_name(sys.argv[0]),)
            )
        ),
    }

    def timestamp_prologue(self):
        """
        Get start time (from commandline or cache), return current time
        """
        try:
            (start_timestamp, current_time) = retrieve_timestamp_with_default(
                getattr(self.options, TIMESTAMP_FILE_OPTION),
                start_timestamp=self.options.start_timestamp,
                default_timestamp=DEFAULT_TIMESTAMP,
                delta=-MAX_RTT,  # make the default delta explicit, current_time = now - MAX_RTT seconds
            )
        except Exception as err:
            raise TimestampException("Failed to retrieve timestamp") from err

        logging.info("Using start timestamp %s", start_timestamp)
        logging.info("Using current time %s", current_time)
        self.start_timestamp = start_timestamp
        self.current_time = current_time

    def timestamp_epilogue(self):
        """
        Write the new timestamp to the file
        """
        try:
            write_timestamp(self.options.timestamp_file, self.current_time)
        except Exception as err:
            raise TimestampException("Failed to write timestamp") from err

class LogMixin:
    """
    A mixin class providing methods for logging.
    """
    LOG_MIXIN_OPTIONS = {
        'debug': ("Enable debug log mode", None, "store_true", False),
        'info': ("Enable info log mode", None, "store_true", False),
        'quiet': ("Enable quiet/warning log mode", None, "store_true", False),
    }

    def log_prologue(self):
        """
        Set the log level
        """
        if self.options.quiet:
            logging.basicConfig(level=logging.WARNING)
        elif self.options.info:
            logging.basicConfig(level=logging.INFO)
        elif self.options.debug:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.ERROR)

    def log_epilogue(self):
        """
        Nothing to do here
        """

class CLIBase:

    CLI_OPTIONS = {}
    CLI_BASE_OPTIONS = {
        'dry-run': ('do not make any updates whatsoever', None, 'store_true', False),
        'configfiles': ('config file to read', 'str', 'store', None),
        'help': ('show this help message and exit', None, 'help', None),
        'ignoreconfigfiles': ('do not read any config files', None, 'store', None),
    }

    def __init__(self, name=None):
        self.name = name
        # Set all the options
        argparser = ArgParser()
        argparser = populate_config_parser(argparser, self.__class__.CLI_BASE_OPTIONS)

        if isinstance(self, HAMixin):
            argparser = populate_config_parser(argparser, self.__class__.HA_MIXIN_OPTIONS)

        if isinstance(self, LogMixin):
            argparser = populate_config_parser(argparser, self.__class__.LOG_MIXIN_OPTIONS)

        if isinstance(self, TimestampMixin):
            argparser = populate_config_parser(argparser, self.__class__.TIMESTAMP_MIXIN_OPTIONS)

        if isinstance(self, LockMixin):
            argparser = populate_config_parser(argparser, self.__class__.LOCK_MIXIN_OPTIONS)

        if isinstance(self, NagiosStatusMixin):
            argparser = populate_config_parser(argparser, self.__class__.NAGIOS_MIXIN_OPTIONS)

        argparser = populate_config_parser(argparser, self.get_options())

        self.options = argparser.parse_args()

    def critical(self, msg):
        if isinstance(self, NagiosStatusMixin):
            self.nagios_epilogue(NAGIOS_CRITICAL, msg)
        else:
            logging.error(msg)
            sys.exit(1)

    def get_options(self):
        # Gather options from the current class and its hierarchy
        options = {}
        for cls in reversed(self.__class__.mro()):
            if hasattr(cls, "CLI_OPTIONS"):
                options.update(cls.CLI_OPTIONS)
        return options

    def final(self):
        """
        Run as finally block in main
        """

    def do(self, dryrun=False):   # pylint: disable=unused-argument
        """
        Method to add actual work to do.
        The method is executed in main method in a generic try/except/finally block
        You can return something, that, when it evals to true, is considered fatal
        """
        logging.error("`do` method not implemented")
        raise NotImplementedError("Not implemented")
        return "Not Implemented"

    def main(self):
        """
        The main method.
        """
        #errors = []

        msg = self.name
        if msg and self.options.dry_run:
            msg += " (dry-run)"
        logging.info("%s started.", msg)

        # Call mixin prologue methods
        # We must fiorst call the Nagios prologue, as it may exit the script immedoately when a report is asked
        try:
            if isinstance(self, NagiosStatusMixin):
                self.nagios_prologue()
        except NagiosException as err:
            self.critical(str(err))

        try:
            if isinstance(self, LogMixin):
                self.log_prologue()

            if isinstance(self, LockMixin):
                self.lock_prologue()

            if isinstance(self, TimestampMixin):
                self.timestamp_prologue()

            if isinstance(self, HAMixin):
                self.ha_prologue()

        except (LockException, HAException, TimestampException) as err:
            self.critical(str(err))


        try:
            self.do(self.options.dry_run)
        except Exception as err:
            self.critical(f"Script failed in an unrecoverable way: {err}")
        finally:
            self.final()
            # Call epilogue_unlock if LockMixin is inherited
            if isinstance(self, LockMixin):
                self.lock_epilogue()

        #self.post(errors)

        # Call mixin epilogue methods
        if isinstance(self, TimestampMixin):
            self.timestamp_epilogue()

        if isinstance(self, LockMixin):
            self.lock_epilogue()

        if isinstance(self, NagiosStatusMixin):
            self.nagios_epilogue()

        if isinstance(self, LogMixin):
            self.log_epilogue()


class FullCLIBase(HAMixin, LockMixin, TimestampMixin, LogMixin, NagiosStatusMixin, CLIBase):
    """
    A class for command line scripts with all mixins, i.e., what you usually want.
    """


def _merge_options(options):
    """Merge the given set of options with the default options, updating default values where needed.

    @type options: dict. keys should be strings, values are multi-typed.
                       value is a simple scalar if the key represents an update to DEFAULT_OPTIONS\
                       value is a SimpleOption tuple otherwise
    """

    opts = deepcopy(options)
    for (k, v) in DEFAULT_OPTIONS.items():
        if k in opts:
            v_ = v[:3] + (opts[k],) + v[4:]
            opts[k] = v_
        else:
            opts[k] = v

    return opts


class CLI(FullCLIBase):

    def __init__(self, name=None, default_options=None):  # pylint: disable=unused-argument
        super().__init__(name)


@deprecated_class("Base your scripts on the CLIBase class instead")
class ExtendedSimpleOption(SimpleOption):
    """
    Extends the SimpleOption class to allow other checks to occur at script prologue and epilogue.

    - nagios reporting
    - checking if running on the designated HA host
    - locking on a file

    The prologue should be called at the start of the script; the epilogue at the end.
    """

    def __init__(self, options, run_prologue=True, excepthook=None, **kwargs):
        """Initialise.

        If run_prologue is True (default), we immediately execute the prologue.

        Note that if taking a lock is requested (default), and the lock cannot be
        acquire for some reason, the program will exit,
        """

        options_ = _merge_options(options)
        super().__init__(options_, **kwargs)

        self.nagios_reporter = None
        self.lockfile = None

        if run_prologue:
            self.prologue()

        if not excepthook:
            sys.excepthook = self.critical_exception_handler
        else:
            sys.excepthook = excepthook

        self.log = fancylogger.getLogger()

    def prologue(self):
        """Checks the options given for settings and takes appropriate action.

        See _merge_options for the format.

        - if nagios_report is set, creates a SimpleNagios instance and prints the report.
        - if ha is set, checks if running on the correct host, set the appropriate nagios message and bail if not.
        - if locking_filename is set, take a lock. If the lock fails, bork and set the nagios exit accordingly.
        """

        # bail if nagios report is requested
        self.nagios_reporter = SimpleNagios(
            _cache=self.options.nagios_check_filename,
            _report_and_exit=self.options.nagios_report,
            _threshold=self.options.nagios_check_interval_threshold,
            _cache_user=self.options.nagios_user,
            _world_readable=self.options.nagios_world_readable_check,
        )

        # check for HA host
        if self.options.ha and not proceed_on_ha_service(self.options.ha):
            self.log.warning("Not running on the target host %s in the HA setup. Stopping.", self.options.ha)
            self.nagios_reporter.ok("Not running on the HA master.")
            sys.exit(NAGIOS_EXIT_OK)

        if not self.options.disable_locking and not self.options.dry_run:
            self.lockfile = TimestampedPidLockfile(
                self.options.locking_filename, threshold=self.options.nagios_check_interval_threshold * 2
            )
            lock_or_bork(self.lockfile, self.nagios_reporter)

        self.log.info("%s has started", _script_name(sys.argv[0]))

    def _epilogue(self):
        if not self.options.disable_locking and not self.options.dry_run:
            release_or_bork(self.lockfile, self.nagios_reporter)

    def epilogue(self, nagios_message, nagios_thresholds=None):
        """Run at the end of a script, quitting gracefully if possible."""
        if nagios_thresholds is None:
            nagios_thresholds = {}

        self._epilogue()

        nagios_thresholds["message"] = nagios_message
        self.nagios_reporter._eval_and_exit(**nagios_thresholds)
        self.log.info("%s has finished", _script_name(sys.argv[0]))  # may not be reached

    def ok(self, nagios_message):
        """Run at the end of a script and force an OK exit."""
        self._epilogue()
        self.nagios_reporter.ok(nagios_message)

    def warning(self, nagios_message):
        """Run at the end of a script and force a Warning exit."""
        self._epilogue()
        self.nagios_reporter.warning(nagios_message)

    def critical(self, nagios_message):
        """Run at the end of a script and force a Critical exit."""
        self._epilogue()
        self.nagios_reporter.critical(nagios_message)

    def unknown(self, nagios_message):
        """Run at the end of a script and force a Unknown exit."""
        self._epilogue()
        self.nagios_reporter.unknown(nagios_message)

    def make_exit_map(self, ok=0, warn=1, crit=2, unkn=3):
        """Make a mapping of exit functions."""
        return {
            ok: self.ok,
            warn: self.warning,
            crit: self.critical,
            unkn: self.unknown,
        }

    def critical_exception_handler(self, tp, value, traceback):
        """
        Run at the end of a script and force a Critical exit.

        This function is meant to be used as sys.excepthook
        """
        self.log.exception("unhandled exception detected: %s - %s", tp, value)
        self.log.debug("traceback %s", traceback)
        message = f"Script failure: {tp} - {value}"
        self.critical(message)


@deprecated_class("Base your scripts on the CLIBase class instead")
class OldCLI:
    """
    Base class to implement cli tools that require timestamps, nagios checks, etc.
    """

    TIMESTAMP_MANDATORY = True

    CLI_OPTIONS = {}
    CACHE_DIR = "/var/cache"

    def __init__(self, name=None, default_options=None):
        """
        Option
            name (default: script name from commandline)
            default_options: pass different set of default options
                (only when creating a new parent class; for regular child classes, use CLI_OPTIONS)
        """
        if name is None:
            name = _script_name(sys.argv[0])
        self.name = name

        self.fulloptions = self.make_options(defaults=default_options)
        self.options = self.fulloptions.options

        self.thresholds = None

        self.start_timestamp = None
        self.current_time = None

    def make_options(self, defaults=None):
        """
        Take the default sync options, set the default timestamp file and merge
        options from class constant OPTIONS

        Return ExtendedSimpleOption instance
        """
        if defaults is None:
            defaults = DEFAULT_CLI_OPTIONS
        # use a copy
        options = deepcopy(defaults)

        # insert default timestamp value file based on name
        if TIMESTAMP_FILE_OPTION in options:
            tsopt = list(options[TIMESTAMP_FILE_OPTION])
            tsopt[-1] = os.path.join(self.CACHE_DIR, f"{self.name}.timestamp")
            options[TIMESTAMP_FILE_OPTION] = tuple(tsopt)

        options.update(self.CLI_OPTIONS)

        if TIMESTAMP_FILE_OPTION not in options and self.TIMESTAMP_MANDATORY:
            raise ValueError(f"no mandatory {TIMESTAMP_FILE_OPTION} option defined")

        return ExtendedSimpleOption(options)

    def ok(self, msg):
        """
        Convenience method that calls ExtendedSimpleOptions ok and exists with nagios OK exitcode
        """
        logging.info(msg)
        self.fulloptions.ok(msg)
        sys.exit(NAGIOS_EXIT_OK[0])

    def warning(self, msg):
        """
        Convenience method that calls ExtendedSimpleOptions warning and exists with nagios warning exitcode
        """
        logging.warning(msg)
        self.fulloptions.warning(msg)
        sys.exit(NAGIOS_EXIT_WARNING[0])

    def critical(self, msg):
        """
        Convenience method that calls ExtendedSimpleOptions critical and exists with nagios critical exitcode
        """
        logging.error(msg)
        self.fulloptions.critical(msg)
        sys.exit(NAGIOS_EXIT_CRITICAL[0])

    def unknown(self, msg):
        """
        Convenience method that calls ExtendedSimpleOptions unknown and exists with nagios unknown exitcode
        """
        logging.error(msg)
        self.fulloptions.unknown(msg)
        sys.exit(NAGIOS_EXIT_UNKNOWN[0])

    def critical_exception(self, msg, exception):
        """
        Convenience method: report exception and critical method
        """
        logging.exception("%s: %s", msg, exception)
        exit_from_errorcode(2, msg)

    def do(self, dry_run):  # pylint: disable=unused-argument
        """
        Method to add actual work to do.
        The method is executed in main method in a generic try/except/finally block
        You can return something, that, when it evals to true, is considered fatal
            self.start_timestamp has start time (i.e. either passed via commandline or
                latest successful run from cache file)
            self.current_time has current_time (to be used as next start_timestamp when all goes well)
            self.options has options from commandline
            self.thresholds can be used to pass the thresholds during epilogue
        """
        logging.error("`do` method not implemented")
        raise NotImplementedError("Not implemented")
        return "Not Implemented"

    def make_time(self):
        """
        Get start time (from commandline or cache), return current time
        """
        try:
            (start_timestamp, current_time) = retrieve_timestamp_with_default(
                getattr(self.options, TIMESTAMP_FILE_OPTION),
                start_timestamp=self.options.start_timestamp,
                default_timestamp=DEFAULT_TIMESTAMP,
                delta=-MAX_RTT,  # make the default delta explicit, current_time = now - MAX_RTT seconds
            )
        except Exception as err:
            self.critical_exception("Failed to retrieve timestamp", err)

        logging.info("Using start timestamp %s", start_timestamp)
        logging.info("Using current time %s", current_time)
        self.start_timestamp = start_timestamp
        self.current_time = current_time

    def post(self, errors, current_time=None):
        """
        Runs in main after do

        If errors evals to true, this is indicates a handled failure
        If errors evals to false, and this is not a dry_run
        it is considered success and creates the cache file with current time
        """
        if current_time is None:
            current_time = self.current_time

        if errors:
            logging.warning("Encountered errors: %s", errors)
            self.warning("Failed to complete without errors.")
        elif not self.options.dry_run:
            # don't update the timestamp on dryrun
            timestamp = -1  # handle failing convert_timestamp
            try:
                _, timestamp = convert_timestamp(current_time)
                write_timestamp(self.options.timestamp_file, timestamp)
            except Exception as err:
                txt = f"Writing timestamp {timestamp} to {self.options.timestamp_file} failed: {err}"
                self.critical_exception(txt, err)

    def final(self):
        """
        Run as finally block in main
        """

    def main(self):
        """
        The main method.
        """
        errors = []

        msg = self.name
        if self.options.dry_run:
            msg += " (dry-run)"
        logging.info("%s started.", msg)

        self.make_time()

        try:
            errors = self.do(self.options.dry_run)
        except Exception as err:
            self.critical_exception("Script failed in a horrible way", err)
        finally:
            self.final()

        self.post(errors)

        self.fulloptions.epilogue(f"{msg} complete", self.thresholds)


@deprecated_class("Base your scripts on the CLIBase class instead")
class NrpeCLI(CLI):
    def __init__(self, name=None, default_options=None):
        super().__init__(name=name, default_options=default_options)

#    def ok(self, msg):
#        """
#        Convenience method that exists with nagios OK exitcode
#        """
#        exit_from_errorcode(0, msg)
#
#    def warning(self, msg):
#        """
#        Convenience method exists with nagios warning exitcode
#        """
#        exit_from_errorcode(1, msg)
#
#    def critical(self, msg):
#        """
#        Convenience method that exists with nagios critical exitcode
#        """
#        exit_from_errorcode(2, msg)
#
#    def unknown(self, msg):
#        """
#        Convenience method that exists with nagios unknown exitcode
#        """
#        exit_from_errorcode(3, msg)
#
