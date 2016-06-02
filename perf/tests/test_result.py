import unittest

import perf
from perf.result import RunResult, Results


class TestResult(unittest.TestCase):
    def test_run_result(self):
        run = RunResult([1.0, 1.5, 2.0], 1000)
        self.assertEqual(run.values, [1.0, 1.5, 2.0])
        self.assertEqual(run.loops, 1000)
        self.assertEqual(str(run), '1.50 sec +- 0.50 sec')

    def test_run_result_json(self):
        run = RunResult([1.0, 1.5, 2.0], loops=1000, warmup=1)
        run = RunResult.from_json(run.json())
        self.assertEqual(run.values, [1.0, 1.5, 2.0])
        self.assertEqual(run.loops, 1000)
        self.assertEqual(run.warmup, 1)

    def test_results(self):
        runs = [RunResult([1.0], loops=100),
                RunResult([1.5], loops=100),
                RunResult([2.0], loops=100)]
        results = Results(runs, "name", {"key": "value"})
        self.assertEqual(results.runs, runs)
        self.assertEqual(results.name, "name")
        self.assertEqual(results.metadata, {"key": "value"})
        self.assertEqual(str(results),
                         'name: 3 runs x 1 sample x 100 loops: '
                         '1.50 sec +- 0.50 sec')


if __name__ == "__main__":
    unittest.main()
