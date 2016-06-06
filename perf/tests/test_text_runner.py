import itertools
import unittest

import perf
from perf import tests


def noop():
    pass


class TestTextRunner(unittest.TestCase):
    def create_runner(self):
        runner = perf.TextRunner(3)
        runner.timer = iter(itertools.count()).__next__
        return runner

    def test_range(self):
        runner = self.create_runner()
        self.assertEqual(list(runner.range()),
                         [(True, 0),
                          (False, 0),
                          (False, 1),
                          (False, 2)])

    def test_bench_func(self):
        runner = self.create_runner()

        with tests.capture_stdout() as stdout:
            runner.bench_func(noop)
        self.assertEqual(stdout.getvalue(),
                         "Warmup 1: 1.00 sec\n"
                         "Run 1: 1.00 sec\n"
                         "Run 2: 1.00 sec\n"
                         "Run 3: 1.00 sec\n")

    def test_done_json(self):
        runner = self.create_runner()
        runner.json = True

        with tests.capture_stderr() as stderr:
            runner.bench_func(noop)
        self.assertEqual(stderr.getvalue(),
                         "Warmup 1: 1.00 sec\n"
                         "Run 1: 1.00 sec\n"
                         "Run 2: 1.00 sec\n"
                         "Run 3: 1.00 sec\n")

        with tests.capture_stdout() as stdout:
            runner.done()
        self.assertEqual(stdout.getvalue(),
                         runner.result.json()+'\n')


if __name__ == "__main__":
    unittest.main()
