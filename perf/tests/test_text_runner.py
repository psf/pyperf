import tempfile

import perf.text_runner
from perf import tests
from perf.tests import mock
from perf.tests import unittest


def check_args(loops, a, b):
    if a != 1:
        raise ValueError
    if b != 2:
        raise ValueError
    # number of loops => number of seconds
    return loops


class TestTextRunner(unittest.TestCase):
    def create_text_runner(self, args):
        runner = perf.text_runner.TextRunner(name='test_runner')
        # disable CPU affinity to not pollute stdout
        runner._cpu_affinity = lambda: None
        runner.parse_args(args)
        return runner

    def check_bench_result(self, runner, stream, result):
        self.assertRegex(stream.getvalue(),
                         r'^(?:Set affinity to isolated CPUs: \[[0-9 ,]+\]\n)?'
                         r'Warmup 1: 1\.00 sec\n'
                         r'Raw sample 1: 1\.00 sec\n'
                         r'Raw sample 2: 1\.00 sec\n'
                         r'Raw sample 3: 1\.00 sec\n'
                         r'Metadata:\n'
                         r'(- .*\n)+'
                         r'\n'
                         r'Average: 1\.00 sec \+- 0\.00 sec '
                             r'\(3 samples; 1 warmup\)\n$')

        # check bench_sample_func() result
        self.assertIsInstance(result, perf.Benchmark)
        self.assertEqual(result.name, 'test_runner')
        self.assertEqual(result.get_nrun(), 1)

    def test_bench_func_raw(self):
        def fake_timer():
            t = fake_timer.value
            fake_timer.value += 1
            return t
        fake_timer.value = 0

        runner = self.create_text_runner(['--raw', '--json',
                                          '--verbose', '--metadata'])

        with mock.patch('perf.perf_counter', fake_timer):
            with tests.capture_stdout() as stdout:
                with tests.capture_stderr() as stderr:
                    result = runner.bench_func(check_args, None, 1, 2)

        self.assertEqual(stdout.getvalue(),
                         result.json())

        self.check_bench_result(runner, stderr, result)

    def test_bench_sample_func_raw(self):
        runner = self.create_text_runner(['--raw', '--json',
                                          '--verbose', '--metadata'])

        with tests.capture_stdout() as stdout:
            with tests.capture_stderr() as stderr:
                result = runner.bench_sample_func(check_args, 1, 2)

        self.assertEqual(stdout.getvalue(),
                         result.json())

        self.check_bench_result(runner, stderr, result)

    def test_loops_calibration(self):
        def sample_func(loops):
            # number of iterations => number of microseconds
            return loops * 1e-6

        runner = self.create_text_runner(['--raw', '-vv'])

        with tests.capture_stdout() as stdout:
            with tests.capture_stderr() as stderr:
                result = runner.bench_sample_func(sample_func)

        self.assertEqual(runner.args.loops, 10 ** 5)
        self.assertEqual(result.loops, 10 ** 5)

        self.assertIn('calibration: 1 loop: 1.00 us\n'
                      'calibration: 10 loops: 10.00 us\n'
                      'calibration: 100 loops: 100.0 us\n'
                      'calibration: 1000 loops: 1.00 ms\n'
                      'calibration: 10^4 loops: 10.0 ms\n'
                      'calibration: 10^5 loops: 100.0 ms\n'
                      'calibration: use 10^5 loops\n',
                      stdout.getvalue())
        self.assertEqual(stderr.getvalue(), '')

    def test_loops_calibration_min_max_time(self):
        def sample_func(loops):
            # number of iterations => number of microseconds
            return loops * 1e-6

        runner = self.create_text_runner(['--raw', '-vv',
                                          '--min-time', '0.001',
                                          '--max-time', '1.0'])
        with tests.capture_stdout():
            with tests.capture_stderr():
                result = runner.bench_sample_func(sample_func)

        self.assertEqual(runner.args.loops, 10 ** 3)
        self.assertEqual(result.loops, 10 ** 3)

    def test_json_file_raw(self):
        with tempfile.NamedTemporaryFile('wb+') as tmp:
            runner = self.create_text_runner(['--raw', '--json-file', tmp.name,
                                              '--verbose', '--metadata'])

            with tests.capture_stdout() as stdout:
                with tests.capture_stderr() as stderr:
                    result = runner.bench_sample_func(check_args, 1, 2)

            self.check_bench_result(runner, stdout, result)

            self.assertEqual(stderr.getvalue(), '')

            tmp.seek(0)
            self.assertEqual(tmp.read().decode('utf-8'),
                             result.json())

    def test_cpu_affinity_psutil_isolcpus(self):
        runner = perf.text_runner.TextRunner()
        runner.parse_args([])

        with mock.patch('perf.text_runner.os') as mock_os:
            del mock_os.sched_setaffinity

            with mock.patch('psutil.Process') as mock_process:
                with mock.patch('io.open') as mock_open:
                    mock_file = mock_open.return_value
                    mock_file.readline.return_value = '1-2'
                    runner._cpu_affinity()
            self.assertEqual(runner.args.affinity, '1-2')

            cpu_affinity = mock_process.return_value.cpu_affinity
            cpu_affinity.assert_called_once_with([1, 2])

    def test_cpu_affinity_isolcpus(self):
        runner = perf.text_runner.TextRunner()
        runner.parse_args([])

        with mock.patch('os.sched_setaffinity', create=True) as mock_setaffinity:
            with mock.patch('io.open') as mock_open:
                mock_file = mock_open.return_value
                mock_file.readline.return_value = '1-2'
                runner._cpu_affinity()
        self.assertEqual(runner.args.affinity, '1-2')
        mock_setaffinity.assert_called_once_with(0, [1, 2])

    def test_cpu_affinity_without_isolcpus(self):
        runner = perf.text_runner.TextRunner()
        runner.parse_args([])

        with mock.patch('os.sched_setaffinity', create=True) as mock_setaffinity:
            with mock.patch('io.open') as mock_open:
                mock_file = mock_open.return_value
                mock_file.readline.return_value = ''
                runner._cpu_affinity()
        self.assertEqual(mock_setaffinity.call_count, 0)


if __name__ == "__main__":
    unittest.main()
