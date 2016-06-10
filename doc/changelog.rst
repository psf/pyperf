Changelog
=========

* Version 0.4

  - New ``--affinity=CPU_LIST`` command line option
  - On Python 2.7, the ``tasket`` command is now used if available to pin
    worker processes to isolated CPUs

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

