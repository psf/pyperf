from __future__ import print_function
import argparse
import errno
import os
import subprocess
import sys

import six
import statistics   # Python 3.4+, or backport on Python 2.7

try:
    # Optional dependency
    import psutil
except ImportError:
    psutil = None

import perf.metadata


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
    loops = run.loops * run.inner_loops
    raw_samples = run._get_raw_samples(warmups=True)
    if not raw:
        samples = [sample / loops for sample in raw_samples]
    else:
        samples = raw_samples

    samples_str = list(bench._format_samples(samples))

    median = bench.median()
    max_delta = median * 0.05
    for index, sample in enumerate(samples):
        if raw:
            sample /= loops
        delta = sample - median
        if abs(delta) > max_delta:
            samples_str[index] += ' (%+.0f%%)' % (delta * 100 / median)

    # FIXME: don't use private attribute
    nwarmup = run._warmups
    if nwarmup:
        warmups = samples_str[:nwarmup]
        samples = samples_str[nwarmup:]
    else:
        samples = samples_str

    if raw:
        name = 'raw samples'
    else:
        name = 'samples'
    text = '%s (%s): %s' % (name, len(samples), ', '.join(samples))
    if nwarmup and verbose >= 0:
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

    warmups = bench.get_warmups()
    text = perf._format_number(warmups)
    if isinstance(warmups, float):
        text += ' (average)'
    print('Number of warmups per run: %s' % text, file=file)

    # Loop iterations per sample
    loops = bench.get_loops()
    inner_loops = bench.get_inner_loops()
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
    def __init__(self, name, samples=3, warmups=1, processes=20,
                 loops=0, min_time=0.1, max_time=1.0, metadata=None,
                 inner_loops=None, _argparser=None):
        if not name:
            raise ValueError("name must be a non-empty string")
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
        self.argparser = parser

    def _calibrate_sample_func(self, sample_func):
        stream = self._stream()

        min_dt = self.args.min_time
        max_loops = 2 ** 32

        loops = 1
        while 1:
            if loops > max_loops:
                raise ValueError("unable to calibrate: loops=%s" % loops)

            dt = sample_func(loops)
            if self.args.verbose:
                print("calibration: %s: %s"
                      % (perf._format_number(loops, 'loop'),
                         perf._format_timedelta(dt)),
                      file=stream)

            if dt >= min_dt:
                break

            loops *= 2

        if self.args.verbose:
            print("calibration: use %s" % perf._format_number(loops, 'loop'),
                  file=stream)

        return loops

    def _process_args(self):
        if self.args.quiet:
            self.args.verbose = False
        if self.args.debug_single_sample:
            self.args.worker = True

        nprocess = self.argparser.get_default('processes')
        nsamples = self.argparser.get_default('samples')
        if self.args.rigorous:
            self.args.processes = nprocess * 2
            # self.args.samples = nsamples * 5 // 3
        elif self.args.fast:
            # use at least 3 processes to benchmark 3 different (randomized)
            # hash functions
            self.args.processes = max(nprocess // 2, 3)
            self.args.samples = max(nsamples * 2 // 3, 2)
        elif self.args.debug_single_sample:
            self.args.processes = 1
            self.args.warmups = 0
            self.args.samples = 1
            self.args.loops = 1
            self.args.min_time = 1e-9

        filename = self.args.output
        if filename and os.path.exists(filename):
            print("ERROR: The JSON file %r already exists" % filename)
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
        # sched_setaffinity() was added to Python 3.3
        has_sched_setaffinity = hasattr(os, 'sched_setaffinity')
        if not has_sched_setaffinity:
            if psutil is not None:
                proc = psutil.Process()
                psutil_has_cpu_affinity = hasattr(proc, 'cpu_affinity')
            else:
                psutil_has_cpu_affinity = False

        cpus = self.args.affinity
        if not cpus:
            stream = self._stream()

            # --affinity option is not set: detect isolated CPUs
            cpus = perf._get_isolated_cpus()
            if not cpus:
                # no isolated CPUs or unable to get the isolated CPUs
                return

            if not has_sched_setaffinity and not psutil_has_cpu_affinity:
                # unable to pin CPUs
                print("WARNING: unable to pin worker processes to "
                      "isolated CPUs, CPU affinity not available", file=stream)
                print("Use Python 3.3 or newer, or install psutil dependency",
                      file=stream)
                return

            if self.args.verbose:
                print("Pin process to isolated CPUs: %s"
                      % perf._format_cpu_list(cpus), file=stream)

            self.args.affinity = perf._format_cpu_list(cpus)
        else:
            cpus = perf._parse_cpu_list(cpus)
            if self.args.verbose:
                print("Pin process to CPUs: %s"
                      % perf._format_cpu_list(cpus),
                      file=self._stream())

        if has_sched_setaffinity:
            os.sched_setaffinity(0, cpus)
        elif psutil_has_cpu_affinity:
            proc = psutil.Process()
            proc.cpu_affinity(cpus)
        else:
            print("ERROR: CPU affinity not available.", file=sys.stderr)
            print("Use Python 3.3 or newer, or install psutil dependency",
                  file=stream)
            sys.exit(1)

    def _worker(self, bench, sample_func):
        stream = self._stream()
        loops = self.args.loops
        start_time = perf.monotonic_clock()

        raw_samples = []
        for is_warmup, index in self._range():
            raw_sample = sample_func(loops)

            # The most accurate time has a resolution of 1 nanosecond. We
            # compute a difference between two timer values. When formatted to
            # decimal, the difference can show more than 9 decimal digits after
            # the dot. Round manually to 10^-9 to produce more compact JSON
            # files and don't pretend to have a better resolution than 1
            # nanosecond.
            raw_sample = round(raw_sample, 9)

            raw_samples.append(raw_sample)

            if self.args.verbose:
                text = bench._format_sample(raw_sample)
                if is_warmup:
                    text = "Warmup %s: %s" % (index, text)
                else:
                    text = "Raw sample %s: %s" % (index, text)
                print(text, file=stream)

        if self.args.verbose:
            print(file=stream)

        duration = perf.monotonic_clock() - start_time
        metadata = dict(self.metadata)
        metadata = {'duration': duration, 'name': self.name}

        run = perf.Run(self.args.warmups, raw_samples,
                       loops=loops,
                       inner_loops=self.inner_loops,
                       metadata=metadata)
        bench.add_run(run)
        self._display_result(bench, check_unstable=False)

        return bench

    def _main(self, sample_func):
        self.parse_args()

        self._cpu_affinity()

        if self.args.loops == 0:
            self.args.loops = self._calibrate_sample_func(sample_func)

        bench = perf.Benchmark(name=self.name)

        try:
            if self.args.worker or self.args.debug_single_sample:
                return self._worker(bench, sample_func)
            else:
                return self._spawn_workers(bench)
        except KeyboardInterrupt:
            print("Interrupted: exit", file=sys.stderr)
            sys.exit(1)

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
        args = []
        args.extend(self.program_args)
        args.extend(('--worker', '--stdout',
                     '--samples', str(self.args.samples),
                     '--warmups', str(self.args.warmups),
                     '--loops', str(self.args.loops)))
        # FIXME: pass --min-time?
        if self.args.verbose:
            args.append('-' + 'v' * self.args.verbose)
        if self.args.affinity:
            args.append('--affinity=%s' % self.args.affinity)

        if self.prepare_subprocess_args:
            self.prepare_subprocess_args(self, args)

        return _bench_suite_from_subprocess(args)

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

    def _spawn_workers(self, bench):
        verbose = self.args.verbose
        quiet = self.args.quiet
        stream = self._stream()
        nprocess = self.args.processes

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
        return bench
