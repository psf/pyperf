import os.path
import sys

from perf.tests import get_output
from perf.tests import unittest


class SystemTests(unittest.TestCase):
    def test_show(self):
        args = [sys.executable, '-m', 'perf', 'system', 'show']
        proc = get_output(args)

        regex = ('(Run "%s -m perf system tune" to tune the system configuration to run benchmarks'
                 '|OK! System ready for benchmarking'
                 '|WARNING: no operation available for your platform)'
                 % os.path.basename(sys.executable))
        self.assertRegex(proc.stdout, regex, msg=proc)

        # The return code is either 0 if the system is tuned or 2 if the
        # system isn't
        self.assertIn(proc.returncode, (0, 2), msg=proc)


if __name__ == "__main__":
    unittest.main()
