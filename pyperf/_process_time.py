"""
Similar to UNIX time command: measure the execution time of a command.

Minimum Python script spawning a program, wait until it completes, and then
write the elapsed time into stdout. Time is measured by the time.perf_counter()
timer.

Python subprocess.Popen() is implemented with fork()+exec(). Minimize the
Python imports to reduce the memory footprint, to reduce the cost of
fork()+exec().

Measure wall-time, not CPU time.

If resource.getrusage() is available: compute the maximum RSS memory in bytes
per process and writes it into stdout as a second line.
"""
import os
import subprocess
import sys
import time

try:
    import resource
except ImportError:
    resource = None


def get_max_rss():
    if resource is not None:
        usage = resource.getrusage(resource.RUSAGE_CHILDREN)
        if sys.platform == "darwin":
            return usage.ru_maxrss
        return usage.ru_maxrss * 1024
    else:
        return 0


def bench_process(loops, args, kw):
    max_rss = 0
    range_it = range(loops)
    start_time = time.perf_counter()

    for loop in range_it:
        start_rss = get_max_rss()

        proc = subprocess.Popen(args, **kw)
        with proc:
            proc.wait()

        exitcode = proc.returncode
        if exitcode != 0:
            print("Command failed with exit code %s" % exitcode, file=sys.stderr)
            sys.exit(exitcode)

        proc = None

        rss = get_max_rss() - start_rss
        max_rss = max(max_rss, rss)

    dt = time.perf_counter() - start_time
    return (dt, max_rss)


def main():
    # Make sure that the pyperf module wasn't imported
    if "pyperf" in sys.modules:
        print(
            "ERROR: don't run %s -m pyperf._process, run the .py script"
            % os.path.basename(sys.executable)
        )
        sys.exit(1)

    if len(sys.argv) < 3:
        print(
            "Usage: %s %s loops program [arg1 arg2 ...]"
            % (os.path.basename(sys.executable), __file__)
        )
        sys.exit(1)

    loops = int(sys.argv[1])
    args = sys.argv[2:]

    kw = {}
    if hasattr(subprocess, "DEVNULL"):
        devnull = None
        kw["stdin"] = subprocess.DEVNULL
        kw["stdout"] = subprocess.DEVNULL
    else:
        devnull = open(os.devnull, "w+", 0)
        kw["stdin"] = devnull
        kw["stdout"] = devnull
    kw["stderr"] = subprocess.STDOUT

    dt, max_rss = bench_process(loops, args, kw)

    if devnull is not None:
        devnull.close()

    # Write timing in seconds into stdout
    print(dt)
    if max_rss:
        print(max_rss)


if __name__ == "__main__":
    main()
