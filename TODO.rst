TODO
====

* Clarify run vs process in TextRunner CLI
* Calibration: use powers of 2, not powers of 10
* Metadata: CPU frequency?
* Remove min/max from very verbose but add --stats to display statistics?
* add_run(): reject sample=0?
* round(sample, 9): does it have an impact on statistics?
* JSON size: truncate even more digits in TextRunner (round(sample, 9)) if
  loops is larger than 1000? perf only displays 3 digits on the average.
  Can it have an impact on the statistics?
* Save system load to detect unstable benchmark?
* "samples" is not the best term, "a data sample is a set of data":
  https://en.wikipedia.org/wiki/Sample_%28statistics%29
* Integration with pybench
