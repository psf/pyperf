import errno
import os.path
import re
import shutil
import sys
import tempfile
import textwrap
import unittest

from pathlib import Path

import pyperf
from pyperf import tests
from pyperf._timeit import Timer


PERF_TIMEIT = (sys.executable, '-m', 'pyperf', 'timeit')
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

PYPY = pyperf.python_implementation() == 'pypy'


def identity(x):
    return x


def reindent(src, indent):
    return src.replace("\n", "\n" + " " * indent)


def template_output(stmt='pass', setup='pass', teardown='pass', init=''):
    if PYPY:
        template = textwrap.dedent("""
        def inner(_it, _timer{init}):
            {setup}
            _t0 = _timer()
            while _it > 0:
                _it -= 1
                {stmt}
            _t1 = _timer()
            {teardown}
            return _t1 - _t0
        """)
    else:
        template = textwrap.dedent("""
        def inner(_it, _timer{init}):
            {setup}
            _t0 = _timer()
            for _i in _it:
                {stmt}
            _t1 = _timer()
            {teardown}
            return _t1 - _t0
        """)

    return template.format(init=init,
                           stmt=reindent(stmt, 8),
                           setup=reindent(setup, 4),
                           teardown=reindent(teardown, 4))


class TestTimeit(unittest.TestCase):
    @unittest.skipIf(sys.platform == 'win32',
                     'https://github.com/psf/pyperf/issues/97')
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
            bench = pyperf.Benchmark.load(filename)
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
        if not pyperf.python_has_jit():
            for run in bench.get_runs():
                self.assertEqual(run.get_total_loops(), 4)

        runs = bench.get_runs()
        self.assertEqual(len(runs), 2)
        for run in runs:
            self.assertIsInstance(run, pyperf.Run)
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
            bench = pyperf.Benchmark.load(filename)
            self.assertEqual(bench.get_nvalue(), 1)

            self.run_timeit(args)
            bench = pyperf.Benchmark.load(filename)
            self.assertEqual(bench.get_nvalue(), 2)

    def test_cli_snippet_error(self):
        args = PERF_TIMEIT + ('x+1',)
        cmd = tests.get_output(args)
        self.assertEqual(cmd.returncode, 1)

        self.assertIn('Traceback (most recent call last):', cmd.stderr)
        self.assertIn("NameError", cmd.stderr)

    # When the PyPy program is copied, it fails with "Library path not found"
    @unittest.skipIf(pyperf.python_implementation() == 'pypy',
                     'pypy program cannot be copied')
    @unittest.skipIf(sys.platform == 'win32',
                     'https://github.com/psf/pyperf/issues/97')
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

        tmp_exe = Path(tmp_exe).resolve()
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
            ref: \. [0-9.]+ (?:ms|us) \+- [0-9.]+ (?:ms|us).*
            changed: \. [0-9.]+ (?:ms|us) \+- [0-9.]+ (?:ms|us).*
            Mean \+- std dev: \[ref\] .* -> \[changed\] .*: (?:[0-9]+\.[0-9][0-9]x (?:faster|slower)|no change)
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

    def test_teardown_single_line(self):
        args = PERF_TIMEIT + ('--teardown', 'assert 2 == 2') + FAST_BENCH_ARGS
        cmd = tests.get_output(args)

        self.assertEqual(cmd.returncode, 0, cmd.stdout + cmd.stderr)

    def test_teardown_multi_line(self):
        args = PERF_TIMEIT + ('--teardown', 'assert 2 == 2',
                              '--teardown', 'assert 2 == 2') + FAST_BENCH_ARGS
        cmd = tests.get_output(args)

        self.assertEqual(cmd.returncode, 0, cmd.stdout + cmd.stderr)


