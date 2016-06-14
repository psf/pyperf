import subprocess
import sys
import unittest

import perf.metadata
from perf.tests import mock


MANDATORY_METADATA = [
    'date',
    'python_implementation', 'python_version',
    'platform']
if sys.platform.startswith('linux'):
    MANDATORY_METADATA.extend(('aslr', 'cpu_model_name'))


class TestMetadata(unittest.TestCase):
    def check_metadata(self, text, dbg_info):
        self.assertIsInstance(text, str)
        self.assertNotEqual(len(text), 0)
        self.assertFalse(text.startswith(' '), dbg_info)
        self.assertNotIn('\n', text, dbg_info)
        self.assertFalse(text.endswith(' '), dbg_info)

    def check_all_metadata(self, metadata):
        for key in MANDATORY_METADATA:
            self.assertIn(key, metadata)
        for key, value in metadata.items():
            dbg_info = 'key=%r value=%r' % (key, value)
            self.check_metadata(key, dbg_info)
            self.check_metadata(value, dbg_info)

    def test_metadata(self):
        metadata = {}
        perf.metadata.collect_metadata(metadata)
        self.check_all_metadata(metadata)

    def test_cpu_affinity(self):
        # affinity=2/4 CPUs
        with mock.patch('os.sched_getaffinity',
                        return_value={2, 3}, create=True):
            with mock.patch('os.cpu_count', return_value=4, create=True):
                metadata = {}
                perf.metadata.collect_metadata(metadata)
        self.assertEqual(metadata['cpu_affinity'], '2-3')

        # affinity=all CPUs: ignore metadata
        with mock.patch('os.sched_getaffinity',
                        return_value={0, 1}, create=True):
            with mock.patch('os.cpu_count', return_value=2, create=True):
                metadata = {}
                perf.metadata.collect_metadata(metadata)
        self.assertNotIn('cpu_affinity', metadata)

    def test_cpu_affinity_psutil(self):
        with mock.patch('perf.metadata.os') as mock_os:
            del mock_os.sched_getaffinity
            mock_os.cpu_count.return_value = 4

            with mock.patch('psutil.Process') as mock_process:
                mock_process.return_value.cpu_affinity.return_value = [2, 3]

                metadata = {}
                perf.metadata.collect_metadata(metadata)
            self.assertEqual(metadata['cpu_affinity'], '2-3')

    def test_cli(self):
        args = [sys.executable, '-m', 'perf.metadata']
        proc = subprocess.Popen(args,
                                stdout=subprocess.PIPE,
                                universal_newlines=True)
        stdout = proc.communicate()[0]
        self.assertEqual(proc.returncode, 0)

        metadata = {}
        for line in stdout.splitlines():
            self.assertIn(': ', line)
            key, value = line.split(': ', 1)
            metadata[key] = value
        self.check_all_metadata(metadata)


if __name__ == "__main__":
    unittest.main()
