Changelog
=========

Version 2.6.2 (2023-11-02)
---------------------------

* Now, pystats stats are collected during warmups.
  Patch by Mike Droettboom.
* system: Fix detection of battery.
  Patch by Victor Stinner

Version 2.6.1 (2023-06-12)
---------------------------

* Fix a possible attribute error in argument parsing.
  Patch by Colton Myers

Version 2.6.0 (2023-03-22)
--------------------------

* Inherit ``PYTHONPATH`` environment variable by default.
  Patch by Theodore Ni.

* ``Runner.bench_async_func()`` takes an optional ``loop_factory`` to support custom loop construction.
  Patch by Itamar O.

Version 2.5.0 (2022-11-04)
--------------------------

* Support collecting specialization statistics from running benchmarks.
  Patch by Mike Droettboom.

* Recognize new name of Graal-based Python as jitted.
  Patch by Michael Droettboom

Version 2.4.1 (2022-08-07)
--------------------------

* Reject --tracemalloc in ``pyperf command``.
  Patch by Yichen Yan

Version 2.4.0 (2022-07-20)
--------------------------

* pyperf now recognizes `pyston <https://github.com/pyston/pyston>`_ as the JIT-based implementation.
  Patch by Kevin Modzelewski.
* :ref:`Runner CLI <runner_cli>` now supports ``--profile=PROFILE`` option for profiling benchmarks.
  Patch by Michael Droettboom.

Version 2.3.1 (2022-02-03)
--------------------------

* Add a ``Runner.bench_async_func()`` to benchmark an asyncio coroutine.
  Patch by Inada Naoki.
* pyperf now recognizes `graalpython <https://github.com/oracle/graalpython>`_ as the JIT-based implementation.
  Patch by Tim Felgentreff.

Version 2.3.0 (2021-09-28)
--------------------------

* pyperf ref:`compare_to command <compare_to_cmd>` now supports the
  ``--table-format`` option which can designate the table format
  between reST and markdown.

Version 2.2.0 (2021-03-24)
--------------------------

* ``--track-memory`` option now supports macOS by using ``psutil``.
* Added ``--copy-env`` command line option that inherits all environment variables.
* The development branch ``master`` was renamed to ``main``.
  See https://sfconservancy.org/news/2020/jun/23/gitbranchname/ for the
  rationale.

Version 2.1.0 (2021-01-14)
--------------------------

* The :ref:`compare_to command <compare_to_cmd>` now computes the geometric
  mean.
* The :ref:`compare_to command <compare_to_cmd>` no longer displays
  percentages: display less numbers to make the output easier to read. Also,
  percentage were almost the same values than the xxx faster or xxx slower
  values, but rounded differenly which introduced confusion.
* Project moved to https://github.com/psf/pyperf/
* system command now only emits a warning rather than failing with a hard error
  if it fails to get or set the frequency of a CPU.
* The pyperf project is now covered by the `PSF Code of Conduct
  <https://www.python.org/psf/codeofconduct/>`_.

Version 2.0.0 (2020-03-19)
--------------------------

* Drop Python 2 support. Use pyperf 1.7.1 if you still need Python 2.7
  support.
* Remove ``python_unicode`` metadata.
* pyperf.perf_counter() is now deprecated: use time.perf_counter() directly.

Version 1.7.1 (2020-03-09)
--------------------------

* Support Python 3.8: ``time.clock()`` no longer exists.

Version 1.7.0 (2019-12-17)
--------------------------

* metadata: add ``python_compiler``
* Windows: inherit ``SystemDrive`` environment variable by default.
  Contribution by Steve Dower.
* Fix tests on ARM and PPC: cpu_model_name metadata is no longer required
  on Linux.
* tests: Do not allow test suite to execute without unittest2 on Python2,
  otherwise man failures occur due to missing 'assertRegex'.
  Contribution by John Vandenberg.
* doc: Update old/dead links.
* Travis CI: drop Python 3.4 support.

Version 1.6.1 (2019-05-21)
--------------------------

