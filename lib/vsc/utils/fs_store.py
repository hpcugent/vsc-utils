#!/usr/bin/env python
# -*- coding: latin-1 -*-
##
# Copyright 2009-2013 Ghent University
#
# This file is part of vsc-utils,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://vscentrum.be/nl/en),
# the Hercules foundation (http://www.herculesstichting.be/in_English)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# All rights reserved.
#
##
"""Functions to help storing information somewhere in the file system.

An example use of this is storing cached information in the user's
home directories to avoid running expensive scripts to obtain it.

@author: Andy Georges (Ghent University)
"""
import cPickle
import os
import pwd
import re
import shutil
import stat
import subprocess
import tempfile

from vsc import fancylogger

from vsc.utils.cache import FileCache


logger = fancylogger.getLogger(__name__)

USER_STORAGE_HOME = '/user/homegengar/'


class FsStoreError(Exception):
    """Base class for VSC related exceptions."""
    def __init__(self):
        Exception.__init__(self)


class FileStoreError(FsStoreError):
    """When something goes wrong when storing data on the file system."""

    def __init__(self, path, err=None):
        """Initializer.

        @type path: string indicating the path to the file which was accessed.
        @type err: the original exception.
        """
        FsStoreError.__init__(self)
        self.path = path
        self.err = err


class FileMoveError(FsStoreError):
    """When moving a file fails for some reason."""

    def __init__(self, src, dest, err=None):
        """Initializer.

        @type src: string indicating the path to the source file.
        @type dest: string indicating the path to the destination file.
        @type err: the original exception, if any.
        """
        FsStoreError.__init__(self)
        self.src = src
        self.dest = dest
        self.err = err


class FileCopyError(FsStoreError):
    """When copying a file for some reason."""

    def __init__(self, src, dest, err=None):
        """Initializer.

        @type src: string indicating the path to the source file.
        @type dest: string indicating the path to the destination file.
        @type err: the original exception, if any.
        """
        FsStoreError.__init__(self)
        self.src = src
        self.dest = dest
        self.err = err


class UserStorageError(FsStoreError):
    """When something goed wrong accessing a user's storage."""

    def __init__(self, err=None):
        """Initializer.

        @type err: the original exception, if any.
        """
        FsStoreError.__init__(self)
        self.err = err


def move_to_user_home(vsc_user_id, src, dest):
    """Copy a file to the home directory of a VSC user.

    @type vsc_user_id: username of the user on the VSC
    @type src: absolute path to the source file
    @type dest: absolute path to the destination file

    @raise FileMoveError: if the file cannot be moved to the user's home dir.

    @deprecated: Replaced by the move_to_user_home_as_root function. This should
                 no longer be used.
    """
    try:
        os.chown(src, pwd.getpwnam(vsc_user_id)[2], pwd.getpwnam(vsc_user_id)[3])  # restrict access
        cmd = "sudo -u %s chmod 700 %s &> /dev/null" % (vsc_user_id, dest)  # make sure destination is writable if it's there
        r = subprocess.call(cmd, shell=True)
        if r > 0:
            logger.warning("could not chmod the file %s as user %s. Exitcode = %d" % (dest, vsc_user_id, r))
        cmd = "sudo -u %s cp %s %s &> /dev/null" % (vsc_user_id, src, dest)  # copy new file
        r = subprocess.call(cmd, shell=True)
        if r > 0:
            logger.warning("could not cp the file %s to %s as user %s. Exitcode = %d" % (src, dest, vsc_user_id, r))
        cmd = "sudo -u %s chmod 400 %s &> /dev/null" % (vsc_user_id, dest)  # change to read-only
        r = subprocess.call(cmd, shell=True)
        if r > 0:
            logger.warning("could not chmod the file %s as user %s. Exitcode = %d" % (dest, vsc_user_id, r))
        os.remove(src)  # get rid of tmp file
    except Exception, err:
        logger.error("failed to copy tmp file %s to destination %s" % (src, dest))
        raise FileMoveError(src, dest, err)


