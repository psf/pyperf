from __future__ import print_function
import argparse
import io
import os
import subprocess
import sys

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


def _parse_cpu_list(cpu_list):
    cpus = []
    for part in cpu_list.split(','):
        if '-' in part:
            parts = part.split('-', 1)
            first = int(parts[0])
            last = int(parts[1])
            for cpu in range(first, last+1):
                cpus.append(cpu)
        else:
            cpus.append(int(part))
    return cpus

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

    return _parse_cpu_list(isolated)


def _bench_from_subprocess(args):
    proc = subprocess.Popen(args,
                            universal_newlines=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)

    if perf._PY3:
        with proc:
            stdout, stderr = proc.communicate()
    else:
        stdout, stderr = proc.communicate()

    if proc.returncode:
        sys.stdout.write(stdout)
        sys.stdout.flush()
        sys.stderr.write(stderr)
        sys.stderr.flush()
        raise RuntimeError("%s failed with exit code %s"
                           % (args[0], proc.returncode))

    return perf.Benchmark.json_load(stdout)


class TextRunner:
    def __init__(self, name=None, nsample=3, nwarmup=1, nprocess=25,
                 nloop=0, min_time=0.1, max_time=1.0, metadata=None,
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
            if self.args.verbose > 1:
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
        if self.args.verbose > 1:
            print("calibration: use %s" % perf._format_number(loops, 'loop'),
                  file=stream)

        return loops

    def parse_args(self, args=None):
        if self.args is not None:
            # arguments already parsed
            return

        self.args = self.argparser.parse_args(args)

    def _stream(self):
        return sys.stderr if self.args.json else sys.stdout

    def _range(self):
        # FIXME: use six.range
        for warmup in range(self.args.nwarmup):
            yield (True, 1 + warmup)
        for run in range(self.args.nsample):
            yield (False, 1 + run)

    def _display_run_result_avg(self, bench):
        stream = self._stream()

        if self.args.metadata:
            perf._display_metadata(bench.metadata, file=stream)
            print(file=stream)

        print("Average: %s" % bench.format(self.args.verbose),
              file=self._stream())

        stream.flush()
        _json_dump(bench, self.args)

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
            cpus = _get_isolated_cpus()
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
            cpus = _parse_cpu_list(cpus)
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
                print(text, file=self._stream())

        bench.add_run(samples)
        self._display_run_result_avg(bench)

        return bench

    def _main(self, sample_func):
        start_time = perf.monotonic_clock()

        self.parse_args()

        self._cpu_affinity()

        if self.args.loops == 0:
            self.args.loops = self._calibrate_sample_func(sample_func)

        loops = self.args.loops
        if loops < 1:
            # FIXME: move this check in argument parsing
            raise ValueError("loops must be >= 1")

        bench = perf.Benchmark(name=self.name,
                               warmups=self.args.nwarmup,
                               loops=loops,
                               inner_loops=self.inner_loops,
                               metadata=self.metadata)

        if not self.args.raw or self.args.metadata:
            from perf import metadata as perf_metadata
            perf_metadata.collect_metadata(bench.metadata)

        if not self.args.raw:
            return self._spawn_workers(bench, start_time)
        else:
            return self._worker(bench, sample_func)

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
                     '--samples', str(self.args.nsample),
                     '--warmups', str(self.args.nwarmup),
                     '--loops', str(self.args.loops)))
        if self.args.verbose:
            args.append('-' + 'v' * self.args.verbose)
        if self.args.affinity:
            args.append('--affinity=%s' % self.args.affinity)

        if self.prepare_subprocess_args:
            self.prepare_subprocess_args(self, args)

        return _bench_from_subprocess(args)

    def _spawn_workers(self, bench, start_time):
        verbose = self.args.verbose
        stream = self._stream()
        nprocess = self.args.processes

        for process in range(nprocess):
            run_bench = self._spawn_worker()
            samples = bench._get_worker_samples(run_bench)
            bench.add_run(samples)
            if verbose > 1:
                perf._display_run(bench, 1 + process, nprocess,
                                  samples, file=stream)
            else:
                print(".", end='', file=stream)
                stream.flush()

        if verbose <= 1:
            print(file=stream)

        duration = perf.monotonic_clock() - start_time
        mins, secs = divmod(duration, 60)
        if mins:
            bench.metadata['duration'] = '%.0f min %.0f sec' % (mins, secs)
        else:
            bench.metadata['duration'] = '%.1f sec' % secs

        if self.args.metadata:
            perf._display_metadata(bench.metadata, file=stream)
            print(file=stream)

        perf._display_benchmark_avg(bench, verbose=verbose, file=stream)

        stream.flush()
        _json_dump(bench, self.args)
        return bench
