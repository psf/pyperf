import itertools
import unittest

import perf.text_runner
from perf import tests


def noop():
    pass


class TestTextRunner(unittest.TestCase):
    def test_bench_func(self):
        def fake_timer():
            t = fake_timer.value
            fake_timer.value += 1
            return t
        fake_timer.value = 0

        runner = perf.text_runner.TextRunner(3)
        runner.parse_args([])
        runner.timer = fake_timer
        runner.verbose = True
        runner.json = True

        with tests.capture_stdout() as stdout:
            with tests.capture_stderr() as stderr:
                runner.bench_func(noop)
        self.assertEqual(stderr.getvalue(),
                         "Warmup 1: 1.00 sec\n"
                         "Run 1: 1.00 sec\n"
                         "Run 2: 1.00 sec\n"
                         "Run 3: 1.00 sec\n"
                         "Average: 1.00 sec +- 0.00 sec "
                             "(min: 1.00 sec, max: 1.00 sec) "
                             "(3 samples)\n")
        self.assertEqual(stdout.getvalue(),
                         runner.result.json()+'\n')


if __name__ == "__main__":
    unittest.main()
