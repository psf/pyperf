import tempfile
import textwrap

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
        runner = perf.text_runner.TextRunner('bench')
        # disable CPU affinity to not pollute stdout
        runner._cpu_affinity = lambda: None
        runner.parse_args(args)
        return runner

    def check_bench_result(self, runner, stream, result):
        self.assertRegex(stream.getvalue(),
                         r'^(calibration: .*\n)*'
                         r'(?:Set affinity to isolated CPUs: \[[0-9 ,]+\]\n)?'
                         r'Warmup 1: 1\.00 sec\n'
                         r'Raw sample 1: 1\.00 sec\n'
                         r'Raw sample 2: 1\.00 sec\n'
                         r'Raw sample 3: 1\.00 sec\n'
                         r'\n'
                         r'Metadata:\n'
                         r'(- .*\n)+'
                         r'\n'
                         r'Median \+- std dev: 1\.00 sec \+- 0\.00 sec\n$')

        # check bench_sample_func() result
        self.assertIsInstance(result, perf.Benchmark)
        self.assertEqual(result.name, 'bench')
        self.assertEqual(result.get_nrun(), 1)

    def test_bench_func_raw(self):
        def fake_timer():
            t = fake_timer.value
            fake_timer.value += 1
            return t
        fake_timer.value = 0

        runner = self.create_text_runner(['--raw', '--json',
                                          '--verbose', '--metadata'])

        with mock.patch('perf.perf_counter', fake_timer):
            with tests.capture_stdout() as stdout:
                with tests.capture_stderr() as stderr:
                    result = runner.bench_func(check_args, None, 1, 2)

        self.assertEqual(stdout.getvalue(),
                         tests.benchmark_as_json(result))

        self.check_bench_result(runner, stderr, result)

    def test_bench_sample_func_raw(self):
        runner = self.create_text_runner(['--raw', '--json',
                                          '--verbose', '--metadata'])

        with tests.capture_stdout() as stdout:
            with tests.capture_stderr() as stderr:
                result = runner.bench_sample_func(check_args, 1, 2)

        self.assertEqual(stdout.getvalue(),
                         tests.benchmark_as_json(result))

        self.check_bench_result(runner, stderr, result)

    def test_loops_calibration(self):
        def sample_func(loops):
            # number of iterations => number of microseconds
            return loops * 1e-6

        runner = self.create_text_runner(['--raw', '-vv'])

        with tests.capture_stdout() as stdout:
            with tests.capture_stderr() as stderr:
                result = runner.bench_sample_func(sample_func)

        self.assertEqual(runner.args.loops, 2 ** 17)
        self.assertEqual(result.loops, 2 ** 17)

        expected = textwrap.dedent('''
            calibration: 1 loop: 1.00 us
            calibration: 2 loops: 2.00 us
            calibration: 4 loops: 4.00 us
            calibration: 8 loops: 8.00 us
            calibration: 16 loops: 16.0 us
            calibration: 32 loops: 32.0 us
            calibration: 64 loops: 64.0 us
            calibration: 128 loops: 128 us
            calibration: 256 loops: 256 us
            calibration: 512 loops: 512 us
            calibration: 1024 loops: 1.02 ms
            calibration: 2048 loops: 2.05 ms
            calibration: 4096 loops: 4.10 ms
            calibration: 8192 loops: 8.19 ms
            calibration: 2^14 loops: 16.4 ms
            calibration: 2^15 loops: 32.8 ms
            calibration: 2^16 loops: 65.5 ms
            calibration: 2^17 loops: 131 ms
            calibration: use 2^17 loops
        ''').strip()
        self.assertIn(expected, stdout.getvalue())
        self.assertEqual(stderr.getvalue(), '')

    def test_loops_calibration_min_max_time(self):
        def sample_func(loops):
            # number of iterations => number of microseconds
            return loops * 1e-6

        runner = self.create_text_runner(['--raw', '-vv',
                                          '--min-time', '0.001',
                                          '--max-time', '1.0'])
        with tests.capture_stdout():
            with tests.capture_stderr():
                result = runner.bench_sample_func(sample_func)

        self.assertEqual(runner.args.loops, 2 ** 10)
        self.assertEqual(result.loops, 2 ** 10)

    def test_json_file_raw(self):
        with tempfile.NamedTemporaryFile('wb+') as tmp:
            runner = self.create_text_runner(['--raw', '--json-file', tmp.name,
                                              '--verbose', '--metadata'])

            with tests.capture_stdout() as stdout:
                with tests.capture_stderr() as stderr:
                    result = runner.bench_sample_func(check_args, 1, 2)

            self.check_bench_result(runner, stdout, result)

            self.assertEqual(stderr.getvalue(), '')

            tmp.seek(0)
            self.assertEqual(tmp.read().decode('utf-8'),
                             tests.benchmark_as_json(result))

    def test_cpu_affinity_setaffinity_isolcpus(self):
        runner = perf.text_runner.TextRunner('bench')
        runner.parse_args(['-v'])

        with mock.patch('os.sched_setaffinity', create=True) as mock_setaffinity:
            with mock.patch('perf._get_isolated_cpus', return_value=[1, 2]):
                with tests.capture_stdout() as stdout:
                    runner._cpu_affinity()

        self.assertEqual(runner.args.affinity, '1-2')
        self.assertEqual(stdout.getvalue(),
                         'Pin process to isolated CPUs: 1-2\n')
        mock_setaffinity.assert_called_once_with(0, [1, 2])

    def test_cpu_affinity_setaffinity_without_isolcpus(self):
        runner = perf.text_runner.TextRunner('bench')
        runner.parse_args(['-v'])

        with mock.patch('os.sched_setaffinity', create=True) as mock_setaffinity:
            with mock.patch('perf._get_isolated_cpus', return_value=None):
                runner._cpu_affinity()
        self.assertEqual(mock_setaffinity.call_count, 0)

    def test_cpu_affinity_psutil_isolcpus(self):
        runner = perf.text_runner.TextRunner('bench')
        runner.parse_args(['-v'])

        with mock.patch('perf.text_runner.os') as mock_os:
            del mock_os.sched_setaffinity

            with mock.patch('perf._get_isolated_cpus', return_value=[1, 2]):
                with mock.patch('perf.text_runner.psutil') as mock_psutil:
                    with tests.capture_stdout() as stdout:
                        runner._cpu_affinity()

        self.assertEqual(runner.args.affinity, '1-2')
        self.assertEqual(stdout.getvalue(),
                         'Pin process to isolated CPUs: 1-2\n')

        cpu_affinity = mock_psutil.Process.return_value.cpu_affinity
        cpu_affinity.assert_called_once_with([1, 2])


if __name__ == "__main__":
    unittest.main()
