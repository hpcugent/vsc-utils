#
# Copyright 2019-2019 Ghent University
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
Ssh helper class
"""

import os
import logging
import paramiko
import socket

class Ssh_util(object):
    """Helper class for ssh connections."""

    def __init__(self, host=None, user=None, passwd=None, port=22, agent_forwarding=False,
                 ssh_config=False, connection_timeout=10, command_timeout=60):
        """constructor"""
        self.host = host
        self.port = port

        self.user=user
        self.passwd = passwd

        self.conn_timeout = connection_timeout
        self.comm_timeout = command_timeout

        self.ssh_config = ssh_config
        self.agent_forw = agent_forwarding
        self.proxy = None

        self.client = None

    def _load_user_config(self):
        """Read proxy commands from local ssh config file."""
        ssh_config_file = os.path.expanduser("~/.ssh/config")

        if os.path.exists(ssh_config_file):
            conf = paramiko.SSHConfig()
            with open(ssh_config_file) as f:
                conf.parse(f)

            host_config = conf.lookup(self.host)
            if 'proxycommand' in host_config:
                self.proxy = paramiko.ProxyCommand(host_config['proxycommand'])

    def connect(self):
        """Create a connection to a host."""
        self.client = paramiko.SSHClient()

        logging.debug("Establishing ssh connection to %s", self.host)
        if self.ssh_config:
            self._load_user_config()

        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.load_system_host_keys()

        try:
            if self.passwd:
                self.client.connect(hostname=self.host, username=self.user, timeout=self.conn_timeout,
                                    sock=self.proxy, allow_agent=False)
            else:
                self.client.connect(hostname=self.host, timeout=self.conn_timeout, sock=self.proxy)


        except paramiko.AuthenticationException:
            logging.error("Authentication to host %s failed, please verify your credentials.", self.host)
            self.disconnect()
            return False

        except paramiko.SSHException as sshException:
            logging.error("Could not establish SSH connection to %s: %s", self.host, sshException)
            self.disconnect()
            return False

        except socket.timeout:
            logging.error("Connection timed out to host: %s", self.host)
            self.disconnect()
            return False

        except Exception as ex:
            logging.error("Problem occured trying to connect to %s error: %s", self.host, ex)
            self.disconnect()
            return False

        return True

    def disconnect(self):
        """disconnect"""
        logging.debug('Disconnecting to %s', self.host)
        self.client.close()

    def testconnect(self):
        """Create a connection."""
        logging.debug('Testing connection to %s', self.host)
        if self.connect():
            logging.debug("Connection seems fine.")
            self.disconnect()
            return True
        else:
            logging.debug("Could not connect.")
            self.disconnect()
            return False

    def run_commands(self, commands):
        """run a list of commands"""
        if not isinstance(commands, list):
            logging.error('commands given is not a list.')
            raise ValueError('commands given is not a list.')

        if self.connect():
            output = []
            for command in commands:
                logging.debug("Executing command: %s", command)

                if self.agent_forw:
                    # enable credential forwarding for this session
                    session = self.client.get_transport().open_session()
                    paramiko.agent.AgentRequestHandler(session)

                try:
                    # Don't need stdin
                    _, stdout, stderr = self.client.exec_command(command, self.comm_timeout)
                    exit_status = stdout.channel.recv_exit_status()

                except Exception as ex:
                    logging.error('Could not run command %s. error: %s', command, ex)
                    exit_status = 1

                try:
                    ssh_stdout = stdout.read().strip()
                except Exception as ex:
                    logging.error('Could not read from stdout. error: %s', ex)
                    exit_status = 1
                    ssh_stdout = ex

                try:
                    ssh_stderr = stderr.read().strip()
                except:
                    logging.error('Could not read from stderr. error: %s', ex)
                    exit_status = 1
                    ssh_stderr = ex

                if exit_status != 0:
                    logging.error("Command failed: %s. stdout: %s stderr: %s",
                                  command, ssh_stdout, ssh_stderr)
                    self.disconnect()
                    return exit_status, ssh_stderr

                else:
                    output.append(ssh_stdout)

            self.disconnect()
            return 0, output

        else:
            logging.error("Could not establish SSH connection")
            return 1, 'Could not establish SSH connection'
