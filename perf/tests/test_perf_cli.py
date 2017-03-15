import os
import sys
import textwrap

import perf
from perf import tests
from perf.tests import unittest


TELCO = os.path.join(os.path.dirname(__file__), 'telco.json')


class BaseTestCase(object):
    maxDiff = 100 * 80

    def create_bench(self, values, metadata=None):
        if metadata is None:
            metadata = {'name': 'bench'}
        elif 'name' not in metadata:
            metadata['name'] = 'bench'
        runs = []
        for value in values:
            run = perf.Run([value],
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
            stdout = self.run_command('show', '-q', '--metadata', tmp_name)

        expected = textwrap.dedent("""
            Common metadata
            ===============

            - hostname: toto

            py2
            ---

            Metadata:
            - python_version: 2.7

            Mean +- std dev: 1.50 sec +- 0.50 sec

            py3
            ---

            Metadata:
            - python_version: 3.4

            Mean +- std dev: 2.00 sec +- 0.50 sec
        """).strip()
        self.assertEqual(stdout.rstrip(), expected)

    def test_metadata(self):
        suite = self.create_suite()

        with tests.temporary_file() as tmp_name:
            suite.dump(tmp_name)
            stdout = self.run_command('metadata', '-q', tmp_name)

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

        expected = ('Mean +- std dev: [ref] 1.50 sec +- 0.50 sec '
                    '-> [changed] 2.00 sec +- 0.50 sec: 1.33x slower (+33%)\n'
                    'Not significant!')
        self.assertEqual(stdout.rstrip(),
                         expected)

    def test_compare_to_table(self):
        ref_result = self.create_bench((1.0,),
                                       metadata={'name': 'telco'})

        changed_result = self.create_bench((2.0,),
                                           metadata={'name': 'telco'})

        stdout = self.compare('compare_to', ref_result, changed_result, '--table')

        expected = textwrap.dedent('''
            +-----------+----------+--------------------------------+
            | Benchmark | ref      | changed                        |
            +===========+==========+================================+
            | telco     | 1.00 sec | 2.00 sec: 2.00x slower (+100%) |
            +-----------+----------+--------------------------------+
        ''').strip()

        self.assertEqual(stdout.rstrip(),
                         expected)

    def test_compare_to_table_not_significant(self):
        ref_result = self.create_bench((1.0, 1.5, 2.0),
                                       metadata={'name': 'telco'})

        changed_result = self.create_bench((1.5, 2.0, 2.5),
                                           metadata={'name': 'telco'})

        stdout = self.compare('compare_to', ref_result, changed_result, '--table')
        expected = "Not significant (1): telco"
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

        expected = ('Mean +- std dev: [ref] 1.50 sec +- 0.50 sec '
                    '-> [changed] 2.00 sec +- 0.50 sec: 1.33x slower (+33%)\n'
                    'Not significant!')
        self.assertEqual(stdout.rstrip(),
                         expected)

    def test_compare_same(self):
        values = (1.0, 1.5, 2.0)
        ref_result = self.create_bench(values, metadata={'name': 'name'})
        changed_result = self.create_bench(values, metadata={'name': 'name'})

        stdout = self.compare('compare', ref_result, changed_result, '-v')

        expected = ('Mean +- std dev: [changed] 1.50 sec +- 0.50 sec '
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
            22.1 ms:  1 #####
            22.1 ms:  0 |
            22.2 ms:  1 #####
            22.2 ms:  2 ##########
            22.2 ms:  3 ##############
            22.3 ms:  6 #############################
            22.3 ms:  4 ###################
            22.3 ms:  7 ##################################
            22.4 ms:  8 ######################################
            22.4 ms: 14 ###################################################################
            22.4 ms: 11 #####################################################
            22.5 ms:  5 ########################
            22.5 ms: 10 ################################################
            22.6 ms:  8 ######################################
            22.6 ms:  4 ###################
            22.6 ms:  7 ##################################
            22.7 ms:  3 ##############
            22.7 ms:  4 ###################
            22.7 ms:  4 ###################
            22.8 ms:  7 ##################################
            22.8 ms:  3 ##############
            22.9 ms:  4 ###################
            22.9 ms:  4 ###################
        """)
        self.check_command(expected, 'hist', TELCO, env=env)

    def test_show(self):
        expected = ("""
            Mean +- std dev: 22.5 ms +- 0.2 ms
        """)
        self.check_command(expected, 'show', TELCO)

    def test_stats(self):
        expected = ("""
            Total duration: 29.2 sec
            Start date: 2016-10-21 03:14:19
            End date: 2016-10-21 03:14:53
            Raw value minimum: 177 ms
            Raw value maximum: 183 ms

            Number of runs: 41
            Total number of values: 120
            Number of values per run: 3
            Number of warmups per run: 1
            Loop iterations per value: 8

            Minimum: 22.1 ms (-2% of the mean)
            Median +- MAD: 22.5 ms +- 0.1 ms
            Mean +- std dev: 22.5 ms +- 0.2 ms
            Maximum: 22.9 ms (+2% of the mean)
        """)
        self.check_command(expected, 'stats', TELCO)

    def test_dump_raw(self):
        expected = """
            Run 1: calibrate
            - 1 loop: 23.1 ms
            - 2 loops: 45.0 ms
            - 4 loops: 89.9 ms
            - 8 loops: 179 ms
            Run 2: raw warmup (1): 180 ms (8 loops); raw values (3): 182 ms, 180 ms, 181 ms
            Run 3: raw warmup (1): 179 ms (8 loops); raw values (3): 178 ms, 179 ms, 179 ms
        """
        stdout = self.run_command('dump', '--raw', TELCO)
        self.assertIn(textwrap.dedent(expected).strip(), stdout)

    def test_dump(self):
        expected = """
            Run 1: calibrate
            - 1 loop: 23.1 ms
            - 2 loops: 45.0 ms
            - 4 loops: 89.9 ms
            - 8 loops: 179 ms
            Run 2: warmup (1): 22.5 ms; values (3): 22.8 ms, 22.5 ms, 22.6 ms
            Run 3: warmup (1): 22.4 ms; values (3): 22.3 ms, 22.4 ms, 22.3 ms
        """
        stdout = self.run_command('dump', TELCO)
        self.assertIn(textwrap.dedent(expected).strip(), stdout)

    def test_dump_quiet(self):
        expected = """
            Run 2: values (3): 22.8 ms, 22.5 ms, 22.6 ms
            Run 3: values (3): 22.3 ms, 22.4 ms, 22.3 ms
        """
        stdout = self.run_command('dump', '--quiet', TELCO)
        self.assertIn(textwrap.dedent(expected).strip(), stdout)

    def test_dump_verbose(self):
        expected = """
            Metadata:
              aslr: Full randomization
              boot_time: 2016-10-19 01:10:08
              cpu_affinity: 2-3
              cpu_config: 2-3=driver:intel_pstate, intel_pstate:turbo, governor:performance, isolated; idle:intel_idle
              cpu_count: 4
              cpu_model_name: Intel(R) Core(TM) i7-3520M CPU @ 2.90GHz
              description: Telco decimal benchmark
              hostname: selma
              loops: 8
              name: telco
              perf_version: 0.8.2
              performance_version: 0.3.3
              platform: Linux-4.7.4-200.fc24.x86_64-x86_64-with-fedora-24-Twenty_Four
              python_cflags: -Wno-unused-result -Wsign-compare -Wunreachable-code -DDYNAMIC_ANNOTATIONS_ENABLED=1 -DNDEBUG -O2 -g -pipe -Wall -Werror=format-security -Wp,-D_FORTIFY_SOURCE=2 -fexceptions -fstack-protector-strong --param=ssp-buffer-size=4 -grecord-gcc-switches -specs=/usr/lib/rpm/redhat/redhat-hardened-cc1 -m64 -mtune=generic -D_GNU_SOURCE -fPIC -fwrapv
              python_executable: /home/haypo/prog/python/performance/venv/cpython3.5-68b776ee7e79/bin/python
              python_implementation: cpython
              python_version: 3.5.1 (64-bit)
              timer: clock_gettime(CLOCK_MONOTONIC), resolution: 1.00 ns

            Run 1: calibrate
            - 1 loop: 23.1 ms
            - 2 loops: 45.0 ms
            - 4 loops: 89.9 ms
            - 8 loops: 179 ms
            Run 2: warmup (1): 22.5 ms; values (3): 22.8 ms, 22.5 ms, 22.6 ms
              cpu_freq: 2=3596 MHz, 3=2998 MHz
              cpu_temp: coretemp:Physical id 0=67 C, coretemp:Core 0=51 C, coretemp:Core 1=67 C
              date: 2016-10-21 03:14:20.496710
              duration: 723 ms
              load_avg_1min: 0.29
              mem_max_rss: 13.5 MB
              runnable_threads: 1
              uptime: 2 day 2 hour 4 min
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
                         '#1: telco (29.2 sec)')

    def test_check_stable(self):
        stdout = self.run_command('check', TELCO)
        self.assertEqual(stdout.rstrip(),
                         'The benchmark seems to be stable')

    def test_check_unstable(self):
        suite = self.create_suite()

        with tests.temporary_file() as tmp_name:
            suite.dump(tmp_name)
            stdout = self.run_command('check', tmp_name)

        expected = textwrap.dedent("""
            py2
            ---

            WARNING: the benchmark result may be unstable
            * the standard deviation (500 ms) is 33% of the mean (1.50 sec)
            * the minimum (1.00 sec) is 33% smaller than the mean (1.50 sec)
            * the maximum (2.00 sec) is 33% greater than the mean (1.50 sec)

            Try to rerun the benchmark with more runs, values and/or loops.
            Run '{0} -m perf system tune' command to reduce the system jitter.
            Use perf stats, perf dump and perf hist to analyze results.
            Use --quiet option to hide these warnings.

            py3
            ---

            WARNING: the benchmark result may be unstable
            * the standard deviation (500 ms) is 25% of the mean (2.00 sec)
            * the minimum (1.50 sec) is 25% smaller than the mean (2.00 sec)
            * the maximum (2.50 sec) is 25% greater than the mean (2.00 sec)

            Try to rerun the benchmark with more runs, values and/or loops.
            Run '{0} -m perf system tune' command to reduce the system jitter.
            Use perf stats, perf dump and perf hist to analyze results.
            Use --quiet option to hide these warnings.
        """).strip()
        expected = expected.format(os.path.basename(sys.executable))
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
        values = (1.0, 1.5, 2.0)
        benchmarks = []
        for name in ("call_simple", "go", "telco"):
            bench = self.create_bench(values, metadata={'name': name})
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

    def test_remove_warmups(self):
        values = [1.0, 2.0, 3.0]
        raw_values = [5.0] + values
        run = perf.Run(values, warmups=[(1, 5.0)],
                       metadata={'name': 'bench'})
        bench = perf.Benchmark([run])

        self.assertEqual(bench._get_nwarmup(), 1)
        self.assertEqual(bench._get_raw_values(warmups=True),
                         raw_values)

        with tests.temporary_directory() as tmpdir:
            filename = os.path.join(tmpdir, 'test.json')
            bench.dump(filename)

            stdout = self.run_command('convert', filename,
                                      '--remove-warmups', '--stdout')
            bench2 = perf.Benchmark.loads(stdout)

        self.assertEqual(bench2._get_nwarmup(), 0)
        self.assertEqual(bench2._get_raw_values(warmups=True),
                         raw_values[1:])

    def test_filter_runs(self):
        runs = (1.0, 2.0, 3.0, 4.0, 5.0)
        bench = self.create_bench(runs)

        self.assertEqual(bench.get_values(), runs)

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

        self.assertEqual(bench2.get_values(), (4.0,))
        self.assertEqual(bench3.get_values(), (1.0, 2.0, 3.0, 5.0))
        self.assertEqual(bench4.get_values(), (1.0, 3.0, 5.0))


if __name__ == "__main__":
    unittest.main()
