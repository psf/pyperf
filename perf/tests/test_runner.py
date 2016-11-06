import collections
import os.path
import tempfile
import textwrap

import six

import perf
from perf import tests
from perf._utils import pipe_cloexec
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


class TestRunner(unittest.TestCase):
    def exec_runner(self, *args, **kwargs):
        def fake_timer():
            t = fake_timer.value
            fake_timer.value += 1.0
            return t
        fake_timer.value = 0.0

        name = kwargs.pop('name', 'bench')
        sample_func = kwargs.pop('sample_func', None)

        runner = perf.Runner(**kwargs)
        # disable CPU affinity to not pollute stdout
        runner._cpu_affinity = lambda: None
        runner.parse_args(args)

        with mock.patch('perf.perf_counter', fake_timer):
            with tests.capture_stdout() as stdout:
                with tests.capture_stderr() as stderr:
                    if sample_func:
                        bench = runner.bench_sample_func(name, sample_func)
                    else:
                        bench = runner.bench_func(name, check_args, None, 1, 2)

        stdout = stdout.getvalue()
        stderr = stderr.getvalue()
        if '--stdout' not in args:
            self.assertEqual(stderr, '')

        # check bench_sample_func() bench
        self.assertIsInstance(bench, perf.Benchmark)
        self.assertEqual(bench.get_name(), name)
        self.assertEqual(bench.get_nrun(), 1)

        return Result(runner, bench, stdout)

    def test_worker(self):
        result = self.exec_runner('--worker')
        self.assertRegex(result.stdout,
                         r'^bench: Median \+- std dev: 1\.00 sec \+- 0\.00 sec\n$')

    def test_debug_single_sample(self):
        result = self.exec_runner('--debug-single-sample', '--worker')
        self.assertEqual(result.bench.get_nsample(), 1)

    def test_pipe(self):
        rpipe, wpipe = pipe_cloexec()
        if six.PY3:
            rfile = open(rpipe, "r", encoding="utf8")
        else:
            rfile = os.fdopen(rpipe, "r")

        with rfile:
            # need to duplicate because the worker closes the pipe FD
            wpipe2 = os.dup(wpipe)
            try:
                result = self.exec_runner('--pipe', str(wpipe2), '--worker')
            finally:
                os.close(wpipe)

            bench_json = rfile.read()
        self.assertEqual(bench_json,
                         tests.benchmark_as_json(result.bench))

    def test_json_exists(self):
        with tempfile.NamedTemporaryFile('wb+') as tmp:

            runner = perf.Runner()
            with tests.capture_stdout() as stdout:
                try:
                    runner.parse_args(['--worker', '--output', tmp.name])
                except SystemExit as exc:
                    self.assertEqual(exc.code, 1)

            self.assertEqual('ERROR: The JSON file %r already exists'
                             % tmp.name,
                             stdout.getvalue().rstrip())

    def test_verbose_metadata(self):
        result = self.exec_runner('--worker', '--verbose', '--metadata')
        self.assertRegex(result.stdout,
                         r'^'
                         r'(?:Calibration [0-9]+: 1\.00 sec \(1 loop: 1\.00 sec\)\n)+'
                         r'Calibration: use [0-9^]+ loops\n'
                         r'\n'
                         r'(?:Warmup [0-9]+: 1\.00 sec \(1 loop: 1\.00 sec\)\n)+'
                         r'\n'
                         r'(?:Sample [0-9]+: 1\.00 sec\n)+'
                         r'\n'
                         r'Metadata:\n'
                         r'(?:- .*\n)+'
                         r'\n'
                         r'bench: Median \+- std dev: 1\.00 sec \+- 0\.00 sec\n$')

    def test_loops_calibration(self):
        def sample_func(loops):
            # number of iterations => number of microseconds
            return loops * 1e-6

        result = self.exec_runner('--worker', '-v', sample_func=sample_func)

        for run in result.bench.get_runs():
            self.assertEqual(run.get_total_loops(), 2 ** 17)

        expected = textwrap.dedent('''
            Calibration 1: 1.00 us (1 loop: 1.00 us)
            Calibration 2: 1.00 us (2 loops: 2.00 us)
            Calibration 3: 1.00 us (4 loops: 4.00 us)
            Calibration 4: 1.00 us (8 loops: 8.00 us)
            Calibration 5: 1.00 us (16 loops: 16.0 us)
            Calibration 6: 1.00 us (32 loops: 32.0 us)
            Calibration 7: 1.00 us (64 loops: 64.0 us)
            Calibration 8: 1.00 us (128 loops: 128 us)
            Calibration 9: 1.00 us (256 loops: 256 us)
            Calibration 10: 1.00 us (512 loops: 512 us)
            Calibration 11: 1.00 us (1024 loops: 1.02 ms)
            Calibration 12: 1.00 us (2048 loops: 2.05 ms)
            Calibration 13: 1.00 us (4096 loops: 4.10 ms)
            Calibration 14: 1.00 us (8192 loops: 8.19 ms)
            Calibration 15: 1.00 us (2^14 loops: 16.4 ms)
            Calibration 16: 1.00 us (2^15 loops: 32.8 ms)
            Calibration 17: 1.00 us (2^16 loops: 65.5 ms)
            Calibration 18: 1.00 us (2^17 loops: 131 ms)

        ''').strip()
        self.assertIn(expected, result.stdout)

    def test_loops_calibration_min_time(self):
        def sample_func(loops):
            # number of iterations => number of microseconds
            return loops * 1e-6

        result = self.exec_runner('--worker', '--min-time', '0.001',
                                  sample_func=sample_func)
        for run in result.bench.get_runs():
            self.assertEqual(run.get_total_loops(), 2 ** 10)

    def test_json_file(self):
        with tests.temporary_directory() as tmpdir:
            filename = os.path.join(tmpdir, 'test.json')

            result = self.exec_runner('--worker', '--output', filename)

            loaded = perf.Benchmark.load(filename)
            tests.compare_benchmarks(self, loaded, result.bench)

    def test_sample_func_zero(self):
        if perf.python_has_jit():
            # If Python has a JIT, perf forces calibration which is already
            # tested by test_calibration_zero()
            self.skipTest("Python has a JIT")

        runner = perf.Runner()
        # disable CPU affinity to not pollute stdout
        runner._cpu_affinity = lambda: None
        runner.parse_args(['--worker', '-l1'])

        def sample_func(loops):
            return 0

        with self.assertRaises(ValueError) as cm:
            runner.bench_sample_func('bench', sample_func)
        self.assertEqual(str(cm.exception), 'sample function returned zero')

    def test_calibration_zero(self):
        runner = perf.Runner()
        # disable CPU affinity to not pollute stdout
        runner._cpu_affinity = lambda: None
        runner.parse_args(['--worker'])

        def sample_func(loops):
            return 0

        with self.assertRaises(ValueError) as cm:
            runner.bench_sample_func('bench', sample_func)
        self.assertIn('error in calibration, loops is too big:',
                      str(cm.exception))

    def test_calibration(self):
        runner = perf.Runner()
        # disable CPU affinity to not pollute stdout
        runner._cpu_affinity = lambda: None
        runner.parse_args(['--worker', '-w2', '-n1', '--min-time=1.0'])

        # Simulate PyPy JIT: running the same function becomes faster
        # after 2 samples while running warmup samples
        def sample_func(loops):
            if loops < 16:
                return 0

            sample_func.step += 1
            if sample_func.step == 1:
                return 3.0
            elif sample_func.step == 2:
                return 0.5
            else:
                return 1.0
        sample_func.step = 0

        with tests.capture_stdout():
            bench = runner.bench_sample_func('bench', sample_func)

        runs = bench.get_runs()
        self.assertEqual(len(runs), 1)

        run = runs[0]
        self.assertEqual(run.warmups,
                         # first calibration samples are zero
                         ((1, 0.0),
                          (2, 0.0),
                          (4, 0.0),
                          (8, 0.0),

                          # first non-zero calibration sample
                          (16, 3.0),

                          # warmup 1, JIT triggered, 3.0 => 0.5 for loops=128
                          (16, 0.5),
                          # warmup 1, new try with loops x 2
                          (32, 1.0),

                          # warmup 2
                          (32, 1.0)))

    def test_loops_power(self):
        runner = perf.Runner()
        runner.parse_args(['--loops', '2^8'])
        self.assertEqual(runner.args.loops, 256)

    def check_two_benchmarks(self, task=None):
        runner = perf.Runner()
        args = ['--worker', '--loops=1', '-w0', '-n3']
        if task is not None:
            args.append('--worker-task=%s' % task)
        runner.parse_args(args)

        def sample_func(loops):
            return 1.0

        def sample_func2(loops):
            return 2.0

        with tests.capture_stdout():
            bench1 = runner.bench_sample_func('bench1', sample_func)
            bench2 = runner.bench_sample_func('bench2', sample_func2)

        return (bench1, bench2)

    def test_two_benchmarks(self):
        bench1, bench2 = self.check_two_benchmarks()

        self.assertEqual(bench1.get_name(), 'bench1')
        self.assertEqual(bench1.get_samples(), (1.0, 1.0, 1.0))
        self.assertEqual(bench2.get_name(), 'bench2')
        self.assertEqual(bench2.get_samples(), (2.0, 2.0, 2.0))

    def test_worker_task(self):
        bench1, bench2 = self.check_two_benchmarks(task=0)
        self.assertEqual(bench1.get_name(), 'bench1')
        self.assertEqual(bench1.get_samples(), (1.0, 1.0, 1.0))
        self.assertIs(bench2, None)

        bench1, bench2 = self.check_two_benchmarks(task=1)
        self.assertIs(bench1, None)
        self.assertEqual(bench2.get_name(), 'bench2')
        self.assertEqual(bench2.get_samples(), (2.0, 2.0, 2.0))

        bench1, bench2 = self.check_two_benchmarks(task=2)
        self.assertIs(bench1, None)
        self.assertIs(bench2, None)

    def test_show_name(self):
        result = self.exec_runner('--worker', name='NAME')
        self.assertRegex(result.stdout,
                         r'^NAME: Median \+- std dev: 1\.00 sec \+- 0\.00 sec\n$')

        result = self.exec_runner('--worker', name='NAME', show_name=False)
        self.assertRegex(result.stdout,
                         r'^Median \+- std dev: 1\.00 sec \+- 0\.00 sec\n$')


