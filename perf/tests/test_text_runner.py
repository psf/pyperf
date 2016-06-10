import itertools
import tempfile

import perf.text_runner
from perf import tests
from perf.tests import mock
from perf.tests import unittest


def check_args(loops, a, b):
    if a != 1:
        raise ValueError
    if b != 2:
        raise ValueError
    # number of loops => number of seconds
    return loops


class TestTextRunner(unittest.TestCase):
    def create_text_runner(self, args):
        runner = perf.text_runner.TextRunner()
        # disable CPU affinity to not pollute stdout
        runner._cpu_affinity = lambda: None
        runner.parse_args(args)
        return runner

    def test_bench_func(self):
        runner = self.create_text_runner(['--raw', '--json', '--verbose'])

        with tests.capture_stdout() as stdout:
            with tests.capture_stderr() as stderr:
                runner.bench_sample_func(check_args, 1, 2)

        self.assertRegex(stderr.getvalue(),
                         r'^(?:Set affinity to isolated CPUs: \[[0-9 ,]+\]\n)?'
                         r'Warmup 1: 1\.00 sec\n'
                         r'Sample 1: 1\.00 sec\n'
                         r'Sample 2: 1\.00 sec\n'
                         r'Sample 3: 1\.00 sec\n'
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

            with tests.capture_stdout() as stdout:
                with tests.capture_stderr() as stderr:
                    runner.bench_sample_func(check_args, 1, 2)

            self.assertRegex(stdout.getvalue(),
                             r'^(?:Set affinity to isolated CPUs: \[[0-9 ,]+\]\n)?'
                             r'Warmup 1: 1\.00 sec\n'
                             r'Sample 1: 1\.00 sec\n'
                             r'Sample 2: 1\.00 sec\n'
                             r'Sample 3: 1\.00 sec\n'
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
