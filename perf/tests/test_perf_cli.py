import os
import subprocess
import sys
import tempfile
import textwrap

import perf
from perf import tests
from perf.tests.test_metadata import check_all_metadata
from perf.tests import unittest


TELCO = os.path.join(os.path.dirname(__file__), 'telco.json')


class BaseTestCase(object):
    maxDiff = 100 * 80

    def create_bench(self, samples, **kw):
        name = kw.pop('name', 'bench')
        bench = perf.Benchmark(name=name, **kw)
        for sample in samples:
            bench.add_run(perf.Run(0, [sample]))
        return bench

    def run_command(self, *args, **kwargs):
        cmd = [sys.executable, '-m', 'perf']
        cmd.extend(args)
        proc = subprocess.Popen(cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                universal_newlines=True,
                                **kwargs)
        stdout, stderr = proc.communicate()

        self.assertEqual(stderr, '')
        self.assertEqual(proc.returncode, 0)
        return stdout


class TestPerfCLI(BaseTestCase, unittest.TestCase):
    def test_show_common_metadata(self):
        bench1 = self.create_bench((1.0, 1.5, 2.0),
                                       name='py2',
                                       metadata={'hostname': 'toto',
                                                 'python_version': '2.7'})
        bench2 = self.create_bench((1.5, 2.0, 2.5),
                                           name='py3',
                                           metadata={'hostname': 'toto',
                                                     'python_version': '3.4'})
        suite = perf.BenchmarkSuite()
        suite.add_benchmark(bench1)
        suite.add_benchmark(bench2)

        with tempfile.NamedTemporaryFile(mode="w+") as tmp:
            suite.dump(tmp.name)
            stdout = self.run_command('show', '--metadata', tmp.name)

        expected = textwrap.dedent("""
            Common metadata:
            - hostname: toto

            py2
            ===

            Metadata:
            - python_version: 2.7

            ERROR: the benchmark is very unstable, the standard deviation is very high (stdev/median: 33%)!
            Try to rerun the benchmark with more runs, samples and/or loops

            Median +- std dev: 1.50 sec +- 0.50 sec

            py3
            ===

            Metadata:
            - python_version: 3.4

            ERROR: the benchmark is very unstable, the standard deviation is very high (stdev/median: 25%)!
            Try to rerun the benchmark with more runs, samples and/or loops

            Median +- std dev: 2.00 sec +- 0.50 sec
        """).strip()
        self.assertEqual(stdout.rstrip(),
                         expected)

    def compare(self, action, ref_result, changed_result, *args):
        with tests.temporary_directory() as tmpdir:
            ref_name = os.path.join(tmpdir, 'ref.json')
            changed_name = os.path.join(tmpdir, 'changed.json')

            ref_result.dump(ref_name)
            changed_result.dump(changed_name)

            stdout = self.run_command(action, ref_name, changed_name, *args)

        return stdout

    def test_compare_to(self):
        ref_result = self.create_bench((1.0, 1.5, 2.0),
                                       name='telco')

        changed_result = self.create_bench((1.5, 2.0, 2.5),
                                           name='telco')

        stdout = self.compare('compare_to', ref_result, changed_result, '-v')

        expected = ('Median +- std dev: [ref] 1.50 sec +- 0.50 sec '
                        '-> [changed] 2.00 sec +- 0.50 sec: 1.3x slower\n'
                    'Not significant!')
        self.assertEqual(stdout.rstrip(),
                         expected)

    def test_compare_not_significant(self):
        ref_result = self.create_bench((1.0, 1.5, 2.0), name='name')
        changed_result = self.create_bench((1.5, 2.0, 2.5), name='name')

        stdout = self.compare('compare', ref_result, changed_result)

        expected = 'Benchmark hidden because not significant (1): name'
        self.assertEqual(stdout.rstrip(),
                         expected)

    def test_compare(self):
        ref_result = self.create_bench((1.0, 1.5, 2.0), name='name')
        changed_result = self.create_bench((1.5, 2.0, 2.5), name='name')

        stdout = self.compare('compare', ref_result, changed_result, '-v')

        expected = ('Median +- std dev: [ref] 1.50 sec +- 0.50 sec '
                        '-> [changed] 2.00 sec +- 0.50 sec: 1.3x slower\n'
                    'Not significant!')
        self.assertEqual(stdout.rstrip(),
                         expected)

    def test_compare_same(self):
        samples = (1.0, 1.5, 2.0)
        ref_result = self.create_bench(samples, name='name')
        changed_result = self.create_bench(samples, name='name')

        stdout = self.compare('compare', ref_result, changed_result, '-v')

        expected = ('Median +- std dev: [changed] 1.50 sec +- 0.50 sec '
                        '-> [ref] 1.50 sec +- 0.50 sec: no change\n'
                    'Not significant!')
        self.assertEqual(stdout.rstrip(),
                         expected)

    def check_command(self, expected, *args, **kwargs):
        stdout = self.run_command(*args, **kwargs)
        self.assertEqual(stdout.rstrip(), textwrap.dedent(expected).strip())

    def test_hist(self):
        # Force terminal size on Python 3 for shutil.get_terminal_size()
        env = dict(os.environ)
        env['COLUMNS'] = '80'
        env['LINES'] = '25'

        expected = ("""
            24.2 ms:  1 ###
            24.3 ms:  1 ###
            24.3 ms:  3 ##########
            24.4 ms:  3 ##########
            24.4 ms:  1 ###
            24.4 ms:  8 ###########################
            24.5 ms: 10 ##################################
            24.5 ms:  9 ##############################
            24.6 ms: 15 ##################################################
            24.6 ms: 12 ########################################
            24.6 ms: 12 ########################################
            24.7 ms:  6 ####################
            24.7 ms: 10 ##################################
            24.8 ms: 20 ###################################################################
            24.8 ms: 12 ########################################
            24.8 ms: 10 ##################################
            24.9 ms:  6 ####################
            24.9 ms:  4 #############
            25.0 ms:  2 #######
            25.0 ms:  1 ###
            25.0 ms:  1 ###
            25.1 ms:  0 |
            25.1 ms:  3 ##########
        """)
        self.check_command(expected, 'hist', TELCO, env=env)

    def test_show(self):
        expected = ("""
            Median +- std dev: 24.7 ms +- 0.2 ms
        """)
        self.check_command(expected, 'show', TELCO)

    def test_show_metadata(self):
        expected = ("""
            Metadata:
            - aslr: enabled
            - cpu_affinity: 2-3 (isolated)
            - cpu_count: 4
            - cpu_model_name: Intel(R) Core(TM) i7-3520M CPU @ 2.90GHz
            - description: Test the performance of the Telco decimal benchmark
            - duration: 23.8 sec
            - hostname: selma
            - name: telco
            - perf_version: 0.7
            - platform: Linux-4.6.3-300.fc24.x86_64-x86_64-with-fedora-24-Twenty_Four
            - python_executable: /usr/bin/python3
            - python_implementation: cpython
            - python_version: 3.5.1 (64bit)
            - timer: clock_gettime(CLOCK_MONOTONIC), resolution: 1.00 ns

            24.3 ms:  2 ######
            24.3 ms:  0 |
            24.3 ms:  4 #############
            24.4 ms:  3 ##########
            24.4 ms:  4 #############
            24.5 ms: 12 ######################################
            24.5 ms:  9 #############################
            24.6 ms: 16 ###################################################
            24.6 ms: 13 #########################################
            24.6 ms: 12 ######################################
            24.7 ms:  7 ######################
            24.7 ms: 14 #############################################
            24.8 ms: 21 ###################################################################
            24.8 ms: 11 ###################################
            24.9 ms:  7 ######################
            24.9 ms:  6 ###################
            24.9 ms:  3 ##########
            25.0 ms:  2 ######
            25.0 ms:  1 ###
            25.1 ms:  0 |
            25.1 ms:  3 ##########

            Raw sample minimum: 97.2 ms
            Raw sample maximum: 101 ms

            Number of runs: 50
            Total number of samples: 150
            Number of samples per run: 3
            Number of warmups per run: 1
            Loop iterations per sample: 4

            Minimum: 24.3 ms (-2%)
            Median +- std dev: 24.7 ms +- 0.2 ms
            Mean +- std dev: 24.7 ms +- 0.2 ms
            Maximum: 25.2 ms (+2%)

            Median +- std dev: 24.7 ms +- 0.2 ms
        """)
        self.check_command(expected, 'show',
                           '--hist', '--metadata', '--stats', TELCO)

    def test_stats(self):
        expected = ("""
            Raw sample minimum: 97.2 ms
            Raw sample maximum: 101 ms

            Number of runs: 50
            Total number of samples: 150
            Number of samples per run: 3
            Number of warmups per run: 1
            Loop iterations per sample: 4

            Minimum: 24.3 ms (-2%)
            Median +- std dev: 24.7 ms +- 0.2 ms
            Mean +- std dev: 24.7 ms +- 0.2 ms
            Maximum: 25.2 ms (+2%)
        """)
        self.check_command(expected, 'stats', TELCO)

    def test_dump_raw(self):
        expected = """
            Run 1: raw warmup (1): 99.7 ms; raw samples (3): 98.3 ms, 98.5 ms, 98.5 ms
            Run 2: raw warmup (1): 100.0 ms; raw samples (3): 99.4 ms, 99.0 ms, 98.6 ms
            Run 3: raw warmup (1): 98.3 ms; raw samples (3): 98.3 ms, 98.2 ms, 97.4 ms
        """
        stdout = self.run_command('dump', '--raw', TELCO)
        self.assertIn(textwrap.dedent(expected).strip(), stdout)

    def test_dump(self):
        expected = """
            Run 1: warmup (1): 24.9 ms; samples (3): 24.6 ms, 24.6 ms, 24.6 ms
            Run 2: warmup (1): 25.0 ms; samples (3): 24.8 ms, 24.8 ms, 24.6 ms
            Run 3: warmup (1): 24.6 ms; samples (3): 24.6 ms, 24.5 ms, 24.3 ms
        """
        stdout = self.run_command('dump', TELCO)
        self.assertIn(textwrap.dedent(expected).strip(), stdout)

    def test_dump_quiet(self):
        expected = """
            Run 1: samples (3): 24.6 ms, 24.6 ms, 24.6 ms
            Run 2: samples (3): 24.8 ms, 24.8 ms, 24.6 ms
            Run 3: samples (3): 24.6 ms, 24.5 ms, 24.3 ms
        """
        stdout = self.run_command('dump', '--quiet', TELCO)
        self.assertIn(textwrap.dedent(expected).strip(), stdout)

    def test_dump_verbose(self):
        expected = """
            Run 1: warmup (1): 24.9 ms; samples (3): 24.6 ms, 24.6 ms, 24.6 ms
              loops: 4
              inner_loops: 1
              date: 2016-07-11T15:39:37
            Run 2: warmup (1): 25.0 ms; samples (3): 24.8 ms, 24.8 ms, 24.6 ms
              loops: 4
              inner_loops: 1
              date: 2016-07-11T15:39:37
            Run 3: warmup (1): 24.6 ms; samples (3): 24.6 ms, 24.5 ms, 24.3 ms
              loops: 4
              inner_loops: 1
              date: 2016-07-11T15:39:37
        """
        stdout = self.run_command('dump', '--verbose', TELCO)
        self.assertIn(textwrap.dedent(expected).strip(), stdout)

    def test_metadata(self):
        stdout = self.run_command('metadata')
        lines = stdout.splitlines()

        self.assertEqual(lines[0], 'Metadata:')
        metadata = {}
        for line in lines[1:]:
            self.assertTrue(line.startswith('- '), repr(line))
            key, value = line[2:].split(': ', 1)
            metadata[key] = value

        check_all_metadata(self, metadata)


