import errno
import os.path
import re
import shutil
import sys
import tempfile
import textwrap

import perf
from perf import tests
from perf.tests import unittest


PERF_TIMEIT = (sys.executable, '-m', 'perf', 'timeit')
# We only need a statement taking longer than 0 nanosecond
FAST_BENCH_ARGS = ('--debug-single-sample',
                   '-s', 'import time',
                   'time.sleep(1e-6)')
# test with a least with two samples
COMPARE_BENCH = ('-l1', '-p1', '-w0', '-n3',
                 '-s', 'import time',
                 'time.sleep(1e-6)')

SLEEP = 'time.sleep(1e-3)'
# The perfect timing is 1 ms +- 0 ms, but tolerate large differences on busy
# systems. The unit test doesn't test the system but more the output format.
MIN_SAMPLE = 0.9  # ms
MAX_SAMPLE = 50.0  # ms
MIN_MEAN = MIN_SAMPLE
MAX_MEAN = MAX_SAMPLE / 2
MAX_STDEV = 10.0  # ms


class TestTimeit(unittest.TestCase):
    def test_worker_verbose(self):
        args = ('--worker',
                '-w', '1',
                '-n', '2',
                '-l', '1',
                '--min-time', '0.001',
                '--metadata',
                '-v',
                '-s', 'import time',
                SLEEP)
        args = PERF_TIMEIT + args
        cmd = tests.get_output(args)
        self.assertEqual(cmd.returncode, 0)
        self.assertEqual(cmd.stderr, '')

        match = re.search(r'Warmup 1: ([0-9.]+) ms \(1 loop: [0-9.]+ ms\)\n'
                          r'\n'
                          r'Sample 1: ([0-9.]+) ms\n'
                          r'Sample 2: ([0-9.]+) ms\n'
                          r'\n'
                          r'Metadata:\n'
                          r'(- .*\n)+'
                          r'\n'
                          r'Median \+- std dev: (?P<median>[0-9.]+) ms \+-'
                          ' (?P<stdev>[0-9.]+) ms\n'
                          r'$',
                          cmd.stdout)
        self.assertIsNotNone(match, repr(cmd.stdout))

        values = [float(match.group(i)) for i in range(1, 4)]
        for value in values:
            self.assertTrue(MIN_SAMPLE <= value <= MAX_SAMPLE,
                            repr(value))

        median = float(match.group('median'))
        self.assertTrue(MIN_MEAN <= median <= MAX_MEAN, median)
        stdev = float(match.group('stdev'))
        self.assertLessEqual(stdev, MAX_STDEV)

    def test_cli(self):
        args = ('-p', '2',
                '-w', '1',
                '-n', '3',
                '-l', '4',
                '--min-time', '0.001',
                '-s', 'import time',
                SLEEP)
        args = PERF_TIMEIT + args
        cmd = tests.get_output(args)
        self.assertEqual(cmd.returncode, 0)
        self.assertEqual(cmd.stderr, '')

        # ignore lines before to ignore random warnings like
        # "ERROR: the benchmark is very unstable"
        match = re.search(r'Median \+- std dev: (?P<median>[0-9.]+) ms'
                          r' \+- (?P<stdev>[0-9.]+) ms'
                          r'$',
                          cmd.stdout.rstrip())
        self.assertIsNotNone(match, repr(cmd.stdout))

        # Tolerate large differences on busy systems
        median = float(match.group('median'))
        self.assertTrue(MIN_MEAN <= median <= MAX_MEAN, median)

        stdev = float(match.group('stdev'))
        self.assertLessEqual(stdev, MAX_STDEV)

    def run_timeit(self, args):
        cmd = tests.get_output(args)
        self.assertEqual(cmd.returncode, 0, cmd.stdout + cmd.stderr)

    def run_timeit_bench(self, args):
        with tests.temporary_directory() as tmpdir:
            filename = os.path.join(tmpdir, 'test.json')
            args += ('--output', filename)
            self.run_timeit(args)
            return perf.Benchmark.load(filename)

    def test_output(self):
        loops = 4
        args = ('-p', '2',
                '-w', '1',
                '-n', '3',
                '-l', str(loops),
                '--min-time', '0.001',
                '-s', 'import time',
                SLEEP)
        args = PERF_TIMEIT + args
        bench = self.run_timeit_bench(args)

        # FIXME: skipped test, since calibration continues during warmup
        if not perf.python_has_jit():
            for run in bench.get_runs():
                self.assertEqual(run.get_total_loops(), 4)

        runs = bench.get_runs()
        self.assertEqual(len(runs), 2)
        for run in runs:
            self.assertIsInstance(run, perf.Run)
            raw_samples = run._get_raw_samples(warmups=True)
            self.assertEqual(len(raw_samples), 4)
            for raw_sample in raw_samples:
                ms = (raw_sample / loops) * 1e3
                self.assertTrue(MIN_SAMPLE <= ms <= MAX_SAMPLE, ms)

    def test_append(self):
        with tests.temporary_directory() as tmpdir:
            filename = os.path.join(tmpdir, 'test.json')
            args = PERF_TIMEIT + ('--append', filename) + FAST_BENCH_ARGS

            self.run_timeit(args)
            bench = perf.Benchmark.load(filename)
            self.assertEqual(bench.get_nsample(), 1)

            self.run_timeit(args)
            bench = perf.Benchmark.load(filename)
            self.assertEqual(bench.get_nsample(), 2)

    def test_cli_snippet_error(self):
        args = PERF_TIMEIT + ('x+1',)
        cmd = tests.get_output(args)
        self.assertEqual(cmd.returncode, 1)

        self.assertIn('Traceback (most recent call last):', cmd.stderr)
        self.assertIn("NameError", cmd.stderr)

    # When the PyPy program is copied, it fails with "Library path not found"
    @unittest.skipIf(perf.python_implementation() == 'pypy',
                     'pypy program cannot be copied')
    def test_python_option(self):
        # Ensure that paths are absolute
        paths = [os.path.realpath(path) for path in sys.path]
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(paths))

        tmp_exe = tempfile.mktemp()
        try:
            shutil.copy2(sys.executable, tmp_exe)

            # Run benchmark to check if --python works
            args = ('--metadata',
                    '--python', tmp_exe,
                    '--inherit-env', 'PYTHONPATH')
            args = PERF_TIMEIT + args + FAST_BENCH_ARGS
            cmd = tests.get_output(args, env=env)
        finally:
            try:
                os.unlink(tmp_exe)
            except OSError as exc:
                if exc.errno != errno.ENOENT:
                    raise

        self.assertEqual(cmd.returncode, 0, repr(cmd.stdout + cmd.stderr))
        self.assertIn("python_executable: %s" % tmp_exe, cmd.stdout)

    def test_name(self):
        name = 'myname'
        args = PERF_TIMEIT + ('--name', name) + FAST_BENCH_ARGS
        bench = self.run_timeit_bench(args)

        self.assertEqual(bench.get_name(), name)

    def test_inner_loops(self):
        inner_loops = 17
        args = PERF_TIMEIT + ('--inner-loops', str(inner_loops)) + FAST_BENCH_ARGS
        bench = self.run_timeit_bench(args)

        metadata = bench.get_metadata()
        self.assertEqual(metadata['inner_loops'].value, inner_loops)

    def test_compare(self):
        args = PERF_TIMEIT + ('--compare', sys.executable) + COMPARE_BENCH
        cmd = tests.get_output(args)

        # ".*" and DOTALL ignore stability warnings
        expected = textwrap.dedent(r'''
            .*: \. [0-9.]+ (?:ms|us) \+- [0-9.]+ (?:ms|us)
            .*
            .*: \. [0-9.]+ (?:ms|us) \+- [0-9.]+ (?:ms|us)
            .*

            (?:Median \+- std dev: .* -> .*: (?:[0-9]+\.[0-9][0-9]x (?:faster|slower)|no change)|Not significant!)
        ''').strip()
        expected = re.compile(expected, flags=re.DOTALL)
        self.assertRegex(cmd.stdout, expected)

    def test_compare_verbose(self):
        args = PERF_TIMEIT + ('--compare', sys.executable, '--verbose')
        args += COMPARE_BENCH
        cmd = tests.get_output(args)

        expected = textwrap.dedent('''
            Benchmark .*
            ==========+

            .*
            Median \+- std dev: .*

            Benchmark .*
            ==========+

            .*
            Median \+- std dev: .*

            Compare
            =======

            Median \+- std dev: .* -> .*: (?:[0-9]+\.[0-9][0-9]x (?:faster|slower)|no change)
        ''').strip()
        expected = re.compile(expected, flags=re.DOTALL)
        self.assertRegex(cmd.stdout, expected)

    def test_compare_quiet(self):
        args = PERF_TIMEIT + ('--compare', sys.executable, '--quiet')
        args += COMPARE_BENCH
        cmd = tests.get_output(args)

        expected = '(?:Median \+- std dev: .* -> .*: (?:[0-9]+\.[0-9][0-9]x (?:faster|slower)|no change)|Not significant!)'
        self.assertRegex(cmd.stdout, expected)


if __name__ == "__main__":
    unittest.main()
