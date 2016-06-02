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
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[0], 'loops=1')
        values = [float(line) for line in lines[1:]]
        for value in values:
            self.assertTrue(0.090 <= value <= 0.150, repr(value))

    def test_cli(self):
        args = [sys.executable,
                '-m', 'perf.timeit',
                '-r', '2',
                '-n', '1',
                '-s', 'import time',
                'time.sleep(0.1)']
        proc = subprocess.Popen(args,
                                stdout=subprocess.PIPE,
                                universal_newlines=True)
        stdout = proc.communicate()[0]
        self.assertEqual(proc.returncode, 0)

        match = re.match(r'^Average: 25 runs x 2 samples x 1 loop: '
                         r'([0-9]+) ms \+- ([0-9]+) ms$',
                         stdout.rstrip())
        self.assertIsNotNone(match, repr(stdout))
        mean = int(match.group(1))
        self.assertTrue(90 <= mean <= 100, mean)
        stdev = int(match.group(2))
        self.assertTrue(0 <= stdev <= 10, stdev)


if __name__ == "__main__":
    unittest.main()
