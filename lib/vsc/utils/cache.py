#
# Copyright 2012-2023 Ghent University
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
Caching utilities.

@author: Andy Georges (Ghent University)
"""
import diskcache as dc
import logging
import time


class FileCache(object):
    """File cache with a timestamp safety.

    Wrapper around diskcache to retain the old API until all usage can be replaced.

    Stores data (something that can be pickled) into a dictionary
    indexed by the data.key(). The value stored is a tuple consisting
    of (the time of addition to the dictionary, the complete
    data instance).

    By default, only updated entries are stored to the file; old
    entries are discarded. This can be changed by setting a flag
    during instatiation or at run time. The changed behaviour only
    has an effect when closing the cache, i.e., storing it to a file.

    Note that the cache is persistent only when it is closed correctly.
    During a crash of your application ar runtime, the information is
    _not_ written to the file.
    """

    def __init__(self, filename, retain_old=True, raise_unpickable=False):
        """Initializer.

        Checks if the file can be accessed and load the data therein if any. If the file does not yet exist, start
        with an empty shelf. This ensures that old data is readily available when the FileCache instance is created.
        The file is closed after reading the data.

        @type filename: string

        @param filename: (absolute) path to the cache file.
        """
        del raise_unpickable

        self.retain_old = retain_old  # this is no longer used

        self.filename = filename
        self.cache = dc.Cache(filename)

        if not retain_old:
            self.cache.clear()

    def update(self, key, data, threshold=None):
        """Update the given data if the existing data is older than the given threshold.

        @type key: something that can serve as a dictionary key (and thus can be pickled)
        @type data: something that can be pickled
        @type threshold: int

        @param key: identification of the data item
        @param data: whatever needs to be stored
        @param threshold: time in seconds
        """
        old, old_timestamp = self.cache.get(key, default=(None, None))
        now = time.time()

        if not old or now - old_timestamp > threshold:
            self.cache[key] = (data, now)

    def load(self, key):
        """Load the stored data for the given key along with the timestamp it was stored.

        @type key: anything that can serve as a dictionary key

        @returns: (timestamp, data) if there is data for the given key, None otherwise.
        """
        return self.cache.get(key, default=None)

    @DeprecationWarning
    def retain(self):
        """Retain non-updated data on close."""
        self.retain_old = True

    @DeprecationWarning
    def discard(self):
        """Discard non-updated data on close."""
        self.retain_old = False

    def close(self):
        """Close the cache."""
        self.cache.close()

        logging.info('closing the file cache at %s', self.filename)
