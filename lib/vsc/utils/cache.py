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
"""
Caching utilities.

@author: Andy Georges (Ghent University)
"""
try:
    import cPickle as pickle
except:
    import pickle
import gzip
import jsonpickle
import os
import time

from vsc.utils import fancylogger


class FileCache(object):
    """File cache with a timestamp safety.

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

        self.log = fancylogger.getLogger(self.__class__.__name__, fname=False)
        self.filename = filename
        self.retain_old = retain_old

        self.new_shelf = {}
        if not retain_old:
            self.log.info("Starting with a new empty cache, not retaining previous info if any.")
            self.shelf = {}
            return

        try:
            with open(self.filename, 'rb') as f:
                try:
                    g = gzip.GzipFile(mode='rb', fileobj=f)  # no context manager available in python 26 yet
                    s = g.read()
                except IOError, err:
                    self.log.error("Cannot load data from cache file %s as gzipped json", self.filename)
                    try:
                        f.seek(0)
                        self.shelf = pickle.load(f)
                    except pickle.UnpicklingError, err:
                        msg = "Problem loading pickle data from %s (corrupt data)" % (self.filename,)
                        if raise_unpickable:
                            self.log.raiseException(msg)
                        else:
                            self.log.error("%s. Continue with empty shelf: %s", msg, err)
                            self.shelf = {}
                    except (OSError, IOError):
                        self.log.raiseException("Could not load pickle data from %s", self.filename)
                else:
                    try:
                        self.shelf = jsonpickle.decode(s)
                    except ValueError, err:
                        self.log.error("Cannot decode JSON from %s [%s]", self.filename, err)
                        self.log.info("Cache in %s starts with an empty shelf", self.filename)
                        self.shelf = {}
                finally:
                    g.close()

        except (OSError, IOError, ValueError), err:
            self.log.warning("Could not access the file cache at %s [%s]", self.filename, err)
            self.shelf = {}
            self.log.info("Cache in %s starts with an empty shelf", (self.filename,))

    def update(self, key, data, threshold):
        """Update the given data if the existing data is older than the given threshold.

        @type key: something that can serve as a dictionary key (and thus can be pickled)
        @type data: something that can be pickled
        @type threshold: int

        @param key: identification of the data item
        @param data: whatever needs to be stored
        @param threshold: time in seconds
        """
        now = time.time()
        old = self.load(key)
        if old:
            (ts, _) = old
            if now - ts > threshold:
                self.new_shelf[key] = (now, data)
                return True
            else:
                self.new_shelf[key] = old
                return False
        else:
            self.new_shelf[key] = (now, data)
            return True

    def load(self, key):
        """Load the stored data for the given key along with the timestamp it was stored.

        @type key: anything that can serve as a dictionary key

        @returns: (timestamp, data) if there is data for the given key, None otherwise.
        """
        return self.new_shelf.get(key, None) or self.shelf.get(key, None)

    def retain(self):
        """Retain non-updated data on close."""
        self.retain_old = True

    def discard(self):
        """Discard non-updated data on close."""
        self.retain_old = False

    def close(self):
        """Close the cache."""
        dirname = os.path.dirname(self.filename)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        f = open(self.filename, 'wb')
        if not f:
            self.log.error('cannot open the file cache at %s for writing' % (self.filename))
        else:
            if self.retain_old:
                self.shelf.update(self.new_shelf)
                self.new_shelf = self.shelf

            g = gzip.GzipFile(mode='wb', fileobj=f)
            pickled = jsonpickle.encode(self.new_shelf)
            g.write(pickled)
            g.close()
            f.close()

            self.log.info('closing the file cache at %s' % (self.filename))
