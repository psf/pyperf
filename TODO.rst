TODO
====

* Clarify run vs process in TextRunner CLI
* Calibration: use powers of 2, not powers of 10
* Metrics measured before and/or after each run:

  * CPU frequency, system load
  * only store min and max?
  * use them to detect unstable benchmark

* Remove min/max from very verbose but add --stats to display statistics?
* add_run(): reject sample=0?
* round(sample, 9): does it have an impact on statistics?
* "samples" is not the best term, "a data sample is a set of data":
  https://en.wikipedia.org/wiki/Sample_%28statistics%29
