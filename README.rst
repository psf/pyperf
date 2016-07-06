****
perf
****

.. image:: https://img.shields.io/pypi/v/perf.svg
   :alt: Latest release on the Python Cheeseshop (PyPI)
   :target: https://pypi.python.org/pypi/perf

.. image:: https://travis-ci.org/haypo/perf.svg?branch=master
   :alt: Build status of perf on Travis CI
   :target: https://travis-ci.org/haypo/perf

The Python ``perf`` module is a toolkit to write, run, analyze and modify
benchmarks.

Features:

* JSON format to store benchmark results
* Command line tools to display, analyze and modify benchmarks
* Statistical tools to analyze the distribution of benchmark results
* ``compare`` command supports comparison between multiple benchmark suites
  (made of multiple benchmarks)
* ``timeit`` command for quick but reliable Python microbenchmarks

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
