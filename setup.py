#!/usr/bin/env python
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
vsc-utils base distribution setup.py

@author: Stijn De Weirdt (Ghent University)
@author: Andy Georges (Ghent University)
"""
import vsc.install.shared_setup as shared_setup
from vsc.install.shared_setup import ag, sdw


def remove_bdist_rpm_source_file():
    """List of files to remove from the (source) RPM."""
    return ['lib/vsc/__init__.py', 'lib/vsc/utils/__init__.py']


shared_setup.remove_extra_bdist_rpm_files = remove_bdist_rpm_source_file
shared_setup.SHARED_TARGET.update({
    'url': 'https://github.ugent.be/hpcugent/vsc-utils',
    'download_url': 'https://github.ugent.be/hpcugent/vsc-utils'
})

PACKAGE = {
    'name': 'vsc-utils',
    'version': '1.6',
    'author': [ag, sdw],
    'maintainer': [ag, sdw],
    'packages': ['vsc', 'vsc.utils'],
    'namespace_packages': ['vsc', 'vsc.utils'],
    'provides': ['python-vsc-packages-utils = 0.11'],
    'scripts': [],
    'install_requires': [
        'vsc-base >= 1.6.3',
        'lockfile >= 0.9.1',
        'netifaces',
        'jsonpickle',
        'crypto',
    ],
}

if __name__ == '__main__':
    shared_setup.action_target(PACKAGE)
