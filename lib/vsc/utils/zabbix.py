
# -*- encoding: utf-8 -*-
#
# Copyright 2012-2022 Ghent University
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
This module adapts the nagios module so its output can be interpreted by Zabbix.

@author: Samuel Moors (Vrije Universiteit Brussel)
"""
from __future__ import print_function

import json
import sys

from vsc.utils.nagios import SimpleNagios, NagiosReporter


class SimpleZabbix(SimpleNagios):
    """Class to allow easy interaction with Zabbix related code"""

    def __init__(self, **kwargs):
        """Initialise message and perfdata"""
        super(SimpleZabbix, self)._init(reporterclass=ZabbixReporter, **kwargs)

    def __str__(self):
        """__str__ determines how the data is written to the cache"""
        processed_dict = {key: value for (key, value) in self.__dict__.items() if not key.startswith('_')}
        return json.dumps(processed_dict)


class ZabbixReporter(NagiosReporter):
    """Reporting class for Zabbix reports"""

    def print_report_and_exit(self, timestamp, nagios_exit_code, nagios_exit_string, nagios_message):
        """Print the zabbix report and exit"""
        json.dump([timestamp, nagios_exit_string, json.loads(nagios_message)], sys.stdout)
        self.log.info("Zabbix check cache file %s contents delivered: %s", self.filename, nagios_message)
        sys.exit(nagios_exit_code)

