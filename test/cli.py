#
# Copyright 2021-2023 Ghent University
#
# This file is part of vsc-reporting,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
# the Flemish Research Foundation (FWO) (http://www.fwo.be/en)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# https://github.ugent.be/hpcugent/vsc-reporting
#
# All rights reserved.
#
"""
xdmod tests
"""
import logging

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)

from vsc.utils.cli import make_time

from vsc.install.testing import TestCase

class TestSlurm(TestCase):

    def test_make_time(self):
        ts = '1933142400'  # TZ=UTC date -d 2031-04-05T08:00:00 +%s
        self.assertEqual(make_time(ts), '2031-04-05')
        self.assertEqual(make_time(ts, fmt='%Y-%m-%dT%H:%M:%S'), '2031-04-05T08:00:00')
        self.assertEqual(make_time(ts, fmt='%Y-%m-%dT%H:%M:%S', begin=True), '2031-04-05T00:00:00')
        self.assertEqual(make_time(ts, fmt='%Y-%m-%dT%H:%M:%S', end=True), '2031-04-05T23:59:59')

