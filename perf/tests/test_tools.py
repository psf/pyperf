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

    def test_mean(self):
        self.assertEqual(perf.mean([1.0, 1.5, 2.0]), 1.5)


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
        self.assertEqual(perf._format_run_result([1.5], False),
                         "1.50 sec")
        self.assertEqual(perf._format_run_result([1.5], True),
                         "1.50 sec (min: 1.50 sec, max: 1.50 sec)")

        # multiple samples with std dev
        self.assertEqual(perf._format_run_result([1.0, 1.5, 2.0], False),
                         "1.50 sec +- 0.50 sec")
        self.assertEqual(perf._format_run_result([1.0, 1.5, 2.0], True),
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


class TestResult(unittest.TestCase):
    def test_run_result(self):
        run = perf.RunResult([1.0, 1.5, 2.0], 1000)
        self.assertEqual(run.values, [1.0, 1.5, 2.0])
        self.assertEqual(run.loops, 1000)
        self.assertEqual(str(run), '1.50 sec +- 0.50 sec')

    def test_results(self):
        runs = [perf.RunResult([1.0], loops=100),
                perf.RunResult([1.5], loops=100),
                perf.RunResult([2.0], loops=100)]
        results = perf.Results(runs, "name", {"key": "value"})
        self.assertEqual(results.runs, runs)
        self.assertEqual(results.name, "name")
        self.assertEqual(results.metadata, {"key": "value"})
        self.assertEqual(str(results),
                         'name: 3 runs x 1 sample x 100 loops: '
                         '1.50 sec +- 0.50 sec')


class MiscTests(unittest.TestCase):
    def test_version(self):
        import setup
        self.assertEqual(perf.__version__, setup.VERSION)


if __name__ == "__main__":
    unittest.main()
