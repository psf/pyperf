BUGS
====

* BUG: "python perf timeit --compare-to=pypy" doesn't tune correctly the runner
  for pypy. pypy requires more warmup values (10) than cpython (1).
* BUG: --duplicate of timeit must be ignored in PyPy, see the discussion
  on the speed mailing list.


TODO
====

* Runner: also require --warmups or --calibrate-warmups for worker on CPython,
  not only on PyPy
* write an unit test for calibrate_warmups()
* check: warn if min/max is 25% smaller/larger than mean, instead of 50%?
* show: add --name option to always display benchmark names
* Implement a system-wide lock to prevent running two benchmarks at the same
  time, especially using CPU pinning
* Calibration run: display time per iteration and total duration
* system:

  * Implement a few system operations on macOS
  * advice: use --affinity when no CPU is isolated
  * set the CPU scaling governor when intel_pstate is not used.
    Use "userland" governor with a fixed CPU speed (max speed)?
  * warn if HyperThread is enabled?
  * check that isolated CPU "respect HyperThreading" (are part of the
    same physical cores)
  * check that rcu_nocbs respects isolated CPUs
  * detect NUMA

* compare: check also if benchmarks are unstable
* compare: display metadata
* External tool (?) to produce nice HTML reports:

  * https://magic.io/blog/uvloop-blazing-fast-python-networking/

    - HTML, JS: d3 graphic library
    - min, max, std dev
    - https://github.com/MagicStack/pgbench
    - https://github.com/MagicStack/vmbench

  * http://hdrhistogram.github.io/HdrHistogram/
  * probability density graphs

    - https://hydra.snabb.co/build/589970/download/2/report.html
    - https://en.wikipedia.org/wiki/Probability_density_function
    - enhance hist_scipy.py to support more than one benchmark
    - https://docs.scipy.org/doc/scipy/reference/tutorial/stats.html

* fix hist if benchmark only contains one value
