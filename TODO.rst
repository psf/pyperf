TODO
====

* Make TextRunner.result private?
* Set TextRunner.result to None in the main process?
* CPU pinning: on Python 2, spawn a child process to calibrate the number of
  outter-loop iterations
* "samples" is not the best term, "a data sample is a set of data":
  https://en.wikipedia.org/wiki/Sample_%28statistics%29
* -m perf CLI: add command to show and/or combine run results
* Integration with pybench
* Detect when benchmark parameters are badly chosen? Only the latest
  benchmark is reliable.

    $ python3 -m perf.timeit -p5 -l1 1+1
    .....
    Average: 241 ns +- 51 ns

    $ python3 -m perf.timeit -p5 -l10 1+1
    .....
    Average: 42.9 ns +- 5.8 ns

    $ python3 -m perf.timeit -p5 -l1000 1+1
    .....
    Average: 19.5 ns +- 2.0 ns

   Standard deviation:

   * -l1: 21%
   * -l10: 14%
   * -l1000: 10%

   Warning if the standard deviation is larger than 10%?
