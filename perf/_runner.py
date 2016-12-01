from __future__ import division, print_function, absolute_import

import argparse
import errno
import math
import os
import subprocess
import sys

import six

import perf
from perf._cli import format_run, format_benchmark, multiline_output
from perf._bench import _load_suite_from_pipe
from perf._cpu_utils import (format_cpu_list, parse_cpu_list,
                             get_isolated_cpus, set_cpu_affinity)
from perf._formatter import format_timedelta, format_number, format_sample
from perf._utils import (MS_WINDOWS, popen_killer,
                         abs_executable, create_environ, pipe_cloexec)

try:
    # Optional dependency
    import psutil
except ImportError:
    psutil = None


class Runner:
    # Default parameters are chosen to have approximatively a run of 0.5 second
    # and so a total duration of 5 seconds by default
    def __init__(self, samples=None, warmups=None, processes=None,
                 loops=0, min_time=0.1, max_time=1.0, metadata=None,
                 show_name=True,
                 program_args=None, add_cmdline_args=None,
                 _argparser=None):
        has_jit = perf.python_has_jit()
        if not samples:
            if has_jit:
                # Since PyPy JIT has less processes:
                # run more samples per process
                samples = 10
            else:
                samples = 3
        if not warmups:
            if has_jit:
                # PyPy JIT needs a longer warmup (at least 1 second)
                warmups = int(math.ceil(1.0 / min_time))
            else:
                warmups = 1
        if not processes:
            if has_jit:
                # Use less processes than non-JIT, because JIT requires more
                # warmups and so each worker is slower
                processes = 6
            else:
                processes = 20

        if metadata is not None:
            self.metadata = metadata
        else:
            self.metadata = {}

        # Worker task identifier: count how many times _worker() was called,
        # see the --worker-task command line option
        self._worker_task = 0

        # result of argparser.parse_args()
        self.args = None

        # callback used to prepare command line arguments to spawn a worker
        # child process. The callback is called with prepare(runner.args, cmd).
        # args must be modified in-place.
        self._add_cmdline_args = add_cmdline_args

        # Command list arguments to call the program: (sys.argv[0],) by
        # default.
        #
        # For example, "python3 -m perf timeit" sets program_args to
        # ('-m', 'perf', 'timeit').
        if program_args:
            self._program_args = program_args
        else:
            self._program_args = (sys.argv[0],)
        self._show_name = show_name

        def strictly_positive(value):
            value = int(value)
            if value <= 0:
                raise ValueError("value must be > 0")
            return value

        def positive_or_nul(value):
            if '^' in value:
                x, _, y = value.partition('^')
                x = int(x)
                y = int(y)
                value = x ** y
            else:
                value = int(value)
            if value < 0:
                raise ValueError("value must be >= 0")
            return value

        def comma_separated(values):
            values = [value.strip() for value in values.split(',')]
            return list(filter(None, values))

        if _argparser is not None:
            parser = _argparser
        else:
            parser = argparse.ArgumentParser()
        parser.description = 'Benchmark'
        parser.add_argument('--rigorous', action="store_true",
                            help='Spend longer running tests '
                                 'to get more accurate results')
        parser.add_argument('--fast', action="store_true",
                            help='Get rough answers quickly')
        parser.add_argument("--debug-single-sample", action="store_true",
                            help="Debug mode, only collect a single sample")
        parser.add_argument('-p', '--processes',
                            type=strictly_positive, default=processes,
                            help='number of processes used to run benchmarks '
                                 '(default: %s)' % processes)
        parser.add_argument('-n', '--samples', dest="samples",
                            type=strictly_positive, default=samples,
                            help='number of samples per process (default: %s)'
                                 % samples)
        parser.add_argument('-w', '--warmups', dest="warmups",
                            type=positive_or_nul, default=warmups,
                            help='number of skipped samples per run used '
                                 'to warmup the benchmark (default: %s)'
                                 % warmups)
        parser.add_argument('-l', '--loops',
                            type=positive_or_nul, default=loops,
                            help='number of loops per sample, 0 means '
                                 'automatic calibration (default: %s)'
                            % loops)
        parser.add_argument('-v', '--verbose', action="store_true",
                            help='enable verbose mode')
        parser.add_argument('-q', '--quiet', action="store_true",
                            help='enable quiet mode')
        parser.add_argument('--pipe', type=int, metavar="FD",
                            help='Write benchmarks encoded as JSON '
                                 'into the pipe FD')
        parser.add_argument('-o', '--output', metavar='FILENAME',
                            help='write results encoded to JSON into FILENAME')
        parser.add_argument('--append', metavar='FILENAME',
                            help='append results encoded to JSON into FILENAME')
        parser.add_argument('--min-time', type=float, default=min_time,
                            help='Minimum duration in seconds of a single '
                                 'sample, used to calibrate the number of '
                                 'loops (default: %s)'
                            % format_timedelta(min_time))
        parser.add_argument('--worker', action='store_true',
                            help='Worker process, run the benchmark.')
        parser.add_argument('--worker-task', type=positive_or_nul, metavar='TASK_ID',
                            help='Identifier of the worker task: '
                                 'only execute the benchmark function TASK_ID')
        parser.add_argument('--calibrate', action="store_true",
                            help="only calibrate the benchmark, "
                                 "don't compute samples")
        parser.add_argument('-d', '--dump', action="store_true",
                            help='display benchmark run results')
        parser.add_argument('--metadata', '-m', action="store_true",
                            help='show metadata')
        parser.add_argument('--hist', '-g', action="store_true",
                            help='display an histogram of samples')
        parser.add_argument('--stats', '-t', action="store_true",
                            help='display statistics (min, max, ...)')
        parser.add_argument("--affinity", metavar="CPU_LIST", default=None,
                            help='Specify CPU affinity for worker processes. '
                                 'This way, benchmarks can be forced to run '
                                 'on a given set of CPUs to minimize run to '
                                 'run variation. By default, worker processes '
                                 'are pinned to isolate CPUs if isolated CPUs '
                                 'are found.')
        parser.add_argument("--inherit-environ", metavar='VARS',
                            type=comma_separated,
                            help='Comma-separated list of environment '
                                 'variables inherited by worker child '
                                 'processes.')
        parser.add_argument("--python", default=sys.executable,
                            help='Python executable '
                                 '(default: use running Python, '
                                 'sys.executable)')

        memory = parser.add_mutually_exclusive_group()
        memory.add_argument('--tracemalloc', action="store_true",
                            help='Trace memory allocations using tracemalloc')
        memory.add_argument('--track-memory', action="store_true",
                            help='Track memory usage using a thread')

        self.argparser = parser

    def _multiline_output(self):
        return self.args.verbose or multiline_output(self.args)

    def _process_args(self):
        args = self.args

        if args.pipe:
            args.quiet = True
            args.verbose = False
        elif args.quiet:
            args.verbose = False

        nprocess = self.argparser.get_default('processes')
        nsamples = self.argparser.get_default('samples')
        if args.rigorous:
            args.processes = nprocess * 2
            # args.samples = nsamples * 5 // 3
        elif args.fast:
            # use at least 3 processes to benchmark 3 different (randomized)
            # hash functions
            args.processes = max(nprocess // 2, 3)
            args.samples = max(nsamples * 2 // 3, 2)
        elif args.debug_single_sample:
            args.processes = 1
            args.warmups = 0
            args.samples = 1
            args.loops = 1
            args.min_time = 1e-9

        if args.calibrate:
            if not args.worker:
                print("ERROR: Calibration can only be done "
                      "in a worker process")
                sys.exit(1)

            args.loops = 0
            # calibration samples will be stored as warmup samples
            args.warmups = 0
            args.samples = 0

        filename = args.output
        if filename and os.path.exists(filename):
            print("ERROR: The JSON file %r already exists" % filename)
            sys.exit(1)

        if args.worker_task and not args.worker:
            print("ERROR: --worker-task can only be used with --worker")
            sys.exit(1)

        if args.tracemalloc:
            try:
                import tracemalloc   # noqa
            except ImportError as exc:
                print("ERROR: fail to import tracemalloc: %s" % exc)
                sys.exit(1)

        if args.track_memory:
            if MS_WINDOWS:
                from perf._win_memory import check_tracking_memory
            else:
                from perf._memory import check_tracking_memory
            err_msg = check_tracking_memory()
            if err_msg:
                print("ERROR: unable to track the memory usage "
                      "(--track-memory): %s" % err_msg)
                sys.exit(1)

        args.python = abs_executable(args.python)

    def parse_args(self, args=None):
        if self.args is None:
            self.args = self.argparser.parse_args(args)
            self._process_args()
        return self.args

    def _range(self):
        for warmup in six.moves.xrange(self.args.warmups):
            yield (True, 1 + warmup)
        for run in six.moves.xrange(self.args.samples):
            yield (False, 1 + run)

    def _cpu_affinity(self):
        cpus = self.args.affinity
        if not cpus:
            # --affinity option is not set: detect isolated CPUs
            isolated = True
            cpus = get_isolated_cpus()
            if not cpus:
                # no isolated CPUs or unable to get the isolated CPUs
                return
        else:
            isolated = False
            cpus = parse_cpu_list(cpus)

        if set_cpu_affinity(cpus):
            if self.args.verbose:
                if isolated:
                    text = ("Pin process to isolated CPUs: %s"
                            % format_cpu_list(cpus))
                else:
                    text = ("Pin process to CPUs: %s"
                            % format_cpu_list(cpus))
                print(text)

            if isolated:
                self.args.affinity = format_cpu_list(cpus)
        else:
            if not isolated:
                print("ERROR: CPU affinity not available.", file=sys.stderr)
                print("Use Python 3.3 or newer, or install psutil dependency")
                sys.exit(1)
            elif not self.args.quiet:
                print("WARNING: unable to pin worker processes to "
                      "isolated CPUs, CPU affinity not available")
                print("Use Python 3.3 or newer, or install psutil dependency")

    def _run_bench(self, metadata, sample_func, inner_loops, loops, nsample,
                   is_warmup=False, is_calibrate=False, calibrate=False):
        unit = metadata.get('unit')
        args = self.args
        if loops <= 0:
            raise ValueError("loops must be >= 1")

        if is_calibrate:
            sample_name = 'Calibration'
        elif is_warmup:
            sample_name = 'Warmup'
        else:
            sample_name = 'Sample'

        samples = []
        index = 1
        if not inner_loops:
            inner_loops = 1
        while True:
            if index > nsample:
                break

            raw_sample = sample_func(loops)
            raw_sample = float(raw_sample)
            sample = raw_sample / (loops * inner_loops)
            if is_warmup:
                value = raw_sample
            else:
                value = sample

            if not value and not(is_calibrate or is_warmup):
                raise ValueError("sample function returned zero")

            if is_warmup:
                samples.append((loops, value))
            else:
                samples.append(value)

            if args.verbose:
                text = format_sample(unit, sample)
                if is_warmup or is_calibrate:
                    text = ('%s (%s: %s)'
                            % (text,
                               format_number(loops, 'loop'),
                               format_sample(unit, raw_sample)))
                print("%s %s: %s" % (sample_name, index, text))

            if calibrate and raw_sample < args.min_time:
                loops *= 2
                if loops > 2 ** 32:
                    raise ValueError("error in calibration, loops is "
                                     "too big: %s" % loops)
                # need more samples for the calibration
                nsample += 1

            index += 1

        if args.verbose:
            if is_calibrate:
                print("Calibration: use %s loops" % format_number(loops))
            print()

        # Run collects metadata
        return (loops, samples)

    def _calibrate(self, sample_func, metadata=None, inner_loops=None):
        if metadata is None:
            metadata = {}
        return self._run_bench(metadata, sample_func, inner_loops,
                               loops=1, nsample=1,
                               calibrate=True,
                               is_calibrate=True, is_warmup=True)

    def _worker_run_bench(self, metadata, sample_func, inner_loops):
        args = self.args
        loops = args.loops

        calibrate = (not loops)
        if calibrate:
            loops, calibrate_warmups = self._calibrate(sample_func, metadata,
                                                       inner_loops)
        else:
            if perf.python_has_jit():
                # With a JIT, continue to calibrate during warmup
                calibrate = True
            calibrate_warmups = None

        if args.warmups:
            loops, warmups = self._run_bench(metadata, sample_func, inner_loops,
                                             loops, args.warmups,
                                             is_warmup=True, calibrate=calibrate)
        else:
            warmups = []
        if calibrate_warmups:
            warmups = calibrate_warmups + warmups
        loops, samples = self._run_bench(metadata, sample_func, inner_loops,
                                         loops, args.samples)

        return (loops, warmups, samples)

    def _worker_run_bench_mem(self, metadata, sample_func, inner_loops):
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

        loops, warmups, samples = self._worker_run_bench(metadata, sample_func,
                                                         inner_loops)

        if args.tracemalloc:
            traced_peak = tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()

            if not traced_peak:
                raise RuntimeError("tracemalloc didn't trace any Python "
                                   "memory allocation")

            # drop timings, replace them with the memory peak
            metadata['unit'] = 'byte'
            warmups = None
            samples = (float(traced_peak),)

        if args.track_memory:
            if MS_WINDOWS:
                mem_peak = get_peak_pagefile_usage()
            else:
                mem_thread.stop()
                mem_peak = mem_thread.peak_usage

            if not mem_peak:
                raise RuntimeError("failed to get the memory peak usage")

            # drop timings, replace them with the memory peak
            metadata['unit'] = 'byte'
            warmups = None
            samples = (float(mem_peak),)

        return (loops, warmups, samples)

    def _worker(self, name, sample_func, inner_loops, func_metadata):
        metadata = dict(self.metadata, name=name)
        if func_metadata:
            metadata.update(func_metadata)
        start_time = perf.monotonic_clock()

        self._cpu_affinity()

        loops, warmups, samples = self._worker_run_bench_mem(metadata,
                                                             sample_func,
                                                             inner_loops)

        duration = perf.monotonic_clock() - start_time
        metadata['duration'] = duration
        metadata['loops'] = loops
        if inner_loops is not None:
            metadata['inner_loops'] = inner_loops

        run = perf.Run(samples, warmups=warmups, metadata=metadata)
        bench = perf.Benchmark((run,))
        self._display_result(bench, checks=False)
        return bench

    def _main(self, name, sample_func, inner_loops, metadata):
        if not name.strip():
            raise ValueError("name must be a non-empty string")

        args = self.parse_args()

        if (self.args.worker_task is not None
           and self.args.worker_task != self._worker_task):
            # Skip the benchmark if it's not the expected worker task
            self._worker_task += 1
            return None

        try:
            if args.worker:
                bench = self._worker(name, sample_func, inner_loops, metadata)
            else:
                bench = self._master()
        except KeyboardInterrupt:
            what = "Benchmark worker" if args.worker else "Benchmark"
            print("%s interrupted: exit" % what, file=sys.stderr)
            sys.exit(1)

        self._worker_task += 1
        return bench

    def _no_keyword_argument(self, kwargs):
        if not kwargs:
            return

        args = ', '.join(map(repr, sorted(kwargs)))
        raise TypeError('unexpected keyword argument %s' % args)

    def bench_sample_func(self, name, sample_func, *args, **kwargs):
        """"Benchmark sample_func(loops, *args)

        The function must return the total elapsed time, not the average time
        per loop iteration. The total elapsed time is required to be able
        to automatically calibrate the number of loops.

        perf.perf_counter() should be used to measure the elapsed time.
        """
        inner_loops = kwargs.pop('inner_loops', None)
        metadata = kwargs.pop('metadata', None)
        self._no_keyword_argument(kwargs)

        if not args:
            return self._main(name, sample_func, inner_loops, metadata)

        def wrap_sample_func(loops):
            return sample_func(loops, *args)

        return self._main(name, wrap_sample_func, inner_loops, metadata)

    def bench_func(self, name, func, *args, **kwargs):
        """"Benchmark func(*args)."""

        inner_loops = kwargs.pop('inner_loops', None)
        metadata = kwargs.pop('metadata', None)
        self._no_keyword_argument(kwargs)

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
                # fast-path when func has no argument: avoid the expensive
                # func(*args) argument unpacking

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

        return self._main(name, sample_func, inner_loops, metadata)

    def timeit(self, name, stmt, setup="pass", inner_loops=None,
               duplicate=None, metadata=None):
        from perf._timeit import bench_timeit
        return bench_timeit(self, name, stmt, setup, inner_loops, duplicate, metadata)

    def _worker_cmd(self, calibrate, wpipe):
        args = self.args

        cmd = [args.python]
        cmd.extend(self._program_args)
        cmd.extend(('--worker', '--pipe', str(wpipe),
                    '--worker-task=%s' % self._worker_task,
                    '--samples', str(args.samples),
                    '--warmups', str(args.warmups),
                    '--loops', str(args.loops),
                    '--min-time', str(args.min_time)))
        if calibrate:
            cmd.append('--calibrate')
        if args.verbose:
            cmd.append('-' + 'v' * args.verbose)
        if args.affinity:
            cmd.append('--affinity=%s' % args.affinity)
        if args.tracemalloc:
            cmd.append('--tracemalloc')
        if args.track_memory:
            cmd.append('--track-memory')

        if self._add_cmdline_args:
            self._add_cmdline_args(cmd, self.args)

        return cmd

    def _spawn_worker(self, calibrate=False):
        rpipe, wpipe = pipe_cloexec()
        if six.PY3:
            rfile = open(rpipe, "r", encoding="utf8")
        else:
            rfile = os.fdopen(rpipe, "r")

        with rfile:
            try:
                cmd = self._worker_cmd(calibrate, wpipe)
                env = create_environ(self.args.inherit_environ)

                kw = {}
                if sys.version_info >= (3, 2):
                    kw['pass_fds'] = [wpipe]
                proc = subprocess.Popen(cmd, env=env, **kw)
            finally:
                os.close(wpipe)

            with popen_killer(proc):
                bench_json = rfile.read()
                rfile.close()

                exitcode = proc.wait()

        if exitcode:
            raise RuntimeError("%s failed with exit code %s"
                               % (cmd[0], exitcode))

        return _load_suite_from_pipe(bench_json)

    def _display_result(self, bench, checks=True):
        args = self.args

        # Display the average +- stdev
        if self.args.quiet:
            checks = False

        if args.pipe is not None:
            fd = args.pipe
            if six.PY3:
                wpipe = open(fd, "w", encoding="utf8")
            else:
                wpipe = os.fdopen(fd, "w")

            with wpipe:
                try:
                    bench.dump(wpipe)
                except IOError as exc:
                    if exc.errno != errno.EPIPE:
                        raise
                    # ignore broken pipe error
        else:
            lines = format_benchmark(bench,
                                     checks=checks,
                                     metadata=args.metadata,
                                     dump=args.dump,
                                     stats=args.stats,
                                     hist=args.hist,
                                     show_name=self._show_name)
            for line in lines:
                print(line)

            sys.stdout.flush()

        if args.append:
            perf.add_runs(args.append, bench)

        if args.output:
            if self._worker_task >= 1:
                perf.add_runs(args.output, bench)
            else:
                bench.dump(args.output)

    def _spawn_workers(self, newline=True):
        bench = None
        args = self.args
        verbose = args.verbose
        quiet = args.quiet
        nprocess = args.processes
        old_loops = self.args.loops
        need_calibration = (not args.loops)
        if need_calibration:
            nprocess += 1
        calibrate = need_calibration

        if verbose and self._worker_task > 0:
            print()

        for process in range(1, nprocess + 1):
            suite = self._spawn_worker(calibrate)

            benchmarks = suite.get_benchmarks()
            if len(benchmarks) != 1:
                raise ValueError("worker produced %s benchmarks instead of 1"
                                 % len(benchmarks))
            worker_bench = benchmarks[0]

            if verbose:
                run = worker_bench.get_runs()[-1]
                run_index = '%s/%s' % (process, nprocess)
                for line in format_run(worker_bench, run_index, run):
                    print(line)
            elif not quiet:
                print(".", end='')

            if calibrate:
                # Use the first worker to calibrate the benchmark. Use a worker
                # process rather than the main process because worker is a
                # little bit more isolated and so should be more reliable.
                first_run = worker_bench.get_runs()[0]
                args.loops = first_run._get_loops()
                if verbose:
                    print("Calibration: use %s loops" % format_number(args.loops))
            calibrate = False

            if bench is not None:
                bench.add_runs(worker_bench)
            else:
                bench = worker_bench

            sys.stdout.flush()

        if not quiet and newline:
            print()

        # restore the old value of loops, to recalibrate for the next
        # benchmark function if loops=0
        args.loops = old_loops

        return bench

    def _master(self):
        bench = self._spawn_workers()
        self._display_result(bench)
        return bench
