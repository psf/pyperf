import datetime
import os.path
import sys
import tempfile

import six

import perf
from perf.tests import mock
from perf.tests import unittest


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
        # There's no particular significance to these values.
        DATA1 = [89.2, 78.2, 89.3, 88.3, 87.3, 90.1, 95.2, 94.3, 78.3, 89.3]
        DATA2 = [79.3, 78.3, 85.3, 79.3, 88.9, 91.2, 87.2, 89.2, 93.3, 79.9]

        # not significant
        significant, tscore = perf.is_significant(DATA1, DATA2)
        self.assertFalse(significant)
        self.assertAlmostEqual(tscore, 1.0947229724603977, places=4)

        significant, tscore2 = perf.is_significant(DATA2, DATA1)
        self.assertFalse(significant)
        self.assertEqual(tscore2, -tscore)

        # significant
        inflated = [x * 10 for x in DATA1]
        significant, tscore = perf.is_significant(inflated, DATA1)
        self.assertTrue(significant)
        self.assertAlmostEqual(tscore, 43.76839453227327, places=4)

        significant, tscore2 = perf.is_significant(DATA1, inflated)
        self.assertTrue(significant)
        self.assertEqual(tscore2, -tscore)

    def test_is_significant_FIXME(self):
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
        pass


class TestTools(unittest.TestCase):
    def test_parse_iso8601(self):
        self.assertEqual(perf._parse_iso8601('2016-07-20T14:06:07'),
                         datetime.datetime(2016, 7, 20, 14, 6, 7))
        self.assertEqual(perf._parse_iso8601('2016-07-20T14:06:07.608319'),
                         datetime.datetime(2016, 7, 20, 14, 6, 7, 608319))

    def test_timedelta(self):
        def fmt_delta(seconds):
            return perf._format_timedelta(seconds)

        self.assertEqual(fmt_delta(555222), "555222 sec")

        self.assertEqual(fmt_delta(1e0), "1.00 sec")
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
        self.assertEqual(perf._format_number(123, 'unit'), '123 units')

        # powers of 10
        self.assertEqual(perf._format_number(10 ** 3, 'unit'),
                         '1000 units')
        self.assertEqual(perf._format_number(10 ** 4, 'unit'),
                         '10^4 units')
        self.assertEqual(perf._format_number(10 ** 4 + 1, 'unit'),
                         '10001 units')
        self.assertEqual(perf._format_number(33 * 10 ** 4, 'unit'),
                         '330000 units')

        # powers of 10
        self.assertEqual(perf._format_number(2 ** 10, 'unit'),
                         '1024 units')
        self.assertEqual(perf._format_number(2 ** 15, 'unit'),
                         '2^15 units')
        self.assertEqual(perf._format_number(2 ** 15),
                         '2^15')
        self.assertEqual(perf._format_number(2 ** 10 + 1, 'unit'),
                         '1025 units')

    def test_format_filesize(self):
        self.assertEqual(perf._format_filesize(0),
                         '0 bytes')
        self.assertEqual(perf._format_filesize(1),
                         '1 byte')
        self.assertEqual(perf._format_filesize(10 * 1024),
                         '10.0 kB')
        self.assertEqual(perf._format_filesize(12.4 * 1024 * 1024),
                         '12.4 MB')


class CPUToolsTests(unittest.TestCase):
    def test_parse_cpu_list(self):
        self.assertIsNone(perf._parse_cpu_list(''))
        self.assertEqual(perf._parse_cpu_list('0'),
                         [0])
        self.assertEqual(perf._parse_cpu_list('0-1,5-6'),
                         [0, 1, 5, 6])
        self.assertEqual(perf._parse_cpu_list('1,3,7'),
                         [1, 3, 7])

        # tolerate spaces
        self.assertEqual(perf._parse_cpu_list(' 1 , 2 '),
                         [1, 2])

        # errors
        self.assertRaises(ValueError, perf._parse_cpu_list, 'x')
        self.assertRaises(ValueError, perf._parse_cpu_list, '1,')

    def test_format_cpu_list(self):
        self.assertEqual(perf._format_cpu_list([0]),
                         '0')
        self.assertEqual(perf._format_cpu_list([0, 1, 5, 6]),
                         '0-1,5-6')
        self.assertEqual(perf._format_cpu_list([1, 3, 7]),
                         '1,3,7')

    def test_get_isolated_cpus(self):
        BUILTIN_OPEN = 'builtins.open' if six.PY3 else '__builtin__.open'

        def check_get(line):
            with mock.patch(BUILTIN_OPEN) as mock_open:
                mock_file = mock_open.return_value
                mock_file.readline.return_value = line
                return perf._get_isolated_cpus()

        # no isolated CPU
        self.assertIsNone(check_get(''))

        # isolated CPUs
        self.assertEqual(check_get('1-2'), [1, 2])

        # /sys/devices/system/cpu/isolated doesn't exist (ex: Windows)
        with mock.patch(BUILTIN_OPEN, side_effect=OSError):
            self.assertIsNone(perf._get_isolated_cpus())


class MiscTests(unittest.TestCase):
    def test_python_implementation(self):
        name = perf.python_implementation()
        self.assertIsInstance(name, str)
        self.assertRegex(name, '^[a-z]+$')

    def test_python_has_jit(self):
        jit = perf.python_has_jit()
        self.assertIsInstance(jit, bool)

    def test_parse_run_list(self):
        with self.assertRaises(ValueError):
            perf._parse_run_list('')
        with self.assertRaises(ValueError):
            perf._parse_run_list('0')
        self.assertEqual(perf._parse_run_list('1'),
                         [0])
        self.assertEqual(perf._parse_run_list('1-2,5-6'),
                         [0, 1, 4, 5])
        self.assertEqual(perf._parse_run_list('1,3,7'),
                         [0, 2, 6])

        # tolerate spaces
        self.assertEqual(perf._parse_run_list(' 1 , 2 '),
                         [0, 1])

        # errors
        self.assertRaises(ValueError, perf._parse_run_list, 'x')
        self.assertRaises(ValueError, perf._parse_run_list, '1,')

    def test_setup_version(self):
        import setup
        self.assertEqual(perf.__version__, setup.VERSION)

    def test_doc_version(self):
        doc_path = os.path.join(os.path.dirname(__file__), '..', '..', 'doc')
        doc_path = os.path.realpath(doc_path)

        old_path = sys.path[:]
        try:
            sys.path.insert(0, doc_path)
            import conf
            self.assertEqual(perf.__version__, conf.version)
            self.assertEqual(perf.__version__, conf.release)
        finally:
            sys.path[:] = old_path


if __name__ == "__main__":
    unittest.main()