def move_to_user_home_as_root(vsc_user_id, src, dest):
    """Copy a file to the home directory of a VSC user.

    @deprecated: please use the newer move_to_user_as_root, which does the same.

    @type vsc_user_id: username of the user on the VSC
    @type src: absolute path to the source file
    @type dest: absolute path to the destination file

    @raise FileMoveError: if the file cannot be moved to the user's home dir.
    """
    move_to_user_as_root(vsc_user_id, src, dest)


def move_to_user_as_root(vsc_user_id, src, dest):
    """Copy a file to a location on some accesible filesystem of a VSC user.

    @type vsc_user_id: username of the user on the VSC
    @type src: absolute path to the source file
    @type dest: absolute path to the destination file

    @raise FileMoveError: if the file cannot be moved.
    """
    try:
        vsc_user_uid = pwd.getpwnam(vsc_user_id)[2]
        vsc_user_gid = pwd.getpwnam(vsc_user_id)[3]
        os.chown(src, vsc_user_uid, vsc_user_gid)
        os.chmod(src, stat.S_IRUSR)
        shutil.copy2(src, dest)
        os.chown(dest, vsc_user_uid, vsc_user_gid)
        os.remove(src)  # get rid of tmp file
    except Exception, err:
        logger.error("failed to move file %s to destination %s" % (src, dest))
        raise FileMoveError(src, dest, err)


def copy_from_user_home(vsc_user_id, src, dest):
    """Copy a file out of a VSC user's home directory.

    @type vsc_user_id: username of the user on the VSC
    @type src: absolute path to the source file
    @type dest: absolute path to the destination file

    @raise FileCopyError: if the file cannot be copied
    """
    try:
        cmd = "sudo -u %s cp %s %s" % (vsc_user_id, src, dest)
        subprocess.call(cmd, shell=True)
    except Exception, err:
        logger.error("failed to copy tmp file %s from user %s to destination %s" % (src, vsc_user_id, dest))
        raise FileCopyError(src, dest, err)


def store_pickle_data_at_user_home(vsc_user_id, path, data):
    """Store the pickled data to a file.

    @type vsc_user_id: username of the user on the VSC.
    @type path: the absolute path to the file, in the users home directory
    @type data: something that can be pickled

    @raise UserStorageError: when we cannot gain access to the user's home directory.
    @raise FileStoreError: a FileStoreError in case of an error putting the data in place.
    @raise FileMoveError: when we cannot move the data to the user's home directory.
    """
    dest = __get_home_mount(path)
    if not os.path.isdir(os.path.dirname(dest)):
        logger.error('home dir %s for vsc_user_id %s not found' % (os.path.dirname(dest), vsc_user_id))
        raise UserStorageError("home dir %s got vsc_user_id was not found %s" % (dest, vsc_user_id))

    store_pickle_data_at_user(vsc_user_id, dest, data)


def store_pickle_data_at_user(vsc_user_id, dest, data):
    """Store the pickled data to a file.

    @type vsc_user_id: username of the user on the VSC.
    @type dest: the absolute path to the file
    @type data: something that can be pickled

    @raise UserStorageError: when we cannot gain access to the user's home directory.
    @raise FileStoreError: a FileStoreError in case of an error putting the data in place.
    @raise FileMoveError: when we cannot move the data to the user's home directory.
    """

    try:
        (tmphandle, desttmp) = tempfile.mkstemp(suffix='.pickle')
        tmpfile = os.fdopen(tmphandle, 'w')
        cPickle.dump(data, tmpfile)
        tmpfile.close()
    except Exception, err:
        logger.error("failed to to pickle information to file %s" % (desttmp))
        raise FileStoreError(desttmp, err)

    logger.info('moving file %s to vsc_user_id %s in file %s' % (desttmp, vsc_user_id, dest))
    move_to_user_as_root(vsc_user_id, desttmp, dest)
    # the move above cleaned up (hence the name move)


