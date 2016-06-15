import os
import re
import subprocess
import sys
import tempfile
import unittest

import perf


SLEEP = 'time.sleep(1e-3)'
# The perfect timing is 1 ms +- 0 ms, but tolerate large differences on busy
# systems. The unit test doesn't test the system but more the output format.
MIN_SAMPLE = 0.9 # ms
MAX_SAMPLE = 5.0 # ms
MIN_MEAN = MIN_SAMPLE
MAX_MEAN = MAX_SAMPLE / 2
MAX_STDEV = 1.5 # ms


class TestTimeit(unittest.TestCase):
    def test_raw_verbose(self):
        args = [sys.executable,
                '-m', 'perf.timeit',
                '--raw',
                '-w', '1',
                '-n', '2',
                '-l', '1',
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
                         r'Sample 1: ([0-9.]+) ms\n'
                         r'Sample 2: ([0-9.]+) ms\n'
                         r'Metadata:\n'
                         r'(- .*\n)+'
                         r'\n'
                         r'Average: (?P<avg>[0-9.]+) ms \+- (?P<stdev>[0-9.]+) ms '
                             r'\(2 samples\)\n'
                         r'$',
                         stdout)
        self.assertIsNotNone(match, repr(stdout))

        values = [float(match.group(i)) for i in range(1, 4)]
        for value in values:
            self.assertTrue(MIN_SAMPLE <= value <= MAX_SAMPLE,
                            repr(value))

        mean = float(match.group('avg'))
        self.assertTrue(MIN_MEAN <= mean <= MAX_MEAN, mean)
        stdev = float(match.group('stdev'))
        self.assertLessEqual(stdev, MAX_STDEV)

    def test_cli(self):
        args = [sys.executable,
                '-m', 'perf.timeit',
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

        match = re.match(r'^\.\.\n'
                         r'Average: (?P<avg>[0-9.]+) ms'
                             r' \+- (?P<stdev>[0-9.]+) ms'
                         r'$',
                         stdout.rstrip())
        self.assertIsNotNone(match, repr(stdout))

        # Tolerate large differences on busy systems
        mean = float(match.group('avg'))
        self.assertTrue(MIN_MEAN <= mean <= MAX_MEAN, mean)

        stdev = float(match.group('stdev'))
        self.assertLessEqual(stdev, MAX_STDEV)

    def test_json_file(self):
        if perf._PY3:
            tmp = tempfile.NamedTemporaryFile('w+', encoding='utf-8')
        else:
            tmp = tempfile.NamedTemporaryFile()
        with tmp:
            args = [sys.executable,
                    '-m', 'perf.timeit',
                    '-p', '2',
                    '-n', '3',
                    '-l', '4',
                    '--json-file', tmp.name,
                    '-s', 'import time',
                    SLEEP]
            proc = subprocess.Popen(args,
                                    stdout=subprocess.PIPE,
                                    universal_newlines=True)
            stdout = proc.communicate()[0]
            self.assertEqual(proc.returncode, 0)

            bench = perf.Benchmark.json_load_from(tmp)

        self.assertEqual(len(bench._runs), 2)
        self.assertEqual(bench.loops, 4)
        self.assertEqual(bench.get_metadata()['loops'], '4')
        for run in bench._runs:
            self.assertEqual(len(run.warmups), 1)
            self.assertEqual(len(run.samples), 3)

            # Tolerate large differences on busy systems
            for warmup in run.warmups:
                self.assertTrue(MIN_SAMPLE <= warmup * 1e3 <= MAX_SAMPLE, warmup)
            for sample in run.samples:
                self.assertTrue(MIN_SAMPLE <= sample * 1e3 <= MAX_SAMPLE, sample)

    def test_cli_help(self):
        args = [sys.executable,
                '-m', 'perf.timeit', '--help']
        env = dict(os.environ, COLUMNS='1000')
        proc = subprocess.Popen(args,
                                stdout=subprocess.PIPE,
                                universal_newlines=True,
                                env=env)
        stdout = proc.communicate()[0]
        self.assertEqual(proc.returncode, 0)

        self.assertIn('[-h] [-p PROCESSES] [-n NSAMPLE] [-w NWARMUP] [-l LOOPS] '
                      '[-v] [--json] [--json-file FILENAME] [--min-time MIN_TIME] '
                      '[--max-time MAX_TIME] [--raw] [--metadata] '
                      '[--affinity CPU_LIST] [-s SETUP] stmt [stmt ...]',
                      stdout)

    def test_cli_snippet_error(self):
        args = [sys.executable,
                '-m', 'perf.timeit', 'x+1']
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
