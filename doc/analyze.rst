+++++++++++++++++++++++++
Analyze benchmark results
+++++++++++++++++++++++++

perf commands
=============

To analyze benchmark results, write the output into a JSON file using
the ``--output`` option (``-o``)::

    $ python3 -m perf timeit '[1,2]*1000' -o bench.json
    .....................
    Median +- std dev: 5.22 us +- 0.22 us

perf provides the following commands oo analyze benchmark results:

* :ref:`perf show <show_cmd>`: single line summary, mean and standard deviation
* :ref:`perf check <check_cmd>`: check if benchmark results stability
* :ref:`perf metadata <metadata_cmd>`: display metadata collected during the
  benchmark
* :ref:`perf dump <dump_cmd>`: see all values per run, including warmup values
  and the calibration run
* :ref:`perf stats <stats_cmd>`: compute various statistics (min/max, mean,
  median, percentiles, etc.).
* :ref:`perf hist <hist_cmd>`: render an histogram to see the shape of
  the distribution.
* :ref:`perf slowest <slowest_cmd>`: top 5 benchmarks which took the most time
  to be run.


Statistics
==========

.. _outlier:

Outliers
--------

If you run a benchmark without tuning the system, it's likely that you will get
`outliers <https://en.wikipedia.org/wiki/Outlier>`_: a few values much slower
than the average.

Example::

    $ python3 -m perf timeit '[1,2]*1000' -o outliers.json
    .....................
    WARNING: the benchmark result may be unstable
    * the maximum (6.02 us) is 39% greater than the mean (4.34 us)

    Try to rerun the benchmark with more runs, values and/or loops.
    Run 'python3 -m perf system tune' command to reduce the system jitter.
    Use perf stats, perf dump and perf hist to analyze results.
    Use --quiet option to hide these warnings.

    Mean +- std dev: 4.34 us +- 0.31 us

Statistics::

    $ python3 -m perf stats outliers.json -q
    Total duration: 11.6 sec
    Start date: 2017-03-16 16:30:01
    End date: 2017-03-16 16:30:16
    Raw value minimum: 135 ms
    Raw value maximum: 197 ms

    Number of runs: 21
    Total number of values: 60
    Number of values per run: 3
    Number of warmups per run: 1
    Loop iterations per value: 2^15

    Minimum:         4.12 us
    Median +- MAD:   4.25 us +- 0.05 us
    Mean +- std dev: 4.34 us +- 0.31 us
    Maximum:         6.02 us

      0th percentile: 4.12 us (-5% of the mean) -- minimum
      5th percentile: 4.15 us (-4% of the mean)
     25th percentile: 4.21 us (-3% of the mean)
     50th percentile: 4.25 us (-2% of the mean) -- median
     75th percentile: 4.30 us (-1% of the mean)
     95th percentile: 4.84 us (+12% of the mean)
    100th percentile: 6.02 us (+39% of the mean) -- maximum

Histogram::

    $ python3 -m perf hist outliers.json -q
    4.10 us: 15 ##############################
    4.20 us: 29 ##########################################################
    4.30 us:  6 ############
    4.40 us:  3 ######
    4.50 us:  2 ####
    4.60 us:  1 ##
    4.70 us:  0 |
    4.80 us:  1 ##
    4.90 us:  0 |
    5.00 us:  0 |
    5.10 us:  0 |
    5.20 us:  2 ####
    5.30 us:  0 |
    5.40 us:  0 |
    5.50 us:  0 |
    5.60 us:  0 |
    5.70 us:  0 |
    5.80 us:  0 |
    5.90 us:  0 |
    6.00 us:  1 ##

Using an histogram, it's easy to see that most values (57 values) are in the
range [4.12 us; 4.84 us], but 3 values are in the range [5.17 us; 6.02 us us]:
39% slower for the maximum (6.02 us). These 3 values at the bottom are caller "outliers"

See :ref:`How to get reproductible benchmark results <stable_bench>` to avoid
outliers.

