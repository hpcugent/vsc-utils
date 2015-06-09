##
# Copyright 2012-2013 Ghent University
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
##
"""
Unit tests for vsc.utils.cache

@author: Andy Georges (Ghent University)
"""

import os
import tempfile
import time
import shutil
import sys
import random
from unittest import TestCase, TestLoader

from vsc.utils.cache import FileCache

LIST_LEN = 30  # same as in paycheck


def get_rand_data():
    """Returns a random dict with between 0 and LIST_LEN elements  and a random threshold"""
    length = random.randint(0, LIST_LEN)
    data = {}
    for x in xrange(length):
        data[random.randint(0, sys.maxint)] = random.randint(0, sys.maxint)
    threshold = random.randint(0, sys.maxint)
    return data, threshold


class TestCache(TestCase):

    def test_contents(self):
        """Check that the contents of the cache is what is expected prior to closing it."""
        # test with random data
        data, threshold = get_rand_data()

        # create a tempfilename
        (handle, filename) = tempfile.mkstemp(dir='/tmp')
        os.unlink(filename)
        os.close(handle)
        cache = FileCache(filename)
        for (key, value) in data.items():
            cache.update(key, value, threshold)

        now = time.time()
        for key in data.keys():
            info = cache.load(key)
            self.assertFalse(info is None)
            (ts, value) = info
            self.assertTrue(value == data[key])
            self.assertTrue(ts <= now)

    def test_save_and_load(self):
        """Check if the loaded data is the same as the saved data."""
        # test with random data
        data, threshold = get_rand_data()
        tempdir = tempfile.mkdtemp()
        # create a tempfilename
        (handle, filename) = tempfile.mkstemp(dir=tempdir)
        os.close(handle)
        shutil.rmtree(tempdir)
        cache = FileCache(filename)
        for (key, value) in data.items():
            cache.update(key, value, threshold)
        cache.close()

        now = time.time()
        new_cache = FileCache(filename)
        for key in data.keys():
            info = cache.load(key)
            self.assertTrue(info is not None)
            (ts, value) = info
            self.assertTrue(value == data[key])
            self.assertTrue(ts <= now)
        new_cache.close()

        shutil.rmtree(tempdir)


def suite():
    """ return all the tests"""
    return TestLoader().loadTestsFromTestCase(TestCache)
