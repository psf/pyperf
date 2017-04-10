import perf
from perf import _cli as cli
from perf.tests import unittest


class CLITests(unittest.TestCase):
    def test_format_result(self):
        run = perf.Run([1.0, 1.5, 2.0],
                       warmups=[(1, 3.0)],
                       metadata={'name': 'mybench'},
                       collect_metadata=False)
        bench = perf.Benchmark([run])
        self.assertEqual(cli.format_result_value(bench),
                         '1.50 sec +- 0.50 sec')
        self.assertEqual(cli.format_result(bench),
                         'Mean +- std dev: 1.50 sec +- 0.50 sec')

    def test_format_result_calibration(self):
        run = perf.Run([], warmups=[(100, 1.0)],
                       metadata={'name': 'bench', 'loops': 100},
                       collect_metadata=False)
        bench = perf.Benchmark([run])
        self.assertEqual(cli.format_result_value(bench),
                         '<calibration: 100 loops>')
        self.assertEqual(cli.format_result(bench),
                         'Calibration: 100 loops')
        self.assertRaises(ValueError, bench.median)


if __name__ == "__main__":
    unittest.main()
