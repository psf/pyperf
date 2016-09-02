TODO
====

* Run workers in a isolated environment (os.environ)
* Calibrate the benchmark in a special worker process? Maybe use the first
  worker for the calibration?
* "venv/pypy5.0-ec75e7c13ad0/bin/python -m perf timeit -w0 -l1 -n 10 pass -v --worker"
  sometimes create a sample equals to 0
* unify calibration and warmup?
* calibration: don't loose the sample, use it as the first sample?
* Make benchmark name mandatory?
* metadata: get Python Mercurial revision and the "+" modified marker
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
