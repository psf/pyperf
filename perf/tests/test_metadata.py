import unittest

import perf.metadata


class TestMetadata(unittest.TestCase):
    def check_metadata(self, text, dbg_info):
        self.assertIsInstance(text, str)
        self.assertFalse(text.startswith(' '), dbg_info)
        self.assertNotIn('\n', text, dbg_info)
        self.assertFalse(text.endswith(' '), dbg_info)

    def test_metadata(self):
        metadata = {}
        perf.metadata.collect_python_metadata(metadata)
        perf.metadata.collect_system_metadata(metadata)
        for key, value in metadata.items():
            dbg_info = 'key=%r value=%r' % (key, value)
            self.check_metadata(key, dbg_info)
            self.check_metadata(value, dbg_info)


if __name__ == "__main__":
    unittest.main()
