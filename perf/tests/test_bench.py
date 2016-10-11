import datetime

import six

import perf
from perf import tests
from perf.tests import unittest


NUMBER_TYPES = six.integer_types + (float,)


class RunTests(unittest.TestCase):
    def test_attr(self):
        run = perf.Run((2.0, 3.0),
                       warmups=((4, 10.0),),
                       metadata={'loops': 2, 'inner_loops': 5},
                       collect_metadata=False)
        self.assertEqual(run._get_loops(), 2)
        self.assertEqual(run._get_inner_loops(), 5)
        self.assertEqual(run.get_total_loops(), 2 * 5)
        self.assertEqual(run.samples,
                         (2.0, 3.0))
        self.assertEqual(run._get_raw_samples(),
                         (20.0, 30.0))
        self.assertEqual(run._get_raw_samples(warmups=True),
                         (10.0, 20.0, 30.0))

        run = perf.Run((2.0, 3.0), warmups=((1, 1.0),))
        self.assertEqual(run._get_loops(), 1)
        self.assertEqual(run._get_inner_loops(), 1)
        self.assertEqual(run.get_total_loops(), 1)

    def test_constructor(self):
        # need at least one sample or one warmup sample
        with self.assertRaises(ValueError):
            perf.Run([], collect_metadata=False)
        perf.Run([1.0], collect_metadata=False)
        perf.Run([], warmups=[(4, 1.0)], collect_metadata=False)

        # number of loops
        with self.assertRaises(ValueError):
            perf.Run([1.0], metadata={'loops': -1}, collect_metadata=False)
        with self.assertRaises(ValueError):
            perf.Run([1.0], metadata={'inner_loops': 0}, collect_metadata=False)

        # loops type error
        with self.assertRaises(ValueError):
            perf.Run([1.0], metadata={'loops': 1.0}, collect_metadata=False)
        with self.assertRaises(ValueError):
            perf.Run([1.0], metadata={'inner_loops': 1.0}, collect_metadata=False)

        # metadata value must not be an empty string
        with self.assertRaises(ValueError):
            perf.Run([1.0], metadata={'name': ''}, collect_metadata=False)
        run = perf.Run([1.0], metadata={'load_avg_1min': 0.0},
                       collect_metadata=False)
        self.assertEqual(run.get_metadata()['load_avg_1min'].value, 0.0)

    def test_number_types(self):
        # ensure that all types of numbers are accepted
        for number_type in NUMBER_TYPES:
            run = perf.Run([number_type(1)], collect_metadata=False)
            self.assertIsInstance(run.samples[0], number_type)

            run = perf.Run([5], warmups=[(4, number_type(3))],
                           collect_metadata=False)
            self.assertEqual(run.warmups, ((4, 3),))
            self.assertIsInstance(run.warmups[0][1], number_type)

    def test_get_date(self):
        date = datetime.datetime.now()
        run = perf.Run([1.0], metadata={'date': date.isoformat()},
                       collect_metadata=False)
        self.assertEqual(run._get_date(), date)

        run = perf.Run([1.0], collect_metadata=False)
        self.assertIsNone(run._get_date())


