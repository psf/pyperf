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
    #        tmp.flush()

    #        args = [sys.executable, '-m', 'perf', 'show', tmp.name]

    #        proc = subprocess.Popen(args,
    #                                stdout=subprocess.PIPE,
    #                                universal_newlines=True)
    #        stdout = proc.communicate()[0]
    #    self.assertEqual(proc.returncode, 0)

    #    self.assertEqual(stdout.rstrip(),
    #                     'Average: 1.50 sec +- 0.50 sec')

    def create_runs(self, samples, metadata=None):
        runs = []
        for sample in samples:
            run = perf.RunResult([sample])
            if metadata:
                run.metadata.update(metadata)
            runs.append(run)
        return runs

    def show(self, verbose=False, metadata=True):
        runs = self.create_runs((1.0, 1.5, 2.0), {'key': 'value'})
        results = perf.Benchmark(runs=runs)

        with tempfile.NamedTemporaryFile(mode="w+") as tmp:
            results.json_dump_into(tmp)
            tmp.flush()

            args = [sys.executable, '-m', 'perf']
            if verbose:
                args.append('-v')
            if not metadata:
                args.append('-M')
            args.extend(('show', tmp.name))

            proc = subprocess.Popen(args,
                                    stdout=subprocess.PIPE,
                                    universal_newlines=True)
            stdout = proc.communicate()[0]
        self.assertEqual(proc.returncode, 0)
        return stdout

    def test_show(self):
        stdout = self.show()
        self.assertEqual(stdout.rstrip(),
                         'Metadata:\n'
                         '- key: value\n'
                         '\n'
                         'Average: 1.50 sec +- 0.50 sec')

    def test_show_verbose(self):
        stdout = self.show(verbose=True, metadata=False)
        self.assertEqual(stdout.rstrip(),
                         'Run 1/3: samples (1): 1.00 sec\n'
                         'Run 2/3: samples (1): 1.50 sec\n'
                         'Run 3/3: samples (1): 2.00 sec\n'
                         '\n'
                         'Average: 1.50 sec +- 0.50 sec '
                         '(3 runs x 1 sample)')

    def compare(self, action, ref_result, changed_result):
        with tempfile.NamedTemporaryFile(mode="w+") as ref_tmp:
            ref_result.json_dump_into(ref_tmp)
            ref_tmp.flush()

            with tempfile.NamedTemporaryFile(mode="w+") as changed_tmp:
                changed_result.json_dump_into(changed_tmp)
                changed_tmp.flush()

                args = [sys.executable, '-m', 'perf',
                        action, ref_tmp.name, changed_tmp.name]

                proc = subprocess.Popen(args,
                                        stdout=subprocess.PIPE,
                                        universal_newlines=True)
                stdout = proc.communicate()[0]

        self.assertEqual(proc.returncode, 0)
        return stdout

    def test_compare_to(self):
        runs = self.create_runs((1.0, 1.5, 2.0),
                                {'hostname': 'toto', 'python_version': '2.7'})
        ref_result = perf.Benchmark(runs=runs, name='py2')

        runs = self.create_runs((1.5, 2.0, 2.5),
                                {'hostname': 'toto', 'python_version': '3.4'})
        changed_result = perf.Benchmark(runs=runs, name='py3')

        stdout = self.compare('compare_to', ref_result, changed_result)

        expected = ('Reference: py2\n'
                    'Changed: py3\n'
                    '\n'
                    'Common metadata:\n'
                    '- hostname: toto\n'
                    '\n'
                    'py2 metadata:\n'
                    '- python_version: 2.7\n'
                    '\n'
                    'py3 metadata:\n'
                    '- python_version: 3.4\n'
                    '\n'
                    'Average: [py2] 1.50 sec +- 0.50 sec '
                        '-> [py3] 2.00 sec +- 0.50 sec: 1.3x slower\n'
                    'Not significant!')
        self.assertEqual(stdout.rstrip(),
                         expected)

    def test_compare(self):
        runs = self.create_runs((1.0, 1.5, 2.0))
        ref_result = perf.Benchmark(runs=runs, name='py2')

        runs = self.create_runs((1.5, 2.0, 2.5))
        changed_result = perf.Benchmark(runs=runs, name='py3')

        stdout = self.compare('compare', ref_result, changed_result)

        expected = ('Reference (best): py2\n'
                    '\n'
                    'Average: [py2] 1.50 sec +- 0.50 sec '
                        '-> [py3] 2.00 sec +- 0.50 sec: 1.3x slower\n'
                    'Not significant!')
        self.assertEqual(stdout.rstrip(),
                         expected)



if __name__ == "__main__":
    unittest.main()
