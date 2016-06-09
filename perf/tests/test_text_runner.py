import itertools
import tempfile
import unittest

import perf.text_runner
from perf import tests
from perf.tests import mock


def noop():
    pass


class TestTextRunner(unittest.TestCase):
    def create_fake_timer(self):
        def fake_timer():
            t = fake_timer.value
            fake_timer.value += 1
            return t
        fake_timer.value = 0
        return fake_timer

    def test_bench_func(self):
        runner = perf.text_runner.TextRunner()
        runner.parse_args(['--raw', '--json', '--verbose'])

        with mock.patch('perf.perf_counter', self.create_fake_timer()):
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
                         runner.result.json())

    def test_json_file(self):
        runner = perf.text_runner.TextRunner()

        with tempfile.NamedTemporaryFile('wb+') as tmp:
            runner.parse_args(['--raw', '-v', '--json-file', tmp.name])

            with mock.patch('perf.perf_counter', self.create_fake_timer()):
                with tests.capture_stdout() as stdout:
                    with tests.capture_stderr() as stderr:
                        runner.bench_func(noop)

            self.assertEqual(stdout.getvalue(),
                             "Warmup 1: 1.00 sec\n"
                             "Run 1: 1.00 sec\n"
                             "Run 2: 1.00 sec\n"
                             "Run 3: 1.00 sec\n"
                             "Average: 1.00 sec +- 0.00 sec "
                                 "(min: 1.00 sec, max: 1.00 sec) "
                                 "(3 samples)\n")

            self.assertEqual(stderr.getvalue(), '')

            tmp.seek(0)
            self.assertEqual(tmp.read().decode('utf-8'),
                             runner.result.json())


if __name__ == "__main__":
    unittest.main()
