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
FAST_BENCH_ARGS = ('--debug-single-value',
                   '-s', 'import time',
                   'time.sleep(1e-6)')
FAST_MIN_TIME = 1e-6
# test with a least with two values
COMPARE_BENCH = ('-l1', '-p1', '-w0', '-n3',
                 '-s', 'import time',
                 'time.sleep(1e-6)')

SLEEP = 'time.sleep(1e-3)'
# The perfect timing is 1 ms +- 0 ms, but tolerate large differences on busy
# systems. The unit test doesn't test the system but more the output format.
MIN_VALUE = 0.9  # ms
MAX_VALUE = 50.0  # ms
MIN_MEAN = MIN_VALUE
MAX_MEAN = MAX_VALUE / 2
MAX_STD_DEV = 10.0  # ms


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

        match = re.search(r'Warmup 1: ([0-9.]+) ms \(loops: 1, raw: [0-9.]+ ms\)\n'
                          r'\n'
                          r'Value 1: ([0-9.]+) ms\n'
                          r'Value 2: ([0-9.]+) ms\n'
                          r'\n'
                          r'Metadata:\n'
                          r'(- .*\n)+'
                          r'\n'
                          r'Mean \+- std dev: (?P<mean>[0-9.]+) ms \+-'
                          ' (?P<mad>[0-9.]+) ms\n'
                          r'$',
                          cmd.stdout)
        self.assertIsNotNone(match, repr(cmd.stdout))

        values = [float(match.group(i)) for i in range(1, 4)]
        for value in values:
            self.assertTrue(MIN_VALUE <= value <= MAX_VALUE,
                            repr(value))

        mean = float(match.group('mean'))
        self.assertTrue(MIN_MEAN <= mean <= MAX_MEAN, mean)
        mad = float(match.group('mad'))
        self.assertLessEqual(mad, MAX_STD_DEV)

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
        match = re.search(r'Mean \+- std dev: (?P<mean>[0-9.]+) ms'
                          r' \+- (?P<mad>[0-9.]+) ms'
                          r'$',
                          cmd.stdout.rstrip())
        self.assertIsNotNone(match, repr(cmd.stdout))

        # Tolerate large differences on busy systems
        mean = float(match.group('mean'))
        self.assertTrue(MIN_MEAN <= mean <= MAX_MEAN, mean)

        mad = float(match.group('mad'))
        self.assertLessEqual(mad, MAX_STD_DEV)

    def run_timeit(self, args):
        cmd = tests.get_output(args)
        self.assertEqual(cmd.returncode, 0, cmd.stdout + cmd.stderr)
        return cmd.stdout

    def run_timeit_bench(self, args):
        with tests.temporary_directory() as tmpdir:
            filename = os.path.join(tmpdir, 'test.json')
            args += ('--output', filename)
            stdout = self.run_timeit(args)
            bench = perf.Benchmark.load(filename)
        return (bench, stdout)

    def test_verbose_output(self):
        args = ('-p', '2',
                '-w', '1',
                '-n', '3',
                # don't pass --loops to test calibration
                '--min-time', '0.001',
                '-s', 'import time',
                '--verbose',
                SLEEP)
        args = PERF_TIMEIT + args
        # Don't check the exact output, only check that the verbose
        # mode doesn't fail with an error (non-zero exist code)
        self.run_timeit_bench(args)

    def test_bench(self):
        loops = 4
        args = ('-p', '2',
                '-w', '1',
                '-n', '3',
                '-l', str(loops),
                '--min-time', '0.001',
                '-s', 'import time',
                SLEEP)
        args = PERF_TIMEIT + args
        bench, stdout = self.run_timeit_bench(args)

        # FIXME: skipped test, since calibration continues during warmup
        if not perf.python_has_jit():
            for run in bench.get_runs():
                self.assertEqual(run.get_total_loops(), 4)

        runs = bench.get_runs()
        self.assertEqual(len(runs), 2)
        for run in runs:
            self.assertIsInstance(run, perf.Run)
            raw_values = run._get_raw_values(warmups=True)
            self.assertEqual(len(raw_values), 4)
            for raw_value in raw_values:
                ms = (raw_value / loops) * 1e3
                self.assertTrue(MIN_VALUE <= ms <= MAX_VALUE, ms)

    def test_append(self):
        with tests.temporary_directory() as tmpdir:
            filename = os.path.join(tmpdir, 'test.json')
            args = PERF_TIMEIT + ('--append', filename) + FAST_BENCH_ARGS

            self.run_timeit(args)
            bench = perf.Benchmark.load(filename)
            self.assertEqual(bench.get_nvalue(), 1)

            self.run_timeit(args)
            bench = perf.Benchmark.load(filename)
            self.assertEqual(bench.get_nvalue(), 2)

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
        bench, stdout = self.run_timeit_bench(args)

        self.assertEqual(bench.get_name(), name)
        self.assertRegex(stdout, re.compile('^%s' % name, flags=re.MULTILINE))

    def test_inner_loops(self):
        inner_loops = 17
        args = PERF_TIMEIT + ('--inner-loops', str(inner_loops)) + FAST_BENCH_ARGS
        bench, stdout = self.run_timeit_bench(args)

        metadata = bench.get_metadata()
        self.assertEqual(metadata['inner_loops'], inner_loops)

    def test_compare_to(self):
        args = ('--compare-to', sys.executable,
                '--python-names=ref:changed')
        args = PERF_TIMEIT + args + COMPARE_BENCH
        cmd = tests.get_output(args)

        # ".*" and DOTALL ignore stability warnings
        expected = textwrap.dedent(r'''
            ref: \. [0-9.]+ (?:ms|us) \+- [0-9.]+ (?:ms|us)
            .*
            changed: \. [0-9.]+ (?:ms|us) \+- [0-9.]+ (?:ms|us)
            .*
            (?:Mean \+- std dev: \[ref\] .* -> \[changed\] .*: (?:[0-9]+\.[0-9][0-9]x (?:faster|slower)|no change)|Not significant!)
        ''').strip()
        expected = re.compile(expected, flags=re.DOTALL)
        self.assertRegex(cmd.stdout, expected)

    def test_compare_to_verbose(self):
        args = PERF_TIMEIT + ('--compare-to', sys.executable, '--verbose')
        args += COMPARE_BENCH
        cmd = tests.get_output(args)

        expected = textwrap.dedent(r'''
            Benchmark .*
            ==========+

            .*
            Mean \+- std dev: .*

            Benchmark .*
            ==========+

            .*
            Mean \+- std dev: .*

            Compare
            =======

            Mean \+- std dev: .* -> .*: (?:[0-9]+\.[0-9][0-9]x (?:faster|slower)|no change)
        ''').strip()
        expected = re.compile(expected, flags=re.DOTALL)
        self.assertRegex(cmd.stdout, expected)

    def test_compare_to_quiet(self):
        args = PERF_TIMEIT + ('--compare-to', sys.executable, '--quiet')
        args += COMPARE_BENCH
        cmd = tests.get_output(args)

        expected = r'(?:Mean \+- std dev: .* -> .*: (?:[0-9]+\.[0-9][0-9]x (?:faster|slower)|no change)|Not significant!)'
        self.assertRegex(cmd.stdout, expected)

    def test_duplicate(self):
        sleep = 1e-3
        duplicate = 10
        args = PERF_TIMEIT
        args += ('-n3', '-p1',
                 '--duplicate', str(duplicate), '--loops', '1',
                 '-s', 'import time', 'time.sleep(%s)' % sleep)
        bench, stdout = self.run_timeit_bench(args)

        metadata = bench.get_metadata()
        self.assertEqual(metadata['timeit_duplicate'], duplicate)
        for raw_value in bench._get_raw_values():
            self.assertGreaterEqual(raw_value, sleep * duplicate)


if __name__ == "__main__":
    unittest.main()
