BUGS
====

* BUG: "python perf timeit --compare-to=pypy" doesn't tune correctly the runner
  for pypy. pypy requires more warmup values (10) than cpython (1).
* BUG: --duplicate of timeit must be ignored in PyPy, see the discussion
  on the speed mailing list.


TODO
====

* Update JSON example
* Rename --samples to --values, rename --debug-single-sample
* Remove --remove-outliers from convert
* Rename Runner.bench_sample_func()
* Compute duration in the main process, not in the worker process? Or replace
  the value in the main process?
* Implement a few system operations on macOS
* --append should get the number of loops from the existing file and avoid
  calibration, at least when no JIT is used.
* Implement a system-wide lock to prevent running two benchmarks at the same
  time, especially using CPU pinning
* system: display uptime
* Need to write unit test for Runner.timeit()
* Calibration run: display time per iteration and total duration
* system:

  * advice: use --affinity when no CPU is isolated
  * set the CPU scaling governor when intel_pstate is not used.
    Use "userland" governor with a fixed CPU speed (max speed)?
  * warn if HyperThread is enabled?
  * check that isolated CPU "respect HyperThreading" (are part of the
    same physical cores)
  * check that rcu_nocbs respects isolated CPUs
  * detect NUMA

* compare: check also if benchmarks are unstable
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

* Runner: add a compare methods to compare N benchmarks
* Add TextRunner.timeit()
* doc: clarify difference between compare & compare_to
* doc: more CLI examples
* doc: timeit, mention -o option
* timeit compare: write result as JSON into one or two files?
* metadata: voluntary_ctxt_switches and nonvoluntary_ctxt_switches of
  /proc/self/status? or/and read /proc/interrupts to count interruptions?
* Pass Python arguments to subprocesses like -I, -O, etc.
* "venv/pypy5.0-ec75e7c13ad0/bin/python -m perf timeit -w0 -l1 -n 10 pass -v --worker"
  sometimes create a value equals to 0
* Write unit test for compare_to --group-by-speed
* Write unit test for tracemalloc and track memory: allocate 30 MB,
  check usage >= 30 MB
* Remove BenchmarkSuite.__iter__()?


Low priority
============

* compare: display metadata
* fix hist if benchmark only contains one value
* support --fast + -p1
* perf CLI: handle FileNotFoundError for input file (need unit test)
* convert --remove-outliers: more serious algorithm? or configurable percent?
