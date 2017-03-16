++++++++++++++++++
Python perf module
++++++++++++++++++

The Python ``perf`` module is a toolkit to write, run and analyze benchmarks.

Documenation:

.. toctree::
   :maxdepth: 2

   user_guide
   developer_guide

Features of the ``perf`` module:

* :ref:`Simple API <api>` to run reliable benchmarks: see :ref:`examples
  <examples>`.
* Automatically calibrate a benchmark for a time budget.
* Spawn multiple worker processes.
* Compute the mean and standard deviation.
* Detect if a benchmark result seems unstable: see the :ref:`perf check command
  <check_cmd>`.
* :ref:`perf stats command <stats_cmd>` to analyze the distribution of benchmark
  results (min/max, mean, median, percentiles, etc.).
* :ref:`perf compare command <compare_cmd>` tests if a difference if
  significant (see :func:`is_significant` function). It supports comparison
  between multiple benchmark suites (made of multiple benchmarks)
* :ref:`perf timeit command line tool <timeit_cmd>` for quick but reliable
  Python microbenchmarks
* :ref:`perf system tune command <system_cmd>` to tune your system to run
  stable benchmarks.
* Automatically collect metadata on the computer and the benchmark:
  use the :ref:`perf metadata command <metadata_cmd>` to display them, or the
  :ref:`perf collect_metadata command  <collect_metadata_cmd>` to manually
  collect them.
* ``--track-memory`` and ``--tracemalloc`` :ref:`options <runner_cli>` to track
  the memory usage of a benchmark.
* :ref:`JSON format <json>` to store benchmark results.
* Support multiple units: seconds, bytes and integer.

Quick Links:

* `perf documentation
  <https://perf.readthedocs.io/>`_ (this documentation)
* `perf project homepage at GitHub
  <https://github.com/haypo/perf>`_ (code, bugs)
* `Download latest perf release at the Python Cheeseshop (PyPI)
  <https://pypi.python.org/pypi/perf>`_

Other Python benchmark projects:

* `performance <https://pypi.python.org/pypi/performance>`_: the Python
  benchmark suite which uses ``perf``
* `Python speed mailing list
  <https://mail.python.org/mailman/listinfo/speed>`_
* `Airspeed Velocity <http://asv.readthedocs.io/>`_:
  A simple Python benchmarking tool with web-based reporting
* `pytest-benchmark
  <https://github.com/ionelmc/pytest-benchmark/>`_
* `boltons.statsutils
  <http://boltons.readthedocs.io/en/latest/statsutils.html>`_
