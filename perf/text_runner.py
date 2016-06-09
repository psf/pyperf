from __future__ import print_function
import argparse
import subprocess
import sys

import perf


class TextRunner:
    def __init__(self):
        self.result = perf.RunResult()
        self.timer = perf.perf_counter
        self.argparser = self._create_argparser()
        # result of argparser.parse_args()
        self.args = None
        self.create_subprocess_args = None

    def _create_argparser(self, nprocess=25, nsample=3, nwarmup=1):
        parser = argparse.ArgumentParser(description='Benchmark')
        parser.add_argument('-n', '--samples', dest="nsample",
                            type=int, default=nsample,
                            help='number of samples per process (default: %s)'
                                 % nsample)
        parser.add_argument('-w', '--warmups', dest="nwarmup",
                            type=int, default=nwarmup,
                            help='number of warmup samples per process (default: %s)'
                                 % nwarmup)
        parser.add_argument('-v', '--verbose', action='count', default=0,
                            help='enable verbose mode')
        parser.add_argument('--json', action="store_true",
                            help='write results encoded to JSON into stdout')
        parser.add_argument('--raw', action="store_true",
                            help='run a single process')
        parser.add_argument('-p', '--processes', type=int, default=nprocess,
                            help='number of processes used to run benchmarks (default: %s)'
                                 % nprocess)
        parser.add_argument('--metadata', action="store_true",
                            help='show metadata')
        return parser

    def parse_args(self, args=None):
        if self.args is not None:
            # arguments already parsed
            return

        self.args = self.argparser.parse_args(args)

    def _stream(self):
        return sys.stderr if self.args.json else None

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

    def _display_headers(self):
        if self.result.loops is not None and self.args.verbose:
            print(perf._format_number(self.result.loops, 'loop'),
                  file=self._stream())

    def _display_result(self):
        text = self.result.format(self.args.verbose)
        nsample = perf._format_number(len(self.result.samples), 'sample')
        text = "Average: %s (%s)" % (text, nsample)
        print(text, file=self._stream())
        sys.stderr.flush()

        if self.args.json:
            print(self.result.json())

    def _main(self, func, *args):
        self.parse_args()
        if not self.args.raw:
            self.subprocesses()
            return

        self._display_headers()
        func(*args)
        self._display_result()

    def _bench_func(self, func, args):
        for is_warmup, run in self._range():
            t1 = self.timer()
            # FIXME: use functools.partial() to not use the slow "func(*args)"
            # unpacking at each iteration?
            func(*args)
            t2 = self.timer()
            self._add(is_warmup, run, t2 - t1)

    def bench_func(self, func, *args):
        return self._main(self._bench_func, func, args)

    def _bench_sample_func(self, func, args):
        for is_warmup, run in self._range():
            # FIXME: use functools.partial() to not use the slow "func(*args)"
            # unpacking at each iteration?
            dt = func(*args)
            self._add(is_warmup, run, dt)

    def bench_sample_func(self, func, *args):
        return self._main(self._bench_sample_func, func, args)

    def _run_subprocess(self):
        if self.create_subprocess_args:
            args = self.create_subprocess_args(self)
        else:
            args = [sys.executable] + sys.argv + ['--raw', '--json']

        return perf.RunResult.from_subprocess(args,
                                              stderr=subprocess.PIPE)

    def subprocesses(self):
        self.parse_args()

        metadata = self.args.metadata
        json = self.args.json
        verbose = self.args.verbose

        result = perf.Results(collect_metadata=json or metadata)
        if not json:
            stream = sys.stdout
        else:
            stream = sys.stderr

        if metadata:
            print("Metadata:", file=stream)
            for key, value in sorted(result.metadata.items()):
                print("- %s: %s" % (key, value), file=stream)

        nprocess = self.args.processes
        for process in range(nprocess):
            run = self._run_subprocess()
            result.runs.append(run)
            if verbose > 1:
                text = perf._very_verbose_run(run)
                print("Run %s/%s: %s" % (1 + process, nprocess, text), file=stream)
            elif verbose:
                mean = perf.mean(run.samples)
                print(perf._format_timedelta(mean), end=' ', file=stream)
                stream.flush()
            else:
                print(".", end='', file=stream)
                stream.flush()
        if verbose <= 1:
            print(file=stream)
        print("Average: %s" % result.format(verbose > 1), file=stream)

        if json:
            stream.flush()
            print(result.json())


    if __name__ == "__main__":
        _main()
