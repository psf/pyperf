TODO
====

* Finish to rename "run_tests" to "benchmark": change the JSON format
* Add unit test on hist: need JSON data file
* JSON files are a litle bit big
* Metadata: "perf show" doesn't show the date
* Save the system load?
* Save the duration? of each run? only of the total?
* Optional dependency to boltons.statsutils or copy code for hist:
  median, median_abs_dev, skewness
* Python 2: use numpy.mean() or numpy.std() when available?
* Make TextRunner.result private?
* Set TextRunner.result to None in the main process?
* CPU pinning: on Python 2, spawn a child process to calibrate the number of
  outter-loop iterations
* "samples" is not the best term, "a data sample is a set of data":
  https://en.wikipedia.org/wiki/Sample_%28statistics%29
* -m perf CLI: add command to show and/or combine run results
* Integration with pybench
