import unittest

import perf


class TestClocks(unittest.TestCase):
    def test_perf_counter(self):
        t1 = perf.perf_counter()
        t2 = perf.perf_counter()
        self.assertGreaterEqual(t2, t1)

    def test_monotonic_clock(self):
        t1 = perf.monotonic_clock()
        t2 = perf.monotonic_clock()
        self.assertGreaterEqual(t2, t1)


class TestStatistics(unittest.TestCase):
    def test_is_significant(self):
        # not significant
        samples1 = (1.0, 1.5, 2.0)
        samples2 = (1.5, 2.0, 2.5)
        self.assertEqual(perf.is_significant(samples1, samples2),
                         (False, -1.224744871391589))

        # significant
        n = 100
        samples1 = (1.0,) * n + (1.5,)
        samples2 = (2.0,) * n + (1.5,)
        self.assertEqual(perf.is_significant(samples1, samples2),
                         (True, -141.4213562373095))

        # FIXME: _TScore() division by zero: error=0
        # n = 100
        # samples1 = (1.0,) * n
        # samples2 = (2.0,) * n
        # self.assertEqual(perf.is_significant(samples1, samples2),
        #                  (True, -141.4213562373095))

        # FIXME: same error
        # # same samples
        # samples = (1.0,) * 50
        # self.assertEqual(perf.is_significant(samples, samples),
        #                  (True, -141.4213562373095))


class TestTools(unittest.TestCase):
    def test_timedelta(self):
        def fmt_delta(seconds):
            return perf._format_timedelta(seconds)

        self.assertEqual(fmt_delta(555222), "555222 sec")

        self.assertEqual(fmt_delta(1e0),  "1.00 sec")
        self.assertEqual(fmt_delta(1e-3), "1.00 ms")
        self.assertEqual(fmt_delta(1e-6), "1.00 us")
        self.assertEqual(fmt_delta(1e-9), "1.00 ns")

        self.assertEqual(fmt_delta(316e-3), "316 ms")
        self.assertEqual(fmt_delta(316e-4), "31.6 ms")
        self.assertEqual(fmt_delta(316e-5), "3.16 ms")

        self.assertEqual(fmt_delta(1e-10), "0.10 ns")

        self.assertEqual(fmt_delta(-2), "-2.00 sec")

    def test_timedelta_stdev(self):
        def fmt_stdev(seconds, stdev):
            return "%s +- %s" % perf._format_timedeltas((seconds, stdev))

        self.assertEqual(fmt_stdev(58123, 192), "58123 sec +- 192 sec")
        self.assertEqual(fmt_stdev(100e-3, 0), "100 ms +- 0 ms")
        self.assertEqual(fmt_stdev(102e-3, 3e-3), "102 ms +- 3 ms")

    def test_format_number(self):
        # plural
        self.assertEqual(perf._format_number(0, 'unit'), '0 unit')
        self.assertEqual(perf._format_number(1, 'unit'), '1 unit')
        self.assertEqual(perf._format_number(2, 'unit'), '2 units')

        # powers of 10
        self.assertEqual(perf._format_number(10 ** 3, 'unit'),
                         '1000 units')
        self.assertEqual(perf._format_number(10 ** 4, 'unit'),
                         '10^4 units')
        self.assertEqual(perf._format_number(10 ** 4 + 1, 'unit'),
                         '10001 units')

    def test_format_cpu_list(self):
        self.assertEqual(perf._format_cpu_list([0]),
                         '0')
        self.assertEqual(perf._format_cpu_list([0, 1, 5, 6]),
                         '0-1,5-6')
        self.assertEqual(perf._format_cpu_list([1, 3, 7]),
                         '1,3,7')


