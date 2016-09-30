import errno
import os.path
import re
import shutil
import six
import subprocess
import sys
import tempfile

import perf
from perf import tests
from perf.tests import unittest


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
        args = [sys.executable,
                '-m', 'perf', 'timeit',
                '--worker',
                '-w', '1',
                '-n', '2',
                '-l', '1',
                '--min-time', '0.001',
                '--metadata',
                '-v',
                '-s', 'import time',
                SLEEP]
        proc = subprocess.Popen(args,
                                stdout=subprocess.PIPE,
                                universal_newlines=True)
        stdout = proc.communicate()[0]
        self.assertEqual(proc.returncode, 0)

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
                          stdout)
        self.assertIsNotNone(match, repr(stdout))

        values = [float(match.group(i)) for i in range(1, 4)]
        for value in values:
            self.assertTrue(MIN_SAMPLE <= value <= MAX_SAMPLE,
                            repr(value))

        median = float(match.group('median'))
        self.assertTrue(MIN_MEAN <= median <= MAX_MEAN, median)
        stdev = float(match.group('stdev'))
        self.assertLessEqual(stdev, MAX_STDEV)

    def test_cli(self):
        args = [sys.executable,
                '-m', 'perf', 'timeit',
                '-p', '2',
                '-w', '1',
                '-n', '3',
                '-l', '4',
                '--min-time', '0.001',
                '-s', 'import time',
                SLEEP]
        proc = subprocess.Popen(args,
                                stdout=subprocess.PIPE,
                                universal_newlines=True)
        stdout = proc.communicate()[0]
        self.assertEqual(proc.returncode, 0)

        # ignore lines before to ignore random warnings like
        # "ERROR: the benchmark is very unstable"
        match = re.search(r'Median \+- std dev: (?P<median>[0-9.]+) ms'
                          r' \+- (?P<stdev>[0-9.]+) ms'
                          r'$',
                          stdout.rstrip())
        self.assertIsNotNone(match, repr(stdout))

        # Tolerate large differences on busy systems
        median = float(match.group('median'))
        self.assertTrue(MIN_MEAN <= median <= MAX_MEAN, median)

        stdev = float(match.group('stdev'))
        self.assertLessEqual(stdev, MAX_STDEV)

    def run_timeit(self, args):
        proc = subprocess.Popen(args,
                                stdout=subprocess.PIPE,
                                universal_newlines=True)
        if six.PY3:
            with proc:
                proc.communicate()
        else:
            proc.communicate()
        self.assertEqual(proc.returncode, 0)

    def test_output(self):
        loops = 4
        with tests.temporary_directory() as tmpdir:
            filename = os.path.join(tmpdir, 'test.json')
            args = [sys.executable,
                    '-m', 'perf', 'timeit',
                    '-p', '2',
                    '-w', '1',
                    '-n', '3',
                    '-l', str(loops),
                    '--min-time', '0.001',
                    '--output', filename,
                    '--name', 'test_output',
                    '-s', 'import time',
                    SLEEP]
            self.run_timeit(args)
            bench = perf.Benchmark.load(filename)

        self.assertEqual(bench.get_name(), 'test_output')

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
            args = [sys.executable,
                    '-m', 'perf', 'timeit',
                    '-p', '1',
                    '-n', '1',
                    '-l', '1',
                    '-w', '0',
                    '--append', filename,
                    '-s', 'import time',
                    SLEEP]

            self.run_timeit(args)
            bench = perf.Benchmark.load(filename)
            self.assertEqual(bench.get_nsample(), 1)

            self.run_timeit(args)
            bench = perf.Benchmark.load(filename)
            self.assertEqual(bench.get_nsample(), 2)

    def test_cli_snippet_error(self):
        args = [sys.executable,
                '-m', 'perf', 'timeit', 'x+1']
        proc = subprocess.Popen(args,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                universal_newlines=True)
        stdout, stderr = proc.communicate()
        self.assertEqual(proc.returncode, 1)

        self.assertIn('Traceback (most recent call last):', stderr)
        self.assertIn("NameError", stderr)

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
            args = [sys.executable,
                    '-m', 'perf', 'timeit',
                    '--metadata', '--debug-single-sample',
                    '--python', tmp_exe,
                    '--inherit-env', 'PYTHONPATH',
                    '-s', 'import time',
                    SLEEP]
            proc = subprocess.Popen(args,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    universal_newlines=True,
                                    env=env)
            stdout, stderr = proc.communicate()
        finally:
            try:
                os.unlink(tmp_exe)
            except OSError as exc:
                if exc.errno != errno.ENOENT:
                    raise

        self.assertEqual(proc.returncode, 0, repr(stdout + stderr))
        self.assertIn("python_executable: %s" % tmp_exe, stdout)


if __name__ == "__main__":
    unittest.main()
