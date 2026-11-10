import os.path
import sys
import unittest
from unittest import mock

from pyperf.tests import get_output


class CPUQuotaTests(unittest.TestCase):
    def _show(self, quota, throttling):
        from pyperf._system import CPUQuota

        system = mock.Mock()
        op = CPUQuota(system)
        with mock.patch('pyperf._collect_metadata.get_cgroup_cpu_quota',
                        return_value=quota), \
             mock.patch('pyperf._collect_metadata.get_cgroup_cpu_throttling',
                        return_value=throttling):
            op.show()
        states = ' '.join(call.args[0]
                          for call in system.log_state.call_args_list)
        advices = ' '.join(call.args[0]
                           for call in system.advice.call_args_list)
        return states, advices

    def test_no_quota_is_silent(self):
        states, advices = self._show(None, None)
        self.assertEqual(states, '')
        self.assertEqual(advices, '')

    def test_quota_set_but_not_throttled(self):
        states, advices = self._show(2.0, {'nr_throttled': 0,
                                           'throttled_usec': 0})
        self.assertIn('2 CPUs', states)
        self.assertNotIn('throttled', states)
        self.assertIn('CPU quota', advices)

    def test_quota_and_throttled(self):
        states, advices = self._show(2.0, {'nr_throttled': 3306,
                                           'throttled_usec': 247631465})
        self.assertIn('2 CPUs', states)
        self.assertIn('3306', states)
        self.assertIn('throttled', states.lower())
        self.assertIn('CPU quota', advices)


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