class BenchmarkTests(unittest.TestCase):
    def check_runs(self, bench, warmups, samples):
        runs = bench.get_runs()
        self.assertEqual(len(runs), len(samples))
        for sample, run in zip(samples, runs):
            self.assertEqual(run.warmups, tuple(warmups))
            self.assertEqual(run.samples, (sample,))

    def test_add_run(self):
        bench = perf.Benchmark()

        # expect Run, not list
        self.assertRaises(TypeError, bench.add_run, [1.0])

        metadata = {'name': 'bench', 'hostname': 'toto'}
        bench.add_run(perf.Run([1.0], metadata=metadata))

        # incompatible: name is different
        metadata = {'name': 'bench2', 'hostname': 'toto'}
        with self.assertRaises(ValueError):
            bench.add_run(perf.Run([1.0], metadata=metadata))

        # incompatible: hostname is different
        metadata = {'name': 'bench', 'hostname': 'homer'}
        with self.assertRaises(ValueError):
            bench.add_run(perf.Run([1.0], metadata=metadata))

        # compatible (same metadata)
        metadata = {'name': 'bench', 'hostname': 'toto'}
        bench.add_run(perf.Run([2.0], metadata=metadata))

    def get_metadata(self, bench):
        metadata = bench.get_metadata()
        result = {}
        for name, obj in metadata.items():
            self.assertEqual(obj.name, name)
            result[obj.name] = obj.value
        return result

    def test_benchmark(self):
        samples = (1.0, 1.5, 2.0)
        raw_samples = tuple(sample * 3 * 20 for sample in samples)
        bench = perf.Benchmark()
        for sample in samples:
            run = perf.Run([sample],
                           warmups=[(1, 3.0)],
                           metadata={'key': 'value',
                                     'loops': 20,
                                     'inner_loops': 3,
                                     'name': 'mybench'},
                           collect_metadata=False)
            bench.add_run(run)

        self.assertEqual(bench.get_samples(), samples)
        self.assertEqual(bench.get_unit(), 'second')
        self.assertEqual(bench._get_raw_samples(), list(raw_samples))
        self.assertEqual(bench.get_nrun(), 3)

        runs = bench.get_runs()
        self.assertIsInstance(runs, list)
        self.assertEqual(len(runs), 3)
        for run in runs:
            self.assertIsInstance(run, perf.Run)
            self.assertEqual(len(run._get_raw_samples(True)), 2)
            self.assertEqual(run._get_loops(), 20)
            self.assertEqual(run._get_inner_loops(), 3)

        self.check_runs(bench, [(1, 3.0)], samples)

        self.assertEqual(bench.get_name(), "mybench")
        self.assertEqual(self.get_metadata(bench),
                         {'key': 'value',
                          'name': 'mybench',
                          'loops': 20,
                          'inner_loops': 3})
        self.assertEqual(bench.format(),
                         '1.50 sec +- 0.50 sec')
        self.assertEqual(str(bench),
                         'Median +- std dev: 1.50 sec +- 0.50 sec')

    def test_get_unit(self):
        bench = perf.Benchmark()
        bench.add_run(perf.Run((1.0,),
                               metadata={'name': 'bench', 'unit': 'byte'},
                               collect_metadata=False))
        self.assertEqual(bench.get_unit(), 'byte')

    def test_json(self):
        samples = (1.0, 1.5, 2.0)
        bench = perf.Benchmark()
        for sample in samples:
            run = perf.Run([sample],
                           warmups=[(1, 3.0)],
                           metadata={'key': 'value',
                                     'loops': 100,
                                     'inner_loops': 20,
                                     'name': 'mybench'},
                           collect_metadata=False)
            bench.add_run(run)

        with tests.temporary_file() as tmp_name:
            bench.dump(tmp_name)
            bench = perf.Benchmark.load(tmp_name)

        for run in bench.get_runs():
            self.assertEqual(run._get_loops(), 100)
            self.assertEqual(run._get_inner_loops(), 20)

        self.assertEqual(bench.get_name(), "mybench")
        self.assertEqual(self.get_metadata(bench),
                         {'key': 'value', 'name': 'mybench',
                          'loops': 100, 'inner_loops': 20})

        self.check_runs(bench, [(1, 3.0)], samples)

    def test__add_benchmark_run(self):
        # bench 1
        samples = (1.0, 2.0, 3.0)
        bench = perf.Benchmark()
        bench.add_run(perf.Run(samples, metadata={'name': 'bench'}))

        # bench 2
        samples2 = (4.0, 5.0, 6.0)
        bench2 = perf.Benchmark()
        bench2.add_run(perf.Run(samples2, metadata={'name': 'bench'}))
        bench.add_runs(bench2)

        self.assertEqual(bench.get_samples(), samples + samples2)

    def test__get_nsample_per_run(self):
        # exact
        bench = perf.Benchmark()
        bench.add_run(perf.Run((1.0, 2.0, 3.0)))
        bench.add_run(perf.Run((4.0, 5.0, 6.0)))
        nsample = bench._get_nsample_per_run()
        self.assertEqual(nsample, 3)
        self.assertIsInstance(nsample, int)

        # average
        bench = perf.Benchmark()
        bench.add_run(perf.Run((1.0, 2.0, 3.0, 4.0)))
        bench.add_run(perf.Run((5.0, 6.0)))
        nsample = bench._get_nsample_per_run()
        self.assertEqual(nsample, 3.0)
        self.assertIsInstance(nsample, float)

    def test_get_warmups(self):
        # exact
        bench = perf.Benchmark()
        bench.add_run(perf.Run((1.0, 2.0, 3.0), warmups=[(1, 1.0)]))
        bench.add_run(perf.Run((5.0, 6.0), warmups=[(1, 4.0)]))
        nwarmup = bench._get_nwarmup()
        self.assertEqual(nwarmup, 1)
        self.assertIsInstance(nwarmup, int)

        # average
        bench = perf.Benchmark()
        bench.add_run(perf.Run([3.0], warmups=[(1, 1.0), (1, 2.0)]))
        bench.add_run(perf.Run([4.0, 5.0, 6.0]))
        nwarmup = bench._get_nwarmup()
        self.assertEqual(nwarmup, 1)
        self.assertIsInstance(nwarmup, float)

    def test_get_nsample(self):
        bench = perf.Benchmark()
        self.assertEqual(bench.get_nsample(), 0)

        bench.add_run(perf.Run([2.0, 3.0], warmups=[(1, 1.0)]))
        self.assertEqual(bench.get_nsample(), 2)

        bench.add_run(perf.Run([5.0], warmups=[(1, 4.0)]))
        self.assertEqual(bench.get_nsample(), 3)

    def test_get_runs(self):
        run1 = perf.Run((1.0,))
        run2 = perf.Run((2.0,))

        bench = perf.Benchmark()
        bench.add_run(run1)
        bench.add_run(run2)
        self.assertEqual(bench.get_runs(), [run1, run2])

    def test_get_total_duration(self):
        bench = perf.Benchmark()
        self.assertEqual(bench.get_total_duration(), 0.0)

        # use duration metadata
        bench.add_run(perf.Run([0.1], metadata={'duration': 1.0}))
        bench.add_run(perf.Run([0.1], metadata={'duration': 2.0}))
        self.assertEqual(bench.get_total_duration(), 3.0)

        # run without duration metadata
        bench.add_run(perf.Run([5.0]))
        self.assertEqual(bench.get_total_duration(), 8.0)

    def test_get_dates(self):
        bench = perf.Benchmark()
        self.assertEqual(bench.get_dates(), ())

        run = perf.Run([1.0], metadata={'date': '2016-07-20T14:06:00', 'duration': 60.0},
                       collect_metadata=False)
        bench.add_run(run)
        self.assertEqual(bench.get_dates(),
                         (datetime.datetime(2016, 7, 20, 14, 6, 0),
                          datetime.datetime(2016, 7, 20, 14, 7, 0)))

        run = perf.Run([1.0], metadata={'date': '2016-07-20T14:10:00', 'duration': 60.0},
                       collect_metadata=False)
        bench.add_run(run)
        self.assertEqual(bench.get_dates(),
                         (datetime.datetime(2016, 7, 20, 14, 6, 0),
                          datetime.datetime(2016, 7, 20, 14, 11, 0)))

    def test_extract_metadata(self):
        warmups = ((1, 5.0),)
        bench = perf.Benchmark()
        bench.add_run(perf.Run((1.0,), warmups=warmups,
                               metadata={'name': 'bench', 'mem_usage': 5},
                               collect_metadata=False))
        bench.add_run(perf.Run((2.0,), warmups=warmups,
                               metadata={'name': 'bench', 'mem_usage': 13},
                               collect_metadata=False))

        bench._extract_metadata('mem_usage')
        self.assertEqual(bench.get_samples(), (5, 13))
        for run in bench.get_runs():
            self.assertEqual(run.warmups, ())

    def test_remove_all_metadata(self):
        bench = perf.Benchmark()
        bench.add_run(perf.Run((1.0,),
                               metadata={'name': 'bench', 'os': 'win', 'unit': 'byte'},
                               collect_metadata=False))
        self.assertEqual(self.get_metadata(bench),
                         {'name': 'bench', 'os': 'win', 'unit': 'byte'})

        bench._remove_all_metadata()
        self.assertEqual(self.get_metadata(bench),
                         {'name': 'bench', 'unit': 'byte'})

    def test_update_metadata(self):
        bench = perf.Benchmark()
        for sample in (1.0, 2.0, 3.0):
            bench.add_run(perf.Run((sample,),
                                   metadata={'name': 'bench'},
                                   collect_metadata=False))
        self.assertEqual(self.get_metadata(bench),
                         {'name': 'bench'})

        bench.update_metadata({'os': 'linux'})
        self.assertEqual(self.get_metadata(bench),
                         {'os': 'linux', 'name': 'bench'})

    def test_update_metadata_no_run(self):
        bench = perf.Benchmark()
        # error: need at least 1 run
        with self.assertRaises(ValueError):
            bench.update_metadata({'os': 'linux'})

    def test_update_metadata_inner_loops(self):
        bench = perf.Benchmark()
        bench.add_run(perf.Run((1.0,),
                               metadata={'inner_loops': 5},
                               collect_metadata=False))
        with self.assertRaises(ValueError):
            bench.update_metadata({'inner_loops': 8})

    def test_calibration(self):
        bench = perf.Benchmark()
        bench.add_run(perf.Run([], warmups=[(100, 1.0)],
                               metadata={'loops': 100},
                               collect_metadata=False))
        self.assertEqual(str(bench), 'Calibration: 100 loops')
        self.assertEqual(bench.format(), '<calibration: 100 loops>')
        self.assertRaises(ValueError, bench.median)


