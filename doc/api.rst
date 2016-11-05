API
===

Statistics
----------

.. function:: is_significant(samples1, samples2)

    Determine whether two samples differ significantly.

    This uses a `Student's two-sample, two-tailed t-test
    <https://en.wikipedia.org/wiki/Student's_t-test>`_ with alpha=0.95.

    Returns ``(significant, t_score)`` where significant is a ``bool``
    indicating whether the two samples differ significantly; ``t_score`` is the
    score from the two-sample T test.


Clocks
------

.. function:: perf_counter()

   Return the value (in fractional seconds) of a performance counter, i.e. a
   clock with the highest available resolution to measure a short duration.  It
   does include time elapsed during sleep and is system-wide.  The reference
   point of the returned value is undefined, so that only the difference between
   the results of consecutive calls is valid.

   On Python 3.3 and newer, it's :func:`time.perf_counter`. On older versions,
   it's :func:`time.clock` on Windows and :func:`time.time` on other
   platforms. See the PEP 418 for more information on Python clocks.

.. function:: monotonic_clock()

   Return the value (in fractional seconds) of a monotonic clock, i.e. a clock
   that cannot go backwards.  The clock is not affected by system clock updates.
   The reference point of the returned value is undefined, so that only the
   difference between the results of consecutive calls is valid.

   On Python 3.3 and newer, it's :func:`time.monotonic`. On older versions,
   it's :func:`time.time` and so is not monotonic. See the PEP 418 for more
   information on Python clocks.

.. seealso::
   `PEP 418 -- Add monotonic time, performance counter, and process time
   functions <https://www.python.org/dev/peps/pep-0418/>`_.


Run
---

.. class:: Run(samples: Sequence[float], warmups: Sequence[float]=None, metadata: dict=None, collect_metadata=True)

   A benchmark run result is made of multiple samples.

   *samples* must be a sequence of numbers (integer or float) greater
   than zero. Usually, *samples* is a list of number of seconds. Samples must
   be normalized per loop iteration (total of outer and inner loops).

   *warmups* is an optional sequence of ``(loops: int, sample: float)`` tuples
   where *sample* must be greater than or equal to zero. Warmup samples are
   "raw samples", they must not be normalized per loop iteration.

   *samples* and/or *warmups* must be a non-empty sequence. If *samples* is
   empty, the run is a calibration run.

   Samples must not be equal to zero. If a sample is zero, use more
   loop iterations: see :ref:`Runs, samples, warmups, outer and inner loops
   <loops>`.

   Set *collect_metadata* to false to not collect system metadata.

   Methods:

   .. method:: get_metadata() -> dict

      Get run metadata.

      The :func:`format_metadata` function can be used to format values.

      See :ref:`Metadata <metadata>`.

   .. method:: get_total_loops() -> int

      Get the total number of loops of the benchmark run:
      outer-loops x inner-loops.

   Attributes:

   .. attribute:: samples

      Benchmark run samples (``tuple`` of numbers).

   .. attribute:: warmups

      Benchmark warmup samples (``tuple`` of numbers).



Benchmark
---------

