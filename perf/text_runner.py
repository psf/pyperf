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
    def __init__(self, nsample=3, nwarmup=1, nprocess=25):
        self.result = perf.RunResult()
        # result of argparser.parse_args()
        self.args = None
        # called with prepare(runner, args), args must be modified in-place
        self.prepare_subprocess_args = None

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
        parser.add_argument('-v', '--verbose', action='count', default=0,
                            help='enable verbose mode')
        parser.add_argument('--json', action='store_true',
                            help='write results encoded to JSON into stdout')
        parser.add_argument('--json-file', metavar='FILENAME',
                            help='write results encoded to JSON into FILENAME')
        parser.add_argument('--raw', action="store_true",
                            help='run a single process')
        parser.add_argument('--metadata', action="store_true",
                            help='show metadata')
        self.argparser = parser

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
                text = "Run %s: %s" % (1 + run, text)
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

    def _main(self, func, *args):
        self.parse_args()
        if not self.args.raw:
            self._subprocesses()
            return

        # only import metadata submodule in worker processes
        import perf.metadata

        self._cpu_affinity()
        perf.metadata.collect_metadata(self.result.metadata)
        func(*args)
        self._display_result()

    def _bench_func(self, func, args):
        # local alias for fast variable lookup
        timer = perf.perf_counter

        if args:
            # Use partial() to avoid expensive argument unpacking of
            # func(*args) syntax when bench_func() is called without argument
            func = functools.partial(func, *args)

        for is_warmup, run in self._range():
            t1 = timer()
            func()
            t2 = timer()
            self._add(is_warmup, run, t2 - t1)

    def bench_func(self, func, *args):
        return self._main(self._bench_func, func, args)

    def _bench_sample_func(self, func, args):
        for is_warmup, run in self._range():
            dt = func(*args)
            self._add(is_warmup, run, dt)

    def bench_sample_func(self, func, *args):
        return self._main(self._bench_sample_func, func, args)

    def _run_subprocess(self):
        args = [sys.executable, sys.argv[0],
                '--raw', '--json',
                '--samples', str(self.args.nsample),
                '--warmups', str(self.args.nwarmup)]
        if self.args.verbose:
            args.append('-' + 'v' * self.args.verbose)

        if self.prepare_subprocess_args:
            self.prepare_subprocess_args(self, args)

        return perf.RunResult.from_subprocess(args,
                                              stderr=subprocess.PIPE)

    def _subprocesses(self):
        self.parse_args()

        verbose = self.args.verbose

        result = perf.Results()
        stream = self._stream()

        nprocess = self.args.processes
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



    if __name__ == "__main__":
        _main()
