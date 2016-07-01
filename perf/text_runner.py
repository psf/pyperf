from __future__ import print_function
import argparse
import io
import os
import subprocess
import sys

import statistics   # Python 3.4+, or backport on Python 2.7

try:
    # Optional dependency
    import psutil
except ImportError:
    psutil = None

import perf


def _json_dump(bench, args):
    if args.json_file:
        # --json-file=FILENAME
        if perf._PY3:
            fp = open(args.json_file, "w", encoding="utf-8")
        else:
            fp = open(args.json_file, "wb")
        with fp:
            bench.json_dump_into(fp)
            fp.flush()
    elif args.json:
        # --json
        stdout = sys.stdout
        bench.json_dump_into(stdout)
        stdout.flush()


def _bench_from_subprocess(args):
    proc = subprocess.Popen(args,
                            universal_newlines=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)

    try:
        if perf._PY3:
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

    return perf.Benchmark.json_load(stdout)


def _display_run(bench, index, nrun, samples, file=None):
    warmups = samples[:bench.warmups]
    samples = samples[bench.warmups:]

    text = ', '.join(bench._format_samples(samples))
    text = 'raw samples (%s): %s' % (len(samples), text)
    if warmups:
        text = ('warmup (%s): %s; %s'
                % (len(warmups),
                   ', '.join(bench._format_samples(warmups)),
                   text))

    text = "Run %s/%s: %s" % (index, nrun, text)
    print(text, file=file)


def _display_stats(result, file=None):
    fmt = result._format_sample
    samples = result.get_samples()

    nrun = result.get_nrun()
    nsample = len(samples)
    nsample_per_run = len(result._runs[0]) - result.warmups
    median = result.median()


    iterations = [perf._format_number(nrun, 'run'),
                  perf._format_number(nsample_per_run, 'sample')]
    if result.loops is not None:
        iterations.append(perf._format_number(result.loops, 'loop'))

    iterations = ' x '.join(iterations)
    iterations += '; %s' % perf._format_number(result.warmups or 0, 'warmup')
    if result.inner_loops is not None:
        iterations += '; %s' % perf._format_number(result.inner_loops, 'inner-loop')

    text = "Number of samples: %s" % perf._format_number(nsample)
    if iterations:
        text = '%s (%s)' % (text, iterations)

    print(text, file=file)
    percent = statistics.stdev(samples) * 100 / median
    print("Standard deviation / median: %.0f%%" % percent, file=file)
    shortest = min(result._get_raw_samples())
    text = result._format_sample(shortest)
    print("Shortest raw sample: %s" % text, file=file)
    print(file=file)

    def format_min(median, value):
        return "%s (%+.1f%%)" % (fmt(value), (value - median) * 100 / median)

    print("Minimum: %s" % format_min(median, min(samples)), file=file)

    def fmt_stdev(value, dev):
        left = median - dev
        right = median + dev
        return ("%s +- %s (%s .. %s)"
                % perf._format_timedeltas((median, dev, left, right)))

    print("Median +- std dev: %s"
          % fmt_stdev(median, statistics.stdev(samples, median)), file=file)

    print("Maximum: %s" % format_min(median, max(samples)), file=file)


