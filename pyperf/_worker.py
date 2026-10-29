from __future__ import annotations
import contextlib
import statistics
import sys
import time
from typing import TYPE_CHECKING, cast, TypeVar, Generic

import pyperf
from pyperf._formatter import (format_number, format_value, format_values,
                               format_timedelta)
from pyperf._hooks import instantiate_selected_hooks
from pyperf._utils import MS_WINDOWS, percentile, median_abs_dev
from pyperf._system import OS_LINUX

if TYPE_CHECKING:
    from pyperf._runner import Runner, RunnerArgs
    from pyperf._bench import Run
    from pyperf._metadata import MetadataType
    from collections.abc import Callable
    from pyperf._formatter import UNIT_TYPE
    from pyperf._linux_memory import PeakMemoryUsageThread as PeakMemoryUsageThreadLinux
    from pyperf._psutil_memory import PeakMemoryUsageThread as PeakMemoryUsageThreadPsutil
    from typing_extensions import override
    from types import ModuleType

else:
    def override(func):
        return func


MAX_LOOPS = 2 ** 32

# Parameters to calibrate and recalibrate warmups

MAX_WARMUP_VALUES = 300
WARMUP_SAMPLE_SIZE = 20

ArgsT = TypeVar("ArgsT", bound="RunnerArgs")

