TODO
====

* round(sample, 9): does it have an impact on statistics?
* JSON size: truncate even more digits in TextRunner (round(sample, 9)) if
  loops is larger than 1000? perf only displays 3 digits on the average.
  Can it have an impact on the statistics?
* Save system load to detect unstable benchmark?
* Add int type in Benchmark.add_run() samples?
* Metadata: "perf show" doesn't show the date
* Metadata: add the date, it was in run metadata but ignored because different
  at each run
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
