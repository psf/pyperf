import collections
import os.path
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


Result = collections.namedtuple('Result', 'runner bench stdout')


class TestRunTextRunner(unittest.TestCase):
    def run_text_runner(self, *args, **kwargs):
        def fake_timer():
            t = fake_timer.value
            fake_timer.value += 1.0
            return t
        fake_timer.value = 0.0

        sample_func = kwargs.pop('sample_func', None)

        runner = perf.text_runner.TextRunner('bench')
        # disable CPU affinity to not pollute stdout
        runner._cpu_affinity = lambda: None
        runner.parse_args(args)

        with mock.patch('perf.perf_counter', fake_timer):
            with tests.capture_stdout() as stdout:
                with tests.capture_stderr() as stderr:
                    if sample_func:
                        bench = runner.bench_sample_func(sample_func)
                    else:
                        bench = runner.bench_func(check_args, None, 1, 2)

        stdout = stdout.getvalue()
        stderr = stderr.getvalue()
        if '--stdout' not in args:
            self.assertEqual(stderr, '')

        # check bench_sample_func() bench
        self.assertIsInstance(bench, perf.Benchmark)
        self.assertEqual(bench.name, 'bench')
        self.assertEqual(bench.get_nrun(), 1)

        return Result(runner, bench, stdout)

    def test_worker(self):
        result = self.run_text_runner('--worker')
        self.assertRegex(result.stdout,
                         r'^Median \+- std dev: 1\.00 sec \+- 0\.00 sec\n$')

    def test_debug_single_sample(self):
        result = self.run_text_runner('--debug-single-sample')
        self.assertEqual(result.bench.get_nsample(), 1)

    def test_stdout(self):
        result = self.run_text_runner('--stdout', '--worker')
        self.assertEqual(result.stdout,
                         tests.benchmark_as_json(result.bench))

    def test_json_exists(self):
        with tempfile.NamedTemporaryFile('wb+') as tmp:

            runner = perf.text_runner.TextRunner('bench')
            with tests.capture_stdout() as stdout:
                try:
                    runner.parse_args(['--worker', '--output', tmp.name])
                except SystemExit as exc:
                    self.assertEqual(exc.code, 1)

            self.assertEqual('ERROR: The JSON file %r already exists'
                             % tmp.name,
                             stdout.getvalue().rstrip())

    def test_verbose_metadata(self):
        result = self.run_text_runner('--worker', '--verbose', '--metadata')
        self.assertRegex(result.stdout,
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

    def test_loops_calibration(self):
        def sample_func(loops):
            # number of iterations => number of microseconds
            return loops * 1e-6

        result = self.run_text_runner('--worker', '-v',
                                      sample_func=sample_func)

        self.assertEqual(result.runner.args.loops, 2 ** 17)
        for run in result.bench.get_runs():
            self.assertEqual(run.loops, 2 ** 17)

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
        self.assertIn(expected, result.stdout)

    def test_loops_calibration_min_time(self):
        def sample_func(loops):
            # number of iterations => number of microseconds
            return loops * 1e-6

        result = self.run_text_runner('--worker', '--min-time', '0.001',
                                      sample_func=sample_func)
        self.assertEqual(result.runner.args.loops, 2 ** 10)
        for run in result.bench.get_runs():
            self.assertEqual(run.loops, 2 ** 10)

    def test_json_file(self):
        with tests.temporary_directory() as tmpdir:
            filename = os.path.join(tmpdir, 'test.json')

            result = self.run_text_runner('--worker', '--output', filename)

            loaded = perf.Benchmark.load(filename)
            tests.compare_benchmarks(self, loaded, result.bench)


class TestTextRunnerCPUAffinity(unittest.TestCase):
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
