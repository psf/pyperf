******
pyperf
******

.. image:: https://img.shields.io/pypi/v/pyperf.svg
   :alt: Latest release on the Python Cheeseshop (PyPI)
   :target: https://pypi.python.org/pypi/pyperf

.. image:: https://travis-ci.org/psf/pyperf.svg?branch=master
   :alt: Build status of pyperf on Travis CI
   :target: https://travis-ci.org/psf/pyperf

The Python ``pyperf`` module is a toolkit to write, run and analyze benchmarks.

Features
========

* Simple API to run reliable benchmarks
* Automatically calibrate a benchmark for a time budget.
* Spawn multiple worker processes.
* Compute the mean and standard deviation.
* Detect if a benchmark result seems unstable.
* JSON format to store benchmark results.
* Support multiple units: seconds, bytes and integer.


Usage
=====

To `run a benchmark`_ use the ``pyperf timeit`` command (result written into
``bench.json``)::

    $ python3 -m pyperf timeit '[1,2]*1000' -o bench.json
    .....................
    Mean +- std dev: 4.22 us +- 0.08 us

Or write a benchmark script ``bench.py``:

.. code:: python

    #!/usr/bin/env python3
    import pyperf

    runner = pyperf.Runner()
    runner.timeit(name="sort a sorted list",
                  stmt="sorted(s, key=f)",
                  setup="f = lambda x: x; s = list(range(1000))")

See `the API docs`_ for full details on the ``timeit`` function and the
``Runner`` class. To run the script and dump the results into a file named
``bench.json``::

    $ python3 bench.py -o bench.json

To `analyze benchmark results`_ use the ``pyperf stats`` command::

    $ python3 -m pyperf stats bench.json
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

There's also:

* ``pyperf compare_to`` command tests if a difference is
  significant. It supports comparison between multiple benchmark suites (made
  of multiple benchmarks)
  ::

    $ python3 -m pyperf compare_to py36.json py38.json --table
    +-----------+---------+------------------------------+
    | Benchmark | py36    | py38                         |
    +===========+=========+==============================+
    | timeit    | 4.70 us | 4.22 us: 1.11x faster (-10%) |
    +-----------+---------+------------------------------+

* ``pyperf system tune`` command to tune your system to run stable benchmarks.
* Automatically collect metadata on the computer and the benchmark:
  use the ``pyperf metadata`` command to display them, or the
  ``pyperf collect_metadata`` command to manually collect them.
* ``--track-memory`` and ``--tracemalloc`` options to track
  the memory usage of a benchmark.


Quick Links
===========

* `pyperf documentation
  <https://pyperf.readthedocs.io/>`_
* `pyperf project homepage at GitHub
  <https://github.com/psf/pyperf>`_ (code, bugs)
* `Download latest pyperf release at the Python Cheeseshop (PyPI)
  <https://pypi.python.org/pypi/pyperf>`_

Command to install pyperf on Python 3::

    python3 -m pip install pyperf

pyperf requires Python 3.6 or newer.

Python 2.7 users can use pyperf 1.7.1 which is the last version compatible with
Python 2.7.

pyperf is distributed under the MIT license.

The pyperf project is covered by the `PSF Code of Conduct
<https://www.python.org/psf/codeofconduct/>`_.

.. _run a benchmark: https://pyperf.readthedocs.io/en/latest/run_benchmark.html
.. _the API docs: http://pyperf.readthedocs.io/en/latest/api.html#Runner.timeit
.. _analyze benchmark results: https://pyperf.readthedocs.io/en/latest/analyze.html
