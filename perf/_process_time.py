"""
Similar to UNIX time command: measure the execution time of a command.

Minimum Python script spawning a program, wait until it completes, and then
write the elapsed time into stdout. Time is measured by the perf_counter()
timer.

Python subprocess.Popen() is implemented with fork()+exec(). Minimize the
Python imports to reduce the memory footprint, to reduce the cost of
fork()+exec().

Measure wall-time, not CPU time: resource.getrusage() is not used.
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


PY3 = (sys.version_info >= (3,))
if PY3:
    xrange = range


def bench_process(timer, loops, args, kw):
    range_it = xrange(loops)
    start = timer()

    for loop in range_it:
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

    dt = timer() - start
    return dt


def main():
    # Make sure that the perf module wasn't imported
    if 'perf' in sys.modules:
        print("ERROR: don't run %s -m perf._process, run the .py script"
              % os.path.basename(sys.executable))
        sys.exit(1)

    if len(sys.argv) < 3:
        print("Usage: %s %s loops program [arg1 arg2 ...]")
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

    dt = bench_process(timer, loops, args, kw)

    if devnull is not None:
        devnull.close()

    # Write timing in seconds into stdout
    print(dt)


if __name__ == "__main__":
    main()
