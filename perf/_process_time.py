"""
Similar to UNIX time command: measure the execution time of a command.

Minimum Python script spawning a program, wait until it completes, and then
write the elapsed time into stdout. Time is measured by the perf_counter()
timer.

Python subprocess.Popen() is implemented with fork()+exec(). Minimize the
Python imports to reduce the memory footprint, to reduce the cost of
fork()+exec().

Measure wall-time, not CPU time.

If resource.getrusage() is available: compute the maximum RSS memory in bytes
per process and writes it into stdout as a second line.
"""
from __future__ import division, print_function, absolute_import

import os
import subprocess
import sys

try:
    # Python 3.3+ (PEP 418)
    from time import perf_counter
except ImportError:
    import time
    if sys.platform == "win32":
        perf_counter = time.clock
    else:
        perf_counter = time.time

try:
    import resource
except ImportError:
    resource = None


def get_max_rss():
    if resource is not None:
        usage = resource.getrusage(resource.RUSAGE_CHILDREN)
        return usage.ru_maxrss * 1024
    else:
        return 0


PY3 = (sys.version_info >= (3,))
if PY3:
    xrange = range


def bench_process(timer, loops, args, kw):
    max_rss = 0
    range_it = xrange(loops)
    start_time = timer()

    for loop in range_it:
        start_rss = get_max_rss()

        proc = subprocess.Popen(args, **kw)
        if PY3:
            with proc:
                proc.wait()
        else:
            proc.wait()

        exitcode = proc.returncode
        if exitcode != 0:
            print("Command failed with exit code %s" % exitcode,
                  file=sys.stderr)
            sys.exit(exitcode)

        proc = None

        rss = get_max_rss() - start_rss
        max_rss = max(max_rss, rss)

    dt = timer() - start_time
    return (dt, max_rss)


def main():
    # Make sure that the perf module wasn't imported
    if 'perf' in sys.modules:
        print("ERROR: don't run %s -m perf._process, run the .py script"
              % os.path.basename(sys.executable))
        sys.exit(1)

    if len(sys.argv) < 3:
        print("Usage: %s %s loops program [arg1 arg2 ...]"
              % (os.path.basename(sys.executable), __file__))
        sys.exit(1)

    loops = int(sys.argv[1])
    args = sys.argv[2:]
    timer = perf_counter

    kw = {}
    if hasattr(subprocess, 'DEVNULL'):
        devnull = None
        kw['stdin'] = subprocess.DEVNULL
        kw['stdout'] = subprocess.DEVNULL
    else:
        devnull = open(os.devnull, 'w+', 0)
        kw['stdin'] = devnull
        kw['stdout'] = devnull
    kw['stderr'] = subprocess.STDOUT

    dt, max_rss = bench_process(timer, loops, args, kw)

    if devnull is not None:
        devnull.close()

    # Write timing in seconds into stdout
    print(dt)
    if max_rss:
        print(max_rss)


if __name__ == "__main__":
    main()
