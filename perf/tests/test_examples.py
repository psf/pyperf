import os.path
import sys

from perf import tests
from perf.tests import unittest


ROOT_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..'))


class ExampleTests(unittest.TestCase):
    def check_command(self, cmd, nproc=3):
        cmd = [sys.executable] + cmd + ["--inherit-env=PYTHONPATH"]
        proc = tests.get_output(cmd)

        self.assertRegex(proc.stdout,
                         r'Median \+- MAD: [0-9.]+ [mun]s '
                         r'\+- [0-9.]+ [mun]s\n')
        self.assertEqual(proc.returncode, 0)

    def test_bench_func(self):
        script = os.path.join(ROOT_DIR, 'doc', 'examples', 'bench_func.py')
        # Use -w1 --min-time=0.001 to reduce the duration of the test
        cmd = [script, '-p2', '-w1', '--min-time=0.001']
        self.check_command(cmd)

    def test_bench_func_no_warmup(self):
        script = os.path.join(ROOT_DIR, 'doc', 'examples', 'bench_func.py')
        cmd = [script, '-p2', '-w0', '--min-time=0.001']
        self.check_command(cmd)

    def test_bench_sample_func(self):
        script = os.path.join(ROOT_DIR, 'doc', 'examples', 'bench_sample_func.py')
        cmd = [script, '-p2', '-w1', '--min-time=0.001']
        self.check_command(cmd)


if __name__ == "__main__":
    unittest.main()
