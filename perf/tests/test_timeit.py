import os
import re
import subprocess
import sys
import tempfile
import unittest

import perf


class TestTimeit(unittest.TestCase):
    def test_raw(self):
        args = [sys.executable,
                '-m', 'perf.timeit',
                '--raw',
                '-w', '1',
                '-n', '2',
                '-l', '1',
                '-v',
                '-s', 'import time',
                'time.sleep(0.1)']
        proc = subprocess.Popen(args,
                                stdout=subprocess.PIPE,
                                universal_newlines=True)
        stdout = proc.communicate()[0]
        self.assertEqual(proc.returncode, 0)

        match = re.match(r'^'
                         r'(?:Set affinity to isolated CPUs: \[[0-9 ,]+\]\n)?'
                         r'Warmup 1: ([0-9]+) ms\n'
                         r'Run 1: ([0-9]+) ms\n'
                         r'Run 2: ([0-9]+) ms\n'
                         r'Metadata:\n'
                         r'(- .*\n)+'
                         r'\n'
                         r'Average: (?P<avg>[0-9]+) ms \+- (?P<stdev>[0-9]+) ms '
                             r'\(2 samples\)\n'
                         r'$',
                         stdout)
        self.assertIsNotNone(match, repr(stdout))

        values = [float(match.group(i)) for i in range(1, 4)]
        for value in values:
            self.assertTrue(90 <= value <= 150, repr(value))

        mean = float(match.group('avg'))
        self.assertTrue(90 <= mean <= 150, mean)
        stdev = float(match.group('stdev'))
        self.assertLessEqual(stdev, 10)

    def test_cli(self):
        args = [sys.executable,
                '-m', 'perf.timeit',
                '-p', '2',
                '-n', '3',
                '-l', '4',
                '-s', 'import time',
                'time.sleep(1e-3)']
        proc = subprocess.Popen(args,
                                stdout=subprocess.PIPE,
                                universal_newlines=True)
        stdout = proc.communicate()[0]
        self.assertEqual(proc.returncode, 0)

        match = re.match(r'^\.\.\n'
                         r'Average: (?P<avg>[0-9]+\.[0-9]+) ms'
                             r' \+- (?P<stdev>[0-9]+\.[0-9]+) ms'
                         r'$',
                         stdout.rstrip())
        self.assertIsNotNone(match, repr(stdout))
        mean = float(match.group('avg'))
        self.assertTrue(0.9 <= mean <= 1.5, mean)
        stdev = float(match.group('stdev'))
        self.assertTrue(0 <= stdev <= 0.10, stdev)

    def test_json_file(self):
        with tempfile.NamedTemporaryFile() as tmp:
            args = [sys.executable,
                    '-m', 'perf.timeit',
                    '-p', '2',
                    '-n', '3',
                    '-l', '4',
                    '--json-file', tmp.name,
                    '-s', 'import time',
                    'time.sleep(1e-3)']
            proc = subprocess.Popen(args,
                                    stdout=subprocess.PIPE,
                                    universal_newlines=True)
            stdout = proc.communicate()[0]
            self.assertEqual(proc.returncode, 0)

            json = tmp.read()
            if perf._PY3:
                json = json.decode('utf-8')
            result = perf.Results.json_loads(json)

        self.assertEqual(len(result.runs), 2)
        for run in result.runs:
            self.assertEqual(len(run.warmups), 1)
            self.assertEqual(len(run.samples), 3)
            self.assertEqual(run.metadata['timeit_loops'], '4')

            for warmup in run.warmups:
                self.assertTrue(0.9e-3 <= warmup <= 1.5e-3, warmup)
            for sample in run.samples:
                self.assertTrue(0.9e-3 <= sample <= 1.5e-3, sample)

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

        self.assertIn('[-h] [-p PROCESSES] [-n NSAMPLE] [-w NWARMUP] '
                      '[-v] [--json] [--json-file FILENAME] [--raw] [--metadata] [-l LOOPS] '
                      '[-s SETUP] stmt [stmt ...]',
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
