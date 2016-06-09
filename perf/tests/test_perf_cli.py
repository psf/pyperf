import subprocess
import sys
import tempfile
import unittest

import perf


class TestPerfCLI(unittest.TestCase):
    #def test_run_result(self):
    #    run = perf.RunResult([1.0, 1.5, 2.0])
    #    json = run.json()

    #    with tempfile.NamedTemporaryFile(mode="w+") as tmp:
    #        tmp.write(json)
    #        tmp.seek(0)

    #        args = [sys.executable, '-m', 'perf', 'show', tmp.name]

    #        proc = subprocess.Popen(args,
    #                                stdout=subprocess.PIPE,
    #                                universal_newlines=True)
    #        stdout = proc.communicate()[0]
    #    self.assertEqual(proc.returncode, 0)

    #    self.assertEqual(stdout.rstrip(),
    #                     'Average: 1.50 sec +- 0.50 sec')

    def results(self, verbose=False, metadata=True):
        runs = []
        for sample in (1.0, 1.5, 2.0):
            run = perf.RunResult([sample])
            run.metadata['key'] = 'value'
            runs.append(run)
        results = perf.Results(runs=runs)
        results.metadata = {'key': 'value'}

        with tempfile.NamedTemporaryFile(mode="w+") as tmp:
            results.json_dump_into(tmp)
            tmp.seek(0)

            args = [sys.executable, '-m', 'perf', 'show', tmp.name]
            if verbose:
                args.append('-v')
            if not metadata:
                args.append('-M')
            proc = subprocess.Popen(args,
                                    stdout=subprocess.PIPE,
                                    universal_newlines=True)
            stdout = proc.communicate()[0]
        self.assertEqual(proc.returncode, 0)
        return stdout

    def test_results(self):
        stdout = self.results()
        self.assertEqual(stdout.rstrip(),
                         'Metadata:\n'
                         '- key: value\n'
                         '\n'
                         'Average: 1.50 sec +- 0.50 sec')

    def test_results_verbose(self):
        stdout = self.results(verbose=True, metadata=False)
        self.assertEqual(stdout.rstrip(),
                         'Run 1/3: samples (1): 1.00 sec\n'
                         'Run 2/3: samples (1): 1.50 sec\n'
                         'Run 3/3: samples (1): 2.00 sec\n'
                         '\n'
                         'Average: 1.50 sec +- 0.50 sec '
                         '(3 runs x 1 sample)')


if __name__ == "__main__":
    unittest.main()
