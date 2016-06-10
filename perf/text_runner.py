from __future__ import print_function
import argparse
import functools
import io
import os
import subprocess
import sys

import perf


def _json_dump(result, args):
    if args.json_file:
        # --json-file=FILENAME
        if perf._PY3:
            fp = open(args.json_file, "w", encoding="utf-8")
        else:
            fp = open(args.json_file, "wb")
        with fp:
            result.json_dump_into(fp)
            fp.flush()
    elif args.json:
        # --json
        stdout = sys.stdout
        result.json_dump_into(stdout)
        stdout.flush()


def _get_isolated_cpus():
    path = '/sys/devices/system/cpu/isolated'
    try:
        fp = io.open(path, encoding='ascii')
        with fp:
            isolated = fp.readline().rstrip()
    except (OSError, IOError):
        # missing file
        return

    if not isolated:
        # no CPU isolated
        return

    cpus = []
    for part in isolated.split(','):
        if '-' in part:
            parts = part.split('-', 1)
            first = int(parts[0])
            last = int(parts[1])
            for cpu in range(first, last+1):
                cpus.append(cpu)
        else:
            cpus.append(int(part))
    return cpus


class TextRunner:
    def __init__(self, name=None, nsample=3, nwarmup=1, nprocess=25,
                 nloop=0, min_time=0.1, max_time=1.0):
        self.name = name
        self.result = perf.RunResult()
        # result of argparser.parse_args()
        self.args = None

        # callback used to create command arguments to spawn a worker child
        # process. The callback is called with prepare(runner, args). args
        # must be modified in-place.
        self.prepare_subprocess_args = None

        # Number of inner-loops of the sample_func for bench_sample_func()
        self.inner_loops = 1

        parser = argparse.ArgumentParser(description='Benchmark')
        parser.add_argument('-p', '--processes', type=int, default=nprocess,
                            help='number of processes used to run benchmarks (default: %s)'
                                 % nprocess)
        parser.add_argument('-n', '--samples', dest="nsample",
                            type=int, default=nsample,
                            help='number of samples per process (default: %s)'
                                 % nsample)
        parser.add_argument('-w', '--warmups', dest="nwarmup",
                            type=int, default=nwarmup,
                            help='number of skipped samples per run used to warmup the benchmark (default: %s)'
                                 % nwarmup)
        parser.add_argument('-l', '--loops', type=int, default=nloop,
                            help='number of loops per sample, 0 means '
                                 'automatic calibration (default: %s)'
                                 % nloop)
        parser.add_argument('-v', '--verbose', action='count', default=0,
                            help='enable verbose mode')
        parser.add_argument('--json', action='store_true',
                            help='write results encoded to JSON into stdout')
        parser.add_argument('--json-file', metavar='FILENAME',
                            help='write results encoded to JSON into FILENAME')
        parser.add_argument('--min-time', type=float, default=0.1,
                            help='Minimum duration in seconds of a single '
                                 'sample, used to calibrate the number of '
                                 'loops (default: 100 ms)')
        parser.add_argument('--max-time', type=float, default=1.0,
                            help='Maximum duration in seconds of a single '
                                 'sample, used to calibrate the number of '
                                 'loops (default: 1 sec)')
        parser.add_argument('--raw', action="store_true",
                            help='run a single process')
        parser.add_argument('--metadata', action="store_true",
                            help='show metadata')
        self.argparser = parser

    def _calibrate_sample_func(self, sample_func):
        stream = self._stream()
        timer = perf.perf_counter

        min_dt = self.args.min_time * 0.90
        max_dt = self.args.max_time
        for index in range(0, 10):
            # FIXME: add a check to detect bugs in sample_func(): put a limit?
            loops = 10 ** index

            dt = sample_func(loops)
            if self.args.verbose > 1:
                print("calibration: 10^%s loops: %s"
                      % (index, perf._format_timedelta(dt)),
                      file=stream)

            if dt >= max_dt:
                index = max(index - 1, 0)
                loops = 10 ** index
                break
            if dt >= min_dt:
                break
        if self.args.verbose > 1:
            print("calibration: use %s" % perf._format_number(loops, 'loop'),
                  file=stream)

        return loops

    def parse_args(self, args=None):
        if self.args is not None:
            # arguments already parsed
            return

        self.args = self.argparser.parse_args(args)
        if self.args.verbose:
            self.args.metadata = True

    def _stream(self):
        return sys.stderr if self.args.json else sys.stdout

    def _range(self):
        # FIXME: use six.range
        for warmup in range(self.args.nwarmup):
            yield (True, warmup)
        for run in range(self.args.nsample):
            yield (False, run)

    def _add(self, is_warmup, run, sample):
        if is_warmup:
            self.result.warmups.append(sample)
        else:
            self.result.samples.append(sample)

        if self.args.verbose:
            text = self.result._format_sample(sample)
            if is_warmup:
                text = "Warmup %s: %s" % (1 + run, text)
            else:
                text = "Sample %s: %s" % (1 + run, text)
            print(text, file=self._stream())

    def _display_result(self):
        stream = self._stream()

        if self.args.metadata:
            perf._display_metadata(self.result.metadata, file=stream)

        text = self.result.format(self.args.verbose)
        nsample = perf._format_number(len(self.result.samples), 'sample')
        text = "Average: %s (%s)" % (text, nsample)
        print(text, file=self._stream())

        stream.flush()
        _json_dump(self.result, self.args)

    def _cpu_affinity(self):
        # FIXME: support also Python 2 using taskset command
        if not hasattr(os, 'sched_setaffinity'):
            # missing os.sched_setaffinity()
            return

        isolated_cpus = _get_isolated_cpus()
        if not isolated_cpus:
            # no CPU isolated, or able to get the info
            return

        if self.args.verbose:
            print("Set affinity to isolated CPUs: %s" % isolated_cpus,
                  file=self._stream())
        os.sched_setaffinity(0, isolated_cpus)

    def _worker(self, sample_func):
        loops = self.args.loops
        if loops < 1:
            # FIXME: move this check in argument parsing
            raise ValueError("--loops must be >= 1")

        # only import metadata submodule in worker processes
        import perf.metadata
        perf.metadata.collect_metadata(self.result.metadata)
        self.result.metadata['loops'] = perf._format_number(loops)
        if self.inner_loops != 1:
            self.result.metadata['inner_loops'] = perf._format_number(self.inner_loops)

        for is_warmup, run in self._range():
            dt = sample_func(loops)
            dt = float(dt) / loops / self.inner_loops
            self._add(is_warmup, run, dt)

        self._display_result()

        result = perf.Results(name=self.name)
        result.runs.append(self.result)
        return result

    def _main(self, sample_func):
        self.parse_args()

        self._cpu_affinity()

        if self.args.loops == 0:
            self.args.loops = self._calibrate_sample_func(sample_func)

        if not self.args.raw:
            return self._spawn_workers()
        else:
            return self._worker(sample_func)

    def bench_sample_func(self, sample_func, *args):
        """"Benchmark sample_func(loops, *args)

        The function must return the total elapsed time, not the average time
        per loop iteration. The total elapsed time is required to be able
        to automatically calibrate the number of loops.

        perf.perf_counter() should be used to measure the elapsed time.
        """

        if not args:
            return self._main(sample_func)

        def wrap_sample_func(loops):
            return sample_func(loops, *args)

        return self._main(wrap_sample_func)

    def bench_func(self, func, *args):
        """"Benchmark func(*args)."""

        def sample_func(loops):
            # use fast local variables
            local_timer = perf.perf_counter
            local_func = func
            local_args = args

            if local_args:
                if loops != 1:
                    range_it = range(loops)

                    t0 = local_timer()
                    for _ in range_it:
                        local_func(*local_args)
                    dt = local_timer() - t0
                else:
                    t0 = local_timer()
                    local_func(*local_args)
                    dt = local_timer() - t0
            else:
                if loops != 1:
                    range_it = range(loops)

                    t0 = local_timer()
                    for _ in range_it:
                        local_func()
                    dt = local_timer() - t0
                else:
                    t0 = local_timer()
                    local_func()
                    dt = local_timer() - t0

            return dt

        return self._main(sample_func)

    def _run_subprocess(self):
        args = [sys.executable, sys.argv[0],
                '--raw', '--json',
                '--samples', str(self.args.nsample),
                '--warmups', str(self.args.nwarmup),
                '--loops', str(self.args.loops)]
        if self.args.verbose:
            args.append('-' + 'v' * self.args.verbose)

        if self.prepare_subprocess_args:
            self.prepare_subprocess_args(self, args)

        return perf.RunResult.from_subprocess(args, stderr=subprocess.PIPE)

    def _spawn_workers(self):
        verbose = self.args.verbose
        stream = self._stream()
        nprocess = self.args.processes
        result = perf.Results(self.name)

        for process in range(nprocess):
            run = self._run_subprocess()
            result.runs.append(run)
            if verbose > 1:
                text = perf._very_verbose_run(run)
                print("Run %s/%s: %s" % (1 + process, nprocess, text), file=stream)
            else:
                print(".", end='', file=stream)
                stream.flush()

        if verbose <= 1:
            print(file=stream)

        if self.args.metadata:
            perf._display_metadata(result.get_metadata(), file=stream)

        print("Average: %s" % result.format(verbose), file=stream)

        stream.flush()
        _json_dump(result, self.args)
        return result
