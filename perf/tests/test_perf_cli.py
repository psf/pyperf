import os
import sys
import textwrap

import perf
from perf import tests
from perf.tests import unittest


TELCO = os.path.join(os.path.dirname(__file__), 'telco.json')


class BaseTestCase(object):
    maxDiff = 100 * 80

    def create_bench(self, samples, metadata=None):
        if metadata is None:
            metadata = {'name': 'bench'}
        elif 'name' not in metadata:
            metadata['name'] = 'bench'
        runs = []
        for sample in samples:
            run = perf.Run([sample],
                           metadata=metadata,
                           collect_metadata=False)
            runs.append(run)
        return perf.Benchmark(runs)

    def run_command(self, *args, **kwargs):
        cmd = [sys.executable, '-m', 'perf']
        cmd.extend(args)

        proc = tests.get_output(cmd, **kwargs)
        self.assertEqual(proc.stderr, '')
        self.assertEqual(proc.returncode, 0)
        return proc.stdout


class TestPerfCLI(BaseTestCase, unittest.TestCase):
    def create_suite(self):
        bench1 = self.create_bench((1.0, 1.5, 2.0),
                                   metadata={'hostname': 'toto',
                                             'python_version': '2.7',
                                             'name': 'py2'})
        bench2 = self.create_bench((1.5, 2.0, 2.5),
                                   metadata={'hostname': 'toto',
                                             'python_version': '3.4',
                                             'name': 'py3'})
        return perf.BenchmarkSuite([bench1, bench2])

    def test_show_common_metadata(self):
        suite = self.create_suite()

        with tests.temporary_file() as tmp_name:
            suite.dump(tmp_name)
            stdout = self.run_command('show', '--metadata', tmp_name)

        expected = textwrap.dedent("""
            Common metadata
            ===============

            - hostname: toto

            py2
            ---

            Metadata:
            - python_version: 2.7

            ERROR: the benchmark is very unstable, the standard deviation is very high (stdev/median: 33%)!
            Try to rerun the benchmark with more runs, samples and/or loops

            Median +- std dev: 1.50 sec +- 0.50 sec

            py3
            ---

            Metadata:
            - python_version: 3.4

            ERROR: the benchmark is very unstable, the standard deviation is very high (stdev/median: 25%)!
            Try to rerun the benchmark with more runs, samples and/or loops

            Median +- std dev: 2.00 sec +- 0.50 sec
        """).strip()
        self.assertEqual(stdout.rstrip(), expected)

    def test_metadata(self):
        suite = self.create_suite()

        with tests.temporary_file() as tmp_name:
            suite.dump(tmp_name)
            stdout = self.run_command('metadata', tmp_name)

        expected = textwrap.dedent("""
            Common metadata
            ===============

            - hostname: toto

            py2
            ---

            Metadata:
            - python_version: 2.7

            py3
            ---

            Metadata:
            - python_version: 3.4
        """).strip()
        self.assertEqual(stdout.rstrip(), expected)

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
                                       metadata={'name': 'telco'})

        changed_result = self.create_bench((1.5, 2.0, 2.5),
                                           metadata={'name': 'telco'})

        stdout = self.compare('compare_to', ref_result, changed_result, '-v')

        expected = ('Median +- std dev: [ref] 1.50 sec +- 0.50 sec '
                    '-> [changed] 2.00 sec +- 0.50 sec: 1.33x slower\n'
                    'Not significant!')
        self.assertEqual(stdout.rstrip(),
                         expected)

    def test_compare_not_significant(self):
        ref_result = self.create_bench((1.0, 1.5, 2.0),
                                       metadata={'name': 'name'})
        changed_result = self.create_bench((1.5, 2.0, 2.5),
                                           metadata={'name': 'name'})

        stdout = self.compare('compare', ref_result, changed_result)

        expected = 'Benchmark hidden because not significant (1): name'
        self.assertEqual(stdout.rstrip(),
                         expected)

    def test_compare(self):
        ref_result = self.create_bench((1.0, 1.5, 2.0),
                                       metadata={'name': 'name'})
        changed_result = self.create_bench((1.5, 2.0, 2.5),
                                           metadata={'name': 'name'})

        stdout = self.compare('compare', ref_result, changed_result, '-v')

        expected = ('Median +- std dev: [ref] 1.50 sec +- 0.50 sec '
                    '-> [changed] 2.00 sec +- 0.50 sec: 1.33x slower\n'
                    'Not significant!')
        self.assertEqual(stdout.rstrip(),
                         expected)

    def test_compare_same(self):
        samples = (1.0, 1.5, 2.0)
        ref_result = self.create_bench(samples, metadata={'name': 'name'})
        changed_result = self.create_bench(samples, metadata={'name': 'name'})

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
            24.2 ms:  3 ###############
            24.2 ms:  1 #####
            24.3 ms:  3 ###############
            24.3 ms:  2 ##########
            24.3 ms:  3 ###############
            24.4 ms: 13 ###################################################################
            24.4 ms:  9 ##############################################
            24.5 ms: 10 ####################################################
            24.5 ms: 11 #########################################################
            24.5 ms:  5 ##########################
            24.6 ms:  9 ##############################################
            24.6 ms:  5 ##########################
            24.6 ms:  9 ##############################################
            24.7 ms:  6 ###############################
            24.7 ms:  5 ##########################
            24.7 ms:  8 #########################################
            24.8 ms:  4 #####################
            24.8 ms:  2 ##########
            24.9 ms:  4 #####################
            24.9 ms:  1 #####
            24.9 ms:  2 ##########
            25.0 ms:  3 ###############
            25.0 ms:  2 ##########
        """)
        self.check_command(expected, 'hist', TELCO, env=env)

    def test_show(self):
        expected = ("""
            Median +- std dev: 24.6 ms +- 0.2 ms
        """)
        self.check_command(expected, 'show', TELCO)

    def test_show_metadata(self):
        expected = ("""
            Metadata:
            - aslr: Full randomization
            - cpu_affinity: 1 (isolated)
            - cpu_config: 1=driver:intel_pstate, intel_pstate:turbo, governor:performance
            - cpu_count: 2
            - cpu_model_name: Intel(R) Core(TM) i7-3520M CPU @ 2.90GHz
            - duration: 400 ms
            - hostname: selma
            - inner_loops: 1
            - loops: 4
            - name: telco
            - perf_version: 0.7
            - platform: Linux-4.6.3-300.fc24.x86_64-x86_64-with-fedora-24-Twenty_Four
            - python_executable: /usr/bin/python3
            - python_implementation: cpython
            - python_version: 3.5.1 (64bit)
            - timer: clock_gettime(CLOCK_MONOTONIC), resolution: 1.00 ns

            24.2 ms:  4 ######################
            24.2 ms:  1 ######
            24.3 ms:  4 ######################
            24.3 ms:  1 ######
            24.4 ms: 12 ###################################################################
            24.4 ms: 11 #############################################################
            24.4 ms: 11 #############################################################
            24.5 ms: 11 #############################################################
            24.5 ms:  6 ##################################
            24.6 ms:  9 ##################################################
            24.6 ms:  7 #######################################
            24.6 ms:  9 ##################################################
            24.7 ms:  4 ######################
            24.7 ms: 10 ########################################################
            24.8 ms:  5 ############################
            24.8 ms:  2 ###########
            24.8 ms:  5 ############################
            24.9 ms:  1 ######
            24.9 ms:  2 ###########
            25.0 ms:  3 #################
            25.0 ms:  2 ###########

            Total duration: 16.0 sec
            Start date: 2016-07-17 22:50:27
            End date: 2016-07-17 22:50:46
            Raw sample minimum: 96.9 ms
            Raw sample maximum: 100 ms

            Number of runs: 40
            Total number of samples: 120
            Number of samples per run: 3
            Number of warmups per run: 1
            Loop iterations per sample: 4

            Minimum: 24.2 ms (-1%)
            Median +- std dev: 24.6 ms +- 0.2 ms
            Mean +- std dev: 24.6 ms +- 0.2 ms
            Maximum: 25.0 ms (+2%)

            Median +- std dev: 24.6 ms +- 0.2 ms
        """)
        self.check_command(expected, 'show',
                           '--hist', '--metadata', '--stats', TELCO)

    def test_stats(self):
        expected = ("""
            Total duration: 16.0 sec
            Start date: 2016-07-17 22:50:27
            End date: 2016-07-17 22:50:46
            Raw sample minimum: 96.9 ms
            Raw sample maximum: 100 ms

            Number of runs: 40
            Total number of samples: 120
            Number of samples per run: 3
            Number of warmups per run: 1
            Loop iterations per sample: 4

            Minimum: 24.2 ms (-1%)
            Median +- std dev: 24.6 ms +- 0.2 ms
            Mean +- std dev: 24.6 ms +- 0.2 ms
            Maximum: 25.0 ms (+2%)
        """)
        self.check_command(expected, 'stats', TELCO)

    def test_dump_raw(self):
        expected = """
            Run 1: raw warmup (1): 98.9 ms (4 loops); raw samples (3): 97.9 ms, 97.8 ms, 98.0 ms
            Run 2: raw warmup (1): 100 ms (4 loops); raw samples (3): 99.0 ms, 98.5 ms, 99.1 ms
            Run 3: raw warmup (1): 100.0 ms (4 loops); raw samples (3): 99.1 ms, 98.3 ms, 98.5 ms
        """
        stdout = self.run_command('dump', '--raw', TELCO)
        self.assertIn(textwrap.dedent(expected).strip(), stdout)

    def test_dump(self):
        expected = """
            Run 1: warmup (1): 24.7 ms; samples (3): 24.5 ms, 24.5 ms, 24.5 ms
            Run 2: warmup (1): 25.0 ms; samples (3): 24.8 ms, 24.6 ms, 24.8 ms
            Run 3: warmup (1): 25.0 ms; samples (3): 24.8 ms, 24.6 ms, 24.6 ms
        """
        stdout = self.run_command('dump', TELCO)
        self.assertIn(textwrap.dedent(expected).strip(), stdout)

    def test_dump_quiet(self):
        expected = """
            Run 1: samples (3): 24.5 ms, 24.5 ms, 24.5 ms
            Run 2: samples (3): 24.8 ms, 24.6 ms, 24.8 ms
            Run 3: samples (3): 24.8 ms, 24.6 ms, 24.6 ms
        """
        stdout = self.run_command('dump', '--quiet', TELCO)
        self.assertIn(textwrap.dedent(expected).strip(), stdout)

    def test_dump_verbose(self):
        expected = """
            Metadata:
              aslr: Full randomization
              cpu_affinity: 1 (isolated)
              cpu_config: 1=driver:intel_pstate, intel_pstate:turbo, governor:performance
              cpu_count: 2
              cpu_model_name: Intel(R) Core(TM) i7-3520M CPU @ 2.90GHz
              duration: 400 ms
              hostname: selma
              inner_loops: 1
              loops: 4
              name: telco
              perf_version: 0.7
              platform: Linux-4.6.3-300.fc24.x86_64-x86_64-with-fedora-24-Twenty_Four
              python_executable: /usr/bin/python3
              python_implementation: cpython
              python_version: 3.5.1 (64bit)
              timer: clock_gettime(CLOCK_MONOTONIC), resolution: 1.00 ns

            Run 1: warmup (1): 24.7 ms; samples (3): 24.5 ms, 24.5 ms, 24.5 ms
              cpu_freq: 1=3588 MHz
              cpu_temp: coretemp:Physical id 0=65 C, coretemp:Core 0=49 C, coretemp:Core 1=65 C
              date: 2016-07-17 22:50:27
              load_avg_1min: 0.12
        """
        stdout = self.run_command('dump', '--verbose', TELCO)
        self.assertIn(textwrap.dedent(expected).strip(), stdout)

    def test_collect_metadata(self):
        stdout = self.run_command('collect_metadata')
        self.assertRegex(stdout,
                         r'^Metadata:\n(- [^:]+: .*\n)+$')

    def test_slowest(self):
        stdout = self.run_command('slowest', TELCO)
        self.assertEqual(stdout.rstrip(),
                         '#1: telco (16.0 sec)')

    def test_check_stable(self):
        stdout = self.run_command('check', TELCO)
        self.assertEqual(stdout.rstrip(),
                         'The benchmark seem to be stable')

    def test_check_unstable(self):
        suite = self.create_suite()

        with tests.temporary_file() as tmp_name:
            suite.dump(tmp_name)
            stdout = self.run_command('check', tmp_name)

        expected = textwrap.dedent("""
            py2
            ---

            ERROR: the benchmark is very unstable, the standard deviation is very high (stdev/median: 33%)!
            Try to rerun the benchmark with more runs, samples and/or loops

            py3
            ---

            ERROR: the benchmark is very unstable, the standard deviation is very high (stdev/median: 25%)!
            Try to rerun the benchmark with more runs, samples and/or loops
        """).strip()
        self.assertEqual(stdout.rstrip(), expected)


class TestConvert(BaseTestCase, unittest.TestCase):
    def test_stdout(self):
        bench = self.create_bench((1.0, 1.5, 2.0))

        with tests.temporary_file() as tmp_name:
            bench.dump(tmp_name)
            stdout = self.run_command('convert', tmp_name, '--stdout')

        self.assertEqual(stdout,
                         tests.benchmark_as_json(bench))

    def test_indent(self):
        bench = self.create_bench((1.0, 1.5, 2.0))

        with tests.temporary_file() as tmp_name:
            bench.dump(tmp_name)
            stdout = self.run_command('convert', tmp_name,
                                      '--indent', '--stdout')

        self.assertEqual(stdout,
                         tests.benchmark_as_json(bench, compact=False))

    def test_convert(self):
        bench = perf.Benchmark.load(TELCO)

        with tests.temporary_directory() as tmpdir:
            filename = os.path.join(tmpdir, 'test.json')
            self.run_command('convert', TELCO, '-o', filename)

            bench2 = perf.Benchmark.load(filename)

        tests.compare_benchmarks(self, bench2, bench)

    def test_filter_benchmarks(self):
        samples = (1.0, 1.5, 2.0)
        benchmarks = []
        for name in ("call_simple", "go", "telco"):
            bench = self.create_bench(samples, metadata={'name': name})
            benchmarks.append(bench)
        suite = perf.BenchmarkSuite(benchmarks)

        with tests.temporary_directory() as tmpdir:
            filename = os.path.join(tmpdir, 'test.json')
            suite.dump(filename)

            stdout = self.run_command('convert', filename,
                                      '--include-benchmark', 'go', '--stdout')
            suite2 = perf.BenchmarkSuite.loads(stdout)

            stdout = self.run_command('convert', filename,
                                      '--exclude-benchmark', 'go', '--stdout')
            suite3 = perf.BenchmarkSuite.loads(stdout)

        self.assertEqual(suite2.get_benchmark_names(),
                         ['go'])

        self.assertEqual(suite3.get_benchmark_names(),
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
        samples = [1.0, 2.0, 3.0]
        raw_samples = [5.0] + samples
        run = perf.Run(samples, warmups=[(1, 5.0)],
                       metadata={'name': 'bench'})
        bench = perf.Benchmark([run])

        self.assertEqual(bench._get_nwarmup(), 1)
        self.assertEqual(bench._get_raw_samples(warmups=True),
                         raw_samples)

        with tests.temporary_directory() as tmpdir:
            filename = os.path.join(tmpdir, 'test.json')
            bench.dump(filename)

            stdout = self.run_command('convert', filename,
                                      '--remove-warmups', '--stdout')
            bench2 = perf.Benchmark.loads(stdout)

        self.assertEqual(bench2._get_nwarmup(), 0)
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
