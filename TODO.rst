TODO
====

* Enhance TextRunner or write a new class to support multiple benchmarks.
  Use case: pybench
  Use case: timeit "key in dict" vs dict.get() vs "try: dict[key]/except KeyError"

* Incompatible change: TextRunner.program_args, drop first parameter
* emit a warning when nohz_full is enabled on at least one CPU
* metadata: voluntary_ctxt_switches and nonvoluntary_ctxt_switches of
  /proc/self/status?
* perf timeit, maybe also TextRunner: add --python cmdline option?
* Store date and boot_time as datetime.datetime in Python, but keep string for
  JSON? It would allow to store microsecond resolution in JSON, but display
  second resolution.
* perf timeit: add --inner-loops=N parameter, if the statement is explicitly
  copied N items
* Pass Python arguments to subprocesses like -I, -O, etc.
* "venv/pypy5.0-ec75e7c13ad0/bin/python -m perf timeit -w0 -l1 -n 10 pass -v --worker"
  sometimes create a sample equals to 0
* Make benchmark name mandatory?
* Write unit test for compare_to --group-by-speed
* Display also stability warnings in compare output
* Write unit test for tracemalloc and track memory: allocate 30 MB,
  check usage >= 30 MB
* Add CLI option to sort benchmarks by start date, not by name
* Enhance TextRunner to be able to run multiple benchmarks
* BenchmarkSuite.get_benchmarks(): don't sort by name? Error if a benchmark
  has no name?
* Remove BenchmarkSuite.__iter__()?
* support BenchmarkSuite directly in TextRunner for pybench
* find a memory efficient storage for common metadata in Run.
  Use collections.ChainMap?


Blocker for perf 1.0 (stable API)
=================================

* Update doc: check public attributes and methods of classes
* Clarify run vs process in TextRunner CLI
* "samples" is not the best term, "a data sample is a set of data":
  https://en.wikipedia.org/wiki/Sample_%28statistics%29
* Enhance TextRunner or write a new one to support multiple benchmarks,
  like pybench or pyperformance
* Use case: compare performance of multiple python expressions to find the
  fastest, common timeit use case


Low priority
============

* add metadata: sys.getcheckinterval, py3: GIL milliseconds? GC enabled?
* really avoid removing existing file: open(name, 'x')
* convert: save the operations made on data in metadata?
* configurable clock? see pybench
* reimplement metdata for compare?
* fix hist if benchmark only contains one sample
* support 2^15 and/or 2**15 syntax for --loops
* support --fast + -p1
* perf CLI: handle FileNotFoundError for input file (need unit test)
* convert --remove-outliers: more serious algorithm? or configurable percent?
