import unittest

import pyperf
from pyperf import _cli as cli


class CLITests(unittest.TestCase):
    def test_format_result(self):
        run = pyperf.Run([1.0, 1.5, 2.0],
                         warmups=[(1, 3.0)],
                         metadata={'name': 'mybench'},
                         collect_metadata=False)
        bench = pyperf.Benchmark([run])
        self.assertEqual(cli.format_result_value(bench),
                         '1.50 sec +- 0.50 sec')
        self.assertEqual(cli.format_result(bench),
                         'Mean +- std dev: 1.50 sec +- 0.50 sec')

    def test_format_result_calibration(self):
        run = pyperf.Run([], warmups=[(100, 1.0)],
                         metadata={'name': 'bench', 'loops': 100},
                         collect_metadata=False)
        bench = pyperf.Benchmark([run])
        self.assertEqual(cli.format_result_value(bench),
                         '<calibration: 100 loops>')
        self.assertEqual(cli.format_result(bench),
                         'Calibration: 100 loops')
        self.assertRaises(ValueError, bench.median)

    def _quota_bench(self, metadata):
        md = {'name': 'bench'}
        md.update(metadata)
        runs = [pyperf.Run([1.0, 1.0, 1.0], metadata=md,
                           collect_metadata=False)
                for _ in range(3)]
        return pyperf.Benchmark(runs)

    def test_checks_warns_on_cpu_quota(self):
        # a run under a CPU quota must warn even though the values look stable
        bench = self._quota_bench({'cpu_quota': '2 CPUs'})
        text = '\n'.join(cli.format_checks(bench))
        self.assertIn('CPU quota', text)
        self.assertIn('2 CPUs', text)

    def test_checks_no_cpu_quota(self):
        bench = self._quota_bench({})
        text = '\n'.join(cli.format_checks(bench))
        self.assertNotIn('CPU quota', text)


if __name__ == "__main__":
    unittest.main()