class TestRunnerCPUAffinity(unittest.TestCase):
    def test_cpu_affinity_args(self):
        runner = perf.Runner()
        runner.parse_args(['-v', '--affinity=3,7'])

        with mock.patch('perf._runner.set_cpu_affinity') as mock_setaffinity:
            with tests.capture_stdout() as stdout:
                runner._cpu_affinity()

        self.assertEqual(runner.args.affinity, '3,7')
        self.assertEqual(stdout.getvalue(),
                         'Pin process to CPUs: 3,7\n')
        mock_setaffinity.assert_called_once_with([3, 7])

    def test_cpu_affinity_isolcpus(self):
        runner = perf.Runner()
        runner.parse_args(['-v'])

        with mock.patch('perf._runner.set_cpu_affinity') as mock_setaffinity:
            with mock.patch('perf._runner.get_isolated_cpus', return_value=[1, 2]):
                with tests.capture_stdout() as stdout:
                    runner._cpu_affinity()

        self.assertEqual(runner.args.affinity, '1-2')
        self.assertEqual(stdout.getvalue(),
                         'Pin process to isolated CPUs: 1-2\n')
        mock_setaffinity.assert_called_once_with([1, 2])

    def test_cpu_affinity_no_isolcpus(self):
        runner = perf.Runner()
        runner.parse_args(['-v'])

        with mock.patch('perf._runner.set_cpu_affinity') as mock_setaffinity:
            with mock.patch('perf._runner.get_isolated_cpus', return_value=None):
                runner._cpu_affinity()

        self.assertFalse(runner.args.affinity)
        self.assertEqual(mock_setaffinity.call_count, 0)


if __name__ == "__main__":
    unittest.main()
