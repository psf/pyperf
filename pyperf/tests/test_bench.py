import datetime
import errno
import gzip
import unittest

import pyperf
from pyperf import tests


NUMBER_TYPES = (int, float)


def create_run(values=None, warmups=None, metadata=None):
    if values is None:
        values = (1.0,)
    if metadata is None:
        metadata = {'name': 'bench'}
    elif 'name' not in metadata:
        metadata['name'] = 'bench'
    return pyperf.Run(values, warmups,
                      metadata=metadata,
                      collect_metadata=False)


class RunTests(unittest.TestCase):
    def test_attr(self):
        run = pyperf.Run((2.0, 3.0),
                         warmups=((4, 0.5),),
                         metadata={'loops': 2, 'inner_loops': 5},
                         collect_metadata=False)
        self.assertEqual(run.get_loops(), 2)
        self.assertEqual(run.get_inner_loops(), 5)
        self.assertEqual(run.get_total_loops(), 2 * 5)
        self.assertEqual(run.values,
                         (2.0, 3.0))
        self.assertEqual(run._get_raw_values(),
                         [20.0, 30.0])
        self.assertEqual(run._get_raw_values(warmups=True),
                         [10.0, 20.0, 30.0])

        run = pyperf.Run((2.0, 3.0), warmups=((1, 1.0),))
        self.assertEqual(run.get_loops(), 1)
        self.assertEqual(run.get_inner_loops(), 1)
        self.assertEqual(run.get_total_loops(), 1)

    def test_constructor(self):
        # need at least one value or one warmup value
        with self.assertRaises(ValueError):
            pyperf.Run([], collect_metadata=False)
        pyperf.Run([1.0], collect_metadata=False)
        pyperf.Run([], warmups=[(4, 1.0)], collect_metadata=False)

        # number of loops
        with self.assertRaises(ValueError):
            pyperf.Run([1.0], metadata={'loops': -1}, collect_metadata=False)
        with self.assertRaises(ValueError):
            pyperf.Run([1.0], metadata={'inner_loops': 0}, collect_metadata=False)

        # loops type error
        with self.assertRaises(ValueError):
            pyperf.Run([1.0], metadata={'loops': 1.0}, collect_metadata=False)
        with self.assertRaises(ValueError):
            pyperf.Run([1.0], metadata={'inner_loops': 1.0}, collect_metadata=False)

        # metadata value must not be an empty string
        with self.assertRaises(ValueError):
            pyperf.Run([1.0], metadata={'name': ''}, collect_metadata=False)
        run = pyperf.Run([1.0], metadata={'load_avg_1min': 0.0},
                         collect_metadata=False)
        self.assertEqual(run.get_metadata()['load_avg_1min'], 0.0)

    def test_name(self):
        # name must be non-empty
        with self.assertRaises(ValueError):
            pyperf.Run([1.0], metadata={'name': '   '})

    def test_number_types(self):
        # ensure that all types of numbers are accepted
        for number_type in NUMBER_TYPES:
            run = pyperf.Run([number_type(1)], collect_metadata=False)
            self.assertIsInstance(run.values[0], number_type)

            run = pyperf.Run([5], warmups=[(4, number_type(3))],
                             collect_metadata=False)
            self.assertEqual(run.warmups, ((4, 3),))
            self.assertIsInstance(run.warmups[0][1], number_type)

    def test_get_date(self):
        date = datetime.datetime.now().isoformat(' ')
        run = pyperf.Run([1.0], metadata={'date': date},
                         collect_metadata=False)
        self.assertEqual(run._get_date(), date)

        run = pyperf.Run([1.0], collect_metadata=False)
        self.assertIsNone(run._get_date())


