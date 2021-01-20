#!/usr/bin/env python
##
# Copyright 2012-2020 Ghent University
#
# This file is part of vsc-utils,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://www.vscentrum.be),
# the Flemish Research Foundation (FWO) (http://www.fwo.be/en)
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
vsc-utils base distribution setup.py

@author: Stijn De Weirdt (Ghent University)
@author: Andy Georges (Ghent University)
"""
import sys

import vsc.install.shared_setup as shared_setup
from vsc.install.shared_setup import ag, sdw

install_requires = [
    'vsc-base >= 3.0.2',
    'lockfile >= 0.9.1',
    'netifaces',
    'jsonpickle',
]
if sys.version_info < (3, 0):
    # jsonpickle pulls in too new and wrong deps on CentOS 7
    install_requires.extend([
        'jsonpickle < 1.4.0'
    ])

else:
    install_requires.extend([
        'jsonpickle'
    ])


PACKAGE = {
    'version': '2.1.7',
    'author': [ag, sdw],
    'maintainer': [ag, sdw],
    'excluded_pkgs_rpm': ['vsc', 'vsc.utils'],  # vsc is default, vsc.utils is provided by vsc-base
    'tests_require': ['mock'],
    'install_requires': install_requires,
    'setup_requires': ['vsc-install >= 0.15.1'],
    'zip_safe': False,
}

if __name__ == '__main__':
    shared_setup.action_target(PACKAGE)
