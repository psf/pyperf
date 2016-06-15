Changelog
=========

Version 0.5
-----------

Changes:

* Replace mean with median
* Add :meth:`perf.Benchmark.median` method
* ``Benchmark.get_metadata()`` method removed: use directly the
  :attr:`perf.Benchmark.metadata` attribute


Version 0.4 (2016-06-15)
------------------------

New features:

* New ``hist`` and ``hist_scipy`` commands: display an histogram (text or
  graphical mode)
* New ``stats`` command: display statistics on a benchmark result
* New ``--affinity=CPU_LIST`` command line option
* Emit a warning or an error in english if the standard deviation is larger
  than 10% and/or the shortest sample is shorter than 1 ms
* Emit a warning or an error if the shortest sample took less than 1 ms
* Add ``perf_version``, ``duration`` metadata. Moreover, the ``date`` metadata
  is now displayed.

API:

* The API deeply changed to mininize duplications of data and make the JSON
  files more compact

Changes:

* The command line interface also changed. For example, ``perf.metadata``
  command becomes ``perf metadata``.
* On Python 2, ``psutil`` optional dependency is now used for CPU affinity.
  It ensures that CPU affinity is set for loop calibration too.
* On Python 2, add dependency to the backported ``statistics`` module
* ``perf.mean()`` and ``perf.stdev()`` functions have been removed: use
  the ``statistics`` module (which is available on Python 2.7 and Python 3)
* New optional dependency on ``boltons`` (``boltons.statsutils``) to compute
  even more statistics in the ``stats`` and ``hist_scipy`` commands


Version 0.3 (2016-06-10)
------------------------

* Add ``compare`` and ``compare_to`` commands to the ``-m perf`` CLI
* TextRunner is now able to spawn child processes, parse command arguments
  and more features
* If TextRunner detects isolated CPUs, it sets automatically the CPU affinity
  to these isolated CPUs
* Add ``--json-file`` command line option
* Add :meth:`TextRunner.bench_sample_func` method
* Add examples of the API to the documentation. Split also the documentation
  into subpages.
* Add metadata ``cpu_affinity``
* Add :func:`perf.is_significant` function
* Move metadata from :class:`~perf.Benchmark` to ``RunResult``
* Rename the ``Results`` class to :class:`~perf.Benchmark`
* Add :attr:`~perf.text_runner.TextRunner.inner_loops` attribute to
  :class:`~perf.text_runner.TextRunner`, used for microbenchmarks when an
  instruction is manually duplicated multiple times

Version 0.2 (2016-06-07)
------------------------

* use JSON to exchange results between processes
* new ``python3 -m perf`` CLI
* new :class:`~perf.text_runner.TextRunner` class
* huge enhancement of the timeit module
* timeit has a better output format in verbose mode and now also supports a
  ``-vv`` (very verbose) mode. Minimum and maximum are not more shown in
  verbose module, only in very verbose mode.
* metadata: add ``python_implementation`` and ``aslr``

Version 0.1 (2016-06-02)
------------------------

* First public release

