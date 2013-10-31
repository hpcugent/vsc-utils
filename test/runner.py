import os
import sys

# make sure what we're testing is first in the path
sys.path.insert(0, os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(__file__))), 'lib'))
sys.path.insert(0, '')


import test.cache as tc
import test.nagios as tn
import test.nagios_results as tr
import test.nagios_simple as ts
import unittest


from vsc.utils import fancylogger
fancylogger.logToScreen(enable=False)

suite = unittest.TestSuite([x.suite() for x in (tc, tn, tr, ts)])

try:
    import xmlrunner
    rs = xmlrunner.XMLTestRunner(output="test-reports").run(suite)
except ImportError, err:
    rs = unittest.TextTestRunner().run(suite)

if not rs.wasSuccessful():
    sys.exit(1)