.. class:: Benchmark(runs)

   A benchmark is made of multiple :class:`Run` objects.

   *runs* must be non-empty sequence of :class:`Run` objects. Runs must
   have a ``name`` metadata (all runs must have the same name).

   Methods:

   .. method:: add_run(run: Run)

      Add a benchmark run: *run* must a :class:`Run` object.

      The new run must be compatible with existing runs: metadata are compared.

   .. method:: add_runs(bench: Benchmark)

      Add runs of the benchmark *bench*.

      See :meth:`BenchmarkSuite.add_runs` method and :func:`add_runs`
      function.

   .. method:: dump(file, compact=True, replace=False)

      Dump the benchmark as JSON into *file*.

      *file* can be a filename, or a file object open for write.

      If *file* is a filename ending with ``.gz``, the file is compressed by
      gzip.

      If *file* is a filename and *replace* is false, the function fails if the
      file already exists.

      If *compact* is true, generate compact file. Otherwise, indent JSON.

      See :ref:`perf JSON <json>`.

   .. method:: format() -> str

      Format the result as ``... +- ...`` (median +- standard deviation) string
      (``str``).

   .. method:: format_sample(sample) -> str

      Format a sample including the unit.

      .. versionadded:: 0.7.8

   .. method:: format_samples(samples) -> str

      Format samples including the unit.

      .. versionadded:: 0.7.8

   .. method:: get_dates() -> (datetime.datetime, datetime.datetime) or None

      Get the start date of the first run and the end date of the last run.

      Return a ``(start, end)`` tuple where start and end are
      ``datetime.datetime`` objects if a least one run has a date metadata.

      Return ``None`` if no run has the ``date`` metadata.

   .. method:: get_metadata() -> dict

      Get metadata common to all runs.

      The :func:`format_metadata` function can be used to format values.

      See :ref:`Metadata <metadata>`.

   .. method:: get_name() -> str

      Get the benchmark name (``str``).

   .. method:: get_nrun() -> int

      Get the number of runs.

   .. method:: get_nsample() -> int

      Get the total number of samples.

   .. method:: get_nwarmup() -> int or float

      Get the number of warmup samples per run.

      Return an ``int`` if all runs use the same number of warmups, or return
      the average as a ``float``.

   .. method:: get_runs() -> List[Run]

      Get the list of :class:`Run` objects.

   .. method:: get_samples()

      Get samples of all runs (values are average per loop iteration).

   .. method:: get_total_duration() -> float

      Get the total duration of the benchmark in seconds.

      Use the ``duration`` metadata of runs, or compute the sum of their
      raw samples including warmup samples.

   .. method:: get_total_loops() -> int or float

      Get the total number of loops per sample (loops x inner-loops).

      Return an ``int`` if all runs have the same number of
      loops, return the average as a ``float`` otherwise.

   .. method:: get_unit() -> str

      Get the unit of samples:

      * ``'byte'``: File size in bytes
      * ``'integer'``: Integer number
      * ``'second'``: Duration in seconds

      .. versionadded:: 0.7.9

   .. classmethod:: load(file) -> Benchmark

      Load a benchmark from a JSON file which was created by :meth:`dump`.

      *file* can be: a filename, ``'-'`` string to load from :data:`sys.stdin`,
      or a file object open to read.

      See :ref:`perf JSON <json>`.

   .. classmethod:: loads(string) -> Benchmark

      Load a benchmark from a JSON string.

      See :ref:`perf JSON <json>`.

   .. method:: median()

      Get the `median <https://en.wikipedia.org/wiki/Median>`_ of
      :meth:`get_samples`.

      The median cannot be equal to zero: :meth:`add_run` raises an error
      if a sample is equal to zero.

   .. method:: __str__() -> str

      Format the result as ``Median +- std dev: ... +- ...`` (median +-
      standard deviation) string (``str``).

   .. method:: update_metadata(metadata: dict)

      Update metadata of all runs of the benchmark.

      If the ``inner_loops`` metadata is already set and its value is modified,
      an exception is raised.

      See :ref:`Metadata <metadata>`.

      .. versionadded:: 0.7.5


BenchmarkSuite
--------------

.. class:: BenchmarkSuite(benchmarks, filename=None)

   A benchmark suite is made of :class:`Benchmark` objects.

   *benchmarks* must be a non-empty sequence of :class:`Benchmark` objects.
   *filename* is the name of the file from which the suite was loaded.

   Methods:

   .. method:: add_benchmark(benchmark: Benchmark)

      Add a :class:`Benchmark` object.

      A suite cannot contain two benchmarks with the same name, because the
      name is used as an unique key: see the :meth:`get_benchmark` method.

   .. method:: add_runs(bench: Benchmark or BenchmarkSuite)

      Add runs of benchmarks.

      *bench* can be a :class:`Benchmark` or a :class:`BenchmarkSuite`.

      See :meth:`Benchmark.add_runs` method and :func:`add_runs` function.

   .. function:: dump(file, compact=True, replace=False)

      Dump the benchmark suite as JSON into *file*.

      *file* can be: a filename, or a file object open for write.

      If *file* is a filename ending with ``.gz``, the file is compressed by
      gzip.

      If *file* is a filename and *replace* is false, the function fails if the
      file already exists.

      If *compact* is true, generate compact file. Otherwise, indent JSON.

      See :ref:`perf JSON <json>`.

   .. method:: get_benchmark(name: str) -> Benchmark

      Get the benchmark called *name*.

      *name* must be non-empty.

      Raise :exc:`KeyError` if there is no benchmark called *name*.

   .. method:: get_benchmark_names() -> List[str]

      Get the list of benchmark names.

   .. method:: get_benchmarks() -> List[Benchmark]

      Get the list of benchmarks sorted by their name.

   .. method:: get_dates() -> (datetime.datetime, datetime.datetime) or None

      Get the start date of the first benchmark and end date of the last
      benchmark.

      Return a ``(start, end)`` tuple where start and end are
      ``datetime.datetime`` objects if a least one benchmark has dates.

      Return ``None`` if no benchmark has dates.

   .. method:: get_metadata() -> dict

      Get metadata common to all benchmarks (common to all runs of all
      benchmarks).

      The :func:`format_metadata` function can be used to format values.

      See the :meth:`Benchmark.get_metadata` method
      and :ref:`Metadata <metadata>`.

      .. versionadded:: 0.7.9

   .. method:: get_total_duration() -> float

      Get the total duration of all benchmarks in seconds.

      See the :meth:`Benchmark.get_total_duration` method.

   .. method:: __iter__()

      Iterate on benchmarks.

   .. method:: __len__() -> int

      Get the number of benchmarks.

   .. classmethod:: load(file)

      Load a benchmark suite from a JSON file which was created by
      :meth:`dump`.

      *file* can be: a filename, ``'-'`` string to load from :data:`sys.stdin`,
      or a file object open to read.

      See :ref:`perf JSON <json>`.

   .. classmethod:: loads(string) -> Benchmark

      Load a benchmark suite from a JSON string.

      See :ref:`perf JSON <json>`.

   Attributes:

   .. attribute:: filename

      Name of the file from which the benchmark suite was loaded.
      It can be ``None``.


