#
# Copyright 2018-2024 Ghent University
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
Unit tests for vsc.utils.timestamp

@author: Jens Timmerman (Ghent University)
"""

import mock

from datetime import datetime

from vsc.install.testing import TestCase
from vsc.utils.dateandtime import utc
from vsc.utils.run import run

from vsc.utils.timestamp import convert_to_datetime, convert_to_unix_timestamp, convert_timestamp
from vsc.utils.timestamp import retrieve_timestamp_with_default, DEFAULT_TIMESTAMP


class TestTimestamp(TestCase):
    """Unit tests for timestamp module"""

    # TODO: test with 201710290205  ( ambigious )
    def test_convert_to_datetime(self):
        date = datetime(1970, 1, 1, tzinfo=utc)
        self.assertEqual(convert_to_datetime("19700101"), date)
        self.assertEqual(convert_to_datetime("0000000000"), date)
        self.assertEqual(convert_to_datetime(0), date)
        self.assertEqual(convert_to_datetime("197001010000"), date)
        self.assertEqual(convert_to_datetime("19700101000000Z"), date)
        self.assertEqual(convert_to_datetime(date), date)

        date = datetime(2018, 3, 25, 0, 0, tzinfo=utc)
        self.assertEqual(convert_to_datetime("20180325"), date)
        date = datetime(2018, 3, 25, 1, 5, tzinfo=utc)
        self.assertEqual(convert_to_datetime("1521939900"), date)
        self.assertEqual(convert_to_datetime(1521939900), date)
        self.assertEqual(convert_to_datetime("201803250105"), date)
        self.assertEqual(convert_to_datetime("20180325010500Z"), date)
        self.assertEqual(convert_to_datetime(date), date)

        date = datetime(2017, 10, 29, 0, 0, tzinfo=utc)
        self.assertEqual(convert_to_datetime("20171029"), date)
        date = datetime(2017, 10, 29, 1, 5, tzinfo=utc)
        self.assertEqual(convert_to_datetime("1509239100"), date)
        self.assertEqual(convert_to_datetime(1509239100), date)
        self.assertEqual(convert_to_datetime("201710290105"), date)
        self.assertEqual(convert_to_datetime("20171029010500Z"), date)
        self.assertEqual(convert_to_datetime(date), date)

    def test_convert_to_unix_timestamp(self):
        _, out = run(["date", "+%s"])
        nowts = convert_to_unix_timestamp()
        self.assertTrue(abs(nowts - int(out.strip())) < 2)

        date = 0
        self.assertEqual(convert_to_unix_timestamp("19700101"), date)
        self.assertEqual(convert_to_unix_timestamp("0000000000"), date)
        self.assertEqual(convert_to_unix_timestamp(0), date)
        self.assertEqual(convert_to_unix_timestamp("197001010000"), date)
        self.assertEqual(convert_to_unix_timestamp("19700101000000Z"), date)
        self.assertEqual(convert_to_unix_timestamp(datetime(1970, 1, 1)), date)

        date = 1521936000
        self.assertEqual(convert_to_unix_timestamp("20180325"), date)
        date = 1521939900
        self.assertEqual(convert_to_unix_timestamp("1521939900"), date)
        self.assertEqual(convert_to_unix_timestamp(1521939900), date)
        self.assertEqual(convert_to_unix_timestamp("201803250105"), date)
        self.assertEqual(convert_to_unix_timestamp("201803250105"), date)
        self.assertEqual(convert_to_unix_timestamp("20180325010500Z"), date)
        self.assertEqual(convert_to_unix_timestamp(datetime(2018, 3, 25, 1, 5)), date)

        date = 1509239100
        self.assertEqual(convert_to_unix_timestamp("1509239100"), date)
        self.assertEqual(convert_to_unix_timestamp(1509239100), date)
        self.assertEqual(convert_to_unix_timestamp("201710290105"), date)
        self.assertEqual(convert_to_unix_timestamp("20171029010500Z"), date)
        self.assertEqual(convert_to_unix_timestamp(date), date)

    def test_convert_timestamp(self):
        """tests for convert_timestamp"""
        datet = datetime(1970, 1, 1, tzinfo=utc)
        date = "19700101000000Z"
        self.assertEqual(convert_timestamp("19700101"), (datet, date))
        self.assertEqual(convert_timestamp("0000000000"), (datet, date))
        self.assertEqual(convert_timestamp(0), (datet, date))
        self.assertEqual(convert_timestamp("197001010000"), (datet, date))
        self.assertEqual(convert_timestamp("19700101000000Z"), (datet, date))
        self.assertEqual(convert_timestamp(datetime(1970, 1, 1)), (datet, date))

        datet = datetime(2018, 3, 25, 0, 0, tzinfo=utc)
        date = "20180325000000Z"
        self.assertEqual(convert_timestamp("20180325"), (datet, date))
        datet = datetime(2018, 3, 25, 1, 5, tzinfo=utc)
        date = "20180325010500Z"
        self.assertEqual(convert_timestamp("1521939900"), (datet, date))
        self.assertEqual(convert_timestamp(1521939900), (datet, date))
        self.assertEqual(convert_timestamp("201803250105"), (datet, date))
        self.assertEqual(convert_timestamp("20180325010500Z"), (datet, date))
        self.assertEqual(convert_timestamp(datetime(2018, 3, 25, 1, 5)), (datet, date))

        datet = datetime(2017, 10, 29, 1, 5, tzinfo=utc)
        date = "20171029010500Z"
        self.assertEqual(convert_timestamp("1509239100"), (datet, date))
        self.assertEqual(convert_timestamp(1509239100), (datet, date))
        self.assertEqual(convert_timestamp("201710290105"), (datet, date))
        self.assertEqual(convert_timestamp("20171029010500Z"), (datet, date))
        self.assertEqual(convert_timestamp(date), (datet, date))

    @mock.patch("vsc.utils.timestamp.read_timestamp")
    def test_retrieve_timestamp(self, mock_read_timestamp):
        """Test for the filestamp retrieval."""
        mock_read_timestamp.return_value = None
        self.assertEqual(convert_to_unix_timestamp(DEFAULT_TIMESTAMP), retrieve_timestamp_with_default("f")[0])

        read_ts = "203412130101"
        mock_read_timestamp.return_value = read_ts

        start_ts = "20140102"
        default_ts = "20150103"
        self.assertEqual(
            convert_to_unix_timestamp(start_ts), retrieve_timestamp_with_default("f", start_timestamp=start_ts)[0]
        )
        self.assertEqual(
            convert_to_unix_timestamp(read_ts), retrieve_timestamp_with_default("f", default_timestamp=default_ts)[0]
        )

        self.assertEqual(utc, retrieve_timestamp_with_default("f", default_timestamp="20140102")[1].tzinfo)

        mock_read_timestamp.return_value = None
        self.assertEqual(
            convert_to_unix_timestamp(default_ts), retrieve_timestamp_with_default("f", default_timestamp=default_ts)[0]
        )