class WorkerTask(Generic[ArgsT]):
    def __init__(self, runner: Runner[ArgsT], name: str, task_func: Callable[[WorkerTask[ArgsT], int],float], func_metadata: MetadataType | None) -> None:
        args = runner.args

        name = name.strip()
        if not name:
            raise ValueError("benchmark name must be a non-empty string")

        self.name = name
        self.args = args
        self.task_func = task_func
        self.loops = args.loops
        self._custom_hooks = runner._custom_hooks

        self.metadata = cast("MetadataType",dict(runner.metadata))
        if func_metadata:
            self.metadata.update(func_metadata)
        if 'unit' not in self.metadata:
            # Set default unit to seconds
            self.metadata['unit'] = 'second'

        self.inner_loops: int | None = None
        self.warmups: list[tuple[int,float]] = None #type: ignore[assignment]
        self.values: list[float] = []

    def _compute_warmup_values(self, values: list[tuple[int,float]], nvalue: int,
                        calibrate_loops: bool = False,
                        start: int = 0) -> None:
        unit = self.metadata.get('unit')
        args = self.args
        if nvalue < 1:
            raise ValueError("nvalue must be >= 1")
        if self.loops <= 0:
            raise ValueError("loops must be >= 1")

        value_name = 'Warmup'

        task_func = self.task_func
        hook_names = args.hook if args.hook is not None else []
        hook_managers = instantiate_selected_hooks(hook_names, self._custom_hooks)
        if len(hook_managers):
            self.metadata["hooks"] = ", ".join(hook_managers.keys())

        index = 1
        inner_loops = self.inner_loops
        if not inner_loops:
            inner_loops = 1
        while True:
            if index > nvalue:
                break

            with contextlib.ExitStack() as stack:
                for hook in hook_managers.values():
                    stack.enter_context(hook)
                raw_value = task_func(self, self.loops)

            raw_value = float(raw_value)
            value = raw_value / (self.loops * inner_loops)

            if not value and not calibrate_loops:
                raise ValueError("benchmark function returned zero")

            values.append((self.loops, value))

            if args.verbose:
                text = format_value(unit, value)
                text = ('%s (loops: %s, raw: %s)'
                        % (text,
                            format_number(self.loops),
                            format_value(unit, raw_value)))
                print("%s %s: %s" % (value_name, start + index, text))

            if calibrate_loops and raw_value < args.min_time:
                if self.loops * 2 > MAX_LOOPS:
                    print("ERROR: failed to calibrate the number of loops")
                    print("Raw timing %s with %s is still smaller than "
                          "the minimum time of %s"
                          % (format_value(unit, raw_value),
                             format_number(self.loops, 'loop'),
                             format_timedelta(args.min_time)))
                    sys.exit(1)
                self.loops *= 2
                # need more values for the calibration
                nvalue += 1

            index += 1

        for hook in hook_managers.values():
            hook.teardown(self.metadata)

    def _compute_values(self, values: list[float], nvalue: int,
                        calibrate_loops: bool = False,
                        start: int = 0) -> None:
        unit = self.metadata.get('unit')
        args = self.args
        if nvalue < 1:
            raise ValueError("nvalue must be >= 1")
        if self.loops <= 0:
            raise ValueError("loops must be >= 1")

        value_name = 'Value'

        task_func = self.task_func
        hook_names = args.hook if args.hook is not None else []
        hook_managers = instantiate_selected_hooks(hook_names, self._custom_hooks)
        if len(hook_managers):
            self.metadata["hooks"] = ", ".join(hook_managers.keys())

        index = 1
        inner_loops = self.inner_loops
        if not inner_loops:
            inner_loops = 1
        while True:
            if index > nvalue:
                break

            with contextlib.ExitStack() as stack:
                for hook in hook_managers.values():
                    stack.enter_context(hook)
                raw_value = task_func(self, self.loops)

            raw_value = float(raw_value)
            value = raw_value / (self.loops * inner_loops)

            if not value and not calibrate_loops:
                raise ValueError("benchmark function returned zero")

            values.append(value)

            if args.verbose:
                text = format_value(unit, value)
                print("%s %s: %s" % (value_name, start + index, text))

            if calibrate_loops and raw_value < args.min_time:
                if self.loops * 2 > MAX_LOOPS:
                    print("ERROR: failed to calibrate the number of loops")
                    print("Raw timing %s with %s is still smaller than "
                          "the minimum time of %s"
                          % (format_value(unit, raw_value),
                             format_number(self.loops, 'loop'),
                             format_timedelta(args.min_time)))
                    sys.exit(1)
                self.loops *= 2
                # need more values for the calibration
                nvalue += 1

            index += 1

        for hook in hook_managers.values():
            hook.teardown(self.metadata)

    def collect_metadata(self) -> MetadataType:
        from pyperf._collect_metadata import collect_metadata
        return collect_metadata(process=False)

    def test_calibrate_warmups(self, nwarmup: int, unit: UNIT_TYPE) -> bool:
        half = nwarmup + (len(self.warmups) - nwarmup) // 2
        sample1 = [value for loops, value in self.warmups[nwarmup:half]]
        sample2 = [value for loops, value in self.warmups[half:]]
        first_value = sample1[0]

        # test if the first value is an outlier
        values = sample1[1:] + sample2
        q1 = percentile(values, 0.25)
        q3 = percentile(values, 0.75)
        iqr = q3 - q1
        outlier_max = (q3 + 1.5 * iqr)
        # only check maximum, not minimum
        outlier = not (first_value <= outlier_max)

        mean1 = statistics.mean(sample1)
        mean2 = statistics.mean(sample2)
        mean_diff = (mean1 - mean2) / float(mean2)

        s1_q1 = percentile(sample1, 0.25)
        s2_q1 = percentile(sample2, 0.25)
        s1_q3 = percentile(sample1, 0.75)
        s2_q3 = percentile(sample2, 0.75)
        q1_diff = (s1_q1 - s2_q1) / float(s2_q1)
        q3_diff = (s1_q3 - s2_q3) / float(s2_q3)

        mad1 = median_abs_dev(sample1)
        mad2 = median_abs_dev(sample2)
        # FIXME: handle division by zero
        mad_diff = (mad1 - mad2) / float(mad2)

        if self.args.verbose:
            stdev1 = statistics.stdev(sample1)
            stdev2 = statistics.stdev(sample2)
            stdev_diff = (stdev1 - stdev2) / float(stdev2)

            sample1_str = format_values(unit, (s1_q1, mean1, s1_q3, stdev1, mad1))
            sample2_str = format_values(unit, (s2_q1, mean2, s2_q3, stdev2, mad2))
            print("Calibration: warmups=%s" % format_number(nwarmup))
            print("  first value: %s, outlier? %s (max: %s)"
                  % (format_value(unit, first_value), outlier,
                     format_value(unit, outlier_max)))
            print("  sample1(%s): Q1=%s mean=%s Q3=%s stdev=%s MAD=%s"
                  % (len(sample1),
                     sample1_str[0],
                     sample1_str[1],
                     sample1_str[2],
                     sample1_str[3],
                     sample1_str[4]))
            print("  sample2(%s): Q1=%s mean=%s Q3=%s stdev=%s MAD=%s"
                  % (len(sample2),
                     sample2_str[0],
                     sample2_str[1],
                     sample2_str[2],
                     sample2_str[3],
                     sample2_str[4]))
            print("  diff: Q1=%+.0f%% mean=%+.0f%% Q3=%+.0f%% stdev=%+.0f%% MAD=%+.0f%%"
                  % (q1_diff * 100,
                     mean_diff * 100,
                     q3_diff * 100,
                     stdev_diff * 100,
                     mad_diff * 100))

        if outlier:
            return False
        if not (-0.5 <= mean_diff <= 0.10):
            return False
        if abs(mad_diff) > 0.10:
            return False
        if abs(q1_diff) > 0.05:
            return False
        if abs(q3_diff) > 0.05:
            return False
        return True

    def calibrate_warmups(self) -> None:
        # calibrate the number of warmups
        if self.loops < 1:
            raise ValueError("loops must be >= 1")

        if self.args.recalibrate_warmups and self.args.warmups:
            nwarmup = self.args.warmups
        else:
            nwarmup = 1

        unit = self.metadata.get('unit', "second")
        start = 0
        # test_calibrate_warmups() requires at least 2 values per sample
        while True:
            total = nwarmup + WARMUP_SAMPLE_SIZE * 2
            nvalue = total - len(self.warmups)
            if nvalue:
                self._compute_warmup_values(self.warmups, nvalue,
                                     start=start)
                start += nvalue

            if self.test_calibrate_warmups(nwarmup, unit):
                break

            if len(self.warmups) >= MAX_WARMUP_VALUES:
                print("ERROR: failed to calibrate the number of warmups")
                values = [format_value(unit, value)
                          for loops, value in self.warmups]
                print("Values (%s): %s" % (len(values), ', '.join(values)))
                sys.exit(1)
            nwarmup += 1

        if self.args.verbose:
            print("Calibration: use %s warmups" % format_number(nwarmup))
            print()

        if self.args.recalibrate_warmups:
            self.metadata['recalibrate_warmups'] = nwarmup
        else:
            self.metadata['calibrate_warmups'] = nwarmup

    def calibrate_loops(self) -> None:
        args = self.args
        if not args.recalibrate_loops:
            self.loops = 1

        if args.warmups is not None:
            nvalue = args.warmups
        else:
            nvalue = 1
        nvalue += args.values
        self._compute_warmup_values(self.warmups, nvalue, calibrate_loops=True)

        if args.verbose:
            print()
            print("Calibration: use %s loops" % format_number(self.loops))
            print()

        if args.recalibrate_loops:
            self.metadata['recalibrate_loops'] = self.loops
        else:
            self.metadata['calibrate_loops'] = self.loops

    def compute_warmups_values(self) -> None:
        args = self.args
        if args.warmups:
            self._compute_warmup_values(self.warmups, args.warmups)
            if args.verbose:
                print()

        self._compute_values(self.values, args.values)
        if args.verbose:
            print()

    def compute(self) -> None:
        args = self.args

        self.metadata['name'] = self.name
        if self.inner_loops is not None:
            self.metadata['inner_loops'] = self.inner_loops
        self.warmups = []
        self.values = []

        if args.calibrate_warmups or args.recalibrate_warmups:
            self.calibrate_warmups()
        elif args.calibrate_loops or args.recalibrate_loops:
            self.calibrate_loops()
        else:
            self.compute_warmups_values()

        # collect metadata
        metadata2 = self.collect_metadata()
        metadata2.update(self.metadata)
        self.metadata = metadata2

        self.metadata['loops'] = self.loops

    def create_run(self) -> Run:
        start_time = time.monotonic()
        self.compute()
        self.metadata['duration'] = time.monotonic() - start_time

        return pyperf.Run(self.values,
                          warmups=self.warmups,
                          metadata=self.metadata,
                          collect_metadata=False)

    def _set_memory_value(self, value: float) -> None:
        is_calibration = (not self.values)
        self.metadata['unit'] = 'byte'
        self.metadata['warmups'] = len(self.warmups)
        self.metadata['values'] = len(self.values)
        if is_calibration:
            values = [(self.loops, value)]
            self.warmups = values
            self.values = []
        else:
            self.warmups = None #type: ignore[assignment]
            self.values = [value]


