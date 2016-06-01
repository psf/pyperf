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


class TestResult(unittest.TestCase):
    def test_result(self):
        result = perf.Result([1.0, 1.5, 2.0], "name", {"key": "value"})
        self.assertEqual(result.values, [1.0, 1.5, 2.0])
        self.assertEqual(result.name, "name")
        self.assertEqual(result.metadata, {"key": "value"})
        self.assertEqual(result.mean(), 1.5)
        self.assertEqual(result.stdev(), 0.5)
        self.assertEqual(str(result), 'name: 1.5 +- 0.5')


class TestStatistics(unittest.TestCase):
    def test_stdev(self):
        self.assertEqual(perf.stdev([1.0, 1.5, 2.0]), 0.5)

    def test_mean(self):
        self.assertEqual(perf.mean([1.0, 1.5, 2.0]), 1.5)


class MiscTests(unittest.TestCase):
    def test_version(self):
        import setup
        self.assertEqual(perf.__version__, setup.VERSION)


if __name__ == "__main__":
    unittest.main()
