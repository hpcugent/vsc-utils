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
The graphyte project lives on GitHub here:
https://github.com/benhoyt/graphyte

It is redistributed here for ease of use. It has been adapted to vsc standards.

Send data to Graphite metrics server (synchronously or on a background thread).
This code is licensed under a permissive MIT license -- see LICENSE.txt in the
original github repository.

"""

import atexit
import logging
import queue
import socket
import threading
import time

__all__ = ['Sender', 'init', 'send']

__version__ = '1.7.1'

default_sender = None
logger = logging.getLogger(__name__)


def _has_whitespace(value):
    return not value or value.split(None, 1)[0] != value


class Sender:
    def __init__(self, host, port=2003, prefix=None, timeout=5, interval=None,
                 queue_size=None, log_sends=False, protocol='tcp',
                 batch_size=1000, tags=None, raise_send_errors=False):
        """Initialize a Sender instance, starting the background thread to
        send messages at given interval (in seconds) if "interval" is not
        None. Send at most "batch_size" messages per socket send operation.
        Default protocol is TCP; use protocol='udp' for UDP.

        Use "tags" to specify common or default tags for this Sender, which
        are sent with each metric along with any tags passed to send().
        """

        self.host = host
        self.port = port
        self.prefix = prefix
        self.timeout = timeout
        self.interval = interval
        self.log_sends = log_sends
        self.protocol = protocol
        self.batch_size = batch_size
        if tags is None:
            self.tags = {}
        else:
            self.tags = tags
        self.raise_send_errors = raise_send_errors

        if self.interval is not None:
            if raise_send_errors:
                raise ValueError('raise_send_errors must be disabled when interval is set')
            if queue_size is None:
                queue_size = int(round(interval)) * 100
            self._queue = queue.Queue(maxsize=queue_size)
            self._thread = threading.Thread(target=self._thread_loop)
            self._thread.daemon = True
            self._thread.start()
            atexit.register(self.stop)

    def __del__(self):
        self.stop()

    def stop(self):
        """Tell the sender thread to finish and wait for it to stop sending
        (should be at most "timeout" seconds).
        """
        if self.interval is not None:
            self._queue.put_nowait(None)
            self._thread.join()
            self.interval = None

    def build_message(self, metric, value, timestamp, tags=None):
        """Build a Graphite message to send and return it as a byte string."""
        if tags is None:
            tags = {}
        if _has_whitespace(metric):
            raise ValueError('"metric" must not have whitespace in it')
        if not isinstance(value, (int, float)):
            raise TypeError('"value" must be an int or a float, not a %s',
                type(value).__name__)

        all_tags = self.tags.copy()
        all_tags.update(tags)
        tags_strs = [f';{k}={v}' for k, v in sorted(all_tags.items())]
        if any(_has_whitespace(t) for t in tags_strs):
            raise ValueError('"tags" keys and values must not have whitespace in them')
        tags_suffix = ''.join(tags_strs)

        prefix = self.prefix + '.' if self.prefix else ''
        message = f"{prefix}{metric}{tags_suffix} {value} {int(round(timestamp))}\n"
        message = message.encode('utf-8')
        return message

    def send(self, metric, value, timestamp=None, tags=None):
        """Send given metric and (int or float) value to Graphite host.
        Performs send on background thread if "interval" was specified when
        creating this Sender.

        If a "tags" dict is specified, send the tags to the Graphite host along
        with the metric, in addition to any default tags passed to Sender() --
        the tags argument here overrides any default tags.
        """
        if tags is None:
            tags = {}
        if timestamp is None:
            timestamp = time.time()
        message = self.build_message(metric, value, timestamp, tags=tags)

        if self.interval is None:
            self.send_socket(message)
        else:
            try:
                self._queue.put_nowait(message)
            except queue.Full:
                logger.error('queue full when sending %s', message)

    def send_message(self, message):
        if self.protocol == 'tcp':
            with socket.create_connection((self.host, self.port), self.timeout) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.sendall(message)
        elif self.protocol == 'udp':
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.sendto(message, (self.host, self.port))
        else:
            raise ValueError('"protocol" must be \'tcp\' or \'udp\', not %s', self.protocol)

    def send_socket(self, message):
        """Low-level function to send message bytes to this Sender's socket.
        You should usually call send() instead of this function (unless you're
        subclassing or writing unit tests).
        """
        if self.log_sends:
            start_time = time.time()
        try:
            self.send_message(message)
        except Exception as error:
            if self.raise_send_errors:
                raise
            logger.error('error sending message %s: %s', message, error)
        else:
            if self.log_sends:
                elapsed_time = time.time() - start_time
                logger.info('sent message %s to %s:%s in %s seconds',
                        message, self.host, self.port, elapsed_time)

    def _thread_loop(self):
        """Background thread used when Sender is in asynchronous/interval mode."""
        last_check_time = time.time()
        messages = []
        while True:
            # Get first message from queue, blocking until the next time we
            # should be sending
            time_since_last_check = time.time() - last_check_time
            time_till_next_check = max(0, self.interval - time_since_last_check)
            try:
                message = self._queue.get(timeout=time_till_next_check)
            except queue.Empty:
                pass
            else:
                if message is None:
                    # None is the signal to stop this background thread
                    break
                messages.append(message)

                # Get any other messages currently on queue without blocking,
                # paying attention to None ("stop thread" signal)
                should_stop = False
                while True:
                    try:
                        message = self._queue.get_nowait()
                    except queue.Empty:
                        break
                    if message is None:
                        should_stop = True
                        break
                    messages.append(message)
                if should_stop:
                    break

            # If it's time to send, send what we've collected
            current_time = time.time()
            if current_time - last_check_time >= self.interval:
                last_check_time = current_time
                for i in range(0, len(messages), self.batch_size):
                    batch = messages[i:i + self.batch_size]
                    self.send_socket(b''.join(batch))
                messages = []

        # Send any final messages before exiting thread
        for i in range(0, len(messages), self.batch_size):
            batch = messages[i:i + self.batch_size]
            self.send_socket(b''.join(batch))

def init(*args, **kwargs):
    """Initialize default Sender instance with given args."""
    global default_sender
    default_sender = Sender(*args, **kwargs)


def send(*args, **kwargs):
    """Send message using default Sender instance."""
    default_sender.send(*args, **kwargs)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('metric',
                        help='name of metric to send')
    parser.add_argument('value', type=float,
                        help='numeric value to send')
    parser.add_argument('-s', '--server', default='localhost',
                        help='hostname of Graphite server to send to, default %(default)s')
    parser.add_argument('-p', '--port', type=int, default=2003,
                        help='port to send message to, default %(default)d')
    parser.add_argument('-u', '--udp', action='store_true',
                        help='send via UDP instead of TCP')
    parser.add_argument('-t', '--timestamp', type=int,
                        help='Unix timestamp for message (defaults to current time)')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help="quiet mode (don't log send to stdout)")
    args = parser.parse_args()

    if not args.quiet:
        logging.basicConfig(level=logging.INFO, format='%(message)s')

    sender = Sender(args.server, port=args.port, log_sends=not args.quiet,
                    protocol='udp' if args.udp else 'tcp')
    sender.send(args.metric, args.value, timestamp=args.timestamp)
