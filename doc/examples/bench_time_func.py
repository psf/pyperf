#!/usr/bin/env python3
import pyperf


def bench_dict(loops, mydict):
    range_it = range(loops)
    t0 = pyperf.perf_counter()

    for loops in range_it:
        mydict['0']
        mydict['100']
        mydict['200']
        mydict['300']
        mydict['400']
        mydict['500']
        mydict['600']
        mydict['700']
        mydict['800']
        mydict['900']

    return pyperf.perf_counter() - t0


runner = pyperf.Runner()
mydict = {str(k): k for k in range(1000)}
# inner-loops: dict[str] is duplicated 10 times
runner.bench_time_func('dict[str]', bench_dict, mydict, inner_loops=10)
