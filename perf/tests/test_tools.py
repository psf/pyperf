import datetime
import os.path
import sys

import six

import perf
from perf._formatter import (format_filesize, format_seconds, format_timedelta,
                             format_timedeltas, format_number)
from perf import _cpu_utils as cpu_utils
from perf import _utils as utils
from perf import tests
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

    def test_median_abs_dev(self):
        self.assertEqual(utils.median_abs_dev(range(97)), 24.0)
        self.assertEqual(utils.median_abs_dev((1, 1, 2, 2, 4, 6, 9)), 1.0)


class TestUtils(unittest.TestCase):
    def test_parse_iso8601(self):
        # Default format using 'T' separator
        self.assertEqual(utils.parse_iso8601('2016-07-20T14:06:07'),
                         datetime.datetime(2016, 7, 20, 14, 6, 7))
        # Microseconds
        self.assertEqual(utils.parse_iso8601('2016-07-20T14:06:07.608319'),
                         datetime.datetime(2016, 7, 20, 14, 6, 7, 608319))
        # Space separator
        self.assertEqual(utils.parse_iso8601('2016-07-20 14:06:07'),
                         datetime.datetime(2016, 7, 20, 14, 6, 7))

    def test_format_seconds(self):
        self.assertEqual(format_seconds(0),
                         "0 sec")
        self.assertEqual(format_seconds(316e-4),
                         "31.6 ms")
        self.assertEqual(format_seconds(15.9),
                         "15.9 sec")
        self.assertEqual(format_seconds(3 * 60 + 15.9),
                         "3 min 15.9 sec")
        self.assertEqual(format_seconds(404683.5876653),
                         "4 day 16 hour 24 min")

    def test_format_timedelta(self):
        fmt_delta = format_timedelta

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
            return "%s +- %s" % format_timedeltas((seconds, stdev))

        self.assertEqual(fmt_stdev(58123, 192), "58123 sec +- 192 sec")
        self.assertEqual(fmt_stdev(100e-3, 0), "100 ms +- 0 ms")
        self.assertEqual(fmt_stdev(102e-3, 3e-3), "102 ms +- 3 ms")

    def test_format_number(self):
        # plural
        self.assertEqual(format_number(0, 'unit'), '0 units')
        self.assertEqual(format_number(1, 'unit'), '1 unit')
        self.assertEqual(format_number(2, 'unit'), '2 units')
        self.assertEqual(format_number(123, 'unit'), '123 units')

        # powers of 10
        self.assertEqual(format_number(10 ** 3, 'unit'),
                         '1000 units')
        self.assertEqual(format_number(10 ** 4, 'unit'),
                         '10^4 units')
        self.assertEqual(format_number(10 ** 4 + 1, 'unit'),
                         '10001 units')
        self.assertEqual(format_number(33 * 10 ** 4, 'unit'),
                         '330000 units')

        # powers of 10
        self.assertEqual(format_number(2 ** 10, 'unit'),
                         '1024 units')
        self.assertEqual(format_number(2 ** 15, 'unit'),
                         '2^15 units')
        self.assertEqual(format_number(2 ** 15),
                         '2^15')
        self.assertEqual(format_number(2 ** 10 + 1, 'unit'),
                         '1025 units')

    def test_format_filesize(self):
        self.assertEqual(format_filesize(0),
                         '0 bytes')
        self.assertEqual(format_filesize(1),
                         '1 byte')
        self.assertEqual(format_filesize(10 * 1024),
                         '10.0 kB')
        self.assertEqual(format_filesize(12.4 * 1024 * 1024),
                         '12.4 MB')

    def test_get_python_names(self):
        self.assertEqual(utils.get_python_names('/usr/bin/python2.7',
                                                '/usr/bin/python3.5'),
                         ('python2.7', 'python3.5'))

        self.assertEqual(utils.get_python_names('/bin/python2.7',
                                                '/usr/bin/python2.7'),
                         ('/bin/python2.7', '/usr/bin/python2.7'))


