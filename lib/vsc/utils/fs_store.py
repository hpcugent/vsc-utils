#
# Copyright 2012-2016 Ghent University
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
"""Functions to help storing information somewhere in the file system.

An example use of this is storing cached information in the user's
scratch directories to avoid running expensive scripts to obtain it.

@author: Andy Georges (Ghent University)
"""
import os

from vsc.utils import fancylogger

from vsc.utils.cache import FileCache


logger = fancylogger.getLogger(__name__)


def store_on_gpfs(user_name, path, key, information, gpfs, login_mount_point, gpfs_mount_point, filename, dry_run=False):
    """
    Store the given information in a cache file that resides in a user's directory.

    @type user_name: string
    @type path: string, representing a directory
    @type key: string, name for the kind of information we are going to store in the cache
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
            cache = FileCache(filename, False)  # data need not be retained
            cache.update(key=key, data=information, threshold=0)
            cache.close()

            gpfs.ignorerealpathmismatch = True
            gpfs.chmod(0640, filename)
            gpfs.chown(path_stat.st_uid, path_stat.st_uid, filename)
            gpfs.ignorerealpathmismatch = False

        logger.info("Stored user %s %s information at %s" % (user_name, key, filename))




