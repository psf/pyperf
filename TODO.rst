TODO
====

* Collect some metadata in each RunResult: needed to add CPU affinity metadata,
  the main process is not pinned to isolated CPus
* Results.get_metadata() combines its own metadata + metadata of all runs.
  Simple filter: skip different values.
* -m perf CLI: add command to combine run results
* -m perf CLI: add compare command
* Integration with pybench
* Raise an error or warning if timings are too short/benchmakr is unstable:

    $ python3 -m perf.timeit -n 1 1+1
    Average: 5 runs x 3 samples x 1 loop: 420 ns +- 284 ns
    $ python3 -m perf.timeit -n 10 1+1
    Average: 5 runs x 3 samples x 10 loops: 66.1 ns +- 33.2 ns
    $ python3 -m perf.timeit -n 100 1+1
    Average: 5 runs x 3 samples x 100 loops: 21.4 ns +- 2.8 ns
    $ python3 -m perf.timeit 1+1
    Average: 5 runs x 3 samples x 10^7 loops: 17.4 ns +- 0.4 ns
