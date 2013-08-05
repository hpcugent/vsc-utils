# -*- encoding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import test.cache as tc
import test.nagios as tn
import test.nagios_results as tr
import unittest


from vsc.utils import fancylogger
fancylogger.logToScreen(enable=False)

suite = unittest.TestSuite([x.suite() for  x in (tc, tn, tr)])

try:
    import xmlrunner
    rs = xmlrunner.XMLTestRunner(output="test-reports").run(suite)
except ImportError, err:
    rs = unittest.TextTestRunner().run(suite)

if not rs.wasSuccessful():
    sys.exit(1)