class BenchmarkTests(unittest.TestCase):
    def check_runs(self, bench, warmups, values):
        runs = bench.get_runs()
        self.assertEqual(len(runs), len(values))
        for value, run in zip(values, runs):
            self.assertEqual(run.warmups, tuple(warmups))
            self.assertEqual(run.values, (value,))

    def test_name(self):
        # no name metadata
        run = pyperf.Run([1.0])
        with self.assertRaises(ValueError):
            pyperf.Benchmark([run])

    def test_add_run(self):
        metadata = {'name': 'bench', 'hostname': 'toto'}
        runs = [create_run(metadata=metadata)]
        bench = pyperf.Benchmark(runs)

        # expect Run, not list
        self.assertRaises(TypeError, bench.add_run, [1.0])

        bench.add_run(create_run(metadata=metadata))

        # incompatible: name is different
        metadata = {'name': 'bench2', 'hostname': 'toto'}
        with self.assertRaises(ValueError):
            bench.add_run(create_run(metadata=metadata))

        # incompatible: hostname is different
        metadata = {'name': 'bench', 'hostname': 'homer'}
        with self.assertRaises(ValueError):
            bench.add_run(create_run(metadata=metadata))

        # compatible (same metadata)
        metadata = {'name': 'bench', 'hostname': 'toto'}
        bench.add_run(create_run(metadata=metadata))

    def test_benchmark(self):
        values = (1.0, 1.5, 2.0)
        raw_values = tuple(value * 3 * 20 for value in values)
        runs = []
        for value in values:
            run = pyperf.Run([value],
                             warmups=[(1, 3.0)],
                             metadata={'key': 'value',
                                       'loops': 20,
                                       'inner_loops': 3,
                                       'name': 'mybench'},
                             collect_metadata=False)
            runs.append(run)
        bench = pyperf.Benchmark(runs)

        self.assertEqual(bench.get_values(), values)
        self.assertEqual(bench.get_unit(), 'second')
        self.assertEqual(bench._get_raw_values(), list(raw_values))
        self.assertEqual(bench.get_nrun(), 3)

        runs = bench.get_runs()
        self.assertIsInstance(runs, list)
        self.assertEqual(len(runs), 3)
        for run in runs:
            self.assertIsInstance(run, pyperf.Run)
            self.assertEqual(len(run._get_raw_values(True)), 2)
            self.assertEqual(run.get_loops(), 20)
            self.assertEqual(run.get_inner_loops(), 3)

        self.check_runs(bench, [(1, 3.0)], values)

        self.assertEqual(bench.get_name(), "mybench")
        self.assertEqual(bench.get_metadata(),
                         {'key': 'value',
                          'name': 'mybench',
                          'loops': 20,
                          'inner_loops': 3})
        self.assertEqual(repr(bench),
                         "<Benchmark 'mybench' with 3 runs>")

    def test_get_unit(self):
        run = pyperf.Run((1.0,),
                         metadata={'name': 'bench', 'unit': 'byte'},
                         collect_metadata=False)
        bench = pyperf.Benchmark([run])
        self.assertEqual(bench.get_unit(), 'byte')

    def create_dummy_benchmark(self):
        runs = [create_run()]
        return pyperf.Benchmark(runs)

    def check_benchmarks_equal(self, bench, bench2):
        self.assertEqual(bench.get_name(), bench2.get_name())
        self.assertEqual(bench.get_values(), bench2.get_values())
        self.assertEqual(bench.get_metadata(), bench2.get_metadata())

    def test_dump_load(self):
        bench = self.create_dummy_benchmark()

        with tests.temporary_file() as tmp_name:
            bench.dump(tmp_name)
            bench2 = pyperf.Benchmark.load(tmp_name)

        self.check_benchmarks_equal(bench, bench2)

    def test_dump_replace(self):
        bench = self.create_dummy_benchmark()

        with tests.temporary_file() as tmp_name:
            bench.dump(tmp_name)

            # dump() must not override an existing file by default
            with self.assertRaises(OSError) as cm:
                bench.dump(tmp_name)
            self.assertEqual(cm.exception.errno, errno.EEXIST)

            # ok if replace is true
            bench.dump(tmp_name, replace=True)

    def test_dump_gzip(self):
        bench = self.create_dummy_benchmark()

        with tests.temporary_file(suffix='.gz') as tmp_name:
            bench.dump(tmp_name)

            with gzip.open(tmp_name, 'rt', encoding='utf-8') as fp:
                json = fp.read()

        expected = tests.benchmark_as_json(bench)
        self.assertEqual(json, expected)

    def test_load_gzip(self):
        bench = self.create_dummy_benchmark()

        with tests.temporary_file(suffix='.gz') as tmp_name:
            bench.dump(tmp_name)
            bench2 = pyperf.Benchmark.load(tmp_name)

        self.check_benchmarks_equal(bench, bench2)

    def test_add_runs(self):
        values1 = (1.0, 2.0, 3.0)
        bench = pyperf.Benchmark([create_run(values1)])

        values2 = (4.0, 5.0, 6.0)
        bench2 = pyperf.Benchmark([create_run(values2)])

        bench.add_runs(bench2)
        self.assertEqual(bench.get_values(), values1 + values2)

    def test__get_nvalue_per_run(self):
        # exact
        runs = [create_run([1.0, 2.0, 3.0]),
                create_run([4.0, 5.0, 6.0])]
        bench = pyperf.Benchmark(runs)
        nvalue = bench._get_nvalue_per_run()
        self.assertEqual(nvalue, 3)
        self.assertIsInstance(nvalue, int)

        # average
        runs = [create_run([1.0, 2.0, 3.0, 4.0]),
                create_run([5.0, 6.0])]
        bench = pyperf.Benchmark(runs)
        nvalue = bench._get_nvalue_per_run()
        self.assertEqual(nvalue, 3.0)
        self.assertIsInstance(nvalue, float)

    def test_get_warmups(self):
        # exact
        runs = [create_run((1.0, 2.0, 3.0), warmups=[(1, 1.0)]),
                create_run((5.0, 6.0), warmups=[(1, 4.0)])]
        bench = pyperf.Benchmark(runs)
        nwarmup = bench._get_nwarmup()
        self.assertEqual(nwarmup, 1)
        self.assertIsInstance(nwarmup, int)

        # average
        runs = [create_run([3.0], warmups=[(1, 1.0), (1, 2.0)]),
                create_run([4.0, 5.0, 6.0])]
        bench = pyperf.Benchmark(runs)
        nwarmup = bench._get_nwarmup()
        self.assertEqual(nwarmup, 1)
        self.assertIsInstance(nwarmup, float)

    def test_get_nvalue(self):
        bench = pyperf.Benchmark([create_run([2.0, 3.0])])
        self.assertEqual(bench.get_nvalue(), 2)

        bench.add_run(create_run([5.0]))
        self.assertEqual(bench.get_nvalue(), 3)

    def test_get_runs(self):
        run1 = create_run([1.0])
        run2 = create_run([2.0])

        bench = pyperf.Benchmark([run1, run2])
        self.assertEqual(bench.get_runs(), [run1, run2])

    def test_get_total_duration(self):
        # use duration metadata
        runs = [create_run([0.1], metadata={'duration': 1.0}),
                create_run([0.1], metadata={'duration': 2.0})]
        bench = pyperf.Benchmark(runs)
        self.assertEqual(bench.get_total_duration(), 3.0)

        # run without duration metadata
        bench.add_run(create_run([5.0], metadata={}))
        self.assertEqual(bench.get_total_duration(), 8.0)

    def test_get_dates(self):
        bench = pyperf.Benchmark([create_run()])
        self.assertIsNone(bench.get_dates())

        metadata = {'date': '2016-07-20T14:06:00', 'duration': 60.0}
        bench = pyperf.Benchmark([create_run(metadata=metadata)])
        self.assertEqual(bench.get_dates(),
                         (datetime.datetime(2016, 7, 20, 14, 6, 0),
                          datetime.datetime(2016, 7, 20, 14, 7, 0)))

        metadata = {'date': '2016-07-20T14:10:00', 'duration': 60.0}
        bench.add_run(create_run(metadata=metadata))
        self.assertEqual(bench.get_dates(),
                         (datetime.datetime(2016, 7, 20, 14, 6, 0),
                          datetime.datetime(2016, 7, 20, 14, 11, 0)))

    def test_extract_metadata(self):
        warmups = ((1, 5.0),)
        runs = [pyperf.Run((1.0,), warmups=warmups,
                           metadata={'name': 'bench', 'mem_usage': 5},
                           collect_metadata=False),
                pyperf.Run((2.0,), warmups=warmups,
                           metadata={'name': 'bench', 'mem_usage': 13},
                           collect_metadata=False)]
        bench = pyperf.Benchmark(runs)

        bench._extract_metadata('mem_usage')
        self.assertEqual(bench.get_values(), (5, 13))
        for run in bench.get_runs():
            self.assertEqual(run.warmups, ())

    def test_remove_all_metadata(self):
        run = pyperf.Run((1.0,),
                         metadata={'name': 'bench', 'os': 'win', 'unit': 'byte'},
                         collect_metadata=False)
        bench = pyperf.Benchmark([run])
        self.assertEqual(bench.get_metadata(),
                         {'name': 'bench', 'os': 'win', 'unit': 'byte'})

        bench._remove_all_metadata()
        self.assertEqual(bench.get_metadata(),
                         {'name': 'bench', 'unit': 'byte'})

    def test_update_metadata(self):
        runs = []
        for value in (1.0, 2.0, 3.0):
            runs.append(pyperf.Run((value,),
                                   metadata={'name': 'bench'},
                                   collect_metadata=False))
        bench = pyperf.Benchmark(runs)
        self.assertEqual(bench.get_metadata(),
                         {'name': 'bench'})

        bench.update_metadata({'os': 'linux'})
        self.assertEqual(bench.get_metadata(),
                         {'os': 'linux', 'name': 'bench'})

    def test_update_metadata_inner_loops(self):
        run = create_run(metadata={'inner_loops': 5})
        bench = pyperf.Benchmark([run])
        with self.assertRaises(ValueError):
            bench.update_metadata({'inner_loops': 8})

    def test_stats(self):
        values = [float(value) for value in range(1, 96)]
        run = create_run(values)
        bench = pyperf.Benchmark([run])
        self.assertEqual(bench.mean(), 48.0)
        self.assertEqual(bench.median(), 48.0)
        self.assertAlmostEqual(bench.stdev(), 27.5680, delta=1e-3)
        self.assertEqual(bench.median_abs_dev(), 24.0)

    def test_stats_same(self):
        values = [5.0 for i in range(10)]
        run = create_run(values)
        bench = pyperf.Benchmark([run])
        self.assertEqual(bench.mean(), 5.0)
        self.assertEqual(bench.median(), 5.0)
        self.assertEqual(bench.stdev(), 0.0)
        self.assertEqual(bench.median_abs_dev(), 0.0)

    def test_stats_empty(self):
        run = create_run(values=[], warmups=[(4, 10.0)])
        bench = pyperf.Benchmark([run])
        self.assertRaises(Exception, bench.mean)
        self.assertRaises(Exception, bench.median)
        self.assertRaises(Exception, bench.stdev)
        self.assertRaises(Exception, bench.median_abs_dev)

    def test_stats_single(self):
        values = [7.0]
        run = create_run(values)
        bench = pyperf.Benchmark([run])
        self.assertEqual(bench.mean(), 7.0)
        self.assertEqual(bench.median(), 7.0)
        self.assertRaises(Exception, bench.stdev)
        self.assertEqual(bench.median_abs_dev(), 0.0)


