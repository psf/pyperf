import os.path
import sys
import unittest

import pyperf
from pyperf import _utils as utils
from pyperf import tests


class MiscTests(unittest.TestCase):
    def test_version_tuple(self):
        self.assertIsInstance(pyperf.VERSION, tuple)
        self.assertTrue(all(isinstance(part, int) for part in pyperf.VERSION),
                        pyperf.VERSION)

    def test_version_str(self):
        self.assertIsInstance(pyperf.__version__, str)
        self.assertEqual(pyperf.__version__,
                         '.'.join(str(part) for part in pyperf.VERSION))

    def test_format_metadata(self):
        self.assertEqual(pyperf.format_metadata('loops', 2 ** 24),
                         '2^24')

    def test_python_implementation(self):
        name = pyperf.python_implementation()
        self.assertIsInstance(name, str)
        self.assertRegex(name, '^[a-z]+$')

    def test_python_has_jit(self):
        jit = pyperf.python_has_jit()
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
        self.assertEqual(pyperf.__version__, setup.VERSION)

    def test_doc_version(self):
        doc_path = os.path.join(os.path.dirname(__file__), '..', '..', 'doc')
        doc_path = os.path.realpath(doc_path)

        old_path = sys.path[:]
        try:
            sys.path.insert(0, doc_path)
            import conf
            self.assertEqual(pyperf.__version__, conf.version)
            self.assertEqual(pyperf.__version__, conf.release)
        finally:
            sys.path[:] = old_path


if __name__ == "__main__":
    unittest.main()
