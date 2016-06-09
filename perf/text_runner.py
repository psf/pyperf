from __future__ import print_function
import argparse
import subprocess
import sys

import perf


class TextRunner:
    def __init__(self, nsample=3, nwarmup=1):
        self.result = perf.RunResult()
        self.nsample = nsample
        self.nwarmup = nwarmup
        # FIXME: json and args.json are duplicated, remove it?
        self.json = False
        self.timer = perf.perf_counter
        self.verbose = False
        self.argparser = self._create_argparser()
        # result of argparser.parse_args()
        self.args = None

    def _create_argparser(self):
        parser = argparse.ArgumentParser(description='Benchmark')
        parser.add_argument('-v', '--verbose', action='count', default=0,
                            help='enable verbose mode')
        parser.add_argument('--json', action="store_true",
                            help='write results encoded to JSON into stdout')
        return parser

    def parse_args(self, args=None):
        if self.args is not None:
            # arguments already parsed
            return

        args = self.argparser.parse_args(args)
        self.args = args
        self.verbose = args.verbose
        self.json = args.json

    def _stream(self):
        return sys.stderr if self.json else None

    def _range(self):
        # FIXME: use six.range
        for warmup in range(self.nwarmup):
            yield (True, warmup)
        for run in range(self.nsample):
            yield (False, run)

    def _add(self, is_warmup, run, sample):
        if is_warmup:
            self.result.warmups.append(sample)
        else:
            self.result.samples.append(sample)

        if self.verbose:
            text = self.result._format_sample(sample)
            if is_warmup:
                text = "Warmup %s: %s" % (1 + run, text)
            else:
                text = "Run %s: %s" % (1 + run, text)
            print(text, file=self._stream())

    def _display_headers(self):
        if self.result.loops is not None and self.verbose:
            print(perf._format_number(self.result.loops, 'loop'),
                  file=self._stream())

    def _display_result(self):
        text = self.result.format(self.verbose)
        nsample = perf._format_number(len(self.result.samples), 'sample')
        text = "Average: %s (%s)" % (text, nsample)
        print(text, file=self._stream())
        sys.stderr.flush()

        if self.json:
            print(self.result.json())

    def _main(self, func, *args):
        self.parse_args()
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

    def _run_subprocess(self, create_args):
        if create_args:
            args = create_args(self)
        else:
            args = [sys.executable] + sys.argv + ['--raw', '--json']

        return perf.RunResult.from_subprocess(args,
                                              stderr=subprocess.PIPE)

    def subprocesses(self, nprocess, create_args=None, metadata=False):
        result = perf.Results(collect_metadata=self.json or metadata)
        if not self.json:
            stream = sys.stdout
        else:
            stream = sys.stderr

        if metadata:
            print("Metadata:", file=stream)
            for key, value in sorted(result.metadata.items()):
                print("- %s: %s" % (key, value), file=stream)

        for process in range(nprocess):
            run = self._run_subprocess(create_args)
            result.runs.append(run)
            if self.verbose > 1:
                text = perf._very_verbose_run(run)
                print("Run %s/%s: %s" % (1 + process, nprocess, text), file=stream)
            elif self.verbose:
                mean = perf.mean(run.samples)
                print(perf._format_timedelta(mean), end=' ', file=stream)
                stream.flush()
            else:
                print(".", end='', file=stream)
                stream.flush()
        if self.verbose <= 1:
            print(file=stream)
        print("Average: %s" % result.format(self.verbose > 1), file=stream)

        if self.json:
            stream.flush()
            print(result.json())


    if __name__ == "__main__":
        _main()
