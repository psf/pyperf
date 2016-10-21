TODO
====

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

* Add "system", "tune_system", (another name) command to tune the system for
  benchmarks: CPU pinning for IRQ, performance governor for CPU speed, etc.
* Remove --stdout or redesign _load_suite_from_stdout()?
* any print("test") in a worker creates a cryptic error message in the master.
  Don't use stdout? Better error message?
* Runner: add a compare methods to compare N benchmarks
* Add TextRunner.timeit()
* doc: clarify difference between compare & compare_to
* doc: more CLI examples
* doc: timeit, mention -o option
* timeit compare: write result as JSON into one or two files?
* emit a warning when nohz_full is enabled on at least one CPU
* metadata: voluntary_ctxt_switches and nonvoluntary_ctxt_switches of
  /proc/self/status? or/and read /proc/interrupts to count interruptions?
* Pass Python arguments to subprocesses like -I, -O, etc.
* "venv/pypy5.0-ec75e7c13ad0/bin/python -m perf timeit -w0 -l1 -n 10 pass -v --worker"
  sometimes create a sample equals to 0
* Write unit test for compare_to --group-by-speed
* Display also stability warnings in compare output
* Write unit test for tracemalloc and track memory: allocate 30 MB,
  check usage >= 30 MB
* Add CLI option to sort benchmarks by start date, not by name
* Enhance TextRunner to be able to run multiple benchmarks
* BenchmarkSuite.get_benchmarks(): don't sort by name?
* Remove BenchmarkSuite.__iter__()?
* find a memory efficient storage for common metadata in Run.
  Use collections.ChainMap?


Blocker for perf 1.0 (stable API)
=================================

* Clarify run vs process in TextRunner CLI
* "samples" is not the best term, "a data sample is a set of data":
  https://en.wikipedia.org/wiki/Sample_%28statistics%29
* Use case: compare performance of multiple python expressions to find the
  fastest, common timeit use case


Low priority
============

* configurable clock? see pybench
* reimplement metadata for compare?
* fix hist if benchmark only contains one sample
* support --fast + -p1
* perf CLI: handle FileNotFoundError for input file (need unit test)
* convert --remove-outliers: more serious algorithm? or configurable percent?
