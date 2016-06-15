Changelog
=========

* Version 0.4

  - New ``python3 -m perf hist`` and ``python3 -m perf hist_scipy`` commands:
    display an histogram in text or graphical (using ``scipy``) mode
  - New ``python3 -m perf stats`` command: display statistics of a result
  - New ``--affinity=CPU_LIST`` command line option
  - On Python 2, ``psutil`` optional dependency is now used for CPU affinity.
    It ensures that CPU affinity is set for loop calibration too.
  - Emit a warning or an error in english if the standard deviation is larger
    than 10% and/or the shortest sample is shorter than 1 ms
  - Emit a warning or an error if the shortest sample took less than 1 ms
  - Move metadata from :class:`perf.RunResult` to :class:`perf.Benchmark`
  - New :attr:`perf.Benchmark.loops` and :attr:`perf.Benchmark.inner_loops`
    attributes (they were previously stored in metadata).
  - The ``TextRunner.result`` attribute has been removed, replaced with
    a new :attr:`~perf.text_runner.TextRunner.metadata` attribute (it's also
    possible to pass metadata to the constructor).
  - On Python 2, add dependency to the backported ``statistics`` module:
    https://pypi.python.org/pypi/statistics
  - ``perf.mean()`` and ``perf.stdev()`` functions have been removed: use
    the ``statistics`` module which is also available on Python 2.7

* Version 0.3 (2016-06-10)

  - Add ``compare`` and ``compare_to`` commands to the ``-m perf`` CLI
  - TextRunner is now able to spawn child processes, parse command arguments
    and more features
  - If TextRunner detects isolated CPUs, it sets automatically the CPU affinity
    to these isolated CPUs
  - Add ``--json-file`` command line option
  - Add :meth:`TextRunner.bench_sample_func` method
  - Add examples of the API to the documentation. Split also the documentation
    into subpages.
  - Add metadata ``cpu_affinity``
  - Add :func:`perf.is_significant` function
  - Move metadata from :class:`~perf.Benchmark` to :class:`~perf.RunResult`
  - Rename the ``Results`` class to :class:`~perf.Benchmark`
  - Add :attr:`~perf.text_runner.TextRunner.inner_loops` attribute to
    :class:`~perf.text_runner.TextRunner`, used for microbenchmarks when an
    instruction is manually duplicated multiple times

* Version 0.2 (2016-06-07)

  - use JSON to exchange results between processes
  - new ``python3 -m perf`` CLI
  - new :class:`~perf.text_runner.TextRunner` class
  - huge enhancement of the timeit module
  - timeit has a better output format in verbose mode and now also supports a
    ``-vv`` (very verbose) mode. Minimum and maximum are not more shown in
    verbose module, only in very verbose mode.
  - metadata: add ``python_implementation`` and ``aslr``

* Version 0.1 (2016-06-02)

  - First public release

