import os.path
import sys
import unittest

from pyperf.tests import get_output


class SystemTests(unittest.TestCase):
    def test_show(self):
        args = [sys.executable, '-m', 'pyperf', 'system', 'show']
        proc = get_output(args)

        regex = ('(Run "%s -m pyperf system tune" to tune the system configuration to run benchmarks'
                 '|OK! System ready for benchmarking'
                 '|WARNING: no operation available for your platform)'
                 % os.path.basename(sys.executable))
        self.assertRegex(proc.stdout, regex, msg=proc)

        # The return code is either 0 if the system is tuned or 2 if the
        # system isn't
        # Also it can return 1 if /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
        # is not available
        self.assertIn(proc.returncode, (0, 1, 2), msg=proc)


if __name__ == "__main__":
    unittest.main()
