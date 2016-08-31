import os.path
import subprocess
import sys

from perf.tests import unittest


ROOT_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..'))


class ExampleTests(unittest.TestCase):
    def check_command(self, cmd, nproc=3):
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, universal_newlines=True)
        stdout = proc.communicate()[0]

        self.assertRegex(stdout,
                         r'^\.{%s}\n'
                         r'Median \+- std dev: [0-9]+\.[0-9]+ [mn]s '
                         r'\+- [0-9]+\.[0-9]+ [mn]s\n$'
                         % nproc)
        self.assertEqual(proc.returncode, 0)

    def test_bench_func(self):
        script = os.path.join(ROOT_DIR, 'doc', 'examples', 'bench_func.py')
        cmd = [sys.executable, script, '-p3']
        self.check_command(cmd)

    def test_bench_func_no_warmup(self):
        script = os.path.join(ROOT_DIR, 'doc', 'examples', 'bench_func.py')
        cmd = [sys.executable, script, '-w0', '-p3']
        self.check_command(cmd)

    def test_bench_sample_func(self):
        script = os.path.join(ROOT_DIR, 'doc', 'examples', 'bench_sample_func.py')
        cmd = [sys.executable, script, '-p3']
        self.check_command(cmd)


if __name__ == "__main__":
    unittest.main()
