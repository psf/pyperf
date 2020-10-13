import datetime
import io
import time
import unittest
from unittest import mock

import pyperf
from pyperf._formatter import (format_filesize, format_seconds, format_timedelta,
                               format_timedeltas, format_number)
from pyperf import _cpu_utils as cpu_utils
from pyperf import _utils as utils


class TestClocks(unittest.TestCase):
    def test_perf_counter(self):
        self.assertIs(pyperf.perf_counter, time.perf_counter)


class TestStatistics(unittest.TestCase):
    def test_is_significant(self):
        # There's no particular significance to these values.
        DATA1 = [89.2, 78.2, 89.3, 88.3, 87.3, 90.1, 95.2, 94.3, 78.3, 89.3]
        DATA2 = [79.3, 78.3, 85.3, 79.3, 88.9, 91.2, 87.2, 89.2, 93.3, 79.9]

        # not significant
        significant, tscore = utils.is_significant(DATA1, DATA2)
        self.assertFalse(significant)
        self.assertAlmostEqual(tscore, 1.0947229724603977, places=4)

        significant, tscore2 = utils.is_significant(DATA2, DATA1)
        self.assertFalse(significant)
        self.assertEqual(tscore2, -tscore)

        # significant
        inflated = [x * 10 for x in DATA1]
        significant, tscore = utils.is_significant(inflated, DATA1)
        self.assertTrue(significant)
        self.assertAlmostEqual(tscore, 43.76839453227327, places=4)

        significant, tscore2 = utils.is_significant(DATA1, inflated)
        self.assertTrue(significant)
        self.assertEqual(tscore2, -tscore)

    def test_is_significant_FIXME(self):
        # FIXME: _TScore() division by zero: error=0
        # n = 100
        # values1 = (1.0,) * n
        # values2 = (2.0,) * n
        # self.assertEqual(utils.is_significant(values1, values2),
        #                  (True, -141.4213562373095))

        # FIXME: same error
        # # same values
        # values = (1.0,) * 50
        # self.assertEqual(utils.is_significant(values, values),
        #                  (True, -141.4213562373095))
        pass

    def test_median_abs_dev(self):
        self.assertEqual(utils.median_abs_dev(range(97)), 24.0)
        self.assertEqual(utils.median_abs_dev((1, 1, 2, 2, 4, 6, 9)), 1.0)

    def test_percentile(self):
        # randomized range(10)
        values = [4, 6, 9, 7, 5, 8, 3, 0, 1, 2]
        self.assertEqual(utils.percentile(values, 0.00), 0)
        self.assertEqual(utils.percentile(values, 0.25), 2.25)
        self.assertEqual(utils.percentile(values, 0.50), 4.5)
        self.assertEqual(utils.percentile(values, 0.75), 6.75)
        self.assertEqual(utils.percentile(values, 1.00), 9)

    def test_geometric_mean(self):
        self.assertEqual(utils.geometric_mean([1.0]), 1.0)
        self.assertAlmostEqual(utils.geometric_mean([54, 24, 36]), 36.0)


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
        self.assertEqual(utils.get_python_names('/usr/bin/python3.6',
                                                '/usr/bin/python3.8'),
                         ('python3.6', 'python3.8'))

        self.assertEqual(utils.get_python_names('/bin/python3.6',
                                                '/usr/bin/python3.6'),
                         ('/bin/python3.6', '/usr/bin/python3.6'))


class CPUToolsTests(unittest.TestCase):
    def test_parse_cpu_list(self):
        parse_cpu_list = cpu_utils.parse_cpu_list

        self.assertIsNone(parse_cpu_list(''))
        self.assertIsNone(parse_cpu_list('\x00'))
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
        def check_get(line):
            def mock_open(*args, **kw):
                return io.StringIO(line)

            with mock.patch('pyperf._utils.open', create=True, side_effect=mock_open):
                return cpu_utils.get_isolated_cpus()

        # no isolated CPU
        self.assertIsNone(check_get(''))

        # isolated CPUs
        self.assertEqual(check_get('1-2'), [1, 2])

        # /sys/devices/system/cpu/isolated doesn't exist (ex: Windows)
        with mock.patch('builtins.open', side_effect=IOError):
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


if __name__ == "__main__":
    unittest.main()
