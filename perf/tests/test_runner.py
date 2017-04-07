import collections
import os.path
import sys
import tempfile
import textwrap

import six

import perf
from perf import tests
from perf._utils import create_pipe, MS_WINDOWS
from perf.tests import mock
from perf.tests import unittest
from perf.tests import ExitStack


def check_args(loops, a, b):
    if a != 1:
        raise ValueError
    if b != 2:
        raise ValueError
    # number of loops => number of seconds
    return loops


Result = collections.namedtuple('Result', 'runner bench stdout')


class TestRunner(unittest.TestCase):
    def create_runner(self, args, **kwargs):
        runner = perf.Runner(**kwargs)
        # disable CPU affinity to not pollute stdout
        runner._cpu_affinity = lambda: None
        runner.parse_args(args)
        return runner

    def exec_runner(self, *args, **kwargs):
        def fake_timer():
            t = fake_timer.value
            fake_timer.value += 1.0
            return t
        fake_timer.value = 0.0

        name = kwargs.pop('name', 'bench')
        time_func = kwargs.pop('time_func', None)

        runner = self.create_runner(args, **kwargs)

        with mock.patch('perf.perf_counter', fake_timer):
            with tests.capture_stdout() as stdout:
                with tests.capture_stderr() as stderr:
                    if time_func:
                        bench = runner.bench_time_func(name, time_func)
                    else:
                        bench = runner.bench_func(name, check_args, None, 1, 2)

        stdout = stdout.getvalue()
        stderr = stderr.getvalue()
        if '--stdout' not in args:
            self.assertEqual(stderr, '')

        # check bench_time_func() bench
        self.assertIsInstance(bench, perf.Benchmark)
        self.assertEqual(bench.get_name(), name)
        self.assertEqual(bench.get_nrun(), 1)

        return Result(runner, bench, stdout)

    def test_worker(self):
        result = self.exec_runner('--worker', '-l1')
        self.assertRegex(result.stdout,
                         r'^bench: Mean \+- std dev: 1\.00 sec \+- 0\.00 sec\n$')

    def test_debug_single_value(self):
        result = self.exec_runner('--debug-single-value', '--worker')
        self.assertEqual(result.bench.get_nvalue(), 1)

    def test_pipe(self):
        rpipe, wpipe = create_pipe()
        with rpipe:
            with wpipe:
                arg = wpipe.to_subprocess()
                # Don't close the file descriptor, it is closed by
                # the Runner class
                wpipe._fd = None

                result = self.exec_runner('--pipe', str(arg),
                                          '--worker', '-l1')

            with rpipe.open_text() as rfile:
                bench_json = rfile.read()

        self.assertEqual(bench_json,
                         tests.benchmark_as_json(result.bench))

    def test_json_exists(self):
        with tempfile.NamedTemporaryFile('wb+') as tmp:

            runner = perf.Runner()
            with tests.capture_stdout() as stdout:
                try:
                    runner.parse_args(['--worker', '-l1',
                                       '--output', tmp.name])
                except SystemExit as exc:
                    self.assertEqual(exc.code, 1)

            self.assertEqual('ERROR: The JSON file %r already exists'
                             % tmp.name,
                             stdout.getvalue().rstrip())

    def test_verbose_metadata(self):
        result = self.exec_runner('--worker', '-l1', '--verbose', '--metadata')
        self.assertRegex(result.stdout,
                         r'^'
                         r'(?:Warmup [0-9]+: 1\.00 sec \(1 loop: 1\.00 sec\)\n)+'
                         r'\n'
                         r'(?:Value [0-9]+: 1\.00 sec\n)+'
                         r'\n'
                         r'Metadata:\n'
                         r'(?:- .*\n)+'
                         r'\n'
                         r'bench: Mean \+- std dev: 1\.00 sec \+- 0\.00 sec\n$')

    def test_loops_calibration(self):
        def time_func(loops):
            # number of iterations => number of microseconds
            return loops * 1e-6

        result = self.exec_runner('--worker', '--calibrate-loops',
                                  '-v', time_func=time_func)

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
        def time_func(loops):
            # number of iterations => number of microseconds
            return loops * 1e-6

        result = self.exec_runner('--worker', '--calibrate-loops',
                                  '--min-time', '0.001',
                                  time_func=time_func)
        for run in result.bench.get_runs():
            self.assertEqual(run.get_total_loops(), 2 ** 10)

    def test_json_file(self):
        with tests.temporary_directory() as tmpdir:
            filename = os.path.join(tmpdir, 'test.json')

            result = self.exec_runner('--worker', '-l1', '--output', filename)

            loaded = perf.Benchmark.load(filename)
            tests.compare_benchmarks(self, loaded, result.bench)

    def test_time_func_zero(self):
        runner = self.create_runner(['--worker', '-l1'])

        def time_func(loops):
            return 0

        with self.assertRaises(ValueError) as cm:
            runner.bench_time_func('bench', time_func)
        self.assertEqual(str(cm.exception),
                         'benchmark function returned zero')

    def test_calibration_zero(self):
        runner = self.create_runner(['--worker', '--calibrate-loops'])

        def time_func(loops):
            return 0

        with self.assertRaises(ValueError) as cm:
            runner.bench_time_func('bench', time_func)
        self.assertIn('error in calibration, loops is too big:',
                      str(cm.exception))

    def check_calibrate_loops(self, runner, time_func, warmups):
        with tests.capture_stdout():
            bench = runner.bench_time_func('bench', time_func)

        runs = bench.get_runs()
        self.assertEqual(len(runs), 1)
        run = runs[0]

        self.assertEqual(run.warmups, warmups)

    def test_calibrate_loops(self):
        args = ['--worker', '-w2', '-n1', '--min-time=1.0',
                '--calibrate-loops']
        runner = self.create_runner(args)

        def time_func(loops):
            if loops < 8:
                return 0.5
            else:
                return 1.0
        time_func.step = 0

        warmups = (
            (1, 0.5),
            (2, 0.5 / 2),
            (4, 0.5 / 4),

            # warmup 1: dt >= min_time
            (8, 1.0 / 8),
            # warmup 2
            (8, 1.0 / 8))
        self.check_calibrate_loops(runner, time_func, warmups)

    def test_calibrate_loops_jit(self):
        args = ['--worker', '-w2', '-n1', '--min-time=1.0',
                '--calibrate-loops']
        runner = self.create_runner(args)

        # Simulate PyPy JIT: running the same function becomes faster
        # after 2 values while running warmup values
        def time_func(loops):
            if loops < 16:
                return 0

            time_func.step += 1
            if time_func.step == 1:
                return 3.0
            elif time_func.step == 2:
                return 0.5
            else:
                return 1.0
        time_func.step = 0

        warmups = (
            # first calibration values are zero
            (1, 0.0),
            (2, 0.0),
            (4, 0.0),
            (8, 0.0),

            # warmup 1: first non-zero calibration value
            (16, 3.0 / 16),

            # warmup 2: JIT triggered, dt < min_time,
            # double number of loops
            (16, 0.5 / 16),
            # warmup 3
            (32, 1.0 / 32))
        self.check_calibrate_loops(runner, time_func, warmups)

    def test_recalibrate_loops_jit(self):
        args = ['--worker', '-w2', '-n1', '--min-time=1.0',
                '--recalibrate-loops', '--loops=16']
        runner = self.create_runner(args)

        # Simulate PyPy JIT: running the same function becomes faster
        # after 2 values while running warmup values
        def time_func(loops):
            time_func.step += 1
            if time_func.step == 1:
                return 1.0
            elif time_func.step == 2:
                return 0.5
            else:
                return 1.0
        time_func.step = 0

        warmups = (
            # warmup 1
            (16, 1.0 / 16),
            # warmup 2: JIT optimized code, dt < min_time
            # double the number of loops
            (16, 0.5 / 16),
            # warmup 3, new try with loops x 2
            (32, 1.0 / 32))
        self.check_calibrate_loops(runner, time_func, warmups)

    def test_loops_power(self):
        # test 'x^y' syntax for loops
        runner = self.create_runner(['--loops', '2^8'])
        self.assertEqual(runner.args.loops, 256)

    def check_two_benchmarks(self, task=None):
        args = ['--worker', '--loops=1', '-w0', '-n3']
        if task is not None:
            args.append('--worker-task=%s' % task)
        runner = self.create_runner(args)

        def time_func(loops):
            return 1.0

        def time_func2(loops):
            return 2.0

        with tests.capture_stdout():
            bench1 = runner.bench_time_func('bench1', time_func)
            bench2 = runner.bench_time_func('bench2', time_func2)

        return (bench1, bench2)

    def test_two_benchmarks(self):
        bench1, bench2 = self.check_two_benchmarks()

        self.assertEqual(bench1.get_name(), 'bench1')
        self.assertEqual(bench1.get_values(), (1.0, 1.0, 1.0))
        self.assertEqual(bench2.get_name(), 'bench2')
        self.assertEqual(bench2.get_values(), (2.0, 2.0, 2.0))

    def test_worker_task(self):
        bench1, bench2 = self.check_two_benchmarks(task=0)
        self.assertEqual(bench1.get_name(), 'bench1')
        self.assertEqual(bench1.get_values(), (1.0, 1.0, 1.0))
        self.assertIs(bench2, None)

        bench1, bench2 = self.check_two_benchmarks(task=1)
        self.assertIs(bench1, None)
        self.assertEqual(bench2.get_name(), 'bench2')
        self.assertEqual(bench2.get_values(), (2.0, 2.0, 2.0))

        bench1, bench2 = self.check_two_benchmarks(task=2)
        self.assertIs(bench1, None)
        self.assertIs(bench2, None)

    def test_show_name(self):
        result = self.exec_runner('--worker', '-l1', name='NAME')
        self.assertRegex(result.stdout,
                         r'^NAME: Mean \+- std dev: 1\.00 sec \+- 0\.00 sec\n$')

        result = self.exec_runner('--worker', '-l1', name='NAME', show_name=False)
        self.assertRegex(result.stdout,
                         r'^Mean \+- std dev: 1\.00 sec \+- 0\.00 sec\n$')

    def test_compare_to(self):
        def time_func(loops):
            return 1.0

        def abs_executable(python):
            return python

        run = perf.Run([1.5],
                       metadata={'name': 'name'},
                       collect_metadata=False)
        bench = perf.Benchmark([run])
        suite = perf.BenchmarkSuite([bench])

        with ExitStack() as cm:
            def popen(*args, **kw):
                mock_popen = mock.Mock()
                mock_popen.wait.return_value = 0
                return mock_popen

            mock_subprocess = cm.enter_context(mock.patch('perf._runner.subprocess'))
            mock_subprocess.Popen.side_effect = popen

            cm.enter_context(mock.patch('perf._runner.abs_executable',
                             side_effect=abs_executable))
            cm.enter_context(mock.patch('perf._runner._load_suite_from_pipe',
                                        return_value=suite))

            args = ["--python=python1", "--compare-to=python2", "--min-time=5",
                    "-p1", "-w3", "-n7", "-l11"]
            runner = self.create_runner(args)
            with tests.capture_stdout():
                runner.bench_time_func('name', time_func)

            def popen_call(python):
                args = [python, mock.ANY, '--worker',
                        '--pipe', mock.ANY, '--worker-task=0',
                        '--values', '7', '--warmups', '3',
                        '--loops', '11', '--min-time', '5.0']
                kw = {}
                if MS_WINDOWS:
                    kw['close_fds'] = False
                elif six.PY3:
                    kw['pass_fds'] = mock.ANY
                return mock.call(args, env=mock.ANY, **kw)

            call1 = popen_call('python2')
            call2 = popen_call('python1')
            mock_subprocess.Popen.assert_has_calls([call1, call2])

    def test_parse_args_twice_error(self):
        args = ["--worker", '-l1']
        runner = perf.Runner()
        runner.parse_args(args)
        with self.assertRaises(RuntimeError):
            runner.parse_args(args)

    def test_duplicated_named(self):
        def time_func(loops):
            return 1.0

        runner = self.create_runner('-l1 -w0 -n1 --worker'.split())
        with tests.capture_stdout():
            runner.bench_time_func('optim', time_func)
            with self.assertRaises(ValueError) as cm:
                runner.bench_time_func('optim', time_func)

        self.assertEqual(str(cm.exception),
                         "duplicated benchmark name: 'optim'")

    def test_bench_command(self):
        args = [sys.executable, '-c', 'pass']

        runner = self.create_runner('-l1 -w0 -n1 --worker'.split())
        with tests.capture_stdout():
            bench = runner.bench_command('bench', args)

        self.assertEqual(bench.get_metadata()['command'],
                         ' '.join(map(repr, args)))


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
