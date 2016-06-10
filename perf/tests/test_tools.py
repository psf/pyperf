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
    def test_stdev(self):
        self.assertEqual(perf.stdev([1.0, 1.5, 2.0]), 0.5)
        self.assertEqual(perf.stdev([1.5, 2.5, 2.5, 2.75, 3.25, 4.75]),
                         1.0810874155219827)

    def test_mean(self):
        self.assertEqual(perf.mean([1.0, 1.5, 2.0]), 1.5)

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

    def test_timedelta_stdev(self):
        def fmt_stdev(seconds, stdev):
            return "%s +- %s" % perf._format_timedeltas((seconds, stdev))

        self.assertEqual(fmt_stdev(58123, 192), "58123 sec +- 192 sec")
        self.assertEqual(fmt_stdev(100e-3, 0), "100 ms +- 0 ms")
        self.assertEqual(fmt_stdev(102e-3, 3e-3), "102 ms +- 3 ms")

    def test_format_run_result(self):
        # 1 sample
        self.assertEqual(perf._format_run_result([1.5], 0),
                         "1.50 sec")
        self.assertEqual(perf._format_run_result([1.5], 1),
                         "1.50 sec")
        self.assertEqual(perf._format_run_result([1.5], 2),
                         "1.50 sec (min: 1.50 sec, max: 1.50 sec)")

        # multiple samples with std dev
        self.assertEqual(perf._format_run_result([1.0, 1.5, 2.0], 0),
                         "1.50 sec +- 0.50 sec")
        self.assertEqual(perf._format_run_result([1.0, 1.5, 2.0], 1),
                         "1.50 sec +- 0.50 sec")
        self.assertEqual(perf._format_run_result([1.0, 1.5, 2.0], 2),
                         "1.50 sec +- 0.50 sec (min: 1.00 sec, max: 2.00 sec)")

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
    def test_run_result(self):
        run = perf.RunResult(samples=[1.0, 1.5, 2.0])
        self.assertEqual(run.samples, [1.0, 1.5, 2.0])
        self.assertEqual(str(run), '1.50 sec +- 0.50 sec')

    def test_run_result_json(self):
        run = perf.RunResult(samples=[1.0, 1.5, 2.0], warmups=[5.0], loops=10)
        run.metadata = {'key': 'value'}

        run = perf.RunResult.json_load(run.json())
        self.assertEqual(run.samples, [1.0, 1.5, 2.0])
        self.assertEqual(run.warmups, [5.0])
        self.assertEqual(run.metadata, {'key': 'value'})
        self.assertEqual(run.loops, 10)

    def test_results(self):
        runs = []
        for sample in (1.0, 1.5, 2.0):
            run = perf.RunResult([sample])
            run.metadata['key'] = 'value'
            runs.append(run)

        results = perf.Benchmark(runs, "name")
        self.assertEqual(results.runs, runs)
        self.assertEqual(results.name, "name")
        self.assertEqual(results.get_metadata(), {'key': 'value'})
        self.assertEqual(str(results),
                         'name: 1.50 sec +- 0.50 sec')
        self.assertEqual(results.format(0),
                         '1.50 sec +- 0.50 sec')
        self.assertEqual(results.format(1),
                         '1.50 sec +- 0.50 sec '
                         '(3 runs x 1 sample)')


class MiscTests(unittest.TestCase):
    def test_version(self):
        import setup
        self.assertEqual(perf.__version__, setup.VERSION)


if __name__ == "__main__":
    unittest.main()
