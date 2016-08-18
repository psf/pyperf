from __future__ import print_function
import argparse
import errno
import math
import os
import subprocess
import sys

import six
import statistics   # Python 3.4+, or backport on Python 2.7

import perf

try:
    # Optional dependency
    import psutil
except ImportError:
    psutil = None


def _bench_suite_from_subprocess(args):
    proc = subprocess.Popen(args,
                            universal_newlines=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)

    try:
        if six.PY3:
            with proc:
                stdout, stderr = proc.communicate()
        else:
            stdout, stderr = proc.communicate()
    except:
        try:
            proc.kill()
        except OSError:
            pass
        proc.wait()
        raise

    if proc.returncode:
        sys.stdout.write(stdout)
        sys.stdout.flush()
        sys.stderr.write(stderr)
        sys.stderr.flush()
        raise RuntimeError("%s failed with exit code %s"
                           % (args[0], proc.returncode))

    return perf.BenchmarkSuite.loads(stdout)


def _display_run(bench, run_index, run,
                 common_metadata=None, raw=False, verbose=0, file=None):
    show_warmup = (verbose >= 0)

    total_loops = run.get_total_loops()
    inner_loops = run._get_inner_loops()

    def format_samples(samples, percent=True):
        samples_str = [bench._format_sample(sample) for sample in samples]
        if not percent:
            return samples_str

        median = bench.median()
        max_delta = median * 0.05
        for index, sample in enumerate(samples):
            if raw:
                sample /= total_loops
            delta = sample - median
            if abs(delta) > max_delta:
                samples_str[index] += ' (%+.0f%%)' % (delta * 100 / median)
        return samples_str

    samples = run.samples
    if raw:
        warmups = [('%s (%s)'
                    % (bench._format_sample(raw_sample),
                       perf._format_number(loops, 'loop')))
                   for loops, raw_sample in run.warmups]
        samples = [sample * total_loops for sample in samples]
    else:
        warmups = run.warmups
        if warmups:
            warmups = [raw_sample / (loops * inner_loops)
                       for loops, raw_sample in warmups]
            warmups = format_samples(warmups)
    samples = format_samples(samples)

    if raw:
        name = 'raw samples'
    else:
        name = 'samples'
    text = '%s (%s): %s' % (name, len(samples), ', '.join(samples))
    if warmups and show_warmup:
        if raw:
            name = 'raw warmup'
        else:
            name = 'warmup'
        text = ('%s (%s): %s; %s'
                % (name, len(warmups), ', '.join(warmups), text))

    text = "Run %s: %s" % (run_index, text)
    print(text, file=file)

    if verbose > 0:
        prefix = '  '
        metadata = run.get_metadata()
        for key in sorted(metadata):
            if common_metadata and key in common_metadata:
                continue
            value = metadata[key]
            print('%s%s: %s' % (prefix, key, value))


def _display_runs(bench, quiet=False, verbose=False, raw=False, file=None):
    runs = bench.get_runs()
    if quiet:
        verbose = -1
    elif verbose:
        verbose = 1
    else:
        verbose = 0

    if verbose > 0:
        common_metadata = bench.get_metadata()
        print("Metadata:", file=file)
        for key in sorted(common_metadata):
            value = common_metadata[key]
            print('  %s: %s' % (key, value), file=file)
        print(file=file)
    else:
        common_metadata = None

    for run_index, run in enumerate(runs, 1):
        _display_run(bench, run_index, run,
                     common_metadata=common_metadata,
                     verbose=verbose, raw=raw, file=file)


