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
        self.assertEqual(len(lines), 2)
        values = [float(line) for line in lines]
        for value in values:
            self.assertTrue(0.09 <= value <= 0.20, repr(value))

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

        text = 'Average on 3 process x 2 runs (1 loops): 100 ms +- 0 ms'
        self.assertEqual(stdout.rstrip(), text, repr(stdout))


if __name__ == "__main__":
    unittest.main()