The project name changes to "pyperf" from "perf", to avoid confusion
with the `Linux perf project <https://perf.wiki.kernel.org/>`_ which has
a Python binding called "perf" as well.

Version 1.6.0 (2019-01-11)
--------------------------

* Add *teardown* optional parameter to :class:`Runner.timeit` and ``--teardown``
  option to the :ref:`perf timeit <timeit_cmd>` command. Patch by **Alex
  Khomchenko**.
* ``Runner.timeit(stmt)`` can now be used to use the statement as the benchmark
  name.
* Port :ref:`system tune <system_cmd>` command to Python 2 (use
  lseek+read/write instead of pread/pwrite which aren't available on Python 2).
  Patch by **Stefan Talpalaru**.
* :ref:`perf collect_metadata <collect_metadata_cmd>` now also supports reading
  CPU frequencies on IBM Z.

Version 1.5.1 (2018-01-10)
--------------------------

* Fix ``--track-memory`` option of the ``Runner.bench_command()`` command.

Version 1.5 (2018-01-09)
------------------------

* Fix ``--track-memory`` and ``--tracemalloc`` options.
  Add non regression tests.
* Remove the ``--max-time`` option of Runner, it was ignored.
* Project moved from https://github.com/haypo/perf to https://github.com/vstinner/perf
* system command: In case the system is not ready for benchmarking, makes
  system show exits with return code 2 so bash scripts could put
  'python -m perf system show' directly without greping for the output.
  Contributed by Boris Feld.
* On Windows: Enables high priority for processes when benchmarking
  (``REALTIME_PRIORITY_CLASS``). Contributed by Steve Dower.

Version 1.4 (2017-07-06)
------------------------

* Fix parse_cpu_list(): strip also NUL characters
* Add examples to the README file. Contributed by **Alex Willmer**.

Version 1.3 (2017-05-29)
------------------------

* Add ``get_loops()`` and ``get_inner_loops()`` methods to Run and Benchmark
  classes
* Documentation: add export_csv.py and plot.py examples
* Rewrite warmup calibration for PyPy:

  - Use Q1, Q3 and stdev, rather than mean and checking if the first value
    is an outlier
  - Always use a sample of 10 values, rather than using a sample of a variable
    size starting with 3 values

* Use lazy import for most imports of the largest modules to reduce the
  number of imported module on 'import perf'.
* Fix handling of broken pipe error to prevent logging the error:
  "Exception ignored in: ... BrokenPipeError: ..."
* ``collect_metadata`` gets more metadata on FreeBSD:

  - use ``os.getloadavg()`` if ``/proc/loadavg`` is not available (ex: FreeBSD)
  - use ``psutil.boot_time()`` if ``/proc/stat`` is not available (ex: FreeBSD)
    to get ``boot_time`` and ``uptime`` metadata

* The Runner constructor now raises an exception if more than one instance is
  created.

Version 1.2 (2017-04-10)
------------------------

* ``stats`` command: count the number of outliers
* Rewrite the calibration code to support PyPy:

  - On PyPy, calibrate also the number of warmups
  - On PyPy, recalibrate the number of loops and warmups
  - Loop calibration now uses the number of warmups and values instead
    of 1 to compute warmup values
  - A worker process cannot calibrate the number of loops and compute values.
    These two operations now require two worker processes.

* Command line interface (CLI): the ``--benchmark``, ``--include-benchmark``
  and ``--exclude-benchmark`` options can now be specified multiple times.
* Rewrite ``dump`` command:

  - Writes one value per line
  - Now display also metadata of calibration runs
  - Enhance formatting of calibration runs
  - Display number of warmup, value and loop

* Add new run metadata:

  - ``calibrate_loops``, ``recalibrate_loops``: number of loops
    of loop calibration/recalibration runs
  - ``calibrate_warmups``, ``recalibrate_warmups``: number of warmups
    of warmup calibration/recalibration runs

Version 1.1 (2017-03-27)
------------------------

* Add a new "perf command" command to measure the timing of a program
* ``Runner.bench_command()`` now measures also the maximum RSS memory if
  available.
* Fix Windows 32bit issue on Python 2.7, fix by yattom.
* ``Runner.bench_func()`` now uses ``functools.partial()`` if the function
  has argument. Calling ``partial()`` is now 1.07x faster (-6%) than calling
  ``func(*args)``.
* Store memory values as integers, not float, when tracking memory usage
  (``--track-memory`` and ``--tracemalloc`` options)

Version 1.0 (2017-03-17)
------------------------

Enhancements:

* ``stats`` command now displays percentiles
* ``hist`` command now also checks the benchmark stability by default
* dump command now displays raw value of calibration runs.
* Add ``Benchmark.percentile()`` method

Backward incompatible changes:

* Remove the ``compare`` command to only keep the ``compare_to`` command
  which is better defined
* Run warmup values must now be normalized per loop iteration.
* Remove ``format()`` and ``__str__()`` methods from Benchmark. These methods
  were too opinionated.
* Rename ``--name=NAME`` option to ``--benchmark=NAME``
* Remove ``perf.monotonic_clock()`` since it wasn't monotonic on Python 2.7.
* Remove ``is_significant()`` from the public API

Other changes:

* check command now only complains if min/max is 50% smaller/larger than
  the mean, instead of 25%.

Version 0.9.6 (2017-03-15)
--------------------------

Major change:

* Display ``Mean +- std dev`` instead of ``Median +- std dev``

Enhancements:

* Add a new ``Runner.bench_command()`` method to measure the execution time of
  a command.
* Add ``mean()``, ``median_abs_dev()`` and ``stdev()`` methods to ``Benchmark``
* ``check`` command: test also minimum and maximum compared to the mean

Major API change, rename "sample" to "value":

* Rename attributes and methods:

  - ``Benchmark.bench_sample_func()`` => ``Benchmark.bench_time_func()``.
  - ``Run.samples`` => ``Run.values``
  - ``Benchmark.get_samples()`` => ``Benchmark.get_values()``
  - ``get_nsample()`` => ``get_nvalue()``
  - ``Benchmark.format_sample()`` => ``Benchmark.format_value()``
  - ``Benchmark.format_samples()`` => ``Benchmark.format_values()``

* Rename Runner command line options:

  - ``--samples`` => ``--values``
  - ``--debug-single-sample`` => ``--debug-single-value``

Changes:

* ``convert``: Remove ``--remove-outliers`` option
* ``check`` command now tests stdev/mean, instead of testing stdev/median
* setup.py: statistics dependency is now installed using ``extras_require`` to
  support setuptools 18 and newer
* Add setup.cfg to enable universal builds: same wheel package for Python 2
  and Python 3
* Add ``perf.VERSION`` constant: tuple of int
* JSON version 6: write metadata common to all benchmarks (common to all runs
  of all benchmarks) at the root; rename 'samples' to 'values' in runs.

Version 0.9.5 (2017-03-06)
--------------------------

* Add ``--python-names`` option to the :ref:`Runner CLI <runner_cli>`
* ``system show`` command now checks if the system is ready for benchmarking
* Fix ``--compare-to`` option: the benchmark was run twice with the reference
  Python, instead of being run first with reference Python and then changed
  Python.
* Runner now raises an exception if a benchmark name is not unique.
* ``compare_to`` command now keeps the original order of benchmarks, only
  sort if ``--by-speed`` option is used.
* Fix ``system`` command on macOS on non-existent ``/proc`` and ``/sys``
  pseudo-files.
* Fix ``system`` bugs on systems with more than 32 processors.

Version 0.9.4 (2017-03-01)
--------------------------

New features:

* Add ``--compare-to`` option to the :ref:`Runner CLI <runner_cli>`
* :ref:`compare_to <compare_to_cmd>` command: Add ``--table`` option to render a table

Bugfixes:

* Fix the ``abs_executable()`` function used to find the absolute path to the
  Python program. Don't follow symbolic links to support correctly virtual
  environments.

Version 0.9.3 (2017-01-16)
--------------------------

* Fix the Windows support.
* system: Don't try to read or write CPU frequency when the
  /sys/devices/system/cpu/cpu0/cpufreq/ directory doesn't exist. For example,
  virtual machines don't have this directory.
* Fix a ``ResourceWarning`` in ``BenchmarkSuite.dump()`` for gzip files.

Version 0.9.2 (2016-12-15)
--------------------------

* Issue #15: Added ``--no-locale`` command line option and locale environment
  variables are now inherited by default.
* Add :meth:`Runner.timeit` method.
* Fix ``stats`` command: display again statistics on the whole benchmark suite.
* Fix a ResourceWarning if interrupted:  Runner now kills the worker process
  when interrupted.
* ``compare`` and ``compare_to``: add percent difference to faster/slower
* Rewrite timeit internally: copy code from CPython 3.7 and adapt it to
  PyPy.

Version 0.9.1 (2016-11-18)
--------------------------

* ``system tune`` now also sets the maximum sample rate of perf event.
* ``system show`` command now also displays advices, not only ``system tune``
* ``system`` now detects when running on a laptop with the power cable
  unplugged.
* ``system tune`` now handles errors when /dev/cpu/N/msr device is missing:
  log an error suggesting to load the ``msr`` kernel module
* Fix a ResourceWarning in Runner._spawn_worker_suite(): wait until the worker
  completes.

Version 0.9.0 (2016-11-07)
--------------------------

Enhancements:

* Runner doesn't ignore worker stdout and stderr anymore. Regular ``print()``
  now works as expected.
* ``system`` command: Add a new ``--affinity`` command line option
* check and system emit a warning if nohz_full is used with the intel_pstate
  driver.
* ``collect_metadata``: On CPUs not using the intel_pstate driver, don't run
  the cpupower command anymore to check if the Turbo Boost is enabled. It
  avoids to spawn N processes in each worker process, where N is the number of
  CPUs used by the worker process. The ``system`` command can be used to tune
  correctly Turbo Boost, or just to check the state of Turbo Boost.

Changes:

* system: tune stops the irqbalance service and sets the CPU affinity of
  interruptions (IRQ).
* The ``--stdout`` internal option has been removed, replaced by a new
  ``--pipe`` option. Workers can now use stdout for regular messages.
* ``get_dates()`` methods now return ``None`` rather than an empty tuple
  if runs don't have the ``date`` metadata.

Version 0.8.3 (2016-11-03)
--------------------------

Enhancement:

* New ``system tune`` command to tune the system for benchmarks: disable Turbo
  Boost, check isolated CPUs, set CPU frequency, set CPU scaling governor to
  "performance", etc.
* Support reading and writing JSON files compressed by gzip: use gzip
  if the filename ends with ``.gz``
* The detection of isolated CPUs now works also on Linux older than 4.2:
  ``/proc/cmdline`` is now parsed to read the ``isolcpus=`` option
  if ``/sys/devices/system/cpu/isolated`` sysfs doesn't exist.

Backward incompatible changes:

* JSON file produced by perf 0.8.3 cannot be read by perf 0.8.2 anymore.
* Remove the Metadata class: values of get_metadata() are directly metadata
  values.
* Drop support for JSON produced with perf 0.7.3 and older. Use perf 0.8.2
  to convert old JSON to new JSON.

Optimizations:

* Loading a large JSON file is now 10x faster (5 sec => 500 ms).
* Optimize ``Benchmark.add_run()``: don't recompute common metadata at each
  call, but update existing common metadata.
* Don't store dates of metadata as datetime.datetime but strings to optimize
  ``Benchmark.load()``

Version 0.8.2 (2016-10-19)
--------------------------

* Fix formatting of benchmark which only contains calibration runs.

Version 0.8.1 (2016-10-19)
--------------------------

* Rename ``metadata`` command to ``collect_metadata``
* Add new commands: ``metadata`` (display metadata of benchmarks files)
  and ``check`` (check if benchmarks seem stable)
* timeit: add ``--duplicate`` option to reduce the overhead of the outer loop.
* BenchmarkSuite constructor now requires a non-empty sequence of Benchmark
  objects.
* Store date in metadata with microsecond resolution.
* ``collect_metadata``: add ``--output`` command line option.
* Bugfix: don't follow symbolic links when getting the absolute path to a
  Python executable. The venv module requires to use the symlink to get the
  modules installed in a virtual environment.

Version 0.8.0 (2016-10-14)
--------------------------

The API was redesigned to support running multiple benchmarks with a single
Runner object.

Enhancements:

* ``--loops`` command line argument now accepts ``x^y`` syntax. For example,
  ``--loops=2^8`` uses ``256`` iterations
* Calibratation is now done in a dedicated process to avoid side effect on the
  first process. This change is important if Python has a JIT compiler, to
  get more reliable timings on the first worker computing samples.

Incompatible API changes:

* Benchmark constructor now requires a non-empty sequence of Run objects.
* A benchmark must now have a name: all runs must have a name metadata.
* Remove *name* argument from Runner constructor and add *name* parameter
  to :func:`Benchmark.bench_func` and :func:`Benchmark.bench_sample_func`
* ``perf.text_runner.TextRunner`` becomes simply ``perf.Runner``.
  Remove the ``perf.text_runner`` module.
* ``TextRunner.program_args`` attribute becomes a parameter of :class:`Runner`
  constructor. *program_args* must no more start with ``sys.executable`` which
  is automatically added, since the executable can now be overridden by the
  ``--python`` command line option.
* The ``TextRunner.prepare_subprocess_args`` attribute becomes a new
  *add_cmdline_args* parameter of :class:`Runner` constructor which is called
  with different arguments than the old *prepare_subprocess_args* callback.

Changes:

* Add *show_name* optional parameter to :class:`Runner`. The runner now
  displays the benchmark name by default.
* The calibration is now done after starting tracing memory
* Run constructor now accepts an empty list of samples. Moreover, it also
  accepts ``int`` and ``long`` number types for warmup sample values, not only
  ``float``.
* Add a new private ``--worker-task`` command line option to only execute
  a specific benchmark function by its identifier.
* Runner now supports calling more than one benchmark function using
  ``--worker-task`` internally.
* Benchmark.dump() and BenchmarkSuite.dump() now fails by default if the
  file already exists. Set the new *replace* parameter to true to allow to
  replace an existing file.

Version 0.7.12 (2016-09-30)
---------------------------

* Add ``--python`` command line option
* ``timeit``: add ``--name``, ``--inner-loops`` and ``--compare-to`` options
* TextRunner don't set CPU affinity of the main process, only on worker
  processes. It may help a little bit when using NOHZ_FULL.
* metadata: add ``boot_time`` and ``uptime`` on Linux
* metadata: add idle driver to ``cpu_config``

Version 0.7.11 (2016-09-19)
---------------------------

* Fix metadata when NOHZ is not used: when /sys/devices/system/cpu/nohz_full
  contains `` (null)\n``

Version 0.7.10 (2016-09-17)
---------------------------

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
  variables are removed, to enhance reproducibility.
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
is now done in the first worker process.

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
* Emit a warning or an error in English if the standard deviation is larger
  than 10% and/or the shortest sample is shorter than 1 ms
* Emit a warning or an error if the shortest sample took less than 1 ms
* Add ``perf_version``, ``duration`` metadata. Moreover, the ``date`` metadata
  is now displayed.

API:

* The API deeply changed to minimize duplications of data and make the JSON
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
* Add :attr:`~TextRunner.inner_loops` attribute to
  :class:`TextRunner`, used for microbenchmarks when an
  instruction is manually duplicated multiple times

Version 0.2 (2016-06-07)
------------------------

* use JSON to exchange results between processes
* new ``python3 -m perf`` CLI
* new :class:`TextRunner` class
* huge enhancement of the timeit module
* timeit has a better output format in verbose mode and now also supports a
  ``-vv`` (very verbose) mode. Minimum and maximum are not more shown in
  verbose module, only in very verbose mode.
* metadata: add ``python_implementation`` and ``aslr``

Version 0.1 (2016-06-02)
------------------------

* First public release
