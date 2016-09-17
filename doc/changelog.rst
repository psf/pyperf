Changelog
=========

Version 0.7.10
--------------

* Fix metadata when there is no isolated CPU
* Fix collecting metadata when /sys/devices/system/cpu/nohz_full doesn't exist

Version 0.7.9 (2016-09-17)
--------------------------

* Add :meth:`Benchmark.get_unit` method
* Add :meth:`BenchmarkSuite.get_metadata` method
* metadata: add ``nohz_full`` and ``isolated`` to ``cpu_config``
* add ``--affinity`` option to the ``metadata`` command
* ``convert``: fix ``--remove-all-metadata``, keep the unit
* metadata: fix regex to get the Mercurial revision for ``python_version``,
  support also locally modified source code (revision ending with "+")

Version 0.7.8 (2016-09-10)
--------------------------

* Worker child processes are now run in a fresh environment: environment
  variables are removed, to enhance reproductability.
* Add ``--inherit-environ`` command line argument.
* metadata: add ``python_cflags``, fix ``python_version`` for PyPy and
  add also the Mercurial version into ``python_version`` (if available)

Version 0.7.7 (2016-09-07)
--------------------------

* Reintroduce TextRunner._spawn_worker_suite() as a temporary workaround
  to fix the pybench benchmark of the performance module.

Version 0.7.6 (2016-09-02)
--------------------------

Tracking memory usage now works correctly on Linux and Windows. The calibration
is now done in a the first worker process.

* ``--tracemalloc`` and ``--track-memory`` now use the memory peak as the
  unique sample for the run.
* Rewrite code to track memory usage on Windows. Add
  ``mem_peak_pagefile_usage`` metadata. The ``win32api`` module is no more
  needed, the code now uses the ``ctypes`` module.
* ``convert``: add ``--remove-all-metadata`` and ``--update-metadata`` commands
* Add ``unit`` metadata: ``byte``, ``integer`` or ``second``.
* Run samples can now be integer (not only float).
* Don't round samples to 1 nanosecond anymore: with a large number of loops
  (ex: 2^24), rounding reduces the accuracy.
* The benchmark calibration is now done by the first worker process

Version 0.7.5 (2016-09-01)
--------------------------

* Add ``Benchmark.update_metadata()`` method
* Warmup samples can now be zero. TextRunner now raises an error if a sample
  function returns zero for a sample, except of calibration and warmup samples.

Version 0.7.4 (2016-08-18)
--------------------------

* Support PyPy
* metadata: add ``mem_max_rss`` and ``python_hash_seed``
* Add :func:`perf.python_implementation` and :func:`perf.python_has_jit`
  functions
* In workers, calibration samples are now stored as warmup samples.
* With a JIT (PyPy), the calibration is now done in each worker. The warmup
  step can compute more warmup samples if a raw sample is shorter than the
  minimum time.
* Warmups of Run objects are now lists of (loops, raw_sample) rather than lists
  of samples. This change requires a change in the JSON format.

Version 0.7.3 (2016-08-17)
--------------------------

* add a new ``slowest`` command
* convert: add ``--extract-metadata=NAME``
* add ``--tracemalloc`` option: use the ``tracemalloc`` module to track
  Python memory allocation and get the peak of memory usage in metadata
  (``tracemalloc_peak``)
* add ``--track-memory`` option: run a thread reading the memory usage
  every millisecond and store the peak as ``mem_peak`` metadata
* ``compare_to``: add ``--group-by-speed`` (``-G``) and ``--min-speed`` options
* metadata: add ``runnable_threads``
* Fix issues on ppc64le Power8

Version 0.7.2 (2016-07-21)
--------------------------

* Add start/end dates and duration to the ``stats`` command
* Fix the program name: ``pyperf``, not ``pybench``!
* Fix the ``-b`` command line option of show/stats/... commands
* Fix metadata: ``load_avg_1min=0.0`` is valid!

Version 0.7.1 (2016-07-18)
--------------------------

* Fix the ``--append`` command line option

Version 0.7 (2016-07-18)
------------------------

* Add a new ``pybench`` program, similar to ``python3 -m perf``
* Most perf CLI commands now support multiple files and support benchmark
  suites.
* Add a new ``dump`` command to the perf CLI and a ``--dump`` option to
  the TextRunner CLI
* ``convert`` command: add ``--indent`` and ``--remove-warmups`` options
* replace ``--json`` option with ``-o/--output``
* New metadata:

  - cpu_config
  - cpu_freq
  - cpu_temp
  - load_avg_1min

Changes:

* New :func:`add_runs` function.
* Once again, rewrite Run and Benchmark API. Benchmark name is now optional.
* New :class:`Run` class: it now stores normalized samples rather than raw
  samples
* Metadata are now stored in Run, no more in Benchmark.
  Benchmark.get_metadata() return metadata common to all runs.
* Metadata become typed (can have a different type than string), the
  new :class:`Metadata` class formats them.

Version 0.6 (2016-07-06)
------------------------

Major change: perf now supports benchmark suites. A benchmark suite is made
of multiple benchmarks. perf commands now accepts benchmark suites as well.

New features:

* New ``convert`` command
* Add new command line options to TextRunner:

  * ``--fast``, ``--rigorous``
  * ``--hist``, ``--stats``
  * ``--json-append``
  * ``--quiet``

Changes:

* Remove ``--max-time`` option of TextRunner
* Replace ``--raw`` option with ``--worker``
* Replace ``--json`` with ``--stdout``
* Replace ``--json-file`` with ``--json``
* New ``perf convert`` command to convert or modify a benchmark suite
* Remove ``perf hist_scipy`` command, replaced with an example in the doc
* Add back "Mean +- Std dev" to the stats command
* Add get_loops() method to Benchmark
* Replace ``python3 -m perf.timeit`` (with dot) CLI with ``-m perf timeit``
  (without dot)
* Add :class:`perf.BenchmarkSuite` class
* name is now mandatory: it must be a non-empty string in Benchmark
  and TextRunner.
* A single JSON file can now contain multiple benchmarks
* Add a dependency to the ``six`` module
  :meth:`Benchmark.add_run` now raises an exception if a sample is zero.
* Benchmark.name becomes a property and is now stored in metadata
* TextRunner now uses powers of 2, rather than powers of 10, to calibrate the
  number of loops


Version 0.5 (2016-06-29)
------------------------

Changes:

* The ``hist`` command now accepts multiple files
* ``hist`` and ``hist_scipy`` commands got a new ``--bins`` option
* Replace mean with median
* Add :meth:`perf.Benchmark.median` method, remove ``Benchmark.mean()`` method
* ``Benchmark.get_metadata()`` method removed: use directly the
  :attr:`perf.Benchmark.metadata` attribute
* Add ``timer`` metadata. ``python_version`` now also contains the architecture
  (32 or 64 bits).


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

