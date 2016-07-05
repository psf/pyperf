import re
import subprocess
import sys
import tempfile
import unittest

import six

import perf


SLEEP = 'time.sleep(1e-3)'
# The perfect timing is 1 ms +- 0 ms, but tolerate large differences on busy
# systems. The unit test doesn't test the system but more the output format.
MIN_SAMPLE = 0.9 # ms
MAX_SAMPLE = 10.0 # ms
MIN_MEAN = MIN_SAMPLE
MAX_MEAN = MAX_SAMPLE / 2
MAX_STDEV = 1.5 # ms


class TestTimeit(unittest.TestCase):
    def test_raw_verbose(self):
        args = [sys.executable,
                '-m', 'perf', 'timeit',
                '--raw',
                '-w', '1',
                '-n', '2',
                '-l', '1',
                '--metadata',
                '-v',
                '-s', 'import time',
                SLEEP]
        proc = subprocess.Popen(args,
                                stdout=subprocess.PIPE,
                                universal_newlines=True)
        stdout = proc.communicate()[0]
        self.assertEqual(proc.returncode, 0)

        match = re.match(r'^'
                         r'(?:Pin process to.* CPUs: [0-9,-]+\n)?'
                         r'Warmup 1: ([0-9.]+) ms\n'
                         r'Raw sample 1: ([0-9.]+) ms\n'
                         r'Raw sample 2: ([0-9.]+) ms\n'
                         r'\n'
                         r'Metadata:\n'
                         r'(- .*\n)+'
                         r'\n'
                         r'Median \+- std dev: (?P<median>[0-9.]+) ms \+- (?P<stdev>[0-9.]+) ms\n'
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
                '-n', '3',
                '-l', '4',
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

    def test_json_file(self):
        if six.PY3:
            tmp = tempfile.NamedTemporaryFile('w+', encoding='utf-8')
        else:
            tmp = tempfile.NamedTemporaryFile()
        loops = 4
        with tmp:
            args = [sys.executable,
                    '-m', 'perf', 'timeit',
                    '-p', '2',
                    '-n', '3',
                    '-l', str(loops),
                    '--json-file', tmp.name,
                    '-s', 'import time',
                    SLEEP]
            proc = subprocess.Popen(args,
                                    stdout=subprocess.PIPE,
                                    universal_newlines=True)
            proc.communicate()
            self.assertEqual(proc.returncode, 0)

            bench = perf.Benchmark.load(tmp.name)

        self.assertEqual(bench.loops, 4)

        runs = bench.get_runs()
        self.assertEqual(len(runs), 2)
        for samples in runs:
            self.assertEqual(len(samples), 4)
            for sample in samples:
                dt = (sample / loops) * 1e3
                self.assertTrue(MIN_SAMPLE <= dt <= MAX_SAMPLE, dt)

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


if __name__ == "__main__":
    unittest.main()