def _display_stats(bench, file=None):
    fmt = bench._format_sample
    samples = bench.get_samples()

    nrun = bench.get_nrun()
    nsample = len(samples)
    median = bench.median()

    # Total duration
    duration = bench.get_total_duration()
    if duration:
        print("Total duration: %s" % perf._format_seconds(duration),
              file=file)

    # Start/End dates
    dates = bench.get_dates()
    if dates:
        start, end = dates
        print("Start date: %s" % start.isoformat())
        print("End date: %s" % end.isoformat())

    # Raw sample minimize/maximum
    raw_samples = bench._get_raw_samples()
    print("Raw sample minimum: %s" % bench._format_sample(min(raw_samples)),
          file=file)
    print("Raw sample maximum: %s" % bench._format_sample(max(raw_samples)),
          file=file)
    print(file=file)

    # Number of samples
    print("Number of runs: %s" % perf._format_number(nrun), file=file)
    print("Total number of samples: %s" % perf._format_number(nsample),
          file=file)

    nsample_per_run = bench._get_nsample_per_run()
    text = perf._format_number(nsample_per_run)
    if isinstance(nsample_per_run, float):
        text += ' (average)'
    print('Number of samples per run: %s' % text, file=file)

    nwarmup = bench._get_nwarmup()
    text = perf._format_number(nwarmup)
    if isinstance(nwarmup, float):
        text += ' (average)'
    print('Number of warmups per run: %s' % text, file=file)

    # Loop iterations per sample
    loops = bench._get_loops()
    inner_loops = bench._get_inner_loops()
    total_loops = loops * inner_loops
    if isinstance(total_loops, int):
        text = perf._format_number(total_loops)
    else:
        text = "%s (average)" % total_loops

    if not(isinstance(inner_loops, int) and inner_loops == 1):
        if isinstance(loops, int):
            loops = perf._format_number(loops, 'outter-loop')
        else:
            loops = '%.1f outter-loops (average)'

        if isinstance(inner_loops, int):
            inner_loops = perf._format_number(inner_loops, 'inner-loop')
        else:
            inner_loops = "%.1f inner-loops (average)" % inner_loops

        text = '%s (%s x %s)' % (text, loops, inner_loops)

    print("Loop iterations per sample: %s" % text, file=file)
    print(file=file)

    # Minimum
    def format_limit(median, value):
        return "%s (%+.0f%%)" % (fmt(value), (value - median) * 100 / median)

    print("Minimum: %s" % format_limit(median, min(samples)), file=file)

    # Median +- std dev
    print(str(bench), file=file)

    # Mean +- std dev
    mean = statistics.mean(samples)
    if len(samples) > 2:
        stdev = statistics.stdev(samples, mean)
        print("Mean +- std dev: %s +- %s"
              % bench._format_samples((mean, stdev)),
              file=file)
    else:
        print("Mean: %s" % bench._format_sample(mean), file=file)

    # Maximum
    print("Maximum: %s" % format_limit(median, max(samples)), file=file)


def _display_histogram(benchmarks, bins=20, extend=False, file=None):
    import collections
    import shutil

    if hasattr(shutil, 'get_terminal_size'):
        columns, lines = shutil.get_terminal_size()
    else:
        columns = 80
        lines = 25

    if not bins:
        bins = max(lines - 3, 3)
        if not extend:
            bins = min(bins, 25)

    all_samples = []
    for bench, title in benchmarks:
        all_samples.extend(bench.get_samples())
    all_min = min(all_samples)
    all_max = max(all_samples)
    sample_k = float(all_max - all_min) / bins
    if not sample_k:
        sample_k = 1.0

    def sample_bucket(value):
        # round towards zero (ROUND_DOWN)
        return int(value / sample_k)
    bucket_min = sample_bucket(all_min)
    bucket_max = sample_bucket(all_max)

    for index, item in enumerate(benchmarks):
        bench, title = item
        if title:
            print("[ %s ]" % title, file=file)

        samples = bench.get_samples()

        buckets = [sample_bucket(value) for value in samples]
        counter = collections.Counter(buckets)
        count_max = max(counter.values())
        count_width = len(str(count_max))

        sample_width = max([len(bench._format_sample(bucket * sample_k))
                            for bucket in range(bucket_min, bucket_max + 1)])
        width = columns - sample_width

        line = ': %s #' % count_max
        width = columns - (sample_width + len(line))
        if not extend:
            width = min(width, 79)
        width = max(width, 3)
        line_k = float(width) / max(counter.values())
        for bucket in range(bucket_min, bucket_max + 1):
            count = counter.get(bucket, 0)
            linelen = int(round(count * line_k))
            text = bench._format_sample(bucket * sample_k)
            line = ('#' * linelen) or '|'
            print("{:>{}}: {:>{}} {}".format(text, sample_width,
                                             count, count_width, line),
                  file=file)

        if index != len(benchmarks) - 1:
            print(file=file)


