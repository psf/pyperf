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
        self.assertEqual(perf.format_timedelta(555222), "555222 sec")

        self.assertEqual(perf.format_timedelta(1e0),  "1.00 sec")
        self.assertEqual(perf.format_timedelta(1e-3), "1.00 ms")
        self.assertEqual(perf.format_timedelta(1e-6), "1.00 us")
        self.assertEqual(perf.format_timedelta(1e-9), "1.00 ns")

        self.assertEqual(perf.format_timedelta(316e-3), "316 ms")
        self.assertEqual(perf.format_timedelta(316e-4), "31.6 ms")
        self.assertEqual(perf.format_timedelta(316e-5), "3.16 ms")

        self.assertEqual(perf.format_timedelta(1e-10), "0.10 ns")

    def test_timedelta_stdev(self):
        self.assertEqual(perf.format_timedelta(58123, 192),
                         "58123 sec +- 192 sec")
        self.assertEqual(perf.format_timedelta(100e-3, 0),
                         "100 ms +- 0 ms")
        self.assertEqual(perf.format_timedelta(102e-3, 3e-3),
                         "102 ms +- 3 ms")


class TestResult(unittest.TestCase):
    def test_result(self):
        result = perf.Result([1.0, 1.5, 2.0], "name", {"key": "value"})
        self.assertEqual(result.values, [1.0, 1.5, 2.0])
        self.assertEqual(result.name, "name")
        self.assertEqual(result.metadata, {"key": "value"})
        self.assertEqual(result.mean(), 1.5)
        self.assertEqual(result.stdev(), 0.5)
        self.assertEqual(str(result), 'name: 1.5 +- 0.5')


class MiscTests(unittest.TestCase):
    def test_version(self):
        import setup
        self.assertEqual(perf.__version__, setup.VERSION)


if __name__ == "__main__":
    unittest.main()
