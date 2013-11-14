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
"""
This file contains the tools for automated administration w.r.t. the VSC
Original Perl code by Stijn Deweirdt

@author: Andy Georges (Ghent University)
"""

__author__ = 'ageorges'
__date__ = 'May 9, 2012'

import re
import logging
import os

from vsc import fancylogger

logger = fancylogger.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def mount_points(mount_type):
    """Determines the mount points for file systems mounted with the given type.

    @return: tuple of two dictionaries
        - with string keys representing mounted devices and values the mount points
        - with string keys representing mount points and values the mounted devices

    #FIXME: Deprecated: replaced by the vsc.filesystems.posix or vsc.filesystems.gpfs modules.
    """
    source = '/proc/mounts'
    reg_mount = re.compile(r"^(?P<dev>\S+)\s+(?P<mntpt>\S+)\s+%s" % (mount_type))
    f = file(source, 'r')
    ms = {}
    ds = {}
    for fs in f.readlines():
        r = reg_mount.search(fs)
        if r:
            (dev, mount_point) = r.groups()
            ms[dev] = mount_point
            ds[mount_point] = dev
    if not ms or not ds:
        logger.error('No devices found that are mounted under %s')
    else:
        logger.info('Found GPFS mount point at: %s' % (ms))
    return (ms, ds)


def match_mount_point_with_path(mount_points, path):
    """See which mount point is used for a given path.

    @type mount_points: dictionary with the mount points as keys and devices as values

    #FIXME: Deprecated: replaced by the vsc.filesystems.posix or vsc.filesystems.gpfs modules.
    """

    # normalise the path
    path = os.path.dirname(os.path.realpath(path))
    for (mp, device) in mount_points.iteritems():
        if path.startswith(mp):
            return (mp, device)

    return (None, None)