class TestConvert(BaseTestCase, unittest.TestCase):
    def test_stdout(self):
        bench = self.create_bench((1.0, 1.5, 2.0))

        with tempfile.NamedTemporaryFile(mode="w+") as tmp:
            bench.dump(tmp.name)
            stdout = self.run_command('convert', tmp.name, '--stdout')

        self.assertEqual(stdout,
                         tests.benchmark_as_json(bench))

    def test_indent(self):
        bench = self.create_bench((1.0, 1.5, 2.0))

        with tempfile.NamedTemporaryFile(mode="w+") as tmp:
            bench.dump(tmp.name)
            stdout = self.run_command('convert', tmp.name,
                                      '--indent', '--stdout')

        self.assertEqual(stdout,
                         tests.benchmark_as_json(bench, compact=False))

    def test_indent(self):
        bench = perf.Benchmark.load(TELCO)

        with tests.temporary_directory() as tmpdir:
            filename = os.path.join(tmpdir, 'test.json')
            self.run_command('convert', TELCO, '-o', filename)

            bench2 = perf.Benchmark.load(filename)

        tests.compare_benchmarks(self, bench2, bench)

    def test_filter_benchmarks(self):
        samples = (1.0, 1.5, 2.0)
        suite = perf.BenchmarkSuite()
        for name in ("call_simple", "go", "telco"):
            suite.add_benchmark(self.create_bench(samples, name=name))

        with tests.temporary_directory() as tmpdir:
            filename = os.path.join(tmpdir, 'test.json')
            suite.dump(filename)

            stdout = self.run_command('convert', filename,
                                      '--include-benchmark', 'go', '--stdout')
            suite2 = perf.BenchmarkSuite.loads(stdout)

            stdout = self.run_command('convert', filename,
                                      '--exclude-benchmark', 'go', '--stdout')
            suite3 = perf.BenchmarkSuite.loads(stdout)

        def get_benchmark_names(suite):
            return [bench.name
                    for bench in suite.get_benchmarks()]

        self.assertEqual(get_benchmark_names(suite2),
                         ['go'])

        self.assertEqual(get_benchmark_names(suite3),
                         ['call_simple', 'telco'])

    def test_remove_outliers(self):
        samples = (100.0,) * 100 + (99.0, 101.0)
        outliers = (90.0, 110.0)
        bench = self.create_bench(samples + outliers)

        with tests.temporary_directory() as tmpdir:
            filename = os.path.join(tmpdir, 'test.json')
            bench.dump(filename)

            stdout = self.run_command('convert', filename,
                                      '--remove-outliers', '--stdout')
            bench2 = perf.Benchmark.loads(stdout)

        self.assertEqual(bench2.get_samples(),
                         samples)

    def test_remove_warmups(self):
        raw_samples = [5.0, 1.0, 2.0, 3.0]
        bench = perf.Benchmark('bench')
        bench.add_run(perf.Run(1, raw_samples))

        self.assertEqual(bench._get_raw_samples(warmups=True),
                         raw_samples)

        with tests.temporary_directory() as tmpdir:
            filename = os.path.join(tmpdir, 'test.json')
            bench.dump(filename)

            stdout = self.run_command('convert', filename,
                                      '--remove-warmups', '--stdout')
            bench2 = perf.Benchmark.loads(stdout)

        self.assertEqual(bench2._get_raw_samples(warmups=True),
                         raw_samples[1:])

    def test_filter_runs(self):
        runs = (1.0, 2.0, 3.0, 4.0, 5.0)
        bench = self.create_bench(runs)

        self.assertEqual(bench.get_samples(), runs)

        with tests.temporary_directory() as tmpdir:
            filename = os.path.join(tmpdir, 'test.json')
            bench.dump(filename)

            stdout = self.run_command('convert', filename,
                                      '--include-runs', '4', '--stdout')
            bench2 = perf.Benchmark.loads(stdout)

            stdout = self.run_command('convert', filename,
                                      '--include-runs', '1-3,5', '--stdout')
            bench3 = perf.Benchmark.loads(stdout)

            stdout = self.run_command('convert', filename,
                                      '--exclude-runs', '2,4', '--stdout')
            bench4 = perf.Benchmark.loads(stdout)

        self.assertEqual(bench2.get_samples(), (4.0,))
        self.assertEqual(bench3.get_samples(), (1.0, 2.0, 3.0, 5.0))
        self.assertEqual(bench4.get_samples(), (1.0, 3.0, 5.0))


if __name__ == "__main__":
    unittest.main()
