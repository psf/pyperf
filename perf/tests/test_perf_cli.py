import subprocess
import sys
import unittest

import perf


class TestPerfCLI(unittest.TestCase):
    def test_run_result(self):
        run = perf.RunResult([1.0, 1.5, 2.0], loops=100)
        json = run.json()

        args = [sys.executable, '-m', 'perf']
        proc = subprocess.Popen(args,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                universal_newlines=True)
        stdout = proc.communicate(json)[0]
        self.assertEqual(proc.returncode, 0)

        self.assertEqual(stdout.rstrip(),
                         'Average: 1.50 sec +- 0.50 sec '
                         '(3 samples x 100 loops)')

    def test_results(self):
        runs = [perf.RunResult([1.0], loops=100),
                perf.RunResult([1.5], loops=100),
                perf.RunResult([2.0], loops=100)]
        json = [run.json() for run in runs]
        json = '\n'.join(json)
        # check that empty lines are ignore
        json = '\n' + json + '\n\n'

        args = [sys.executable, '-m', 'perf']
        proc = subprocess.Popen(args,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                universal_newlines=True)
        stdout = proc.communicate(json)[0]
        self.assertEqual(proc.returncode, 0)

        self.assertEqual(stdout.rstrip(),
                         'Average: 1.50 sec +- 0.50 sec '
                         '(3 runs x 1 sample x 100 loops)')


if __name__ == "__main__":
    unittest.main()
