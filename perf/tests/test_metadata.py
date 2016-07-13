import sys
import textwrap

import six

import perf.metadata
from perf.tests import mock
from perf.tests import unittest


MANDATORY_METADATA = [
    'date',
    'python_implementation', 'python_version',
    'platform']
if sys.platform.startswith('linux'):
    MANDATORY_METADATA.extend(('aslr', 'cpu_model_name'))


class TestMetadata(unittest.TestCase):
    def test_collect_metadata(self):
        metadata = {}
        perf.metadata._collect_metadata(metadata)

        for key in MANDATORY_METADATA:
            self.assertIn(key, metadata)

        for key, value in metadata.items():
            # test key
            self.assertIsInstance(key, str)
            self.assertRegex(key, '^[a-z][a-z0-9_]+$')

            # test value
            self.assertIsInstance(value, str)
            self.assertNotEqual(value, '')
            self.assertEqual(value.strip(), value)
            self.assertNotIn('\n', value)

    def test_collect_cpu_metadata(self):
        freq = '123 MHz'
        cpus = range(4)
        # FIXME: use ExitStack
        with mock.patch('perf.metadata._get_logical_cpu_count',
                        return_value=4):
            with mock.patch('perf.metadata._get_cpu_frequencies',
                            return_value={cpu: freq for cpu in cpus}):
                with mock.patch('perf.metadata._get_cpu_temperatures',
                                return_value=None):
                    with mock.patch('perf.metadata._get_cpu_affinity',
                                    return_value={2, 3}):
                        with mock.patch('perf._get_isolated_cpus',
                                        return_value={1, 2, 3}):
                            metadata = {}
                            perf.metadata._collect_cpu_metadata(metadata)
                            # the main purpose of the whole test is this check
                            self.assertEqual(metadata['cpu_affinity'],
                                             '2-3 (isolated)')

                            self.assertEqual(metadata['cpu_freq'],
                                             '2-3:123 MHz')


                    with mock.patch('perf.metadata._get_cpu_affinity',
                                    return_value={0, 1, 2, 3}):
                        metadata = {}
                        perf.metadata._collect_cpu_metadata(metadata)
                        self.assertNotIn('cpu_affinity', metadata)


class CpuFunctionsTests(unittest.TestCase):
    def test_cpu_frequencies(self):
        cpuinfo = textwrap.dedent("""
            processor	: 0
            vendor_id	: GenuineIntel
            cpu family	: 6
            cpu MHz		: 1600.000
            power management:

            processor	: 1
            cpu MHz		: 2901.000

            processor	: 2
            vendor_id	: GenuineIntel
            cpu MHz		: 2901.000
            clflush size	: 64
        """)

        def mock_open(filename, *args, **kw):
            if filename == '/proc/cpuinfo':
                data = cpuinfo
            elif filename == '/sys/devices/system/cpu/cpu0/cpufreq/scaling_driver':
                data = 'DRIVER\n'
            elif filename == '/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor':
                data = 'GOVERNOR\n'
            elif filename.startswith('/sys/devices/system/cpu/cpu2'):
                raise IOError
            else:
                raise ValueError("unexpect open: %r" % filename)
            return six.StringIO(data)

        with mock.patch('perf.metadata.open', create=True, side_effect=mock_open):
            cpu_freq = perf.metadata._get_cpu_frequencies([0, 2])
        self.assertEqual(cpu_freq, {0: '1600 MHz (driver:DRIVER, governor:GOVERNOR)',
                                    2: '2901 MHz'})


if __name__ == "__main__":
    unittest.main()
