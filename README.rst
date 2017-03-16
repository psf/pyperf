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

Features:

* Simple API to run reliable benchmarks
* Automatically calibrate a benchmark for a time budget.
* Spawn multiple worker processes.
* Compute the mean and standard deviation on values.
* Detect if a benchmark result seems unstable: see the check command.
* ``perf stats`` command to analyze the distribution of benchmark
  results (min/max, mean, median, percentiles, etc.).
* ``perf compare`` command tests if a difference if
  significant (see the ``is_significant()`` function). It supports comparison
  between multiple benchmark suites (made of multiple benchmarks)
* ``perf timeit`` command line tool for quick but reliable
  Python microbenchmarks
* ``perf system`` tune command to tune your system to run stable benchmarks.
* Automatically collect metadata on the computer and the benchmark:
  use the ``perf metadata`` command to display them, or the
  ``perf collect_metadata`` command to manually collect them.
* ``--track-memory`` and ``--tracemalloc`` options to track
  the memory usage of a benchmark.
* JSON format to store benchmark results.
* Support multiple units: seconds, bytes and integer.

Links:

* `perf project homepage at GitHub
  <https://github.com/haypo/perf>`_ (code, bugs)
* `perf documentation
  <https://perf.readthedocs.io/>`_
* `Download latest perf release at the Python Cheeseshop (PyPI)
  <https://pypi.python.org/pypi/perf>`_
* License: MIT

perf supports Python 2.7 and Python 3. Install perf on Python 3::

    python3 -m pip install perf
