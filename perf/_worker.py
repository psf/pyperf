from __future__ import division, print_function, absolute_import

import sys

import statistics

import perf
from perf._formatter import (format_number, format_value, format_values,
                             format_timedelta)
from perf._utils import MS_WINDOWS

try:
    # Python 3.3 provides a real monotonic clock (PEP 418)
    from time import monotonic as monotonic_clock
except ImportError:
    # time.time() can go backward on Python 2, but it's fine for Runner
    from time import time as monotonic_clock


MAX_LOOPS = 2 ** 32

# Parameters to calibrate warmups

# Maximum difference in percent of the first value
# and the mean the second sample
MAX_WARMUP_VALUE_DIFF = 25.0
# Maximum difference in percent of the mean of two samples
MAX_WARMUP_MEAN_DIFF = 15.0
# Considering that min_time=100 ms, limit warmup to 30 seconds
MAX_WARMUP_VALUES = 300


def warmup_mean(values):
    if len(values) != 1:
        return statistics.mean(values)
    else:
        return values[0]


def format_warmup_sample(sample, unit):
    if len(sample) != 1:
        mean = statistics.mean(sample)
        stdev = statistics.stdev(sample)
        return "%s +- %s" % format_values(unit, (mean, stdev))
    else:
        return format_value(unit, sample[0])


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

    def compute_values(self, values, nvalue,
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
        first_value = self.warmups[nwarmup][1]
        sample1 = [value for loops, value in self.warmups[nwarmup:half]]
        sample2 = [value for loops, value in self.warmups[half:]]
        mean1 = warmup_mean(sample1)
        mean2 = warmup_mean(sample2)

        value_diff = abs(mean2 - first_value) * 100.0 / first_value
        mean_diff = abs(mean2 - mean1) * 100.0 / mean1
        if self.args.verbose:
            print("Calibration: warmups: %s, "
                  "first value: %s (%.1f%% of mean2), "
                  "sample1(%s): %s, "
                  "sample2(%s): %s (%.1f%% of mean1)"
                  % (format_number(nwarmup),
                     format_value(unit, first_value),
                     value_diff,
                     len(sample1), format_warmup_sample(sample1, unit),
                     len(sample2), format_warmup_sample(sample2, unit),
                     mean_diff))

        if value_diff > MAX_WARMUP_VALUE_DIFF:
            return False
        if mean_diff > MAX_WARMUP_MEAN_DIFF:
            return False
        return True

    def calibrate_warmups(self):
        # calibrate the number of warmups
        if self.loops < 1:
            raise ValueError("loops must be >= 1")

        if self.args.calibrate_warmups:
            nwarmup = 1
            self.metadata['calibrate_warmups'] = True
        else:
            nwarmup = self.args.warmups
            self.metadata['recalibrate_warmups'] = True

        unit = self.metadata.get('unit')
        start = 0
        min_sample_size = 5
        total = nwarmup + min_sample_size * 2
        while True:
            nvalue = total - len(self.warmups)
            if nvalue:
                self.compute_values(self.warmups, nvalue,
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
        self.metadata['warmups'] = nwarmup

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
            # calibrate or recalibrate the number of loops
            if not self.loops:
                self.loops = 1
                self.metadata['calibrate_loops'] = True
            else:
                self.metadata['recalibrate_loops'] = True

            self.compute_values(self.warmups, args.warmups,
                                is_warmup=True,
                                calibrate_loops=True)

            if args.verbose:
                print()
                print("Calibration: use %s loops" % format_number(self.loops))
                print()
        else:
            # compute warmups and values
            if args.warmups:
                self.compute_values(self.warmups, args.warmups, is_warmup=True)
            if args.verbose:
                print()

            self.compute_values(self.values, args.values)
            if args.verbose:
                print()

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