def read_pickled_data_from_user(self, vsc_user_id, path):
    """Unpickle and read the data from the stored pickled file cache.

    @type vsc_user_id: username of the user of the VSC
    @type path: the path to the file, relative to the user's home directory

    @return: the unpickled data.

    @raise UserStorageError: when we cannot gain access to the user's home directory.
    @raise FileStoreError: when we cannot get the data
    """
    try:
        home = pwd.getpwnam(vsc_user_id)[5]
    except Exception, err:
        self.logger.error("cannot obtain home directory: vsc_user_id %s inactive (?)" % (vsc_user_id))
        raise UserStorageError(err)
    if not os.path.isdir(home):
        self.logger.error("home dir %s for vsc_user_id %s not found" % (home, vsc_user_id))
        raise UserStorageError("home dir %s for vsc_user_id %s not found" % (home, vsc_user_id))

    orig = os.path.join("%s" % (home), "%s" % (path))
    # See if we can write to tmp
    tmpdir = "/tmp"
    desttmp = os.path.join(tmpdir, "%s%s.tmp" % (vsc_user_id, path))

    copy_from_user_home(vsc_user_id, orig, desttmp)

    # We should be able to read the file
    try:
        f = open(desttmp, 'r')
        data = cPickle.load(f)
        f.close()
        os.remove(desttmp)
        return data
    except cPickle.PickleError, err:
        os.remove(desttmp)
        raise FileStoreError(path, err)
    except (IOError, OSError), err:
        self.logger.error("failed to unpickle from file %s" % (desttmp))
        raise FileStoreError(desttmp, err)


def __get_home_mount(home):
    """Replace the 'home' in the home dir path with the GPFS mount point.

    This makes sure that the root user can write files, since we are no
    longer moving through NFS.

    @type home: string representing the path to a user's home dir.

    @returns: string representing a path where files can be written by the root
              user.
    """
    home_reg = re.compile('/home/')
    if home_reg.search(home):
        ps = home.split(os.sep)[3:]
        return os.path.join(USER_STORAGE_HOME, os.sep.join(ps))
    else:
        return home


def store_on_gpfs(user_name, path, key, information, gpfs, login_mount_point, gpfs_mount_point, filename, dry_run=False):
    """
    Store the given information in a cache file that resides in a user's directory.

    @type user_name: string
    @type path: string, representing a directory
    @type showq_information: a recursive dict structure
    @type gpfs: GpfsOperations instance
    @type login_mount_point: path representing the mount point of the storage location on the login nodes
    @type gpfs_mount_point: path representing the mount point of the storage location when GPFS mounted
    @type dry_run: boolean
    """

    if user_name and user_name.startswith('vsc4'):
        logger.debug("Storing %s information for user %s" % (key, user_name,))
        logger.debug("information: %s" % (information,))
        logger.debug("path for storing information would be %s" % (path,))

        # FIXME: We need some better way to address this
        # Right now, we replace the nfs mount prefix which the symlink points to
        # with the gpfs mount point. this is a workaround until we resolve the
        # symlink problem once we take new default scratch into production
        if gpfs.is_symlink(path):
            target = os.path.realpath(path)
            logger.debug("path is a symlink, target is %s" % (target,))
            logger.debug("login_mount_point is %s" % (login_mount_point,))
            if target.startswith(login_mount_point):
                new_path = target.replace(login_mount_point, gpfs_mount_point, 1)
                logger.info("Found a symlinked path %s to the nfs mount point %s. Replaced with %s" %
                            (path, login_mount_point, gpfs_mount_point))
            else:
                logger.warning("Unable to store quota information for %s on %s; symlink cannot be resolved properly"
                                % (user_name, path))
        else:
            new_path = path

        path_stat = os.stat(new_path)
        filename = os.path.join(new_path, filename)

        if dry_run:
            logger.info("Dry run: would update cache for at %s with %s" % (new_path, "%s" % (information,)))
            logger.info("Dry run: would chmod 640 %s" % (filename,))
            logger.info("Dry run: would chown %s to %s %s" % (filename, path_stat.st_uid, path_stat.st_gid))
        else:
            cache = FileCache(filename)
            cache.update(key=key, data=information, threshold=0)
            cache.close()

            gpfs.ignorerealpathmismatch = True
            gpfs.chmod(0640, filename)
            gpfs.chown(path_stat.st_uid, path_stat.st_uid, filename)
            gpfs.ignorerealpathmismatch = False

        logger.info("Stored user %s showq information at %s" % (user_name, filename))




