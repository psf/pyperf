import sys

import perf.metadata
from perf.tests import mock
from perf.tests import unittest
try:
    import psutil
except ImportError:
    psutil = None


MANDATORY_METADATA = [
    'python_implementation', 'python_version',
    'platform']
if sys.platform.startswith('linux'):
    MANDATORY_METADATA.extend(('aslr', 'cpu_model_name'))


def check_all_metadata(testcase, metadata):
    for key in MANDATORY_METADATA:
        testcase.assertIn(key, metadata)

    for key, value in metadata.items():
        # test key
        testcase.assertIsInstance(key, str)
        testcase.assertRegex(key, '^[a-z][a-z_]+$')

        # test value
        testcase.assertIsInstance(value, str)
        testcase.assertNotEqual(value, '')
        testcase.assertEqual(value.strip(), value)
        testcase.assertNotIn('\n', value)


class TestMetadata(unittest.TestCase):
    def test_metadata(self):
        metadata = {}
        perf.metadata.collect_metadata(metadata)
        check_all_metadata(self, metadata)

    def test_cpu_affinity_getaffinity(self):
        # affinity=2/4 CPUs
        with mock.patch('os.sched_getaffinity',
                        return_value={2, 3}, create=True):
            with mock.patch('os.cpu_count', return_value=4, create=True):
                with mock.patch('perf._get_isolated_cpus', return_value=None):
                    metadata = {}
                    perf.metadata.collect_metadata(metadata)
        self.assertEqual(metadata['cpu_affinity'], '2-3')

        # affinity=all CPUs: ignore metadata
        with mock.patch('os.sched_getaffinity',
                        return_value={0, 1}, create=True):
            with mock.patch('os.cpu_count', return_value=2, create=True):
                with mock.patch('perf._get_isolated_cpus', return_value=None):
                    metadata = {}
                    perf.metadata.collect_metadata(metadata)
        self.assertNotIn('cpu_affinity', metadata)

    def test_cpu_affinity_isolated(self):
        with mock.patch('os.sched_getaffinity',
                        return_value={2, 3}, create=True):
            with mock.patch('os.cpu_count', return_value=4, create=True):
                with mock.patch('perf._get_isolated_cpus', return_value=[2, 3]):
                    metadata = {}
                    perf.metadata.collect_metadata(metadata)
        self.assertEqual(metadata['cpu_affinity'], '2-3 (isolated)')

    @unittest.skipIf(psutil is None, 'need psutil')
    def test_cpu_affinity_psutil(self):
        with mock.patch('perf.metadata.os') as mock_os:
            del mock_os.sched_getaffinity
            mock_os.cpu_count.return_value = 4

            with mock.patch('perf._get_isolated_cpus', return_value=None):
                with mock.patch('psutil.Process') as mock_process:
                    mock_affinity = mock_process.return_value.cpu_affinity

                    # affinity=2/4 CPUs
                    mock_affinity.return_value = [2, 3]
                    metadata = {}
                    perf.metadata.collect_metadata(metadata)
                    self.assertEqual(metadata['cpu_affinity'], '2-3')

                    # affinity=all CPUs: ignore metadata
                    mock_affinity.return_value = [0, 1, 2, 3]
                    metadata = {}
                    perf.metadata.collect_metadata(metadata)
                    self.assertNotIn('cpu_affinity', metadata)


if __name__ == "__main__":
    unittest.main()
