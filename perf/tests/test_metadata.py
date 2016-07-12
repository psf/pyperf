import contextlib
import os.path
import sys
import textwrap

import perf.metadata
from perf.tests import mock
from perf.tests import unittest


MANDATORY_RUN_METADATA = ['date']

MANDATORY_METADATA = [
    'python_implementation', 'python_version',
    'platform']
if sys.platform.startswith('linux'):
    MANDATORY_METADATA.extend(('aslr', 'cpu_model_name'))


def check_all_metadata(testcase, metadata, mandatory=MANDATORY_METADATA):
    for key in mandatory:
        testcase.assertIn(key, metadata)

    for key, value in metadata.items():
        # test key
        testcase.assertIsInstance(key, str)
        testcase.assertRegex(key, '^[a-z][a-z0-9_]+$')

        # test value
        testcase.assertIsInstance(value, str)
        testcase.assertNotEqual(value, '')
        testcase.assertEqual(value.strip(), value)
        testcase.assertNotIn('\n', value)


class TestMetadata(unittest.TestCase):
    def test_run_metadata(self):
        metadata = {}
        perf.metadata.collect_run_metadata(metadata)
        check_all_metadata(self, metadata, MANDATORY_RUN_METADATA)

    def test_benchmark_metadata(self):
        metadata = {}
        perf.metadata.collect_benchmark_metadata(metadata)
        check_all_metadata(self, metadata)

    def check_metadata(self, key, value):
        metadata = {}
        perf.metadata.collect_benchmark_metadata(metadata)
        self.assertEqual(metadata[key], value)

    def check_missing_metadata(self, key):
        metadata = {}
        perf.metadata.collect_benchmark_metadata(metadata)
        self.assertNotIn(key, metadata)

    def test_cpu_affinity_isolated(self):
        with mock.patch('perf.metadata._get_logical_cpu_count', return_value=4):
            with mock.patch('perf.metadata._get_cpu_affinity', return_value={2, 3}):
                with mock.patch('perf._get_isolated_cpus', return_value={1, 2, 3}):
                    self.check_metadata('cpu_affinity', '2-3 (isolated)')

            with mock.patch('perf.metadata._get_cpu_affinity', return_value={0, 1, 2, 3}):
                self.check_missing_metadata('cpu_affinity')


class CpuFunctionsTests(unittest.TestCase):
    def test_cpu_frequencies(self):
        data = textwrap.dedent("""
            processor	: 0
            vendor_id	: GenuineIntel
            cpu family	: 6
            cpu MHz		: 1600.000
            power management:

            processor	: 1
            vendor_id	: GenuineIntel
            cpu MHz		: 2901.000
            clflush size	: 64
        """)
        with mock.patch('perf.metadata.open', mock.mock_open(read_data=data)):
            cpu_freq = perf.metadata._get_cpu_frequencies()
        self.assertEqual(cpu_freq, {})


if __name__ == "__main__":
    unittest.main()