class TestBenchmarkSuite(unittest.TestCase):
    def benchmark(self, name):
        run = pyperf.Run([1.0, 1.5, 2.0],
                         metadata={'name': name},
                         collect_metadata=False)
        return pyperf.Benchmark([run])

    def test_suite(self):
        telco = self.benchmark('telco')
        go = self.benchmark('go')
        suite = pyperf.BenchmarkSuite([telco, go])

        self.assertIsNone(suite.filename)
        self.assertEqual(len(suite), 2)
        self.assertEqual(suite.get_benchmarks(), [telco, go])
        self.assertEqual(suite.get_benchmark('go'), go)
        with self.assertRaises(KeyError):
            suite.get_benchmark('non_existent')

    def create_dummy_suite(self):
        telco = self.benchmark('telco')
        go = self.benchmark('go')
        return pyperf.BenchmarkSuite([telco, go])

    def check_dummy_suite(self, suite):
        benchmarks = suite.get_benchmarks()
        self.assertEqual(len(benchmarks), 2)
        self.assertEqual(benchmarks[0].get_name(), 'telco')
        self.assertEqual(benchmarks[1].get_name(), 'go')

    def test_json(self):
        suite = self.create_dummy_suite()

        with tests.temporary_file() as filename:
            suite.dump(filename)
            suite = pyperf.BenchmarkSuite.load(filename)

        self.assertEqual(suite.filename, filename)

        self.check_dummy_suite(suite)

    def test_dump_replace(self):
        suite = self.create_dummy_suite()

        with tests.temporary_file() as tmp_name:
            suite.dump(tmp_name)

            # dump() must not override an existing file by default
            with self.assertRaises(OSError) as cm:
                suite.dump(tmp_name)
            self.assertEqual(cm.exception.errno, errno.EEXIST)

            # ok if replace is true
            suite.dump(tmp_name, replace=True)

    def test_add_runs(self):
        # bench 1
        values = (1.0, 2.0, 3.0)
        run = pyperf.Run(values, metadata={'name': "bench"})
        bench = pyperf.Benchmark([run])
        suite = pyperf.BenchmarkSuite([bench])

        # bench 2
        values2 = (4.0, 5.0, 6.0)
        run = pyperf.Run(values2, metadata={'name': "bench"})
        bench2 = pyperf.Benchmark([run])
        suite.add_runs(bench2)

        bench = suite.get_benchmark('bench')
        self.assertEqual(bench.get_values(), values + values2)

    def test_get_total_duration(self):
        run = create_run([1.0])
        bench = pyperf.Benchmark([run])
        suite = pyperf.BenchmarkSuite([bench])

        run = create_run([2.0])
        bench = pyperf.Benchmark([run])
        suite.add_runs(bench)

        self.assertEqual(suite.get_total_duration(), 3.0)

    def test_get_dates(self):
        run = create_run(metadata={'date': '2016-07-20T14:06:00',
                                   'duration': 60.0,
                                   'name': 'bench1'})
        bench = pyperf.Benchmark([run])
        suite = pyperf.BenchmarkSuite([bench])
        self.assertEqual(suite.get_dates(),
                         (datetime.datetime(2016, 7, 20, 14, 6, 0),
                          datetime.datetime(2016, 7, 20, 14, 7, 0)))

        run = create_run(metadata={'date': '2016-07-20T14:10:00',
                                   'duration': 60.0,
                                   'name': 'bench2'})
        bench = pyperf.Benchmark([run])
        suite.add_benchmark(bench)
        self.assertEqual(suite.get_dates(),
                         (datetime.datetime(2016, 7, 20, 14, 6, 0),
                          datetime.datetime(2016, 7, 20, 14, 11, 0)))

    def test_get_metadata(self):
        benchmarks = []
        for name in ('a', 'b'):
            run = pyperf.Run([1.0],
                             metadata={'name': name, 'os': 'linux'},
                             collect_metadata=False)
            bench = pyperf.Benchmark([run])
            benchmarks.append(bench)

        suite = pyperf.BenchmarkSuite(benchmarks)
        self.assertEqual(suite.get_metadata(),
                         {'os': 'linux'})


if __name__ == "__main__":
    unittest.main()
