import os
import sys
import textwrap
import unittest

import pyperf
from pyperf import tests


TESTDIR = os.path.dirname(__file__)
TELCO = os.path.join(TESTDIR, 'telco.json')


class BaseTestCase(object):
    maxDiff = 100 * 80

    def create_bench(self, values, metadata=None):
        if metadata is None:
            metadata = {'name': 'bench'}
        elif 'name' not in metadata:
            metadata['name'] = 'bench'
        runs = []
        for value in values:
            run = pyperf.Run([value],
                             metadata=metadata,
                             collect_metadata=False)
            runs.append(run)
        return pyperf.Benchmark(runs)

    def run_command(self, *args, **kwargs):
        cmd = [sys.executable, '-m', 'pyperf']
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
                                             'name': 'py36'})
        bench2 = self.create_bench((1.5, 2.0, 2.5),
                                   metadata={'hostname': 'toto',
                                             'python_version': '3.4',
                                             'name': 'py38'})
        return pyperf.BenchmarkSuite([bench1, bench2])

    def test_show_common_metadata(self):
        suite = self.create_suite()

        with tests.temporary_file() as tmp_name:
            suite.dump(tmp_name)
            stdout = self.run_command('show', '-q', '--metadata', tmp_name)

        expected = textwrap.dedent("""
            Common metadata
            ===============

            - hostname: toto

            py36
            ----

            Metadata:
            - python_version: 2.7

            Mean +- std dev: 1.50 sec +- 0.50 sec

            py38
            ----

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

            py36
            ----

            Metadata:
            - python_version: 2.7

            py38
            ----

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
                    '-> [changed] 2.00 sec +- 0.50 sec: 1.33x slower\n'
                    'Not significant!')
        self.assertEqual(stdout.rstrip(),
                         expected)

    def test_compare_to_rest_table(self):
        ref_result = self.create_bench((1.0,),
                                       metadata={'name': 'telco'})

        changed_result = self.create_bench((2.0,),
                                           metadata={'name': 'telco'})

        stdout = self.compare('compare_to', ref_result, changed_result, '--table')

        expected = textwrap.dedent('''
            +-----------+----------+------------------------+
            | Benchmark | ref      | changed                |
            +===========+==========+========================+
            | telco     | 1.00 sec | 2.00 sec: 2.00x slower |
            +-----------+----------+------------------------+
        ''').strip()

        self.assertEqual(stdout.rstrip(),
                         expected)


    def test_compare_to_md_table(self):
        ref_result = self.create_bench((1.0,),
                                       metadata={'name': 'telco'})

        changed_result = self.create_bench((2.0,),
                                           metadata={'name': 'telco'})

        stdout = self.compare('compare_to', ref_result, changed_result, '--table',
                              '--table-format', 'md')

        expected = textwrap.dedent('''
            | Benchmark | ref      | changed                |
            |-----------|:--------:|:----------------------:|
            | telco     | 1.00 sec | 2.00 sec: 2.00x slower |
        ''').strip()

        self.assertEqual(stdout.rstrip(),
                         expected)

    def test_compare_to_table_not_significant(self):
        ref_result = self.create_bench((1.0, 1.5, 2.0),
                                       metadata={'name': 'telco'})

        changed_result = self.create_bench((1.5, 2.0, 2.5),
                                           metadata={'name': 'telco'})

        stdout = self.compare('compare_to', ref_result, changed_result, '--table')
        expected = "Benchmark hidden because not significant (1): telco"
        self.assertEqual(stdout.rstrip(),
                         expected)

    def test_compare_to_not_significant(self):
        ref_result = self.create_bench((1.0, 1.5, 2.0),
                                       metadata={'name': 'name'})
        changed_result = self.create_bench((1.5, 2.0, 2.5),
                                           metadata={'name': 'name'})

        stdout = self.compare('compare_to', ref_result, changed_result)

        expected = 'Benchmark hidden because not significant (1): name'
        self.assertEqual(stdout.rstrip(),
                         expected)

    def test_compare_to_not_significant_verbose(self):
        ref_result = self.create_bench((1.0, 1.5, 2.0),
                                       metadata={'name': 'name'})
        changed_result = self.create_bench((1.5, 2.0, 2.5),
                                           metadata={'name': 'name'})

        stdout = self.compare('compare_to', ref_result, changed_result, '-v')

        expected = ('Mean +- std dev: [ref] 1.50 sec +- 0.50 sec '
                    '-> [changed] 2.00 sec +- 0.50 sec: 1.33x slower\n'
                    'Not significant!')
        self.assertEqual(stdout.rstrip(),
                         expected)

    def test_compare_to_same(self):
        values = (1.0, 1.5, 2.0)
        ref_result = self.create_bench(values, metadata={'name': 'name'})
        changed_result = self.create_bench(values, metadata={'name': 'name'})

        stdout = self.compare('compare_to', ref_result, changed_result, '-v')

        expected = ('Mean +- std dev: [ref] 1.50 sec +- 0.50 sec '
                    '-> [changed] 1.50 sec +- 0.50 sec: no change\n'
                    'Not significant!')
        self.assertEqual(stdout.rstrip(),
                         expected)

    def check_command(self, expected, *args, **kwargs):
        stdout = self.run_command(*args, **kwargs)
        self.assertEqual(stdout, textwrap.dedent(expected).lstrip())

    def test_compare_to_cli(self):
        py36 = os.path.join(TESTDIR, 'mult_list_py36.json')
        py37 = os.path.join(TESTDIR, 'mult_list_py37.json')
        py38 = os.path.join(TESTDIR, 'mult_list_py38.json')

        # 2 files
        expected = """
            [1]*1000: Mean +- std dev: [mult_list_py36] 2.13 us +- 0.06 us -> [mult_list_py37] 2.09 us +- 0.04 us: 1.02x faster
            [1,2]*1000: Mean +- std dev: [mult_list_py36] 3.70 us +- 0.05 us -> [mult_list_py37] 5.28 us +- 0.09 us: 1.42x slower
            [1,2,3]*1000: Mean +- std dev: [mult_list_py36] 4.61 us +- 0.13 us -> [mult_list_py37] 6.05 us +- 0.11 us: 1.31x slower

            Geometric mean: 1.22x slower
        """
        self.check_command(expected, 'compare_to', py36, py37)

        # 2 files grouped by speed
        expected = """
            Slower (2):
            - [1,2]*1000: 3.70 us +- 0.05 us -> 5.28 us +- 0.09 us: 1.42x slower
            - [1,2,3]*1000: 4.61 us +- 0.13 us -> 6.05 us +- 0.11 us: 1.31x slower

            Faster (1):
            - [1]*1000: 2.13 us +- 0.06 us -> 2.09 us +- 0.04 us: 1.02x faster

            Geometric mean: 1.22x slower
        """
        self.check_command(expected, 'compare_to', "--group-by-speed", py36, py37)

        # 2 files grouped by speed (with not significant)
        expected = """
            Faster (2):
            - [1,2]*1000: 3.70 us +- 0.05 us -> 3.18 us +- 0.08 us: 1.16x faster
            - [1,2,3]*1000: 4.61 us +- 0.13 us -> 4.17 us +- 0.11 us: 1.11x faster

            Benchmark hidden because not significant (1): [1]*1000

            Geometric mean: 1.09x faster
        """
        self.check_command(expected, 'compare_to', "--group-by-speed", py36, py38)

        # 3 files
        expected = """
            [1]*1000
            ========

            Mean +- std dev: [mult_list_py36] 2.13 us +- 0.06 us -> [mult_list_py37] 2.09 us +- 0.04 us: 1.02x faster
            Mean +- std dev: [mult_list_py36] 2.13 us +- 0.06 us -> [mult_list_py38] 2.13 us +- 0.03 us: 1.00x slower
            Not significant!

            [1,2]*1000
            ==========

            Mean +- std dev: [mult_list_py36] 3.70 us +- 0.05 us -> [mult_list_py37] 5.28 us +- 0.09 us: 1.42x slower
            Mean +- std dev: [mult_list_py36] 3.70 us +- 0.05 us -> [mult_list_py38] 3.18 us +- 0.08 us: 1.16x faster

            [1,2,3]*1000
            ============

            Mean +- std dev: [mult_list_py36] 4.61 us +- 0.13 us -> [mult_list_py37] 6.05 us +- 0.11 us: 1.31x slower
            Mean +- std dev: [mult_list_py36] 4.61 us +- 0.13 us -> [mult_list_py38] 4.17 us +- 0.11 us: 1.11x faster

            Geometric mean
            ==============

            mult_list_py37: 1.22x slower
            mult_list_py38: 1.09x faster
        """
        self.check_command(expected, 'compare_to', py36, py37, py38)

        # 3 files as table
        expected = """
            +----------------+----------------+-----------------------+-----------------------+
            | Benchmark      | mult_list_py36 | mult_list_py37        | mult_list_py38        |
            +================+================+=======================+=======================+
            | [1]*1000       | 2.13 us        | 2.09 us: 1.02x faster | not significant       |
            +----------------+----------------+-----------------------+-----------------------+
            | [1,2]*1000     | 3.70 us        | 5.28 us: 1.42x slower | 3.18 us: 1.16x faster |
            +----------------+----------------+-----------------------+-----------------------+
            | [1,2,3]*1000   | 4.61 us        | 6.05 us: 1.31x slower | 4.17 us: 1.11x faster |
            +----------------+----------------+-----------------------+-----------------------+
            | Geometric mean | (ref)          | 1.22x slower          | 1.09x faster          |
            +----------------+----------------+-----------------------+-----------------------+
        """
        self.check_command(expected, 'compare_to', '--table', py36, py37, py38)

        # 3 files as table grouped by speed
        expected = """
            +----------------+----------------+-----------------------+
            | Benchmark      | mult_list_py36 | mult_list_py37        |
            +================+================+=======================+
            | [1]*1000       | 2.13 us        | 2.09 us: 1.02x faster |
            +----------------+----------------+-----------------------+
            | [1,2,3]*1000   | 4.61 us        | 6.05 us: 1.31x slower |
            +----------------+----------------+-----------------------+
            | [1,2]*1000     | 3.70 us        | 5.28 us: 1.42x slower |
            +----------------+----------------+-----------------------+
            | Geometric mean | (ref)          | 1.22x slower          |
            +----------------+----------------+-----------------------+
        """
        self.check_command(expected, 'compare_to', '--table', "--group-by-speed", py36, py37)

    def test_compare_to_cli_tags(self):
        py36 = os.path.join(TESTDIR, 'mult_list_py36_tags.json')
        py37 = os.path.join(TESTDIR, 'mult_list_py37_tags.json')

        # 2 files
        expected = """
            Benchmarks with tag 'bar':
            ==========================

            [1,2]*1000: Mean +- std dev: [mult_list_py36_tags] 3.70 us +- 0.05 us -> [mult_list_py37_tags] 5.28 us +- 0.09 us: 1.42x slower
            [1,2,3]*1000: Mean +- std dev: [mult_list_py36_tags] 4.61 us +- 0.13 us -> [mult_list_py37_tags] 6.05 us +- 0.11 us: 1.31x slower

            Geometric mean: 1.37x slower

            Benchmarks with tag 'foo':
            ==========================

            [1]*1000: Mean +- std dev: [mult_list_py36_tags] 2.13 us +- 0.06 us -> [mult_list_py37_tags] 2.09 us +- 0.04 us: 1.02x faster
            [1,2]*1000: Mean +- std dev: [mult_list_py36_tags] 3.70 us +- 0.05 us -> [mult_list_py37_tags] 5.28 us +- 0.09 us: 1.42x slower

            Geometric mean: 1.18x slower

            All benchmarks:
            ===============

            [1]*1000: Mean +- std dev: [mult_list_py36_tags] 2.13 us +- 0.06 us -> [mult_list_py37_tags] 2.09 us +- 0.04 us: 1.02x faster
            [1,2]*1000: Mean +- std dev: [mult_list_py36_tags] 3.70 us +- 0.05 us -> [mult_list_py37_tags] 5.28 us +- 0.09 us: 1.42x slower
            [1,2,3]*1000: Mean +- std dev: [mult_list_py36_tags] 4.61 us +- 0.13 us -> [mult_list_py37_tags] 6.05 us +- 0.11 us: 1.31x slower

            Geometric mean: 1.22x slower
        """
        self.check_command(expected, 'compare_to', py36, py37)

        expected = """
            Benchmarks with tag 'bar':
            ==========================

            +----------------+---------------------+-----------------------+
            | Benchmark      | mult_list_py36_tags | mult_list_py37_tags   |
            +================+=====================+=======================+
            | [1,2]*1000     | 3.70 us             | 5.28 us: 1.42x slower |
            +----------------+---------------------+-----------------------+
            | [1,2,3]*1000   | 4.61 us             | 6.05 us: 1.31x slower |
            +----------------+---------------------+-----------------------+
            | Geometric mean | (ref)               | 1.37x slower          |
            +----------------+---------------------+-----------------------+

            Benchmarks with tag 'foo':
            ==========================

            +----------------+---------------------+-----------------------+
            | Benchmark      | mult_list_py36_tags | mult_list_py37_tags   |
            +================+=====================+=======================+
            | [1]*1000       | 2.13 us             | 2.09 us: 1.02x faster |
            +----------------+---------------------+-----------------------+
            | [1,2]*1000     | 3.70 us             | 5.28 us: 1.42x slower |
            +----------------+---------------------+-----------------------+
            | Geometric mean | (ref)               | 1.18x slower          |
            +----------------+---------------------+-----------------------+

            All benchmarks:
            ===============

            +----------------+---------------------+-----------------------+
            | Benchmark      | mult_list_py36_tags | mult_list_py37_tags   |
            +================+=====================+=======================+
            | [1]*1000       | 2.13 us             | 2.09 us: 1.02x faster |
            +----------------+---------------------+-----------------------+
            | [1,2]*1000     | 3.70 us             | 5.28 us: 1.42x slower |
            +----------------+---------------------+-----------------------+
            | [1,2,3]*1000   | 4.61 us             | 6.05 us: 1.31x slower |
            +----------------+---------------------+-----------------------+
            | Geometric mean | (ref)               | 1.22x slower          |
            +----------------+---------------------+-----------------------+
        """
        self.check_command(expected, 'compare_to', '--table', py36, py37)

    def test_compare_to_cli_min_speed(self):
        py36 = os.path.join(TESTDIR, 'mult_list_py36.json')
        py37 = os.path.join(TESTDIR, 'mult_list_py37.json')
        py38 = os.path.join(TESTDIR, 'mult_list_py38.json')

        # 2 files, min-speed=10
        expected = """
            [1,2]*1000: Mean +- std dev: [mult_list_py36] 3.70 us +- 0.05 us -> [mult_list_py37] 5.28 us +- 0.09 us: 1.42x slower
            [1,2,3]*1000: Mean +- std dev: [mult_list_py36] 4.61 us +- 0.13 us -> [mult_list_py37] 6.05 us +- 0.11 us: 1.31x slower

            Benchmark hidden because not significant (1): [1]*1000

            Geometric mean: 1.22x slower
        """
        self.check_command(expected, 'compare_to', "--min-speed=10", py36, py37)

        # 2 files, min-speed=40
        expected = """
            [1,2]*1000: Mean +- std dev: [mult_list_py36] 3.70 us +- 0.05 us -> [mult_list_py37] 5.28 us +- 0.09 us: 1.42x slower

            Benchmark hidden because not significant (2): [1]*1000, [1,2,3]*1000

            Geometric mean: 1.22x slower
        """
        self.check_command(expected, 'compare_to', "--min-speed=40", py36, py37)

        # 3 files as table, min-speed=10
        expected = """
            +----------------+----------------+-----------------------+-----------------------+
            | Benchmark      | mult_list_py36 | mult_list_py37        | mult_list_py38        |
            +================+================+=======================+=======================+
            | [1,2]*1000     | 3.70 us        | 5.28 us: 1.42x slower | 3.18 us: 1.16x faster |
            +----------------+----------------+-----------------------+-----------------------+
            | [1,2,3]*1000   | 4.61 us        | 6.05 us: 1.31x slower | 4.17 us: 1.11x faster |
            +----------------+----------------+-----------------------+-----------------------+
            | Geometric mean | (ref)          | 1.22x slower          | 1.09x faster          |
            +----------------+----------------+-----------------------+-----------------------+

            Benchmark hidden because not significant (1): [1]*1000
        """
        self.check_command(expected, 'compare_to', '--table', "--min-speed=10", py36, py37, py38)

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

            Number of calibration run: 1
            Number of run with values: 40
            Total number of run: 41

            Number of warmup per run: 1
            Number of value per run: 3
            Loop iterations per value: 8
            Total number of values: 120

            Minimum:         22.1 ms
            Median +- MAD:   22.5 ms +- 0.1 ms
            Mean +- std dev: 22.5 ms +- 0.2 ms
            Maximum:         22.9 ms

              0th percentile: 22.1 ms (-2% of the mean) -- minimum
              5th percentile: 22.3 ms (-1% of the mean)
             25th percentile: 22.4 ms (-1% of the mean) -- Q1
             50th percentile: 22.5 ms (-0% of the mean) -- median
             75th percentile: 22.7 ms (+1% of the mean) -- Q3
             95th percentile: 22.9 ms (+2% of the mean)
            100th percentile: 22.9 ms (+2% of the mean) -- maximum

            Number of outlier (out of 22.0 ms..23.0 ms): 0
        """)
        self.check_command(expected, 'stats', TELCO)

    def test_dump_raw(self):
        expected = """
            Run 1: calibrate the number of loops: 8
            - raw calibrate 1: 23.1 ms (loops: 1)
            - raw calibrate 2: 45.0 ms (loops: 2)
            - raw calibrate 3: 89.9 ms (loops: 4)
            - raw calibrate 4: 179 ms (loops: 8)
            Run 2: 1 warmup, 3 values, 8 loops
            - raw warmup 1: 180 ms
            - raw value 1: 182 ms
            - raw value 2: 180 ms
            - raw value 3: 181 ms
        """
        stdout = self.run_command('dump', '--raw', TELCO)
        self.assertIn(textwrap.dedent(expected).strip(), stdout)

    def test_dump(self):
        expected = """
            Run 1: calibrate the number of loops: 8
            - calibrate 1: 23.1 ms (loops: 1, raw: 23.1 ms)
            - calibrate 2: 22.5 ms (loops: 2, raw: 45.0 ms)
            - calibrate 3: 22.5 ms (loops: 4, raw: 89.9 ms)
            - calibrate 4: 22.4 ms (loops: 8, raw: 179 ms)
            Run 2: 1 warmup, 3 values, 8 loops
            - warmup 1: 22.5 ms
            - value 1: 22.8 ms
            - value 2: 22.5 ms
            - value 3: 22.6 ms
        """
        stdout = self.run_command('dump', TELCO)
        self.assertIn(textwrap.dedent(expected).strip(), stdout)

    def test_dump_track_memory(self):
        expected = """
            Run 1: calibrate the number of loops: 2^15
            - calibrate 1: 7188.0 kB (loops: 2^15)
            Run 2: 0 warmups, 1 value, 2^15 loops
            - value 1: 7188.0 kB
            Run 3: 0 warmups, 1 value, 2^15 loops
            - value 1: 7192.0 kB
            Run 4: 0 warmups, 1 value, 2^15 loops
            - value 1: 7208.0 kB
        """
        filename = os.path.join(TESTDIR, 'track_memory.json')
        stdout = self.run_command('dump', filename)
        self.assertIn(textwrap.dedent(expected).strip(), stdout)

    def test_dump_quiet(self):
        expected = """
            Run 2:
            - value 1: 22.8 ms
            - value 2: 22.5 ms
            - value 3: 22.6 ms
            Run 3:
            - value 1: 22.3 ms
            - value 2: 22.4 ms
            - value 3: 22.3 ms
        """
        stdout = self.run_command('dump', '--quiet', TELCO)
        self.assertIn(textwrap.dedent(expected).strip(), stdout)

    def test_dump_verbose(self):
        expected = """
            Run 1: calibrate the number of loops: 8
            - calibrate 1: 23.1 ms (loops: 1, raw: 23.1 ms)
            - calibrate 2: 22.5 ms (loops: 2, raw: 45.0 ms)
            - calibrate 3: 22.5 ms (loops: 4, raw: 89.9 ms)
            - calibrate 4: 22.4 ms (loops: 8, raw: 179 ms)
            - Metadata:
              cpu_freq: 2=3596 MHz, 3=1352 MHz
              cpu_temp: coretemp:Physical id 0=67 C, coretemp:Core 0=51 C, coretemp:Core 1=67 C
              date: 2016-10-21 03:14:19.670631
              duration: 338 ms
              load_avg_1min: 0.29
              mem_max_rss: 13.4 MB
              runnable_threads: 1
              uptime: 2 day 2 hour 4 min
            Run 2: 1 warmup, 3 values, 8 loops
            - warmup 1: 22.5 ms
            - value 1: 22.8 ms
            - value 2: 22.5 ms
            - value 3: 22.6 ms
            - Metadata:
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

    def test_command(self):
        command = [sys.executable, '-c', 'pass']
        stdout = self.run_command('command', '--debug-single-value', *command)
        self.assertRegex(stdout,
                         r'^\.\ncommand: [0-9.]+ (?:ms|sec)$')

    def test_check_unstable(self):
        suite = self.create_suite()

        with tests.temporary_file() as tmp_name:
            suite.dump(tmp_name)
            stdout = self.run_command('check', tmp_name)

        expected = textwrap.dedent("""
            py36
            ----

            WARNING: the benchmark result may be unstable
            * the standard deviation (500 ms) is 33% of the mean (1.50 sec)

            Try to rerun the benchmark with more runs, values and/or loops.
            Run '{0} -m pyperf system tune' command to reduce the system jitter.
            Use pyperf stats, pyperf dump and pyperf hist to analyze results.
            Use --quiet option to hide these warnings.

            py38
            ----

            WARNING: the benchmark result may be unstable
            * the standard deviation (500 ms) is 25% of the mean (2.00 sec)

            Try to rerun the benchmark with more runs, values and/or loops.
            Run '{0} -m pyperf system tune' command to reduce the system jitter.
            Use pyperf stats, pyperf dump and pyperf hist to analyze results.
            Use --quiet option to hide these warnings.
        """).strip()
        expected = expected.format(os.path.basename(sys.executable))
        self.assertEqual(stdout.rstrip(), expected)

    def _check_track_memory_bench(self, bench, loops):
        self.assertEqual(bench.get_nrun(), 2)
        for run in bench.get_runs():
            self.assertEqual(run.warmups, ())
            self.assertEqual(len(run.values), 1)
            self.assertIsInstance(run.values[0], int)
            self.assertEqual(run.get_loops(), loops)
            metadata = run.get_metadata()
            self.assertEqual(metadata['warmups'], 1)
            self.assertEqual(metadata['values'], 3)

    def _check_track_memory(self, track_option):
        with tests.temporary_file() as tmp_name:
            self.run_command('timeit',
                             track_option,
                             '-p2', '-w1', '-l5', '-n3',
                             '[1,2]*1000',
                             '-o', tmp_name)
            bench = pyperf.Benchmark.load(tmp_name)

        self._check_track_memory_bench(bench, loops=5)

    def test_track_memory(self):
        self._check_track_memory('--track-memory')

    def test_tracemalloc(self):
        try:
            import tracemalloc   # noqa
        except ImportError:
            self.skipTest('tracemalloc module not available')

        self._check_track_memory('--tracemalloc')

    @unittest.skipIf(sys.platform == 'win32',
                     'https://github.com/psf/pyperf/issues/97')
    def test_command_track_memory(self):
        cmd = (sys.executable, '-c', 'pass')
        with tests.temporary_file() as tmp_name:
            args = ('command',
                    '--track-memory',
                    '-p2', '-w1', '-l2', '-n3',
                    '-o', tmp_name,
                    '--')
            args += cmd
            self.run_command(*args)
            bench = pyperf.Benchmark.load(tmp_name)

        self._check_track_memory_bench(bench, loops=2)


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
        bench = pyperf.Benchmark.load(TELCO)

        with tests.temporary_directory() as tmpdir:
            filename = os.path.join(tmpdir, 'test.json')
            self.run_command('convert', TELCO, '-o', filename)

            bench2 = pyperf.Benchmark.load(filename)

        tests.compare_benchmarks(self, bench2, bench)

    def test_filter_benchmarks(self):
        values = (1.0, 1.5, 2.0)
        benchmarks = []
        for name in ("call_simple", "go", "telco"):
            bench = self.create_bench(values, metadata={'name': name})
            benchmarks.append(bench)
        suite = pyperf.BenchmarkSuite(benchmarks)

        with tests.temporary_directory() as tmpdir:
            filename = os.path.join(tmpdir, 'test.json')
            suite.dump(filename)

            stdout = self.run_command('convert', filename,
                                      '--include-benchmark', 'go', '--stdout')
            suite2 = pyperf.BenchmarkSuite.loads(stdout)

            stdout = self.run_command('convert', filename,
                                      '--exclude-benchmark', 'go', '--stdout')
            suite3 = pyperf.BenchmarkSuite.loads(stdout)

        self.assertEqual(suite2.get_benchmark_names(),
                         ['go'])

        self.assertEqual(suite3.get_benchmark_names(),
                         ['call_simple', 'telco'])

    def test_remove_warmups(self):
        values = [1.0, 2.0, 3.0]
        raw_values = [5.0] + values
        run = pyperf.Run(values, warmups=[(1, 5.0)],
                         metadata={'name': 'bench'})
        bench = pyperf.Benchmark([run])

        self.assertEqual(bench._get_nwarmup(), 1)
        self.assertEqual(bench._get_raw_values(warmups=True),
                         raw_values)

        with tests.temporary_directory() as tmpdir:
            filename = os.path.join(tmpdir, 'test.json')
            bench.dump(filename)

            stdout = self.run_command('convert', filename,
                                      '--remove-warmups', '--stdout')
            bench2 = pyperf.Benchmark.loads(stdout)

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
            bench2 = pyperf.Benchmark.loads(stdout)

            stdout = self.run_command('convert', filename,
                                      '--include-runs', '1-3,5', '--stdout')
            bench3 = pyperf.Benchmark.loads(stdout)

            stdout = self.run_command('convert', filename,
                                      '--exclude-runs', '2,4', '--stdout')
            bench4 = pyperf.Benchmark.loads(stdout)

        self.assertEqual(bench2.get_values(), (4.0,))
        self.assertEqual(bench3.get_values(), (1.0, 2.0, 3.0, 5.0))
        self.assertEqual(bench4.get_values(), (1.0, 3.0, 5.0))


if __name__ == "__main__":
    unittest.main()
