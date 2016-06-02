from __future__ import absolute_import, print_function
import itertools
import subprocess
import sys
import timeit

import perf


_DEFAULT_NPROCESS = 25
_DEFAULT_WARMUP = 1
_DEFAULT_REPEAT = 3
_MIN_TIME = 0.1
_MAX_TIME = 1.0


def _calibrate_timer(timer, verbose=0, stream=None):
    min_dt = _MIN_TIME * 0.90
    for i in range(0, 10):
        number = 10 ** i
        dt = timer.timeit(number)
        if verbose > 1:
            print("10^%s loops: %s" % (i, perf._format_timedelta(dt)), file=stream)
        if dt >= _MAX_TIME:
            i = max(i - 1, 1)
            number = 10 ** i
            break
        if dt >= min_dt:
            break
    if verbose > 1:
        print("calibration: use %s" % perf._format_number(number, 'loop'), file=stream)
    return number


def _main_common(args=None):
    # FIXME: use top level imports?
    # FIXME: get ride of getopt! use python 3 timeit main()
    import getopt
    if args is None:
        args = sys.argv[1:]

    try:
        opts, args = getopt.getopt(args, "n:s:r:p:w:vmh",
                                   ["number=", "setup=", "repeat=",
                                    "nprocess=", "warmup=",
                                    "verbose", "raw", "json", "metadata",
                                    "help"])
    except getopt.error as err:
        print(err)
        print("use -h/--help for command line help")
        sys.exit(2)

    class Namespace:
        pass

    stmt = "\n".join(args) or "pass"
    ns = Namespace()
    ns.raw = False
    ns.json = False
    ns.metadata = False
    ns.verbose = 0
    nprocess = _DEFAULT_NPROCESS
    warmup = _DEFAULT_WARMUP
    number = 0   # auto-determine
    setup = []
    repeat = _DEFAULT_REPEAT
    for o, a in opts:
        if o in ("-v", "--verbose"):
            ns.verbose += 1
        if o == "--raw":
            ns.raw = True
        if o == "--json":
            ns.json = True
        if o in ("-p", "--nprocess"):
            nprocess = int(a)
        if o in ("-m", "--metadata"):
            ns.metadata = True
        if o in ("-w", "--warmup"):
            warmup = int(a)
        if o in ("-n", "--number"):
            number = int(a)
        if o in ("-s", "--setup"):
            setup.append(a)
        if o in ("-r", "--repeat"):
            repeat = int(a)
            if repeat <= 0:
                repeat = 1
        if o in ("-h", "--help"):
            # FIXME: display perf.timeit usage, not timeit help!
            print(timeit.__doc__)
            sys.exit(0)
    setup = "\n".join(setup) or "pass"

    # Include the current directory, so that local imports work (sys.path
    # contains the directory of this script, rather than the current
    # directory)
    import os
    sys.path.insert(0, os.curdir)

    timer = timeit.Timer(stmt, setup, perf.perf_counter)
    if number == 0:
        stream = sys.stderr if ns.json else None
        try:
            number = _calibrate_timer(timer, ns.verbose, stream=stream)
        except:
            timer.print_exc()
            sys.exit(1)

    return (timer, ns, nprocess, warmup, repeat, number)


def _main_raw(timer, ns, verbose, warmup, repeat, number):
    result = perf.RunResult(loops=number)

    try:
        if not ns.json:
            print(perf._format_number(number, 'loop'))
        for i in range(warmup + repeat):
            it = itertools.repeat(None, number)
            dt = timer.inner(it, timer.timer) / number
            if i < warmup:
                result.warmups.append(dt)
            else:
                result.samples.append(dt)

            text = perf._format_timedelta(dt)
            if i < warmup:
                text = 'warmup %s: %s' % (1 + i, text)
            else:
                text = 'sample %s: %s' % (1 + i - warmup, text)
            if not ns.json:
                print(text)
            else:
                print(text, file=sys.stderr)
                sys.stderr.flush()
    except:
        timer.print_exc()
        return 1

    if ns.json:
        print(result.json())
    return None


def _run_subprocess(number, timeit_args, warmup):
    args = [sys.executable,
            '-m', 'perf.timeit',
            '--raw', '--json',
            "-n", str(number)]
    # FIXME: don't pass duplicate -n
    args.extend(timeit_args)

    proc = subprocess.Popen(args,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            universal_newlines=True)

    # FIXME: use context manager on Python 3
    stdout, stderr = proc.communicate()

    return perf.RunResult.from_json(stdout)


def _main():
    args = sys.argv[1:]
    timer, ns, processes, warmup, repeat, number = _main_common(args)
    if ns.raw:
        _main_raw(timer, ns, ns.verbose, warmup, repeat, number)
        return

    result = perf.Results()
    if not ns.json:
        stream = sys.stdout
    else:
        stream = sys.stderr

    if ns.metadata:
        from perf import metadata as perf_metadata

        perf_metadata.collect_metadata(result.metadata)

        print("Metadata:", file=stream)
        for key, value in sorted(result.metadata.items()):
            print("- %s: %s" % (key, value), file=stream)

    for process in range(processes):
        run = _run_subprocess(number, args, warmup)
        result.runs.append(run)
        if ns.verbose > 1:
            text = ', '.join(perf._format_timedeltas(run.samples))
            text = 'runs (%s): %s' % (len(run.samples), text)
            if run.warmups:
                text = ('warmup (%s): %s; %s'
                        % (len(run.warmups),
                           ', '.join(perf._format_timedeltas(run.warmups)),
                           text))

            print("Run %s/%s: %s" % (1 + process, processes, text), file=stream)
        elif ns.verbose:
            mean = perf.mean(run.samples)
            print(perf._format_timedelta(mean), end=' ', file=stream)
            stream.flush()
        else:
            print(".", end='', file=stream)
            stream.flush()
    if ns.verbose <= 1:
        print(file=stream)
    print("Average: %s" % result.format(ns.verbose > 1), file=stream)

    if ns.json:
        stream.flush()
        print(result.json())


if __name__ == "__main__":
    _main()
