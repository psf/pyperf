import os.path
import unittest
from unittest import mock

import pyperf
from pyperf import tests


def check_args(loops, a, b):
    if a != 1:
        raise ValueError
    if b != 2:
        raise ValueError
    return loops


class TestInProcess(unittest.TestCase):
    def create_runner(self, args, **kwargs):
        pyperf.Runner._created.clear()
        runner = pyperf.Runner(**kwargs)
        runner._cpu_affinity = lambda: None
        runner.parse_args(args)
        return runner

    def fake_timer(self):
        t = self._timer_value
        self._timer_value += 1.0
        return t

    def exec_in_process(self, *extra_args, name="bench", time_func=None, **kwargs):
        self._timer_value = 0.0

        def fake_get_clock_info(clock):
            class ClockInfo:
                implementation = "fake_clock"
                resolution = 1.0

            return ClockInfo()

        args = ["--in-process", "-p1", "-n3", "-l1", "-w1"] + list(extra_args)
        runner = self.create_runner(args, **kwargs)

        with mock.patch("time.perf_counter", self.fake_timer):
            with mock.patch("time.get_clock_info", fake_get_clock_info):
                with tests.capture_stdout() as stdout:
                    with tests.capture_stderr() as stderr:
                        if time_func:
                            bench = runner.bench_time_func(name, time_func)
                        else:
                            bench = runner.bench_func(name, check_args, None, 1, 2)

        stdout = stdout.getvalue()
        stderr = stderr.getvalue()
        return bench, stdout, stderr

    def test_bench_func(self):
        bench, stdout, _ = self.exec_in_process()
        self.assertIsInstance(bench, pyperf.Benchmark)
        self.assertEqual(bench.get_name(), "bench")

    def test_bench_time_func(self):
        def time_func(loops):
            return 1.0

        bench, stdout, _ = self.exec_in_process(time_func=time_func)
        self.assertIsInstance(bench, pyperf.Benchmark)
        self.assertEqual(bench.get_name(), "bench")
        self.assertEqual(bench.get_nvalue(), 3)

    def test_values_count(self):
        bench, _, _ = self.exec_in_process("-n5")
        self.assertEqual(bench.get_nvalue(), 5)

    def test_json_output(self):
        with tests.temporary_directory() as tmpdir:
            filename = os.path.join(tmpdir, "test.json")
            bench, _, _ = self.exec_in_process("--output", filename)
            loaded = pyperf.Benchmark.load(filename)
            self.assertEqual(loaded.get_name(), bench.get_name())
            self.assertEqual(loaded.get_nvalue(), bench.get_nvalue())

    def test_calibrate_loops(self):
        def time_func(loops):
            return loops * 1e-6

        bench, stdout, _ = self.exec_in_process(
            "-p1", "-w0", "-n2", "--min-time=0.001", time_func=time_func
        )
        self.assertIsInstance(bench, pyperf.Benchmark)

    def test_two_benchmarks(self):
        self._timer_value = 0.0

        def fake_get_clock_info(clock):
            class ClockInfo:
                implementation = "fake_clock"
                resolution = 1.0

            return ClockInfo()

        args = ["--in-process", "-p1", "-l1", "-w0", "-n3"]
        runner = self.create_runner(args)

        def time_func1(loops):
            return 1.0

        def time_func2(loops):
            return 2.0

        with mock.patch("time.perf_counter", self.fake_timer):
            with mock.patch("time.get_clock_info", fake_get_clock_info):
                with tests.capture_stdout():
                    bench1 = runner.bench_time_func("bench1", time_func1)
                    bench2 = runner.bench_time_func("bench2", time_func2)

        self.assertEqual(bench1.get_name(), "bench1")
        self.assertEqual(bench1.get_values(), (1.0, 1.0, 1.0))
        self.assertEqual(bench2.get_name(), "bench2")
        self.assertEqual(bench2.get_values(), (2.0, 2.0, 2.0))

    def test_show_name(self):
        bench, stdout, _ = self.exec_in_process(name="NAME")
        self.assertIn("NAME:", stdout)

    def test_show_name_false(self):
        bench, stdout, _ = self.exec_in_process(name="NAME", show_name=False)
        self.assertNotIn("NAME:", stdout)

    def test_no_subprocess_spawned(self):
        with mock.patch("pyperf._manager.Manager.spawn_worker") as mock_spawn:
            bench, _, _ = self.exec_in_process()
            mock_spawn.assert_not_called()


if __name__ == "__main__":
    unittest.main()
