#
# Copyright 2024-2024 Ghent University
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
Utilities for sending data like netcat utility.

@author Wouter Depypere (Ghent University)
"""

import logging
import socket

def connect_and_send(host, port, data, timeout=10):
    """
    connect to a host with given timeout and write data to it.
    data can be:
     - bytes
     - string
     - list of strings

    timeout value is counted for the entire connection so includes
    sending of data.
    """
    # convert list to string if needed
    if isinstance(data, list):
        data = "".join(data)

    # make sure data is bytes
    if isinstance(data, str):
        data = data.encode('utf-8')

    logging.debug("connection to %s:%s with a timeout of %s", host, port, timeout)
    with socket.create_connection((host, port), timeout=timeout) as sock:
        logging.debug("sending data: %s", data)
        sock.sendall(data)