class MemoryUsage:
    def __init__(self) -> None:
        self.mem_thread: PeakMemoryUsageThreadLinux | PeakMemoryUsageThreadPsutil | None = None
        self.get_peak_profile_usage: Callable[[], int] | None = None

    def start(self) -> None:
        if MS_WINDOWS:
            from pyperf._win_memory import get_peak_pagefile_usage
            self.get_peak_profile_usage = get_peak_pagefile_usage
        elif OS_LINUX:
            from pyperf._linux_memory import PeakMemoryUsageThread as PeakMemoryUsageThreadLinux
            self.mem_thread = PeakMemoryUsageThreadLinux()
            self.mem_thread.start()
        else:
            from pyperf._psutil_memory import PeakMemoryUsageThread as PeakMemoryUsageThreadPsutil
            self.mem_thread = PeakMemoryUsageThreadPsutil()
            self.mem_thread.start()

    def get_memory_peak(self) -> int:
        if self.get_peak_profile_usage is not None:
            mem_peak = self.get_peak_profile_usage()
            return mem_peak
        elif self.mem_thread is not None:
            self.mem_thread.stop()
            mem_peak = self.mem_thread.peak_usage
            return mem_peak

        raise RuntimeError("failed to get the memory peak usage")


class WorkerProcessTask(WorkerTask[ArgsT]):
    @override
    def compute(self) -> None:
        args = self.args

        mem_usage: MemoryUsage | None = None
        tracemalloc_module: ModuleType | None = None

        if args.track_memory:
            mem_usage = MemoryUsage()
            mem_usage.start()

        if args.tracemalloc:
            import tracemalloc
            tracemalloc_module = tracemalloc
            tracemalloc_module.start()

        WorkerTask.compute(self)

        if tracemalloc_module is not None:
            traced_peak = tracemalloc_module.get_traced_memory()[1]
            tracemalloc_module.stop()

            if not traced_peak:
                raise RuntimeError("tracemalloc didn't trace any Python "
                                   "memory allocation")

            # drop timings, replace them with the memory peak
            self._set_memory_value(traced_peak)

        if mem_usage is not None:
            mem_peak = mem_usage.get_memory_peak()
            # drop timings, replace them with the memory peak
            self._set_memory_value(mem_peak)

    @override
    def collect_metadata(self) -> MetadataType:
        from pyperf._collect_metadata import collect_metadata
        return collect_metadata()