def _display_histogram(results, bins=20, extend=False, file=None):
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
    for result in results:
        all_samples.extend(result.get_samples())
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

    for index, result in enumerate(results):
        if len(results) > 1:
            print("[ %s ]" % result.name, file=file)

        samples = result.get_samples()

        counter = collections.Counter([sample_bucket(value) for value in samples])
        count_max = max(counter.values())
        count_width = len(str(count_max))

        sample_width = max([len(result._format_sample(bucket * sample_k))
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
            text = result._format_sample(bucket * sample_k)
            line = ('#' * linelen) or '|'
            print("{:>{}}: {:>{}} {}".format(text, sample_width,
                                             count, count_width, line),
                  file=file)

        if index != len(results) -1:
            print(file=file)


def _warn_if_bench_unstable(bench, file=None):
    if not bench.get_nrun():
        raise ValueError("benchmark has no run")
    samples = bench.get_samples()

    # Display a warning if the standard deviation is larger than 10%
    median = bench.median()
    # Avoid division by zero
    if median and len(samples) > 1:
        k = statistics.stdev(samples) / median
        if k > 0.10:
            if k > 0.20:
                print("ERROR: the benchmark is very unstable, the standard "
                      "deviation is very high (stdev/median: %.0f%%)!"
                      % (k * 100),
                      file=file)
            else:
                print("WARNING: the benchmark seems unstable, the standard "
                      "deviation is high (stdev/median: %.0f%%)"
                      % (k * 100),
                      file=file)
            print("Try to rerun the benchmark with more runs, samples "
                  "and/or loops",
                  file=file)
            print(file=file)

    # Check that the shortest sample took at least 1 ms
    shortest = min(bench._get_raw_samples())
    text = bench._format_sample(shortest)
    if shortest < 1e-3:
        if shortest < 1e-6:
            print("ERROR: the benchmark may be very unstable, "
                  "the shortest raw sample only took %s" % text)
        else:
            print("WARNING: the benchmark may be unstable, "
                  "the shortest raw sample only took %s" % text)
        print("Try to rerun the benchmark with more loops "
              "or increase --min-time",
              file=file)
        print(file=file)


def _display_metadata(metadata, file=None, header="Metadata:"):
    if not metadata:
        return
    print(header, file=file)
    for key, value in sorted(metadata.items()):
        print("- %s: %s" % (key, value), file=file)


def _display_benchmark(bench, file=None, check_unstable=True, metadata=False,
                       runs=False, stats=False, hist=False):
    if runs:
        runs = bench.get_runs()
        nrun = len(runs)
        for index, samples in enumerate(runs, 1):
            _display_run(bench, index, nrun, samples, file=file)
        print(file=file)

    if metadata:
        _display_metadata(bench.metadata, file=file)
        print(file=file)

    if hist:
        _display_histogram([bench], file=file)
        print(file=file)

    if stats:
        _display_stats(bench)
        print(file=file)

    if check_unstable:
        _warn_if_bench_unstable(bench, file=file)

    print("Median +- std dev: %s" % bench.format(), file=file)


class TextRunner:
    def __init__(self, name=None, samples=3, warmups=1, processes=25,
                 loops=0, min_time=0.1, max_time=1.0, metadata=None,
                 inner_loops=None):
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

        parser = argparse.ArgumentParser(description='Benchmark')
        parser.add_argument('-p', '--processes', type=strictly_positive, default=processes,
                            help='number of processes used to run benchmarks (default: %s)'
                                 % processes)
        parser.add_argument('-n', '--samples', dest="samples",
                            type=strictly_positive, default=samples,
                            help='number of samples per process (default: %s)'
                                 % samples)
        parser.add_argument('-w', '--warmups', dest="warmups",
                            type=positive_or_nul, default=warmups,
                            help='number of skipped samples per run used to warmup the benchmark (default: %s)'
                                 % warmups)
        parser.add_argument('-l', '--loops', type=positive_or_nul, default=loops,
                            help='number of loops per sample, 0 means '
                                 'automatic calibration (default: %s)'
                                 % loops)
        parser.add_argument('-v', '--verbose', action="store_true",
                            help='enable verbose mode')
        parser.add_argument('-q', '--quiet', action="store_true",
                            help='enable quiet mode')
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
        parser.add_argument('--hist', action="store_true",
                            help='display an histogram of samples')
        parser.add_argument('--stats', action="store_true",
                            help='display statistics (min, max, ...)')
        parser.add_argument("--affinity", metavar="CPU_LIST", default=None,
                            help="Specify CPU affinity for worker processes. "
                                 "This way, benchmarks can be forced to run "
                                 "on a given set of CPUs to minimize run to "
                                 "run variation. By default, worker processes "
                                 "are pinned to isolate CPUs if isolated CPUs "
                                 "are found.")
        self.argparser = parser

    def _calibrate_sample_func(self, sample_func):
        stream = self._stream()

        min_dt = self.args.min_time * 0.90
        max_dt = self.args.max_time
        for index in range(0, 10):
            # FIXME: add a check to detect bugs in sample_func(): put a limit?
            loops = 10 ** index

            dt = sample_func(loops)
            if self.args.verbose:
                print("calibration: %s: %s"
                      % (perf._format_number(loops, 'loop'),
                         perf._format_timedelta(dt)),
                      file=stream)

            if dt >= max_dt:
                index = max(index - 1, 0)
                loops = 10 ** index
                break
            if dt >= min_dt:
                break
        if self.args.verbose:
            print("calibration: use %s" % perf._format_number(loops, 'loop'),
                  file=stream)

        return loops

    def parse_args(self, args=None):
        if self.args is not None:
            # arguments already parsed
            return

        self.args = self.argparser.parse_args(args)
        if self.args.quiet:
            self.args.verbose = False

    def _stream(self):
        return sys.stderr if self.args.json else sys.stdout

    def _range(self):
        # FIXME: use six.range
        for warmup in range(self.args.warmups):
            yield (True, 1 + warmup)
        for run in range(self.args.samples):
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

        samples = []
        for is_warmup, index in self._range():
            sample = sample_func(bench.loops)

            # The most accurate time has a resolution of 1 nanosecond. We
            # compute a difference between two timer values. When formatted to
            # decimal, the difference can show more than 9 decimal digits after
            # the dot. Round manually to 10^-9 to produce more compact JSON
            # files and don't pretend to have a better resolution than 1
            # nanosecond.
            sample = round(sample, 9)

            samples.append(sample)

            if self.args.verbose:
                text = bench._format_sample(sample)
                if is_warmup:
                    text = "Warmup %s: %s" % (index, text)
                else:
                    text = "Raw sample %s: %s" % (index, text)
                print(text, file=stream)

        if self.args.verbose:
            print(file=stream)

        bench.add_run(samples)
        self._display_result(bench, check_unstable=False)

        return bench

    def _main(self, sample_func):
        start_time = perf.monotonic_clock()

        self.parse_args()

        self._cpu_affinity()

        if self.args.loops == 0:
            self.args.loops = self._calibrate_sample_func(sample_func)

        bench = perf.Benchmark(name=self.name,
                               warmups=self.args.warmups,
                               loops=self.args.loops,
                               inner_loops=self.inner_loops,
                               metadata=self.metadata)

        if not self.args.raw or self.args.metadata:
            from perf import metadata as perf_metadata
            perf_metadata.collect_metadata(bench.metadata)

        try:
            if not self.args.raw:
                return self._spawn_workers(bench, start_time)
            else:
                return self._worker(bench, sample_func)
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
        args.extend(('--raw', '--json',
                     '--samples', str(self.args.samples),
                     '--warmups', str(self.args.warmups),
                     '--loops', str(self.args.loops)))
        if self.args.verbose:
            args.append('-' + 'v' * self.args.verbose)
        if self.args.affinity:
            args.append('--affinity=%s' % self.args.affinity)

        if self.prepare_subprocess_args:
            self.prepare_subprocess_args(self, args)

        return _bench_from_subprocess(args)

    def _display_result(self, bench, check_unstable=True):
        stream = self._stream()

        # Display the average +- stdev
        if self.args.quiet:
            check_unstable = False
        _display_benchmark(bench,
                           file=stream,
                           check_unstable=check_unstable,
                           metadata=self.args.metadata,
                           stats=self.args.stats,
                           hist=self.args.hist)

        stream.flush()
        _json_dump(bench, self.args)

    def _spawn_workers(self, bench, start_time):
        verbose = self.args.verbose
        quiet = self.args.quiet
        stream = self._stream()
        nprocess = self.args.processes

        for process in range(nprocess):
            run_bench = self._spawn_worker()
            samples = bench._get_worker_samples(run_bench)
            bench.add_run(samples)
            if verbose:
                _display_run(bench, 1 + process, nprocess,
                             samples, file=stream)
            elif not quiet:
                print(".", end='', file=stream)
                stream.flush()

        if not quiet:
            print(file=stream)

        duration = perf.monotonic_clock() - start_time
        mins, secs = divmod(duration, 60)
        if mins:
            bench.metadata['duration'] = '%.0f min %.0f sec' % (mins, secs)
        else:
            bench.metadata['duration'] = '%.1f sec' % secs

        self._display_result(bench)
        return bench
