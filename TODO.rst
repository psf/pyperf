TODO
====

* convert: save operations in metadata?
* Fix hist command for a benchmark suite with multiple benchmarks: don't
  use the same scale for unrelated benchmarks
* "smart" JSON append:

  - add new runs to an existing JSON file. rerun exactly the same benchmark
    using --json-append
  - use metadata as the key to check if the benchmark is the same?
    ignore date? ignore CPU affinity?

* "merge" two JSON files: cumulate benchmarks, add runs if two files have the
  same benchmark, etc.


Blocker for perf 1.0 (stable API)
=================================

* Clarify run vs process in TextRunner CLI
* "samples" is not the best term, "a data sample is a set of data":
  https://en.wikipedia.org/wiki/Sample_%28statistics%29


Low priority
============

* convert --remove-outliers: more serious algorithm? or configurable percent?
* support multiple units, or remove _format_samples.
  Track memory usage in CPython benchmark suite?
* use the calibration at the first warmup sample in raw mode


Ideas
=====

* limit the number of processes when a single sample takes 5 seconds
* rework parameters (processes, samples, loops) depending on max time,
  not hardcoded parameters
* Metrics measured before and/or after each run:

  * CPU frequency, system load
  * only store min and max?
  * use them to detect unstable benchmark

