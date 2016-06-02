from __future__ import absolute_import
import itertools
import subprocess
import sys
import timeit

import perf


_MIN_TIME = 0.1
_MAX_TIME = 1.0


def _calibrate_timer(timer, verbose=False):
    min_dt = _MIN_TIME * 0.90
    for i in range(0, 10):
        number = 10 ** i
        dt = timer.timeit(number)
        text = perf._format_timedelta((dt,))[0]
        if verbose:
            print("10^%s iterations: %s" % (i, text))
        if dt >= _MAX_TIME:
            i = max(i - 1, 1)
            number = 10 ** i
            break
        if dt >= min_dt:
            break
    if verbose:
        min_dt, max_dt = perf._format_timedelta((_MIN_TIME, _MAX_TIME))
        print("=> use %s (min: %s, max: %s)"
              % (perf._format_number(number, 'iteration'), min_dt, max_dt))
    return number


def _main_common(args=None, verbose=False):
    # FIXME: use top level imports?
    # FIXME: get ride of getopt! use python 3 timeit main()
    import getopt
    if args is None:
        args = sys.argv[1:]

    try:
        opts, args = getopt.getopt(args, "n:s:r:h",
                                   ["number=", "setup=", "repeat=", "help"])
    except getopt.error as err:
        print(err)
        print("use -h/--help for command line help")
        return 2

    stmt = "\n".join(args) or "pass"
    number = 0   # auto-determine
    setup = []
    repeat = timeit.default_repeat
    for o, a in opts:
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
            return 0
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
            return 1

    return (timer, repeat, number)


def _main_raw(args=None):
    timer, repeat, number = _main_common()

    result = perf.RunResult(loops=number)
    try:
        print("loops=%s" % number)
        for i in range(repeat):
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
    if '--raw' in sys.argv:
        sys.argv.remove('--raw')
        _main_raw()
        return

    # FIXME: better argument parsing
    args = sys.argv[1:]
    if '-v' in args:
        verbose = True
        args.remove('-v')
    else:
        verbose = False

    # FIXME: don't hardcode the number of runs!
    processes = 25
    warmup = 1

    timer, repeat, number = _main_common(args, verbose)
    result = perf.Results()
    for process in range(processes):
        run = _run_subprocess(number, args, warmup)
        result.runs.append(run)
        if verbose:
            if run.warmup:
                values1 = run.values[:run.warmup]
                values2 = run.values[run.warmup:]
                text = ('warmup (%s): %s; %s'
                        % (len(values1),
                           ', '.join(perf._format_timedelta(values1)),
                           ', '.join(perf._format_timedelta(values2))))
            else:
                text = ', '.join(perf._format_timedelta(run.values))

            print("Run %s/%s: %s" % (1 + process, processes, text))
    print("Average: %s" % result.format(verbose))


if __name__ == "__main__":
    _main()
