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
        self.assertEqual(perf.stdev([1.5, 2.5, 2.5, 2.75, 3.25, 4.75]),
                         1.0810874155219827)

    def test_mean(self):
        self.assertEqual(perf.mean([1.0, 1.5, 2.0]),
                         1.5)


class MiscTests(unittest.TestCase):
    def test_version(self):
        import setup
        self.assertEqual(perf.__version__, setup.VERSION)


if __name__ == "__main__":
    unittest.main()
