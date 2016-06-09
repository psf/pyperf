import itertools
import tempfile

import perf.text_runner
from perf import tests
from perf.tests import mock
from perf.tests import unittest


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

    def create_text_runner(self, args):
        runner = perf.text_runner.TextRunner()
        # disable CPU affinity to not pollute stdout
        runner._cpu_affinity = lambda: None
        runner.parse_args(args)
        return runner

    def test_bench_func(self):
        runner = self.create_text_runner(['--raw', '--json', '--verbose'])

        with mock.patch('perf.perf_counter', self.create_fake_timer()):
            with tests.capture_stdout() as stdout:
                with tests.capture_stderr() as stderr:
                    runner.bench_func(noop)

        self.assertRegex(stderr.getvalue(),
                         r'^(?:Set affinity to isolated CPUs: \[[0-9 ,]+\]\n)?'
                         r'Warmup 1: 1\.00 sec\n'
                         r'Run 1: 1\.00 sec\n'
                         r'Run 2: 1\.00 sec\n'
                         r'Run 3: 1\.00 sec\n'
                         r'Metadata:\n'
                         r'(- .*\n)+'
                         r'\n'
                         r'Average: 1\.00 sec \+- 0\.00 sec '
                             r'\(3 samples\)\n$')

        self.assertEqual(stdout.getvalue(),
                         runner.result.json())

    def test_json_file(self):
        with tempfile.NamedTemporaryFile('wb+') as tmp:
            runner = self.create_text_runner(['--raw', '-v',
                                              '--json-file', tmp.name])

            with mock.patch('perf.perf_counter', self.create_fake_timer()):
                with tests.capture_stdout() as stdout:
                    with tests.capture_stderr() as stderr:
                        runner.bench_func(noop)

            self.assertRegex(stdout.getvalue(),
                             r'^(?:Set affinity to isolated CPUs: \[[0-9 ,]+\]\n)?'
                             r'Warmup 1: 1\.00 sec\n'
                             r'Run 1: 1\.00 sec\n'
                             r'Run 2: 1\.00 sec\n'
                             r'Run 3: 1\.00 sec\n'
                             r'Metadata:\n'
                             r'(- .*\n)+'
                             r'\n'
                             r'Average: 1\.00 sec \+- 0\.00 sec '
                                r'\(3 samples\)\n$')

            self.assertEqual(stderr.getvalue(), '')

            tmp.seek(0)
            self.assertEqual(tmp.read().decode('utf-8'),
                             runner.result.json())

    def test_cpu_affinity(self):
        runner = perf.text_runner.TextRunner()
        runner.parse_args([])

        # with isolated CPUs
        with mock.patch('os.sched_setaffinity', create=True) as mock_setaffinity:
            with mock.patch('io.open') as mock_open:
                mock_file = mock_open.return_value
                mock_file.readline.return_value = '1-2'
                runner._cpu_affinity()
        mock_setaffinity.assert_called_once_with(0, [1, 2])

        # without isolated CPU
        with mock.patch('os.sched_setaffinity', create=True) as mock_setaffinity:
            with mock.patch('io.open') as mock_open:
                mock_file = mock_open.return_value
                mock_file.readline.return_value = ''
                runner._cpu_affinity()
        self.assertEqual(mock_setaffinity.call_count, 0)


if __name__ == "__main__":
    unittest.main()
