import subprocess
import sys
import tempfile
import unittest

import perf


class TestPerfCLI(unittest.TestCase):
    def test_run_result(self):
        run = perf.RunResult([1.0, 1.5, 2.0], loops=100)
        json = run.json()

        with tempfile.NamedTemporaryFile() as tmp:
            tmp.write(json)
            tmp.seek(0)

            args = [sys.executable, '-m', 'perf', tmp.name]

            proc = subprocess.Popen(args,
                                    stdout=subprocess.PIPE,
                                    universal_newlines=True)
            stdout = proc.communicate()[0]
        self.assertEqual(proc.returncode, 0)

        self.assertEqual(stdout.rstrip(),
                         'Average: 1.50 sec +- 0.50 sec '
                         '(3 samples x 100 loops)')

    def results(self, verbose=False):
        runs = [perf.RunResult([1.0], loops=100),
                perf.RunResult([1.5], loops=100),
                perf.RunResult([2.0], loops=100)]
        json = [run.json() for run in runs]
        json = '\n'.join(json)
        # check that empty lines are ignore
        json = '\n' + json + '\n\n'

        with tempfile.NamedTemporaryFile() as tmp:
            tmp.write(json)
            tmp.seek(0)

            args = [sys.executable, '-m', 'perf', tmp.name]
            if verbose:
                args.append('-v')
            proc = subprocess.Popen(args,
                                    stdout=subprocess.PIPE,
                                    universal_newlines=True)
            stdout = proc.communicate()[0]
        self.assertEqual(proc.returncode, 0)
        return stdout

    def test_results(self):
        stdout = self.results()
        self.assertEqual(stdout.rstrip(),
                         'Average: 1.50 sec +- 0.50 sec '
                         '(3 runs x 1 sample x 100 loops)')

    def test_results_verbose(self):
        stdout = self.results(True)
        self.assertEqual(stdout.rstrip(),
                         'Run 1/3: runs (1): 1.00 sec\n'
                         'Run 2/3: runs (1): 1.50 sec\n'
                         'Run 3/3: runs (1): 2.00 sec\n'
                         'Average: 1.50 sec +- 0.50 sec '
                         '(min: 1.00 sec, max: 2.00 sec) '
                         '(3 runs x 1 sample x 100 loops)')


if __name__ == "__main__":
    unittest.main()
