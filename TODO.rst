TODO
====

* add function to add new runs to an existing JSON file
* "merge" two JSON files: cumulate benchmarks, add runs if two files have the
  same benchmark, etc.
* compare: avoid duplicated benchmark names
* Clarify run vs process in TextRunner CLI
* Calibration: use powers of 2, not powers of 10
* Metrics measured before and/or after each run:

  * CPU frequency, system load
  * only store min and max?
  * use them to detect unstable benchmark

* round(sample, 9): does it have an impact on statistics?
* "samples" is not the best term, "a data sample is a set of data":
  https://en.wikipedia.org/wiki/Sample_%28statistics%29