class TimerTests(unittest.TestCase):
    def test_raises_if_setup_is_missing(self):
        with self.assertRaises(ValueError) as cm:
            Timer(setup=None)

        err = cm.exception
        self.assertEqual(str(err), 'setup is neither a string nor callable')

    def test_raises_if_stmt_is_missing(self):
        with self.assertRaises(ValueError) as cm:
            Timer(stmt=None)

        err = cm.exception
        self.assertEqual(str(err), 'stmt is neither a string nor callable')

    def test_raises_if_teardown_is_missing(self):
        with self.assertRaises(ValueError) as cm:
            Timer(teardown=None)

        err = cm.exception
        self.assertEqual(str(err), 'teardown is neither a string nor callable')

    def test_raises_if_setup_contains_invalid_syntax(self):
        with self.assertRaises(SyntaxError) as cm:
            Timer(setup='foo = 1, 2, *')

        err = cm.exception
        self.assertTrue('invalid syntax' in str(err))

    def test_raises_if_stmt_contains_invalid_syntax(self):
        with self.assertRaises(SyntaxError) as cm:
            Timer(stmt='foo = 1, 2, *')

        err = cm.exception
        self.assertTrue('invalid syntax' in str(err))

    def test_raises_if_teardown_contains_invalid_syntax(self):
        with self.assertRaises(SyntaxError) as cm:
            Timer(teardown='foo = 1, 2, *')

        err = cm.exception
        self.assertTrue('invalid syntax' in str(err))

    def test_raises_if_setup_and_stmt_contain_invalid_syntax(self):
        with self.assertRaises(SyntaxError) as cm:
            Timer(setup="foo = 'bar', \\ ", stmt="bar = 'baz'")

        err = cm.exception

        if PYPY:
            self.assertTrue("Unknown character" in str(err))
        else:
            self.assertTrue('unexpected character after line' in str(err))

    def test_raises_if_stmt_and_teardown_contain_invalid_syntax(self):
        with self.assertRaises(SyntaxError) as cm:
            Timer(stmt="foo = 'bar', \\ ", teardown="bar = 'baz'")

        err = cm.exception

        if PYPY:
            self.assertTrue("Unknown character" in str(err))
        else:
            self.assertTrue('unexpected character after line' in str(err))

    def test_returns_valid_template_if_setup_is_str(self):
        setup = "foo = 'bar'\nbar = 'baz'"
        timer = Timer(setup=setup)
        self.assertEqual(timer.src, template_output(setup=setup))

    def test_returns_valid_template_if_stmt_is_str(self):
        stmt = "foo = 'bar'\nbar = 'baz'"
        timer = Timer(stmt=stmt)
        self.assertEqual(timer.src, template_output(stmt=stmt))

    def test_returns_valid_template_if_teardown_is_str(self):
        teardown = "foo = 'bar'\nbar = 'baz'"
        timer = Timer(teardown=teardown)
        self.assertEqual(timer.src, template_output(teardown=teardown))

    def test_returns_valid_template_with_all_str_params(self):
        setup, stmt, teardown = "a = 1 + 2", "b = 2 + 3", "c = 3 + 4"
        timer = Timer(setup=setup, stmt=stmt, teardown=teardown)
        self.assertEqual(timer.src, template_output(stmt, setup, teardown))

    def test_returns_valid_template_if_setup_is_code(self):
        setup = identity
        timer = Timer(setup=setup)
        output = template_output(setup='_setup()', init=', _setup=_setup')
        self.assertEqual(timer.src, output)
        self.assertDictEqual({'_setup': setup}, timer.local_ns)

    def test_returns_valid_template_if_stmt_is_code(self):
        stmt = identity
        timer = Timer(stmt=stmt)
        output = template_output(stmt='_stmt()', init=', _stmt=_stmt')
        self.assertEqual(timer.src, output)
        self.assertDictEqual({'_stmt': stmt}, timer.local_ns)

    def test_returns_valid_template_if_teardown_is_code(self):
        teardown = identity
        timer = Timer(teardown=teardown)
        output = template_output(teardown='_teardown()',
                                 init=', _teardown=_teardown')
        self.assertEqual(timer.src, output)
        self.assertDictEqual({'_teardown': teardown}, timer.local_ns)

    def test_returns_valid_template_with_all_callable_params(self):
        setup, stmt, teardown = identity, identity, identity
        timer = Timer(setup=setup, stmt=stmt, teardown=teardown)
        output = template_output(setup='_setup()', stmt='_stmt()',
                                 teardown='_teardown()',
                                 init=', _setup=_setup, _stmt=_stmt, '
                                      '_teardown=_teardown')
        self.assertEqual(timer.src, output)
        self.assertDictEqual({'_setup': setup, '_stmt': stmt,
                              '_teardown': teardown}, timer.local_ns)


if __name__ == "__main__":
    unittest.main()
