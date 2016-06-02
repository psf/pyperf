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


def _calibrate_timer(timer, verbose=0):
    min_dt = _MIN_TIME * 0.90
    for i in range(0, 10):
        number = 10 ** i
        dt = timer.timeit(number)
        if verbose > 1:
            print("10^%s loops: %s" % (i, perf._format_timedelta(dt)))
        if dt >= _MAX_TIME:
            i = max(i - 1, 1)
            number = 10 ** i
            break
        if dt >= min_dt:
            break
    if verbose > 1:
        print("calibration: use %s" % perf._format_number(number, 'loop'))
    return number


def _main_common(args=None):
    # FIXME: use top level imports?
    # FIXME: get ride of getopt! use python 3 timeit main()
    import getopt
    if args is None:
        args = sys.argv[1:]

    try:
        opts, args = getopt.getopt(args, "n:s:r:p:w:vh",
                                   ["number=", "setup=", "repeat=",
                                    "nprocess=", "warmup=",
                                    "verbose", "raw", "help"])
    except getopt.error as err:
        print(err)
        print("use -h/--help for command line help")
        sys.exit(2)

    stmt = "\n".join(args) or "pass"
    raw = False
    verbose = 0
    nprocess = _DEFAULT_NPROCESS
    warmup = _DEFAULT_WARMUP
    number = 0   # auto-determine
    setup = []
    repeat = _DEFAULT_REPEAT
    for o, a in opts:
        if o in ("-v", "--verbose"):
            verbose += 1
        if o == "--raw":
            raw = True
        if o in ("-p", "--nprocess"):
            nprocess = int(a)
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
            # FIXME: it's not the right CLI, --verbose doesn't exist
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
        try:
            number = _calibrate_timer(timer, verbose)
        except:
            timer.print_exc()
            sys.exit(1)

    return (timer, raw, verbose, nprocess, warmup, repeat, number)


def _main_raw(timer, verbose, warmup, repeat, number):
    result = perf.RunResult(loops=number, warmup=warmup)

    try:
        print("loops=%s" % number)
        for i in range(warmup + repeat):
            it = itertools.repeat(None, number)
            dt = timer.inner(it, timer.timer) / number
            result.values.append(dt)
            print(dt)
    except:
        timer.print_exc()
        return 1

    # FIXME: verbose mode
    #print(result)
    return None


def _run_subprocess(number, timeit_args, warmup):
    args = [sys.executable,
            '-m', 'perf.timeit',
            '--raw',
            "-n", str(number)]
    # FIXME: don't pass duplicate -n
    args.extend(timeit_args)

    proc = subprocess.Popen(args,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            universal_newlines=True)
    # FIXME: use context manager on Python 3
    stdout, stderr = proc.communicate()
    values = []
    loops = None
    for line in stdout.splitlines():
        if not values and line.startswith('loops='):
            loops = int(line[6:])
            continue
        # FIXME: nice error message on parsing error
        value = float(line)
        values.append(value)
    return perf.RunResult(values, loops=loops, warmup=warmup)


def _main():
    args = sys.argv[1:]
    timer, raw, verbose, processes, warmup, repeat, number = _main_common(args)
    if raw:
        _main_raw(timer, verbose, warmup, repeat, number)
        return

    result = perf.Results()
    for process in range(processes):
        run = _run_subprocess(number, args, warmup)
        result.runs.append(run)
        if verbose > 1:
            if run.warmup:
                values1 = run.values[:run.warmup]
                values2 = run.values[run.warmup:]
                text = ('warmup (%s): %s; runs (%s): %s'
                        % (len(values1),
                           ', '.join(perf._format_timedeltas(values1)),
                           len(values2),
                           ', '.join(perf._format_timedeltas(values2))))
            else:
                text = ', '.join(perf._format_timedeltas(run.values))
                text = 'runs (%s): %s' % (len(run.values), text)

            print("Run %s/%s: %s" % (1 + process, processes, text))
        elif verbose:
            mean = perf.mean(run.values[run.warmup:])
            print(perf._format_timedelta(mean), end=' ')
            sys.stdout.flush()
        else:
            print(".", end='')
            sys.stdout.flush()
    if verbose <= 1:
        print()
    print("Average: %s" % result.format(verbose > 1))


if __name__ == "__main__":
    _main()
