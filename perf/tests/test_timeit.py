import re
import subprocess
import sys
import unittest


class TestTimeit(unittest.TestCase):
    def test_raw(self):
        args = [sys.executable,
                '-m', 'perf.timeit',
                '--raw',
                '-r', '2',
                '-n', '1',
                '-s', 'import time',
                'time.sleep(0.1)']
        proc = subprocess.Popen(args,
                                stdout=subprocess.PIPE,
                                universal_newlines=True)
        stdout = proc.communicate()[0]
        self.assertEqual(proc.returncode, 0)

        lines = stdout.splitlines()
        self.assertEqual(len(lines), 4)
        self.assertEqual(lines[0], 'loops=1')
        values = [float(line) for line in lines[1:]]
        for value in values:
            self.assertTrue(0.090 <= value <= 0.150, repr(value))

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
                         r'Average: 2 runs x 3 samples x 4 loops: '
                         r'([0-9]+\.[0-9]+) ms \+- ([0-9]+\.[0-9]+) ms$',
                         stdout.rstrip())
        self.assertIsNotNone(match, repr(stdout))
        mean = float(match.group(1))
        self.assertTrue(0.9 <= mean <= 1.5, mean)
        stdev = float(match.group(2))
        self.assertTrue(0 <= stdev <= 0.10, stdev)


if __name__ == "__main__":
    unittest.main()
