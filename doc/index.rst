+++++++++++
Python perf
+++++++++++

The Python ``perf`` module is a toolkit to write, run, analyze and modify
benchmarks.

Features:

* JSON format to store benchmark results
* ``pyperf`` (or ``python3 -m perf``) command line tool to display, compare,
  analyze and modify benchmark results
* Statistical tools to analyze the distribution of benchmark results
* ``compare`` command supports comparison between multiple benchmark suites
  (made of multiple benchmarks)
* ``timeit`` command for quick but reliable Python microbenchmarks

Links:

* `perf project homepage at GitHub
  <https://github.com/haypo/perf>`_ (code, bugs)
* `perf documentation
  <https://perf.readthedocs.io/>`_ (this documentation)
* `Download latest perf release at the Python Cheeseshop (PyPI)
  <https://pypi.python.org/pypi/perf>`_
* License: MIT

Table Of Content:

.. toctree::
   :maxdepth: 2

   perf
   cli
   runner
   examples
   api
   changelog

See also:

* `performance <https://pypi.python.org/pypi/performance>`_: the Python
  benchmark suite
* `pytest-benchmark
  <https://github.com/ionelmc/pytest-benchmark/>`_
* `Python speed mailing list
  <https://mail.python.org/mailman/listinfo/speed>`_
* `boltons.statsutils
  <http://boltons.readthedocs.io/en/latest/statsutils.html>`_
