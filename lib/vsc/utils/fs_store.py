#!/usr/bin/env python
##
#
# Copyright 2012 Ghent University
# Copyright 2012 Andy Georges
#
# This file is part of the tools originally by the HPC team of
# Ghent University (http://ugent.be/hpc).
#
# This is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation v2.
##
"""Functions to help storing information somewhere in the file system.

An example use of this is storing cached information in the user's
home directories to avoid running expensive scripts to obtain it.
"""
import cPickle
import os
import pwd
import re
import shutil
import stat
import subprocess

from vsc import fancylogger

from vsc.exceptions import FileCopyError, FileMoveError, FileStoreError, UserStorageError
from vsc.filesystem.gpfs import GpfsOperations


logger = fancylogger.getLogger(__name__)

USER_STORAGE_HOME = '/user/homegengar/'

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

    @type vsc_user_id: username of the user on the VSC
    @type src: absolute path to the source file
    @type dest: absolute path to the destination file

    @raise FileMoveError: if the file cannot be moved to the user's home dir.
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


def store_pickle_data_at_user(vsc_user_id, path, data):
    """Store the pickled data to a file.

    @type vsc_user_id: username of the user on the VSC.
    @type path: the path to the file, relative to the vsc_user_id's home directory
    @type data: something that can be pickled

    @raise UserStorageError: when we cannot gain access to the user's home directory.
    @raise FileStoreError: a FileStoreError in case of an error putting the data in place.
    @raise FileMoveError: when we cannot move the data to the user's home directory.
    """
    try:
        home = pwd.getpwnam(vsc_user_id)[5]
    except Exception, err:
        logger.error('cannot obtain home directory: vsc_user_id %s inactive' % (vsc_user_id))
        raise UserStorageError(err)

    home = __get_home_mount(home)
    if not os.path.isdir(home):
        logger.error('home dir %s for vsc_user_id %s not found' % (home, vsc_user_id))
        raise UserStorageError("home dir %s got vsc_user_id was not found %s" % (home, vsc_user_id))

    dest = os.path.join("%s" % (home), "%s" % (path))
    tmpdir = "/tmp"
    desttmp = os.path.join(tmpdir, "%s%s.tmp" % (vsc_user_id, path))
    if not os.path.exists(desttmp):
        try:
            f = open(desttmp, 'w')
            f.write('')
            f.close()
        except Exception, err:
            logger.error("failed to write to temporary file %s" % (desttmp))
            raise FileStoreError(desttmp, err)

    try:
        f = open(desttmp, 'w')
        cPickle.dump(data, f)
        f.close()
    except Exception, err:
        logger.error("failed to to pickle information to file %s" % (desttmp))
        raise FileStoreError(desttmp, err)

    logger.info('moving file %s to vsc_user_id %s home dir in file %s' % (desttmp, vsc_user_id, dest))
    move_to_user_home_as_root(vsc_user_id, desttmp, dest)


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

