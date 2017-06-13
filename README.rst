****
perf
****

.. image:: https://img.shields.io/pypi/v/perf.svg
   :alt: Latest release on the Python Cheeseshop (PyPI)
   :target: https://pypi.python.org/pypi/perf

.. image:: https://travis-ci.org/haypo/perf.svg?branch=master
   :alt: Build status of perf on Travis CI
   :target: https://travis-ci.org/haypo/perf

The Python ``perf`` module is a toolkit to write, run and analyze benchmarks.

Features
--------

* Simple API to run reliable benchmarks
* Automatically calibrate a benchmark for a time budget.
* Spawn multiple worker processes.
* Compute the mean and standard deviation.
* Detect if a benchmark result seems unstable.
* JSON format to store benchmark results.
* Support multiple units: seconds, bytes and integer.

Usage
-----

To `run a benchmark`_ use the ``perf timeit`` command::

    $ python3 -m perf timeit '[1,2]*1000' -o bench.json
    .....................
    Mean +- std dev: 4.22 us +- 0.08 us

or write a benchmark script:

.. code:: python

    #!/usr/bin/env python3
    import perf
    import time


    def func():
        time.sleep(0.001)


    runner = perf.Runner()
    benchmark = runner.bench_func('sleep', func)
    benchmark.dump('sleep.json', replace=True)

To `analyze benchmark results`_ use the ``perf stats`` command::

    $ python3 -m perf stats telco.json
    Total duration: 29.2 sec
    Start date: 2016-10-21 03:14:19
    End date: 2016-10-21 03:14:53
    Raw value minimum: 177 ms
    Raw value maximum: 183 ms

    Number of calibration run: 1
    Number of run with values: 40
    Total number of run: 41

    Number of warmup per run: 1
    Number of value per run: 3
    Loop iterations per value: 8
    Total number of values: 120

    Minimum:         22.1 ms
    Median +- MAD:   22.5 ms +- 0.1 ms
    Mean +- std dev: 22.5 ms +- 0.2 ms
    Maximum:         22.9 ms

      0th percentile: 22.1 ms (-2% of the mean) -- minimum
      5th percentile: 22.3 ms (-1% of the mean)
     25th percentile: 22.4 ms (-1% of the mean) -- Q1
     50th percentile: 22.5 ms (-0% of the mean) -- median
     75th percentile: 22.7 ms (+1% of the mean) -- Q3
     95th percentile: 22.9 ms (+2% of the mean)
    100th percentile: 22.9 ms (+2% of the mean) -- maximum

    Number of outlier (out of 22.0 ms..23.0 ms): 0

There's also

* ``perf compare_to`` command tests if a difference is
  significant. It supports comparison between multiple benchmark suites (made
  of multiple benchmarks)
  ::
  
    $ python3 -m perf compare_to py2.json py3.json --table
    +-----------+---------+------------------------------+
    | Benchmark | py2     | py3                          |
    +===========+=========+==============================+
    | timeit    | 4.70 us | 4.22 us: 1.11x faster (-10%) |
    +-----------+---------+------------------------------+

* ``perf system`` tune command to tune your system to run stable benchmarks.
* Automatically collect metadata on the computer and the benchmark:
  use the ``perf metadata`` command to display them, or the
  ``perf collect_metadata`` command to manually collect them.
* ``--track-memory`` and ``--tracemalloc`` options to track
  the memory usage of a benchmark.

Quick Links
-----------
* `perf documentation
  <https://perf.readthedocs.io/>`_
* `perf project homepage at GitHub
  <https://github.com/haypo/perf>`_ (code, bugs)
* `Download latest perf release at the Python Cheeseshop (PyPI)
  <https://pypi.python.org/pypi/perf>`_

Command to install perf on Python 3::

    python3 -m pip install perf

perf supports Python 2.7 and Python 3. It is distributed under the MIT license.

.. _run a benchmark: https://perf.readthedocs.io/en/latest/run_benchmark.html
.. _analyze benchmark results: https://perf.readthedocs.io/en/latest/analyze.html
