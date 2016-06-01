from __future__ import absolute_import
import subprocess
import sys
import timeit

import perf


_MIN_TIME = 0.2


def _calibrate_timer(timer):
    # determine number so that _MIN_TIME <= total time
    for i in range(1, 10):
        number = 10**i
        dt = timer.timeit(number)
        if dt >= _MIN_TIME:
            break
    return number


def _main_common(args=None):
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
            number = _calibrate_timer(timer)
        except:
            timer.print_exc()
            return 1

    return (timer, repeat, number)


def _main_raw(args=None):
    timer, repeat, number = _main_common()

    result = perf.RunResult(loops=number)
    try:
        for i in range(repeat):
            dt = timer.timeit(number) / number
            result.values.append(dt)
            print(dt)
    except:
        timer.print_exc()
        return 1

    # FIXME: verbose mode
    #print(result.metadata)
    #print(result)
    return None


def _run_subprocess(number):
    args = [sys.executable,
            '-m', 'perf.timeit',
            '--raw',
            "-n", str(number)]
    # FIXME: don't pass duplicate -n
    args.extend(sys.argv[1:])

    proc = subprocess.Popen(args,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            universal_newlines=True)
    # FIXME: use context manager on Python 3
    stdout, stderr = proc.communicate()
    values = []
    # FIXME: pass also metadata like loops
    for line in stdout.splitlines():
        # FIXME: nice error message on parsing error
        value = float(line)
        values.append(value)
    return perf.RunResult(values, loops=number)


def _main():
    if '--raw' in sys.argv:
        sys.argv.remove('--raw')
        _main_raw()
    else:
        # FIXME: add command line option
        verbose = False
        # FIXME: don't hardcode the number of runs!
        processes = 3

        timer, repeat, number = _main_common()
        result = perf.Results()
        for process in range(processes):
            run = _run_subprocess(number)
            if verbose:
                print("[%s/%s] %s" % (1 + process, processes, run))
            result.runs.append(run)
        print("Average: %s" % result)


if __name__ == "__main__":
    _main()