Runner
------

.. class:: Runner(samples=3, warmups=1, processes=20, loops=0, min_time=0.1, max_time=1.0, metadata=None, show_name=True, program_args=None, add_cmdline_args=None)

   Tool to run a benchmark in text mode.

   Spawn *processes* worker processes to run the benchmark.

   *metadata* is passed to the :class:`~Run` constructor.

   *samples*, *warmups* and *processes* are the default number of samples,
   warmup samples and processes. These values can be changed with command line
   options. See :ref:`Runner CLI <runner_cli>` for command line
   options.

   *program_args* is a list of strings passed to Python on the command line to
   run the program. By default, ``(sys.argv[0],)`` is used. For example,
   ``python3 -m perf timeit`` sets *program_args* to
   ``('-m', 'perf', 'timeit')``.

   *add_cmdline_args* is an optional callback used to add command line
   arguments to the command line of worker processes. The callback is called
   with ``add_cmdline_args(cmd, args)`` where *cmd* is the command line
   (``list``) which must be modified in place and *args* is the :attr:`args`
   attribute of the runner.

   If *show_name* is true, displays the benchmark name.

   If isolated CPUs are detected, the CPU affinity is automatically
   set to these isolated CPUs. See :ref:`CPU pinning and CPU isolation
   <pin-cpu>`.

   Methods:

   .. method:: bench_func(name, func, \*args, inner_loops=None)

      Benchmark the function ``func(*args)``.

      *name* is the name of the benchmark.

      The *inner_loops* parameter is used to normalize timing per loop
      iteration.

      The design of :meth:`bench_func` has a non negligible overhead on
      microbenchmarks: each loop iteration calls ``func(*args)`` but Python
      function calls are expensive. The :meth:`bench_sample_func` method is
      recommended if ``func(*args)`` takes less than ``1`` millisecond
      (``0.001`` second).

      To call ``func()`` with keyword arguments, use ``functools.partial``.

      Return a :class:`Benchmark` instance.

   .. method:: bench_sample_func(name, sample_func, \*args, inner_loops=None)

      Benchmark ``sample_func(loops, *args)``.

      *name* is the name of the benchmark.

      The function must return raw samples: the total elapsed time of all
      loops. Runner will divide raw samples by ``loops x inner_loops``
      (*loops* and *inner_loops* parameters).

      :func:`perf_counter` should be used to measure the elapsed time.

      To call ``sample_func()`` with keyword arguments, use
      ``functools.partial``.

      Return a :class:`Benchmark` instance.

   .. method:: parse_args(args=None)

      Parse command line arguments using :attr:`argparser` and put the result
      into the :attr:`args` attribute.

      Return the :attr:`args` attribute.

   Attributes:

   .. attribute:: args

      Namespace of arguments: result of the :meth:`parse_args` method, ``None``
      before :meth:`parse_args` is called.

   .. attribute:: argparser

      An :class:`argparse.ArgumentParser` object used to parse command line
      options.

   .. attribute:: metadata

      Benchmark metadata (``dict``).


Functions
---------

.. function:: add_runs(filename: str, result)

   Append a :class:`Benchmark` or :class:`BenchmarkSuite` to an existing
   benchmark suite file, or create a new file.

   If the file already exists, adds runs to existing benchmarks.

   See :meth:`BenchmarkSuite.add_runs` method.


.. function:: format_metadata(name: str, value)

   Format a metadata value. The formatter depends on *name*.

   See :ref:`Metadata <metadata>`.


.. function:: python_implementation()

   Name of the Python implementation in lower case.

   Examples:

   * ``cpython``
   * ``ironpython``
   * ``jython``
   * ``pypy``

   Use ``sys.implementation.name`` and ``platform.python_implementation()``.

   See also the `PEP 421 <https://www.python.org/dev/peps/pep-0421/>`_.

   .. versionadded:: 0.7.4

.. function:: python_has_jit()

   Return ``True`` if Python has a Just In Time compiler (JIT).

   For example, return ``True`` for PyPy but ``False`` for CPython.

   .. versionadded:: 0.7.4