def _warn_if_bench_unstable(bench):
    # FIXME: modify Benchmark constructor to avoid this annoying case?
    if not bench.get_nrun():
        raise ValueError("benchmark has no run")

    warnings = []
    warn = warnings.append
    samples = bench.get_samples()

    # Display a warning if the standard deviation is larger than 10%
    median = bench.median()
    # Avoid division by zero
    if median and len(samples) > 1:
        k = statistics.stdev(samples) / median
        if k > 0.10:
            if k > 0.20:
                warn("ERROR: the benchmark is very unstable, the standard "
                     "deviation is very high (stdev/median: %.0f%%)!"
                     % (k * 100))
            else:
                warn("WARNING: the benchmark seems unstable, the standard "
                     "deviation is high (stdev/median: %.0f%%)"
                     % (k * 100))
            warn("Try to rerun the benchmark with more runs, samples "
                 "and/or loops")
            warn("")

    # Check that the shortest sample took at least 1 ms
    shortest = min(bench._get_raw_samples())
    text = bench._format_sample(shortest)
    if shortest < 1e-3:
        if shortest < 1e-6:
            warn("ERROR: the benchmark may be very unstable, "
                 "the shortest raw sample only took %s" % text)
        else:
            warn("WARNING: the benchmark may be unstable, "
                 "the shortest raw sample only took %s" % text)
        warn("Try to rerun the benchmark with more loops "
             "or increase --min-time")
        warn("")

    return warnings


def _display_metadata(metadata, header="Metadata:", file=None):
    if not metadata:
        return
    print(header, file=file)
    for key, value in sorted(metadata.items()):
        print("- %s: %s" % (key, value), file=file)


def _display_benchmark(bench, file=None, check_unstable=True, metadata=False,
                       dump=False, stats=False, hist=False):
    if metadata:
        _display_metadata(bench.get_metadata(), file=file)
        print(file=file)

    if dump:
        _display_runs(bench, file=file)
        print(file=file)

    if hist:
        _display_histogram([(bench, None)], file=file)
        print(file=file)

    if stats:
        _display_stats(bench, file=file)
        print(file=file)

    if check_unstable:
        warnings = _warn_if_bench_unstable(bench)
        for line in warnings:
            print(line, file=file)

    print(str(bench), file=file)