class TestResult(unittest.TestCase):
    def check_runs(self, bench, samples, warmup):
        runs = bench.get_runs()
        self.assertEqual(len(runs), len(samples))
        for sample, run in zip(samples, runs):
            self.assertEqual(run, (warmup, sample))

    def test_add_run_nsample(self):
        bench = perf.Benchmark(warmups=1)
        bench.add_run([1.5, 1.0])
        self.assertRaises(ValueError, bench.add_run, [1.5, 1.0, 2.0])
        bench.add_run([1.5, 1.0])

    def test_add_run_warmups(self):
        bench = perf.Benchmark(warmups=1)
        # need at least 2 samples
        self.assertRaises(ValueError, bench.add_run, [])
        self.assertRaises(ValueError, bench.add_run, [1.0])
        bench.add_run([1.5, 1.0])

    def test_benchmark_warmups_property(self):
        bench = perf.Benchmark()
        self.assertEqual(bench.warmups, 1)

        with self.assertRaises(ValueError):
            bench.warmups = -1
        with self.assertRaises(ValueError):
            bench.warmups = "hello"

        bench.warmups = 0
        self.assertEqual(bench.warmups, 0)

        with self.assertRaises(ValueError):
            perf.Benchmark(warmups=-1)
        with self.assertRaises(ValueError):
            perf.Benchmark(warmups="hello")

    def test_benchmark_loops_property(self):
        bench = perf.Benchmark()
        self.assertIsNone(bench.loops)
        with self.assertRaises(ValueError):
            bench.loops = -1
        with self.assertRaises(ValueError):
            perf.Benchmark(loops=-1)

    def test_benchmark_inner_loops_property(self):
        bench = perf.Benchmark()
        self.assertIsNone(bench.inner_loops)
        with self.assertRaises(ValueError):
            bench.inner_loops = -1
        with self.assertRaises(ValueError):
            perf.Benchmark(inner_loops=-1)

    def test_benchmark(self):
        samples = (1.0, 1.5, 2.0)
        raw_samples = tuple(sample * 3 * 20 for sample in samples)
        bench = perf.Benchmark(name="name", warmups=1, loops=20, inner_loops=3)
        for raw_sample in raw_samples:
            bench.add_run([3.0, raw_sample])
        bench.metadata['key'] = 'value'

        self.assertEqual(bench.get_samples(), samples)
        self.assertEqual(bench._get_raw_samples(), list(raw_samples))
        self.assertEqual(bench.get_nrun(), 3)

        runs = bench.get_runs()
        self.assertIsInstance(runs, list)
        self.assertEqual(len(runs), 3)
        for run_samples in runs:
            self.assertIsInstance(run_samples, tuple)
            self.assertEqual(len(run_samples), 2)

        self.check_runs(bench, raw_samples, 3.0)

        self.assertEqual(bench.name, "name")
        self.assertEqual(bench.loops, 20)
        self.assertEqual(bench.inner_loops, 3)
        self.assertEqual(bench.metadata, {'key': 'value'})
        self.assertEqual(str(bench),
                         'name: 1.50 sec +- 0.50 sec')
        self.assertEqual(bench.format(0),
                         '1.50 sec +- 0.50 sec')
        self.assertEqual(bench.format(1),
                         '1.50 sec +- 0.50 sec '
                         '(3 runs x 1 sample x 20 loops; 1 warmup; 3 inner-loops)')

    def test_benchmark_json(self):
        samples = (1.0, 1.5, 2.0)
        bench = perf.Benchmark(name="name", warmups=1,
                               loops=100, inner_loops=20,
                               metadata={'key': 'value'})
        for sample in samples:
            bench.add_run([3.0, sample])

        bench = perf.Benchmark.json_load(bench.json())
        self.assertEqual(bench.name, "name")
        self.assertEqual(bench.metadata, {'key': 'value'})
        self.assertEqual(bench.loops, 100)
        self.assertEqual(bench.inner_loops, 20)

        self.check_runs(bench, samples, 3.0)



class MiscTests(unittest.TestCase):
    def test_version(self):
        import setup
        self.assertEqual(perf.__version__, setup.VERSION)


if __name__ == "__main__":
    unittest.main()
