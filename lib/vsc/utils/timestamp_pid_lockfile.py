#!/usr/bin/env python
'''Several lockfile strategies for VSC tools that will be 
running.

Implementation based on the PIDLockFile of http://pypi.python.org/pypi/lockfile.
The above is available for Python 2.4, if a diff is applied.

Created Mar 26, 2012

@author Andy Georges
'''
import errno
import os
import signal
import time

from lockfile.linklockfile import LockBase, LockFailed, NotLocked, NotMyLock

import vsc.fancylogger as fancylogger


class LockFileReadError(Exception):
    '''Exception raised when we cannot get the expected information from the lock file.'''
    pass


class TimestampedPidLockfile(LockBase, object):
    '''Basic lock file implementation.
    '''

    def __init__(self, path, threshold=60):
        '''Intializer.'''
        LockBase.__init__(self, path, False)
        self.threshold = threshold
        self.logger = fancylogger.getLogger(self.__class__.__name__)

    def read_pid_timestamp(self):
        '''Obtain the PID and timestamp from the lockfile.

        Returns a tuple (pid :: Int, timestamp :: Int)
        '''
        return _read_pid_timestamp_file(self.path)

    def is_locked(self):
        '''We are locked if the lockfile exists.'''
        return os.path.exists(self.path)

    def i_am_locking(self):
        '''We are locking if our PID is stored in the lockfile.'''
        if self.is_locked():
            (pid, _) = _read_pid_timestamp_file(self.path)
            return pid == os.getpid()
        return False

    def acquire(self):
        '''Obtains the lock, storing its own PID and the timestamp 
        at which the lock was obtained in the lockfile.

        Raises a LockFailed exception when the lock cannot be obtained.
        '''
        try:
            _write_pid_timestamp_file(self.path)
            self.logger.info('Obtained lock on timestamped pid lockfile %s' % (self.path))
        except OSError, err:
            if err.errno == errno.EEXIST:
                ## Check if the timestamp is older than the threshold
                (pid, timestamp) = _read_pid_timestamp_file(self.path)
                if time.time() - timestamp > self.threshold:
                    _find_and_kill(pid)
                    os.unlink(self.path)
                    self.logger.warning('Obsolete lockfile detected at %s: pid = %d, timestamp = %s' % (self.path, pid, time.ctime(timestamp)))
                    try:
                        _write_pid_timestamp_file(self.path)
                    except OSError, err:
                        self.logger.error('Unable to obtain lock on %s' % (self.path))
                        raise LockFailed
                else:
                    self.logger.error('Unable to obtain lock on %s' % (self.path))
                    raise LockFailed

    def release(self):
        '''Release the lock.

        Remove the lockfile to indicate the lock was released.
        '''
        if not self.is_locked():
            self.logger.error('Trying to release a lock that does not exist at %s.' % (self.path))
            raise NotLocked
        if not self.i_am_locking():
            self.logger.error('Trying to release a lock the current process is not holding at %s' % (self.path))
            raise NotMyLock
        os.remove(self.path)


def _read_pid_timestamp_file(path):
    '''Get the PID and the timestamp from the file.
    This information is stored in plaintext on two separate lines.

    @type path: string corresponding to an (absolute) path to a file.

    Returns (pid :: Int, timestamp :: Int).
    '''
    try:
        pidfp = open(path, 'r')
    except IOError, err:
        if err.errno == errno.ENOENT:
            return None
        else:
            raise LockFileReadError('Cannot get the information from the pid file.')

    pidLine = pidfp.readline().strip()
    timestampLine = pidfp.readline().strip()

    try:
        pid = int(pidLine)
        timestamp = int(timestampLine)
        return (pid, timestamp)
    except ValueError:
        raise LockFileReadError("Contents of pid file %s invalid" % (path))


def _write_pid_timestamp_file(path):
    '''Write the PID and timestamp to the file.

    @type path: string corresponding to an (absolute) path to a file.
    '''
    pidfp = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    pidfile = os.fdopen(pidfp, 'w')
    pidfile.write("%s\n%d\n" % (os.getpid(), int(time.time())))
    pidfile.flush()
    pidfile.close()


def _find_and_kill(pid):
    '''See if the process corresponding to the given PID is still running. If so,
    kill it (gently).
    '''
    for psLine in os.popen('ps ax'):
        fields = psLine.split()
        if fields[0] == pid:
            os.kill(pid, signal.SIGHUP)
            return True
    return False