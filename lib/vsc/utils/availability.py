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
Module for high-availability functionality.

@author: Andy Georges (Ghent University)
"""

from netifaces import interfaces, ifaddresses, AF_INET


def proceed_on_ha_service(host_ip):
    """Verifies that we are actually executing on the expected host.

    @type host: string

    @param host: IP address of the high-availability host (the failover alias)

    @returns: True if we are on the correct host, False if not.
    """

    machine_addresses = []
    for iface_name in interfaces():
        addresses = [i['addr'] for i in ifaddresses(iface_name).setdefault(AF_INET, [{'addr': None}]) if i['addr']]
        machine_addresses.extend(addresses)

    return host_ip in machine_addresses
