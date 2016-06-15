import subprocess
import sys
import tempfile
import unittest

import perf


class TestPerfCLI(unittest.TestCase):
    def create_bench(self, samples, **kw):
        bench = perf.Benchmark(**kw)
        for sample in samples:
            bench.add_run([sample])
        return bench

    def show(self, verbose=False, metadata=True):
        results = self.create_bench((1.0, 1.5, 2.0), metadata={'key': 'value'})

        with tempfile.NamedTemporaryFile(mode="w+") as tmp:
            results.json_dump_into(tmp)
            tmp.flush()

            args = [sys.executable, '-m', 'perf']
            if verbose:
                args.append('-' + 'v' * verbose)
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
        expected = ('Metadata:\n'
                    '- key: value\n'
                    '\n'
                    'ERROR: the benchmark is very unstable, the standard '
                        'deviation is very high (33%)!\n'
                    'Try to rerun the benchmark with more runs, samples '
                        'and/or loops\n'
                    '\n'
                    'Average: 1.50 sec +- 0.50 sec\n')
        self.assertEqual(stdout, expected)

    def test_show_verbose(self):
        stdout = self.show(verbose=2, metadata=False)
        expected = ('Run 1/3: samples (1): 1.00 sec\n'
                    'Run 2/3: samples (1): 1.50 sec\n'
                    'Run 3/3: samples (1): 2.00 sec\n'
                    '\n'
                    'ERROR: the benchmark is very unstable, the standard '
                        'deviation is very high (33%)!\n'
                    'Try to rerun the benchmark with more runs, samples '
                        'and/or loops\n'
                    '\n'
                    'Shortest sample: 1.00 sec\n'
                    '\n'
                    'Average: 1.50 sec +- 0.50 sec '
                        '(min: 1.00 sec, max: 2.00 sec) (3 runs x 1 sample)\n')
        self.assertEqual(stdout, expected)

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
        ref_result = self.create_bench((1.0, 1.5, 2.0),
                                       name='py2',
                                       metadata={'hostname': 'toto',
                                                 'python_version': '2.7'})

        changed_result = self.create_bench((1.5, 2.0, 2.5),
                                           name='py3',
                                           metadata={'hostname': 'toto',
                                                     'python_version': '3.4'})

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
        ref_result = self.create_bench((1.0, 1.5, 2.0), name='py2')
        changed_result = self.create_bench((1.5, 2.0, 2.5), name='py3')

        stdout = self.compare('compare', ref_result, changed_result)

        expected = ('Reference (best): py2\n'
                    '\n'
                    'Average: [py2] 1.50 sec +- 0.50 sec '
                        '-> [py3] 2.00 sec +- 0.50 sec: 1.3x slower\n'
                    'Not significant!')
        self.assertEqual(stdout.rstrip(),
                         expected)

    def test_compare_same(self):
        samples = (1.0, 1.5, 2.0)
        ref_result = self.create_bench(samples, name='b')
        changed_result = self.create_bench(samples, name='a')

        stdout = self.compare('compare', ref_result, changed_result)

        expected = ('Reference (best): a\n'
                    '\n'
                    'Average: [a] 1.50 sec +- 0.50 sec '
                        '-> [b] 1.50 sec +- 0.50 sec: same speed\n'
                    'Not significant!')
        self.assertEqual(stdout.rstrip(),
                         expected)


if __name__ == "__main__":
    unittest.main()
