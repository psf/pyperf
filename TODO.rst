Before 0.7 release
==================

* run metadata: add duration in seconds
* decide if metadata is collected by default or not
* rename --json to --output/-o
* rename --json-append to --append
* Run: store normalize samples and store loops/inner_loops as run metadata?
* run: convert loops/inner_loops to metadata


TODO
====

* "smart" JSON append:

  - add new runs to an existing JSON file. rerun exactly the same benchmark
    using --json-append
  - use metadata as the key to check if the benchmark is the same?
    ignore date? ignore CPU affinity?
  - "merge" two JSON files: cumulate benchmarks, add runs if two files have the
    same benchmark, etc.


Blocker for perf 1.0 (stable API)
=================================

* Clarify run vs process in TextRunner CLI
* "samples" is not the best term, "a data sample is a set of data":
  https://en.wikipedia.org/wiki/Sample_%28statistics%29


Low priority
============

* add metadata: sys.getcheckinterval, py3: GIL milliseconds? GC enabled?
* really avoid removing existing file: open(name, 'x')
* test cpu_temp on computer with multiple physical cores
* convert: save the operations made on data in metadata?
* configurable clock? see pybench
* reimplement metdata for compare?
* fix hist if benchmark only contains one sample
* support 2^15 and/or 2**15 syntax for --loops
* support --fast + -p1
* perf CLI: handle FileNotFoundError (need unit test)
* convert --remove-outliers: more serious algorithm? or configurable percent?
* support multiple units, or remove _format_samples.
  Track memory usage in CPython benchmark suite?
* use the calibration at the first warmup sample in raw mode
* metadata: implement time.get_time_info() on Python 2

  * Call QueryPerformanceFrequency() on Windows using ctypes?

* cleanup --verbose in CLIs


Ideas
=====

* limit the number of processes when a single sample takes 5 seconds
* rework parameters (processes, samples, loops) depending on max time,
  not hardcoded parameters