class CPUToolsTests(unittest.TestCase):
    def test_parse_cpu_list(self):
        parse_cpu_list = cpu_utils.parse_cpu_list

        self.assertIsNone(parse_cpu_list(''))
        self.assertEqual(parse_cpu_list('0'),
                         [0])
        self.assertEqual(parse_cpu_list('0-1,5-6'),
                         [0, 1, 5, 6])
        self.assertEqual(parse_cpu_list('1,3,7'),
                         [1, 3, 7])

        # tolerate spaces
        self.assertEqual(parse_cpu_list(' 1 , 2 '),
                         [1, 2])

        # errors
        self.assertRaises(ValueError, parse_cpu_list, 'x')
        self.assertRaises(ValueError, parse_cpu_list, '1,')

    def test_format_cpu_list(self):
        self.assertEqual(cpu_utils.format_cpu_list([0]),
                         '0')
        self.assertEqual(cpu_utils.format_cpu_list([0, 1, 5, 6]),
                         '0-1,5-6')
        self.assertEqual(cpu_utils.format_cpu_list([1, 3, 7]),
                         '1,3,7')

    def test_get_isolated_cpus(self):
        BUILTIN_OPEN = 'builtins.open' if six.PY3 else '__builtin__.open'

        def check_get(line):
            with mock.patch(BUILTIN_OPEN) as mock_open:
                mock_file = mock_open.return_value
                mock_file.readline.return_value = line
                return cpu_utils.get_isolated_cpus()

        # no isolated CPU
        self.assertIsNone(check_get(''))

        # isolated CPUs
        self.assertEqual(check_get('1-2'), [1, 2])

        # /sys/devices/system/cpu/isolated doesn't exist (ex: Windows)
        with mock.patch(BUILTIN_OPEN, side_effect=IOError):
            self.assertIsNone(cpu_utils.get_isolated_cpus())

    def test_parse_cpu_mask(self):
        parse_cpu_mask = cpu_utils.parse_cpu_mask
        self.assertEqual(parse_cpu_mask('f0'),
                         0xf0)
        self.assertEqual(parse_cpu_mask('fedcba00,12345678'),
                         0xfedcba0012345678)
        self.assertEqual(parse_cpu_mask('ffffffff,ffffffff,ffffffff,ffffffff'),
                         2**128 - 1)

    def test_format_cpu_mask(self):
        format_cpu_mask = cpu_utils.format_cpu_mask
        self.assertEqual(format_cpu_mask(0xf0),
                         '000000f0')
        self.assertEqual(format_cpu_mask(0xfedcba0012345678),
                         'fedcba00,12345678')

    def test_format_cpus_as_mask(self):
        format_cpus_as_mask = cpu_utils.format_cpus_as_mask
        self.assertEqual(format_cpus_as_mask({4, 5, 6, 7}),
                         '000000f0')


class MiscTests(unittest.TestCase):
    def test_format_metadata(self):
        self.assertEqual(perf.format_metadata('loops', 2 ** 24),
                         '2^24')

    def test_python_implementation(self):
        name = perf.python_implementation()
        self.assertIsInstance(name, str)
        self.assertRegex(name, '^[a-z]+$')

    def test_python_has_jit(self):
        jit = perf.python_has_jit()
        self.assertIsInstance(jit, bool)

    @unittest.skipUnless(hasattr(os, 'symlink'), 'need os.symlink')
    def test_abs_executable(self):
        with tests.temporary_file() as tmpname:
            tmpname = os.path.realpath(tmpname)

            try:
                os.symlink(sys.executable, tmpname)
            except (OSError, NotImplementedError):
                self.skipTest("os.symlink() failed")

            self.assertEqual(utils.abs_executable(tmpname),
                             tmpname)

    def test_parse_run_list(self):
        parse_run_list = utils.parse_run_list

        with self.assertRaises(ValueError):
            parse_run_list('')
        with self.assertRaises(ValueError):
            parse_run_list('0')
        self.assertEqual(parse_run_list('1'),
                         [0])
        self.assertEqual(parse_run_list('1-2,5-6'),
                         [0, 1, 4, 5])
        self.assertEqual(parse_run_list('1,3,7'),
                         [0, 2, 6])

        # tolerate spaces
        self.assertEqual(parse_run_list(' 1 , 2 '),
                         [0, 1])

        # errors
        self.assertRaises(ValueError, parse_run_list, 'x')
        self.assertRaises(ValueError, parse_run_list, '1,')

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
