TODO
====

* use the calibration at the first warmup sample in raw mode
* limit the number of processes when a single sample takes 5 seconds
* remove --raw option: use raw method for -p1 or when -p is missing
* add function to add new runs to an existing JSON file
* "merge" two JSON files: cumulate benchmarks, add runs if two files have the
  same benchmark, etc.
* compare: avoid duplicated benchmark names
* Clarify run vs process in TextRunner CLI
* Metrics measured before and/or after each run:

  * CPU frequency, system load
  * only store min and max?
  * use them to detect unstable benchmark

* round(sample, 9): does it have an impact on statistics?
* "samples" is not the best term, "a data sample is a set of data":
  https://en.wikipedia.org/wiki/Sample_%28statistics%29
* support multiple units, or remove _format_samples.
  Track memory usage in CPython benchmark suite?
