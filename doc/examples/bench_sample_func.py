import perf.text_runner

mydict = {str(k): k for k in range(1000)}

def func(loops):
    t0 = perf.perf_counter()
    for loops in range(loops):
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
    return perf.perf_counter() - t0

# inner-loops: mydict[int] is duplicated 10 times
runner = perf.text_runner.TextRunner(inner_loops=10)
runner.bench_sample_func(func)
