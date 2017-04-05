from __future__ import division, print_function, absolute_import

import perf
from perf._formatter import format_number, format_value
from perf._utils import MS_WINDOWS

try:
    # Python 3.3 provides a real monotonic clock (PEP 418)
    from time import monotonic as monotonic_clock
except ImportError:
    # time.time() can go backward on Python 2, but it's fine for Runner
    from time import time as monotonic_clock


MAX_LOOPS = 2 ** 32


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
        # calibrate during warmup?
        self.calibrate_warmups = perf.python_has_jit()

    def run_bench(self, nvalue,
                  is_warmup=False, is_calibrate=False, calibrate=False):
        unit = self.metadata.get('unit')
        args = self.args
        if self.loops <= 0:
            raise ValueError("loops must be >= 1")

        if is_calibrate:
            value_name = 'Calibration'
        elif is_warmup:
            value_name = 'Warmup'
        else:
            value_name = 'Value'

        values = []
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

            if not value and not(is_calibrate or is_warmup):
                raise ValueError("benchmark function returned zero")

            if is_warmup:
                values.append((self.loops, value))
            else:
                values.append(value)

            if args.verbose:
                text = format_value(unit, value)
                if is_warmup or is_calibrate:
                    text = ('%s (%s: %s)'
                            % (text,
                               format_number(self.loops, 'loop'),
                               format_value(unit, raw_value)))
                print("%s %s: %s" % (value_name, index, text))

            if calibrate and raw_value < args.min_time:
                self.loops *= 2
                if self.loops > MAX_LOOPS:
                    raise ValueError("error in calibration, loops is "
                                     "too big: %s" % self.loops)
                # need more values for the calibration
                nvalue += 1

            index += 1

        if args.verbose:
            if is_calibrate:
                print("Calibration: use %s loops" % format_number(self.loops))
            print()

        return values

    def calibrate_loops(self):
        return self.run_bench(nvalue=1,
                              calibrate=True,
                              is_calibrate=True, is_warmup=True)

    def collect_metadata(self):
        from perf._collect_metadata import collect_metadata
        return collect_metadata(process=False)

    def compute_values(self):
        args = self.args

        self.metadata['name'] = self.name
        if self.inner_loops is not None:
            self.metadata['inner_loops'] = self.inner_loops

        calibrate = (not self.loops)
        if calibrate:
            self.loops = 1
            calibrate_warmups = self.calibrate_loops()
        else:
            if self.calibrate_warmups:
                calibrate = True
            calibrate_warmups = None

        if args.warmups:
            warmups = self.run_bench(nvalue=args.warmups,
                                     is_warmup=True, calibrate=calibrate)
        else:
            warmups = []
        if calibrate_warmups:
            warmups = calibrate_warmups + warmups
        self.warmups = warmups
        self.values = self.run_bench(nvalue=args.values)

        metadata2 = self.collect_metadata()
        metadata2.update(self.metadata)
        self.metadata = metadata2

        self.metadata['loops'] = self.loops

    def create_run(self):
        start_time = monotonic_clock()
        self.compute_values()
        self.metadata['duration'] = monotonic_clock() - start_time

        return perf.Run(self.values,
                        warmups=self.warmups,
                        metadata=self.metadata,
                        collect_metadata=False)


class WorkerProcessTask(WorkerTask):
    def compute_values(self):
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

        WorkerTask.compute_values(self)

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
    def compute_values(self):
        WorkerTask.compute_values(self)
        if self.args.track_memory:
            value = self.metadata.pop('command_max_rss', None)
            if not value:
                raise RuntimeError("failed to get the process RSS")

            self.metadata['unit'] = 'byte'
            self.warmups = None
            self.values = (value,)
