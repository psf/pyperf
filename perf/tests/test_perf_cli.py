import os
import subprocess
import sys
import tempfile
import textwrap
import unittest

import perf


TELCO = os.path.join(os.path.dirname(__file__), 'telco.json')


class TestPerfCLI(unittest.TestCase):
    def create_bench(self, samples, **kw):
        bench = perf.Benchmark(warmups=0, **kw)
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
        expected = ('Run 1/3: raw samples (1): 1.00 sec\n'
                    'Run 2/3: raw samples (1): 1.50 sec\n'
                    'Run 3/3: raw samples (1): 2.00 sec\n'
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

    def check_command(self, expected, *args, **kwargs):
        cmd = [sys.executable, '-m', 'perf']
        cmd.extend(args)
        proc = subprocess.Popen(cmd,
                                stdout=subprocess.PIPE,
                                universal_newlines=True,
                                **kwargs)
        stdout = proc.communicate()[0]

        self.assertEqual(stdout.rstrip(), textwrap.dedent(expected).strip())

    def test_hist(self):
        # Force terminal size on Python 3 for shutil.get_terminal_size()
        env = dict(os.environ)
        env['COLUMNS'] = '80'
        env['LINES'] = '25'

        expected = ("""
            26.3 ms:  1 ##
            26.4 ms:  0 |
            26.4 ms:  3 ######
            26.5 ms:  1 ##
            26.5 ms:  1 ##
            26.6 ms:  8 ################
            26.6 ms:  6 ############
            26.6 ms: 10 ####################
            26.7 ms: 17 ##################################
            26.7 ms: 17 ##################################
            26.8 ms: 24 ###############################################
            26.8 ms: 34 ###################################################################
            26.9 ms: 28 #######################################################
            26.9 ms: 14 ############################
            26.9 ms: 19 #####################################
            27.0 ms: 18 ###################################
            27.0 ms: 10 ####################
            27.1 ms: 12 ########################
            27.1 ms:  9 ##################
            27.2 ms: 12 ########################
            27.2 ms:  4 ########
            27.2 ms:  1 ##
            27.3 ms:  1 ##
        """)
        self.check_command(expected, 'hist', TELCO, env=env)

    def test_stats(self):
        expected = ("""
            Number of samples: 250
            Minimum 26.4 ms
            Maximum 27.3 ms

            Mean + std dev: 26.9 ms +- 0.2 ms
            Median +- std dev: 26.9 ms +- 0.2 ms
            Median +- MAD: 26.9 ms +- 0.1 ms

            Skewness: 0.04
        """)
        self.check_command(expected, 'stats', TELCO)


if __name__ == "__main__":
    unittest.main()
