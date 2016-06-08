import os
import re
import subprocess
import sys
import unittest


class TestTimeit(unittest.TestCase):
    def test_raw(self):
        args = [sys.executable,
                '-m', 'perf.timeit',
                '--raw',
                '-w', '1',
                '-r', '2',
                '-n', '1',
                '-v',
                '-s', 'import time',
                'time.sleep(0.1)']
        proc = subprocess.Popen(args,
                                stdout=subprocess.PIPE,
                                universal_newlines=True)
        stdout = proc.communicate()[0]
        self.assertEqual(proc.returncode, 0)

        match = re.match(r'^1 loop\n'
                         r'Warmup 1: ([0-9]+) ms\n'
                         r'Run 1: ([0-9]+) ms\n'
                         r'Run 2: ([0-9]+) ms\n'
                         r'Average: ([0-9]+) ms \+- ([0-9]+) ms '
                            r'\(min: ([0-9]+) ms, max: ([0-9]+) ms\) '
                            r'\(2 samples\)\n'
                         r'$',
                         stdout)
        self.assertIsNotNone(match, repr(stdout))

        values = [float(match.group(i)) for i in range(1, 4)]
        for value in values:
            self.assertTrue(90 <= value <= 150, repr(value))

        mean = float(match.group(4))
        self.assertTrue(90 <= mean <= 150, mean)
        stdev = float(match.group(5))
        self.assertLessEqual(stdev, 10)

        min_dt, max_dt = float(match.group(6)), float(match.group(7))
        self.assertTrue(90 <= min_dt <= max_dt < 150, (min_dt, max_dt))

    def test_cli(self):
        args = [sys.executable,
                '-m', 'perf.timeit',
                '-p', '2',
                '-r', '3',
                '-n', '4',
                '-s', 'import time',
                'time.sleep(1e-3)']
        proc = subprocess.Popen(args,
                                stdout=subprocess.PIPE,
                                universal_newlines=True)
        stdout = proc.communicate()[0]
        self.assertEqual(proc.returncode, 0)

        match = re.match(r'^\.\.\n'
                         r'Average: ([0-9]+\.[0-9]+) ms'
                             r' \+- ([0-9]+\.[0-9]+) ms'
                         r' \(2 runs x 3 samples x 4 loops\)$',
                         stdout.rstrip())
        self.assertIsNotNone(match, repr(stdout))
        mean = float(match.group(1))
        self.assertTrue(0.9 <= mean <= 1.5, mean)
        stdev = float(match.group(2))
        self.assertTrue(0 <= stdev <= 0.10, stdev)

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

        self.assertIn('[-h] [-v] [--json] [--raw] [--metadata] [-p PROCESSES] '
                      '[-n LOOPS] [-r REPEAT] [-w WARMUPS] [-s SETUP] stmt [stmt ...]',
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
