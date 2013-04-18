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
vsc-utils base distribution setup.py

@author: Stijn De Weirdt (Ghent University)
@author: Andy Georges (Ghent University)
"""
import shared_setup
from shared_setup import ag, jt, sdw


def remove_bdist_rpm_source_file():
    """List of files to remove from the (source) RPM."""
    return ['lib/vsc/__init__.py']


shared_setup.remove_extra_bdist_rpm_files = remove_bdist_rpm_source_file
shared_setup.SHARED_TARGET.update({
    'url': 'https://github.ugent.be/hpcugent/vsc-utils',
    'download_url': 'https://github.ugent.be/hpcugent/vsc-utils'
})


PACKAGE = {
    'name': 'vsc-utils',
    'version': '1.0',
    'author': [ag, sdw],
    'maintainer': [ag, sdw],
    'packages': ['vsc', 'vsc.utils'],
    'namespace_packages': ['vsc', 'vsc.utils'],
    'provides': ['python-vsc-packages-utils = 0.11'],
    'scripts': [],
    'install_requires': [
        'vsc-base >= 0.90',
        'lockfile >= 0.9.1',
    ],
}

if __name__ == '__main__':
    shared_setup.action_target(PACKAGE)
