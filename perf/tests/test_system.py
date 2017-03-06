import os.path
import sys

from perf.tests import get_output
from perf.tests import unittest


class SystemTests(unittest.TestCase):
    def test_show(self):
        args = [sys.executable, '-m', 'perf', 'system', 'show']
        proc = get_output(args)
        self.assertEqual(proc.returncode, 0)

        regex = ('(Run "%s -m perf system tune" to tune the system configuration to run benchmarks'
                 '|OK! System ready for benchmarking'
                 '|WARNING: no operation available for your platform)'
                 % os.path.basename(sys.executable))
        self.assertRegex(proc.stdout, regex)


if __name__ == "__main__":
    unittest.main()
