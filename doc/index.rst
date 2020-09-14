++++++++++++++++++++
Python pyperf module
++++++++++++++++++++

The Python ``pyperf`` module is a toolkit to write, run and analyze benchmarks.

Documenation:

.. toctree::
   :maxdepth: 2

   user_guide
   developer_guide

Features of the ``pyperf`` module:

* :ref:`Simple API <api>` to run reliable benchmarks: see :ref:`examples
  <examples>`.
* Automatically calibrate a benchmark for a time budget.
* Spawn multiple worker processes.
* Compute the mean and standard deviation.
* Detect if a benchmark result seems unstable: see the :ref:`pyperf check command
  <check_cmd>`.
* :ref:`pyperf stats command <stats_cmd>` to analyze the distribution of benchmark
  results (min/max, mean, median, percentiles, etc.).
* :ref:`pyperf compare_to command <compare_to_cmd>` tests if a difference if
  significant. It supports comparison
  between multiple benchmark suites (made of multiple benchmarks)
* :ref:`pyperf timeit command line tool <timeit_cmd>` for quick but reliable
  Python microbenchmarks
* :ref:`pyperf system tune command <system_cmd>` to tune your system to run
  stable benchmarks.
* Automatically collect metadata on the computer and the benchmark:
  use the :ref:`pyperf metadata command <metadata_cmd>` to display them, or the
  :ref:`pyperf collect_metadata command  <collect_metadata_cmd>` to manually
  collect them.
* ``--track-memory`` and ``--tracemalloc`` :ref:`options <runner_cli>` to track
  the memory usage of a benchmark.
* :ref:`JSON format <json>` to store benchmark results.
* Support multiple units: seconds, bytes and integer.

Quick Links:

* `pyperf documentation
  <https://pyperf.readthedocs.io/>`_ (this documentation)
* `pyperf project homepage at GitHub
  <https://github.com/psf/pyperf>`_ (code, bugs)
* `Download latest pyperf release at the Python Cheeseshop (PyPI)
  <https://pypi.python.org/pypi/pyperf>`_

Other Python benchmark projects:

* `pyperformance <https://pypi.python.org/pypi/pyperformance>`_: the Python
  benchmark suite which uses ``pyperf``
* `Python speed mailing list
  <https://mail.python.org/mailman/listinfo/speed>`_
* `Airspeed Velocity <http://asv.readthedocs.io/>`_:
  A simple Python benchmarking tool with web-based reporting
* `pytest-benchmark
  <https://github.com/ionelmc/pytest-benchmark/>`_
* `boltons.statsutils
  <http://boltons.readthedocs.io/en/latest/statsutils.html>`_

The pyperf project is covered by the `PSF Code of Conduct
<https://www.python.org/psf/codeofconduct/>`_.