class TestBenchmarkSuite(unittest.TestCase):
    def benchmark(self, name):
        bench = perf.Benchmark()
        bench.add_run(perf.Run([1.0, 1.5, 2.0], metadata={'name': name}))
        return bench

    def test_suite(self):
        suite = perf.BenchmarkSuite()
        telco = self.benchmark('telco')
        suite.add_benchmark(telco)
        go = self.benchmark('go')
        suite.add_benchmark(go)

        self.assertIsNone(suite.filename)
        self.assertEqual(len(suite), 2)
        self.assertEqual(suite.get_benchmarks(), [go, telco])
        self.assertEqual(suite.get_benchmark('go'), go)
        with self.assertRaises(KeyError):
            suite.get_benchmark('non_existent')

    def test_json(self):
        suite = perf.BenchmarkSuite()
        suite.add_benchmark(self.benchmark('telco'))
        suite.add_benchmark(self.benchmark('go'))

        with tests.temporary_file() as filename:
            suite.dump(filename)
            suite = perf.BenchmarkSuite.load(filename)

        self.assertEqual(suite.filename, filename)

        benchmarks = suite.get_benchmarks()
        self.assertEqual(len(benchmarks), 2)
        self.assertEqual(benchmarks[0].get_name(), 'go')
        self.assertEqual(benchmarks[1].get_name(), 'telco')

    def test_add_runs(self):
        # bench 1
        samples = (1.0, 2.0, 3.0)
        bench = perf.Benchmark()
        bench.add_run(perf.Run(samples, metadata={'name': "bench"}))
        suite = perf.BenchmarkSuite()
        suite.add_benchmark(bench)

        # bench 2
        samples2 = (4.0, 5.0, 6.0)
        bench2 = perf.Benchmark()
        bench2.add_run(perf.Run(samples2, metadata={'name': "bench"}))
        suite.add_runs(bench2)

        bench = suite.get_benchmark('bench')
        self.assertEqual(bench.get_samples(), samples + samples2)

    def test_get_total_duration(self):
        suite = perf.BenchmarkSuite()

        bench = perf.Benchmark()
        bench.add_run(perf.Run([1.0]))
        suite.add_benchmark(bench)

        bench = perf.Benchmark()
        bench.add_run(perf.Run([2.0]))
        suite.add_benchmark(bench)

        self.assertEqual(suite.get_total_duration(), 3.0)

    def test_get_dates(self):
        suite = perf.BenchmarkSuite()
        self.assertEqual(suite.get_dates(), ())

        bench = perf.Benchmark()
        run = perf.Run([1.0], metadata={'date': '2016-07-20T14:06:00', 'duration': 60.0},
                       collect_metadata=False)
        bench.add_run(run)
        suite.add_benchmark(bench)
        self.assertEqual(suite.get_dates(),
                         (datetime.datetime(2016, 7, 20, 14, 6, 0),
                          datetime.datetime(2016, 7, 20, 14, 7, 0)))

        bench = perf.Benchmark()
        run = perf.Run([1.0], metadata={'date': '2016-07-20T14:10:00', 'duration': 60.0},
                       collect_metadata=False)
        bench.add_run(run)
        suite.add_benchmark(bench)
        self.assertEqual(suite.get_dates(),
                         (datetime.datetime(2016, 7, 20, 14, 6, 0),
                          datetime.datetime(2016, 7, 20, 14, 11, 0)))

    def get_metadata(self, suite):
        metadata = suite.get_metadata()
        result = {}
        for name, obj in metadata.items():
            self.assertEqual(obj.name, name)
            result[obj.name] = obj.value
        return result

    def test_get_metadata(self):
        suite = perf.BenchmarkSuite()

        for name in ('a', 'b'):
            bench = perf.Benchmark()
            run = perf.Run([1.0],
                           metadata={'name': name, 'os': 'linux'},
                           collect_metadata=False)
            bench.add_run(run)
            suite.add_benchmark(bench)

        self.assertEqual(self.get_metadata(suite),
                         {'os': 'linux'})


if __name__ == "__main__":
    unittest.main()