If you cannot get stable benchmark results, another option is to use median and
median absolute deviation (MAD) instead of mean and standard deviation. Median
and MAD are `robust statistics
<https://en.wikipedia.org/wiki/Robust_statistics>`_ which ignore :ref:`outliers
<outlier>`.


.. _min:

Minimum VS average
------------------

Links:

* `Statistically Rigorous Java Performance Evaluation
  <http://buytaert.net/statistically-rigorous-java-performance-evaluation>`_
  by Andy Georges, Dries Buytaert and Lieven Eeckhout, 2007
* `Benchmarking: minimum vs average
  <http://blog.kevmod.com/2016/06/benchmarking-minimum-vs-average/>`_
  (June 2016) by Kevin Modzelewski
* `My journey to stable benchmark, part 3 (average)
  <https://haypo.github.io/journey-to-stable-benchmark-average.html>`_
  (May 2016) by Victor Stinner
* Median versus Mean: `perf issue #1: Use a better measures than average and
  standard <https://github.com/haypo/perf/issues/1>`_
* timeit module of PyPy now uses average:
  `change timeit to report the average +- stdandard deviation
  <https://bitbucket.org/pypy/pypy/commits/fb6bb835369e>`_


Median and median absolute deviation VS mean and standard deviation
---------------------------------------------------------------------

Median and median absolute deviation (MAD) are `robust statistics
<https://en.wikipedia.org/wiki/Robust_statistics>`_ which ignore :ref:`outliers
<outlier>`.

* `[Speed] Median +- MAD or Mean +- std dev?
  <https://mail.python.org/pipermail/speed/2017-March/000512.html>`_
* `perf issue #1: Use a better measures than average and standard deviation
  <https://github.com/haypo/perf/issues/1>`_
* `perf issue #20: Mean error of distribution
  <https://github.com/haypo/perf/issues/20>`_


Probability distribution
------------------------

The :ref:`hist command <hist_cmd>` renders an histogram of the distribution of
all values.

See also:

* `Probability distribution
  <https://en.wikipedia.org/wiki/Probability_distribution>`_ (Wikipedia)
* `"How NOT to Measure Latency" by Gil Tene
  <https://www.youtube.com/watch?v=lJ8ydIuPFeU>`_ (video at Youtube)
* `HdrHistogram: A High Dynamic Range Histogram.
  <http://hdrhistogram.github.io/HdrHistogram/>`_: "look at the entire
  percentile spectrum"
* `Multimodal distribution
  <https://en.wikipedia.org/wiki/Multimodal_distribution>`_.


Why is perf so slow?
====================

``--fast`` and ``--rigorous`` options indirectly have an impact on the total
duration of benchmarks. The ``perf`` module is not optimized for the total
duration but to produce :ref:`reliable benchmarks <stable_bench>`.

The ``--fast`` is designed to be fast, but remain reliable enough to be
sensitive. Using less worker processes and less values per worker would
produce unstable results.


Compare benchmark results
=========================

Let's use Python 2 and Python 3 to generate two different benchmark results::

    $ python2 -m perf timeit '[1,2]*1000' -o py2.json
    .....................
    Median +- std dev: 6.27 us +- 0.20 us

    $ python3 -m perf timeit '[1,2]*1000' -o py3.json
    .....................
    Median +- std dev: 5.25 us +- 0.11 us

The :ref:`perf compare_to <compare_cmd>` command compares the second benchmark
to the first benchmark::

    $ python3 -m perf compare_to py2.json py3.json
    Median +- std dev: [py2] 6.27 us +- 0.20 us -> [py3] 5.25 us +- 0.11 us: 1.20x faster (-16%)

Python 3 is faster than Python 2 on this benchmark.

Variant: render a table::

    $ python3 -m perf compare_to py2.json py3.json --table
    +-----------+---------+------------------------------+
    | Benchmark | py2     | py3                          |
    +===========+=========+==============================+
    | timeit    | 6.27 us | 5.25 us: 1.20x faster (-16%) |
    +-----------+---------+------------------------------+