class TextRunner:
    # Default parameters are chosen to have approximatively a run of 0.5 second
    # and so a total duration of 5 seconds by default
    def __init__(self, name, samples=None, warmups=None, processes=None,
                 loops=0, min_time=0.1, max_time=1.0, metadata=None,
                 inner_loops=None, _argparser=None):
        if not name:
            raise ValueError("name must be a non-empty string")

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

        self.name = name
        if metadata is not None:
            self.metadata = metadata
        else:
            self.metadata = {}

        # result of argparser.parse_args()
        self.args = None

        # callback used to prepare command line arguments to spawn a worker
        # child process. The callback is called with prepare(runner, args).
        # args must be modified in-place.
        self.prepare_subprocess_args = None

        # Command list arguments to call the program:
        # (sys.executable, sys.argv[0]) by default. For example,
        # "python3 -m perf.timeit" sets program_args to
        # (sys.executable, '-m', 'perf.timeit').
        self.program_args = (sys.executable, sys.argv[0])

        # Number of inner-loops of the sample_func for bench_sample_func()
        self.inner_loops = inner_loops

        def strictly_positive(value):
            value = int(value)
            if value <= 0:
                raise ValueError("value must be > 0")
            return value

        def positive_or_nul(value):
            value = int(value)
            if value < 0:
                raise ValueError("value must be >= 0")
            return value

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
        parser.add_argument('--stdout', action='store_true',
                            help='write results encoded to JSON into stdout')
        parser.add_argument('-o', '--output', metavar='FILENAME',
                            help='write results encoded to JSON into FILENAME')
        parser.add_argument('--append', metavar='FILENAME',
                            help='append results encoded to JSON into FILENAME')
        parser.add_argument('--min-time', type=float, default=min_time,
                            help='Minimum duration in seconds of a single '
                                 'sample, used to calibrate the number of '
                                 'loops (default: %s)'
                            % perf._format_timedelta(min_time))
        parser.add_argument('--worker', action="store_true",
                            help='worker process, run the benchmark')
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
        parser.add_argument('--tracemalloc', action="store_true",
                            help='Trace memory allocations using tracemalloc')
        parser.add_argument('--track-memory', action="store_true",
                            help='Track memory usage using a thread')
        self.argparser = parser

    def _process_args(self):
        args = self.args

        if args.quiet:
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

        filename = args.output
        if filename and os.path.exists(filename):
            print("ERROR: The JSON file %r already exists" % filename)
            sys.exit(1)

        if args.tracemalloc:
            try:
                import tracemalloc   # noqa
            except ImportError as exc:
                print("ERROR: fail to import tracemalloc: %s" % exc)
                sys.exit(1)

        if args.track_memory:
            from perf._memory import check_tracking_memory
            err_msg = check_tracking_memory()
            if err_msg:
                print("ERROR: unable to track the memory usage "
                      "(--track-memory): %s" % err_msg)
                sys.exit(1)

    def parse_args(self, args=None):
        if self.args is None:
            self.args = self.argparser.parse_args(args)
            self._process_args()
        return self.args

    def _stream(self):
        return sys.stderr if self.args.stdout else sys.stdout

    def _range(self):
        for warmup in six.moves.xrange(self.args.warmups):
            yield (True, 1 + warmup)
        for run in six.moves.xrange(self.args.samples):
            yield (False, 1 + run)

    def _cpu_affinity(self):
        stream = self._stream()

        cpus = self.args.affinity
        if not cpus:
            # --affinity option is not set: detect isolated CPUs
            isolated = True
            cpus = perf._get_isolated_cpus()
            if not cpus:
                # no isolated CPUs or unable to get the isolated CPUs
                return
        else:
            isolated = False
            cpus = perf._parse_cpu_list(cpus)

        if perf._set_cpu_affinity(cpus):
            if self.args.verbose:
                if isolated:
                    text = ("Pin process to isolated CPUs: %s"
                            % perf._format_cpu_list(cpus))
                else:
                    text = ("Pin process to CPUs: %s"
                            % perf._format_cpu_list(cpus))
                print(text, file=stream)

            if isolated:
                self.args.affinity = perf._format_cpu_list(cpus)
        else:
            if not isolated:
                print("ERROR: CPU affinity not available.", file=sys.stderr)
                print("Use Python 3.3 or newer, or install psutil dependency",
                      file=stream)
                sys.exit(1)
            else:
                print("WARNING: unable to pin worker processes to "
                      "isolated CPUs, CPU affinity not available", file=stream)
                print("Use Python 3.3 or newer, or install psutil dependency",
                      file=stream)

    def _run_bench(self, bench, sample_func, loops, nsample,
                   is_warmup=False, is_calibrate=False, calibrate=False):
        args = self.args
        stream = self._stream()
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
        inner_loops = self.inner_loops or 1
        while True:
            if index > nsample:
                break

            raw_sample = sample_func(loops)
            sample = float(raw_sample) / (loops * inner_loops)
            if is_warmup:
                value = raw_sample
            else:
                value = sample

            # FIXME: if the value is zero, drop it in calibration mode,
            # or raise an error in non-calibration mode

            # The most accurate time has a resolution of 1 nanosecond. We
            # compute a difference between two timer values. When formatted to
            # decimal, the difference can show more than 9 decimal digits after
            # the dot. Round manually to 10^-9 to produce more compact JSON
            # files and don't pretend to have a better resolution than 1
            # nanosecond.
            value = round(value, 9)
            if is_warmup:
                samples.append((loops, value))
            else:
                samples.append(value)

            if args.verbose:
                text = bench._format_sample(sample)
                if is_warmup or is_calibrate:
                    text = ('%s (%s: %s)'
                            % (text,
                               perf._format_number(loops, 'loop'),
                               bench._format_sample(raw_sample)))
                text = ("%s %s: %s"
                        % (sample_name, index, text))
                print(text, file=stream)

            if calibrate and raw_sample < args.min_time:
                loops *= 2
                if loops > 2 ** 32:
                    raise ValueError("error in calibration, loops is "
                                     "too big: %s" % loops)
                # need more samples for the calibration
                nsample += 1

            index += 1

        if args.verbose:
            print(file=stream)

        # Run collects metadata
        return (loops, samples)

    def _calibrate(self, bench, sample_func):
        return self._run_bench(bench, sample_func,
                               loops=1, nsample=1,
                               calibrate=True,
                               is_calibrate=True, is_warmup=True)

    def _worker(self, bench, sample_func):
        args = self.args
        loops = args.loops
        metadata = dict(self.metadata)
        start_time = perf.monotonic_clock()
        stream = self._stream()

        calibrate = (not loops)
        if calibrate:
            loops, calibrate_warmups = self._calibrate(bench, sample_func)
        else:
            if perf.python_has_jit():
                # With a JIT, continue to calibrate during warmup
                calibrate = True
            calibrate_warmups = None

        if args.track_memory:
            from perf._memory import PeakMemoryUsageThread
            mem_thread = PeakMemoryUsageThread()
            mem_thread.start()
        else:
            mem_thread = None

        if args.tracemalloc:
            try:
                import tracemalloc
            except ImportError as exc:
                args.tracemalloc = False
                print("WARNING: fail to import tracemalloc: %s"
                       % exc, file=stream)
            else:
                tracemalloc.start()

        if args.warmups:
            loops, warmups = self._run_bench(bench, sample_func, loops,
                                             args.warmups,
                                             is_warmup=True, calibrate=calibrate)
        else:
            warmups = ()
        if calibrate_warmups:
            warmups = calibrate_warmups + warmups
        loops, samples = self._run_bench(bench, sample_func, loops,
                                         args.samples)

        if args.tracemalloc:
            traced_peak = tracemalloc.get_traced_memory()[1]
            if traced_peak:
                metadata['mem_tracemalloc_peak'] = traced_peak

        if mem_thread is not None:
            mem_thread.stop()
            if mem_thread.peak_usage:
                # FIXME: rename it to "mem_uss_peak" on Linux
                # FIXME: rename it to "mem_peak_pagefile" on Windows
                metadata['mem_peak'] = mem_thread.peak_usage

        duration = perf.monotonic_clock() - start_time
        metadata['duration'] = duration
        metadata['name'] = self.name
        metadata['loops'] = loops
        if self.inner_loops is not None and self.inner_loops != 1:
            metadata['inner_loops'] = self.inner_loops

        run = perf.Run(samples, warmups=warmups, metadata=metadata)
        bench.add_run(run)
        self._display_result(bench, check_unstable=False)

        # Save loops into args
        args.loops = loops

    def _main(self, sample_func):
        args = self.parse_args()

        self._cpu_affinity()

        bench = perf.Benchmark()

        try:
            if args.worker:
                self._worker(bench, sample_func)
            else:
                self._spawn_workers(bench, sample_func)
        except KeyboardInterrupt:
            print("Interrupted: exit", file=sys.stderr)
            sys.exit(1)

        return bench

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

        return self._main(sample_func)

    def _spawn_worker(self):
        args = self.args

        cmd = []
        cmd.extend(self.program_args)
        cmd.extend(('--worker', '--stdout',
                     '--samples', str(args.samples),
                     '--warmups', str(args.warmups),
                     '--loops', str(args.loops),
                     '--min-time', str(args.min_time)))
        if args.verbose:
            cmd.append('-' + 'v' * args.verbose)
        if args.affinity:
            cmd.append('--affinity=%s' % args.affinity)
        if args.tracemalloc:
            cmd.append('--tracemalloc')
        if args.track_memory:
            cmd.append('--track-memory')

        if self.prepare_subprocess_args:
            self.prepare_subprocess_args(self, cmd)

        return _bench_suite_from_subprocess(cmd)

    def _display_result(self, bench, check_unstable=True):
        stream = self._stream()
        args = self.args

        # Display the average +- stdev
        if self.args.quiet:
            check_unstable = False
        _display_benchmark(bench,
                           file=stream,
                           check_unstable=check_unstable,
                           metadata=args.metadata,
                           dump=args.dump,
                           stats=args.stats,
                           hist=args.hist)

        stream.flush()
        if args.append:
            perf.add_runs(args.append, bench)

        if args.stdout:
            try:
                bench.dump(sys.stdout)
            except IOError as exc:
                if exc.errno != errno.EPIPE:
                    raise
                # ignore broken pipe error

                # Close stdout to avoid the warning "Exception ignored in: ..."
                # at exit
                try:
                    sys.stdout.close()
                except IOError:
                    # close() is likely to fail with EPIPE (BrokenPipeError)
                    pass

        if args.output:
            bench.dump(args.output)

    def _spawn_workers(self, bench, sample_func):
        args = self.args
        verbose = args.verbose
        quiet = args.quiet
        stream = self._stream()
        nprocess = args.processes

        if not args.loops:
            args.loops, warmups = self._calibrate(bench, sample_func)
            # drop warmup samples

        for process in range(nprocess):
            run_suite = self._spawn_worker()

            run_benchmarks = run_suite.get_benchmarks()
            if len(run_benchmarks) != 1:
                raise ValueError("worker produced %s benchmarks instead of 1"
                                 % len(run_benchmarks))
            run_bench = run_benchmarks[0]

            bench.add_runs(run_bench)

            if verbose:
                run = bench.get_runs()[-1]
                run_index = '%s/%s' % (1 + process, nprocess)
                _display_run(bench, run_index, run, file=stream)
            elif not quiet:
                print(".", end='', file=stream)
                stream.flush()

        if not quiet:
            print(file=stream)

        self._display_result(bench)
