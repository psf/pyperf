from __future__ import division, print_function, absolute_import

import sys

import statistics

import perf
from perf._formatter import (format_number, format_value, format_values,
                             format_timedelta)
from perf._utils import MS_WINDOWS, percentile

try:
    # Python 3.3 provides a real monotonic clock (PEP 418)
    from time import monotonic as monotonic_clock
except ImportError:
    # time.time() can go backward on Python 2, but it's fine for Runner
    from time import time as monotonic_clock


MAX_LOOPS = 2 ** 32

# Parameters to calibrate and recalibrate warmups

# Maximum absolute difference of the mean of sample 1
# compared to the mean of the sample 2
MAX_WARMUP_MEAN_DIFF = 0.10
# Considering that min_time=100 ms, limit warmup to 30 seconds
MAX_WARMUP_VALUES = 300


class WorkerTask:
    def __init__(self, runner, name, task_func, func_metadata):
        args = runner.args

        name = name.strip()
        if not name:
            raise ValueError("benchmark name must be a non-empty string")

        self.name = name
        self.args = args
        self.task_func = task_func
        self.metadata = dict(runner.metadata)
        if func_metadata:
            self.metadata.update(func_metadata)

        self.loops = args.loops
        self.inner_loops = None
        self.warmups = None
        self.values = None

    def _compute_values(self, values, nvalue,
                        is_warmup=False,
                        calibrate_loops=False,
                        start=0):
        unit = self.metadata.get('unit')
        args = self.args
        if nvalue < 1:
            raise ValueError("nvalue must be >= 1")
        if self.loops <= 0:
            raise ValueError("loops must be >= 1")

        if is_warmup:
            value_name = 'Warmup'
        else:
            value_name = 'Value'

        index = 1
        inner_loops = self.inner_loops
        if not inner_loops:
            inner_loops = 1
        while True:
            if index > nvalue:
                break

            raw_value = self.task_func(self, self.loops)
            raw_value = float(raw_value)
            value = raw_value / (self.loops * inner_loops)

            if not value and not calibrate_loops:
                raise ValueError("benchmark function returned zero")

            if is_warmup:
                values.append((self.loops, value))
            else:
                values.append(value)

            if args.verbose:
                text = format_value(unit, value)
                if is_warmup:
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

    def collect_metadata(self):
        from perf._collect_metadata import collect_metadata
        return collect_metadata(process=False)

    def test_calibrate_warmups(self, nwarmup, unit):
        half = nwarmup + (len(self.warmups) - nwarmup) // 2
        sample1 = [value for loops, value in self.warmups[nwarmup:half]]
        sample2 = [value for loops, value in self.warmups[half:]]
        mean1 = statistics.mean(sample1)
        mean2 = statistics.mean(sample2)
        first_value = sample1[0]

        # test if the first value is an outlier
        values = sample1[1:] + sample2
        q1 = percentile(values, 0.25)
        q3 = percentile(values, 0.75)
        iqr = q3 - q1
        outlier_max = (q3 + 1.5 * iqr)
        # only check maximum, not minimum
        outlier = not(first_value <= outlier_max)

        # Consider that sample 2 is more stable than sample 1, so
        # use it as reference
        mean_diff = abs(mean1 - mean2) / float(mean2)

        if self.args.verbose:
            if outlier:
                in_range = "outlier: > %s" % format_value(unit, outlier_max)
            else:
                in_range = "good: <= %s" % format_value(unit, outlier_max)

            stdev1 = statistics.stdev(sample1)
            stdev2 = statistics.stdev(sample2)
            sample1_str = format_values(unit, (mean1, stdev1))
            sample2_str = format_values(unit, (mean2, stdev2))
            print("Calibration: warmups: %s, "
                  "first value: %s (%s), "
                  "sample1(%s): %s (%+.0f%%) +- %s, "
                  "sample2(%s): %s +- %s"
                  % (format_number(nwarmup),
                     format_value(unit, first_value),
                     in_range,
                     len(sample1),
                     sample1_str[0],
                     mean_diff * 100,
                     sample1_str[1],
                     len(sample2),
                     sample2_str[0],
                     sample2_str[1]))

        if outlier:
            return False
        return (mean_diff <= MAX_WARMUP_MEAN_DIFF)

    def calibrate_warmups(self):
        # calibrate the number of warmups
        if self.loops < 1:
            raise ValueError("loops must be >= 1")

        if self.args.recalibrate_warmups:
            nwarmup = self.args.warmups
        else:
            nwarmup = 1

        unit = self.metadata.get('unit')
        start = 0
        # test_calibrate_warmups() requires at least 2 values per sample
        min_sample_size = 3
        total = nwarmup + min_sample_size * 2
        while True:
            nvalue = total - len(self.warmups)
            if nvalue:
                self._compute_values(self.warmups, nvalue,
                                     is_warmup=True,
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

            total = max(total, nwarmup * 3)
            sample_size = max((nvalue - nwarmup) // 2, min_sample_size)
            total = max(total, nwarmup + sample_size * 2)

        if self.args.verbose:
            print("Calibration: use %s warmups" % format_number(nwarmup))
            print()

        if self.args.recalibrate_warmups:
            self.metadata['recalibrate_warmups'] = nwarmup
        else:
            self.metadata['calibrate_warmups'] = nwarmup

    def calibrate_loops(self):
        args = self.args
        if not args.recalibrate_loops:
            self.loops = 1

        if args.warmups is not None:
            nvalue = args.warmups
        else:
            nvalue = 1
        nvalue += args.values
        self._compute_values(self.warmups, nvalue,
                             is_warmup=True,
                             calibrate_loops=True)

        if args.verbose:
            print()
            print("Calibration: use %s loops" % format_number(self.loops))
            print()

        if args.recalibrate_loops:
            self.metadata['recalibrate_loops'] = self.loops
        else:
            self.metadata['calibrate_loops'] = self.loops

    def compute_warmups_values(self):
        args = self.args
        if args.warmups:
            self._compute_values(self.warmups, args.warmups, is_warmup=True)
            if args.verbose:
                print()

        self._compute_values(self.values, args.values)
        if args.verbose:
            print()

    def compute(self):
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

        # collect metatadata
        metadata2 = self.collect_metadata()
        metadata2.update(self.metadata)
        self.metadata = metadata2

        self.metadata['loops'] = self.loops

    def create_run(self):
        start_time = monotonic_clock()
        self.compute()
        self.metadata['duration'] = monotonic_clock() - start_time

        return perf.Run(self.values,
                        warmups=self.warmups,
                        metadata=self.metadata,
                        collect_metadata=False)


class WorkerProcessTask(WorkerTask):
    def compute(self):
        args = self.args

        if args.track_memory:
            if MS_WINDOWS:
                from perf._win_memory import get_peak_pagefile_usage
            else:
                from perf._memory import PeakMemoryUsageThread
                mem_thread = PeakMemoryUsageThread()
                mem_thread.start()

        if args.tracemalloc:
            import tracemalloc
            tracemalloc.start()

        WorkerTask.compute(self)

        if args.tracemalloc:
            traced_peak = tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()

            if not traced_peak:
                raise RuntimeError("tracemalloc didn't trace any Python "
                                   "memory allocation")

            # drop timings, replace them with the memory peak
            self.metadata['unit'] = 'byte'
            self.warmups = None
            self.values = (traced_peak,)

        if args.track_memory:
            if MS_WINDOWS:
                mem_peak = get_peak_pagefile_usage()
            else:
                mem_thread.stop()
                mem_peak = mem_thread.peak_usage

            if not mem_peak:
                raise RuntimeError("failed to get the memory peak usage")

            # drop timings, replace them with the memory peak
            self.metadata['unit'] = 'byte'
            self.warmups = None
            self.values = (mem_peak,)

    def collect_metadata(self):
        from perf._collect_metadata import collect_metadata
        return collect_metadata()


class BenchCommandTask(WorkerTask):
    def compute(self):
        WorkerTask.compute(self)
        if self.args.track_memory:
            value = self.metadata.pop('command_max_rss', None)
            if not value:
                raise RuntimeError("failed to get the process RSS")

            self.metadata['unit'] = 'byte'
            self.warmups = None
            self.values = (value,)
