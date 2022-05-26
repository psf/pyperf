.. _api:

API
===

The module version can be read from ``pyperf.VERSION`` (tuple of int) or
``pyperf.__version__`` (str).

See :ref:`API examples <examples>`.

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

.. function:: perf_counter()

   Deprecated alias to ``time.perf_counter()``: use ``time.perf_counter()``
   directly.

   .. deprecated:: 2.0

.. function:: python_implementation()

   Name of the Python implementation in lower case.

   Examples:

   * ``cpython``
   * ``ironpython``
   * ``jython``
   * ``pypy``

   Use ``sys.implementation.name`` or ``platform.python_implementation()``.

   See also the `PEP 421 <https://www.python.org/dev/peps/pep-0421/>`_.

.. function:: python_has_jit()

   Return ``True`` if Python has a Just In Time compiler (JIT).

   For example, return ``True`` for PyPy but ``False`` for CPython.


Run class
---------

.. class:: Run(values: Sequence[float], warmups: Sequence[float]=None, metadata: dict=None, collect_metadata=True)

   A benchmark run result is made of multiple values.

   *values* must be a sequence of numbers (integer or float) greater
   than zero. Values must be normalized per loop iteration. Usually, *values*
   is a list of number of seconds.

   *warmups* is an optional sequence of ``(loops: int, value)`` tuples
   where *value* must be a number (integer or float) greater than or equal to
   zero. Warmup values must be normalized per loop iteration.

   *values* and/or *warmups* must be a non-empty sequence. If *values* is
   empty, the run is a calibration run.

   Values must not be equal to zero. If a value is zero, use more
   loop iterations: see :ref:`Runs, values, warmups, outer and inner loops
   <loops>`.

   *metadata* are metadata of the run, see :ref:`Metadata <metadata>`.
   Important metadata:

   * ``name`` (mandatory, non-empty str): benchmark name
   * ``loops`` (``int >= 1``): number of outer-loops
   * ``inner_loops`` (``int >= 1``): number of inner-loops
   * ``unit`` (str): unit of values: ``'second'``, ``'byte'`` or ``'integer'``

   Set *collect_metadata* to false to not collect system metadata.

   Methods:

   .. method:: get_metadata() -> dict

      Get run metadata.

      The :func:`format_metadata` function can be used to format values.

      See :ref:`Metadata <metadata>`.

   .. method:: get_loops() -> int

      Get the number of outer loop iterations from metadata.

      Return 1 if metadata have no ``'loops'`` entry.

      .. versionadded:: 1.3

   .. method:: get_inner_loops() -> int

      Get the number of inner loop iterations from metadata.

      Return 1 if metadata have no ``'inner_loops'`` entry.

      .. versionadded:: 1.3

   .. method:: get_total_loops() -> int

      Get the total number of loops of the benchmark run:
      get_loops() x get_inner_loops().

   Attributes:

   .. attribute:: values

      Benchmark run values (``tuple`` of numbers).

   .. attribute:: warmups

      Benchmark warmup values (``tuple`` of numbers).



Benchmark class
---------------

.. class:: Benchmark(runs)

   A benchmark is made of multiple :class:`Run` objects.

   *runs* must be non-empty sequence of :class:`Run` objects. Runs must
   have a ``name`` metadata (all runs must have the same name).

   Methods:

   .. method:: add_run(run: Run)

      Add a benchmark run: *run* must a :class:`Run` object.

      The new run must be compatible with existing runs, the following metadata
      must be the same (same value or no value for all runs):

      * ``aslr``
      * ``cpu_count``
      * ``cpu_model_name``
      * ``hostname``
      * ``inner_loops``
      * ``name``
      * ``platform``
      * ``python_executable``
      * ``python_implementation``
      * ``python_version``
      * ``unit``

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

      See the :ref:`pyperf JSON format <json>`.

   .. method:: format_value(value) -> str

      Format a value including the unit.

   .. method:: format_values(values) -> str

      Format values including the unit.

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

   .. method:: get_nvalue() -> int

      Get the total number of values.

   .. method:: get_nwarmup() -> int or float

      Get the number of warmup values per run.

      Return an ``int`` if all runs use the same number of warmups, or return
      the average as a ``float``.

   .. method:: get_runs() -> List[Run]

      Get the list of :class:`Run` objects.

   .. method:: get_values()

      Get values of all runs.

   .. method:: get_total_duration() -> float

      Get the total duration of the benchmark in seconds.

      Use the ``duration`` metadata of runs, or compute the sum of their
      raw values including warmup values.

   .. method:: get_loops() -> int or float

      Get the number of outer loop iterations of runs.

      Return an ``int`` if all runs have the same number of
      outer loops, return the average as a ``float`` otherwise.

      .. versionadded:: 1.3

   .. method:: get_inner_loops() -> int or float

      Get the number of inner loop iterations of runs.

      Return an ``int`` if all runs have the same number of
      outer loops, return the average as a ``float`` otherwise.

      .. versionadded:: 1.3

   .. method:: get_total_loops() -> int or float

      Get the total number of loops per value (outer-loops x inner-loops).

      Return an ``int`` if all runs have the same number of
      loops, return the average as a ``float`` otherwise.

   .. method:: get_unit() -> str

      Get the unit of values:

      * ``'byte'``: File size in bytes
      * ``'integer'``: Integer number
      * ``'second'``: Duration in seconds

   .. classmethod:: load(file) -> Benchmark

      Load a benchmark from a JSON file which was created by :meth:`dump`.

      *file* can be a filename, ``'-'`` string to load from :data:`sys.stdin`,
      or a file object open to read.

      Raise an exception if the file contains more than one benchmark.

      See the :ref:`pyperf JSON format <json>`.

   .. classmethod:: loads(string) -> Benchmark

      Load a benchmark from a JSON string.

      Raise an exception if JSON contains more than one benchmark.

      See the :ref:`pyperf JSON format <json>`.

   .. method:: mean()

      Compute the `arithmetic mean
      <https://en.wikipedia.org/wiki/Arithmetic_mean>`_ of :meth:`get_values`.

      The mean is greater than zero: :meth:`add_run` raises an error
      if a value is equal to zero.

      Raise an exception if the benchmark has no values.

   .. method:: median()

      Compute the `median <https://en.wikipedia.org/wiki/Median>`_ of
      :meth:`get_values`.

      The median is greater than zero: :meth:`add_run` raises an error
      if a value is equal to zero.

      Raise an exception if the benchmark has no values.

   .. method:: percentile(p)

      Compute the p-th `percentile <https://en.wikipedia.org/wiki/Percentile>`_
      of :meth:`get_values`.

      p must be in the range [0; 100]:

      * p=0 computes the minimum
      * p=25 computes Q1
      * p=50 computes the median (see also the :meth:`median` method)
      * p=75 computes Q3
      * p=100 computes the maximum

   .. method:: stdev()

      Compute the `standard deviation
      <https://en.wikipedia.org/wiki/Standard_deviation>`_ of
      :meth:`get_values`.

      Raise an exception if the benchmark has less than 2 values.

   .. method:: median_abs_dev()

      Compute the `median absolute deviation (MAD)
      <https://en.wikipedia.org/wiki/Median_absolute_deviation>`_ of
      :meth:`get_values`.

      Raise an exception if the benchmark has no values.

   .. method:: update_metadata(metadata: dict)

      Update metadata of all runs of the benchmark.

      If the ``inner_loops`` metadata is already set and its value is modified,
      an exception is raised.

      See :ref:`Metadata <metadata>`.


BenchmarkSuite class
--------------------

.. class:: BenchmarkSuite(benchmarks, filename=None)

   A benchmark suite is made of :class:`Benchmark` objects.

   *benchmarks* must be a non-empty sequence of :class:`Benchmark` objects.
   *filename* is the name of the file from which the suite was loaded.

   Methods:

   .. method:: add_benchmark(benchmark: Benchmark)

      Add a :class:`Benchmark` object.

      A suite cannot contain two benchmarks with the same name, because the
      name is used as a unique key: see the :meth:`get_benchmark` method.

   .. method:: add_runs(bench: Benchmark or BenchmarkSuite)

      Add runs of benchmarks.

      *bench* can be a :class:`Benchmark` or a :class:`BenchmarkSuite`.

      See :meth:`Benchmark.add_runs` method and :func:`add_runs` function.

   .. function:: dump(file, compact=True, replace=False)

      Dump the benchmark suite as JSON into *file*.

      *file* can be a filename, or a file object open for write.

      If *file* is a filename ending with ``.gz``, the file is compressed by
      gzip.

      If *file* is a filename and *replace* is false, the function fails if the
      file already exists.

      If *compact* is true, generate compact file. Otherwise, indent JSON.

      See the :ref:`pyperf JSON format <json>`.

   .. method:: get_benchmark(name: str) -> Benchmark

      Get the benchmark called *name*.

      *name* must be non-empty.

      Raise :exc:`KeyError` if there is no benchmark called *name*.

   .. method:: get_benchmark_names() -> List[str]

      Get the list of benchmark names.

   .. method:: get_benchmarks() -> List[Benchmark]

      Get the list of benchmarks.

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

      *file* can be a filename, ``'-'`` string to load from :data:`sys.stdin`,
      or a file object open to read.

      See the :ref:`pyperf JSON format <json>`.

   .. classmethod:: loads(string) -> Benchmark

      Load a benchmark suite from a JSON string.

      See the :ref:`pyperf JSON format <json>`.

   Attributes:

   .. attribute:: filename

      Name of the file from which the benchmark suite was loaded.
      It can be ``None``.


Runner class
------------

.. class:: Runner(values=3, warmups=1, processes=20, loops=0, min_time=0.1, metadata=None, show_name=True, program_args=None, add_cmdline_args=None)

   Tool to run a benchmark in text mode.

   Spawn *processes* worker processes to run the benchmark.

   *metadata* is passed to the :class:`~Run` constructor.

   *values*, *warmups* and *processes* are the default number of values,
   warmup values and processes. These values can be changed with command line
   options. See :ref:`Runner CLI <runner_cli>` for command line
   options.

   *program_args* is a list of strings passed to Python on the command line to
   run the program. By default, ``(sys.argv[0],)`` is used. For example,
   ``python3 -m pyperf timeit`` sets *program_args* to
   ``('-m', 'pyperf', 'timeit')``.

   *add_cmdline_args* is an optional callback used to add command line
   arguments to the command line of worker processes. The callback is called
   with ``add_cmdline_args(cmd, args)`` where *cmd* is the command line
   (``list``) which must be modified in place and *args* is the :attr:`args`
   attribute of the runner.

   If *show_name* is true, displays the benchmark name.

   If isolated CPUs are detected, the CPU affinity is automatically
   set to these isolated CPUs. See :ref:`CPU pinning and CPU isolation
   <pin-cpu>`.

   Methods to run benchmarks:

   * :meth:`bench_func`
   * :meth:`bench_async_func`
   * :meth:`timeit`
   * :meth:`bench_command`
   * :meth:`bench_time_func`

   Only once instance of Runner must be created. Use the same instance to run
   all benchmarks.

   Methods:

   .. method:: bench_func(name, func, \*args, inner_loops=None, metadata=None)

      Benchmark the function ``func(*args)``.

      *name* is the benchmark name, it must be unique in the same script.

      The *inner_loops* parameter is used to normalize timing per loop
      iteration.

      The design of :meth:`bench_func` has a non negligible overhead on
      microbenchmarks: each loop iteration calls ``func(*args)`` but Python
      function calls are expensive. The :meth:`timeit` and
      :meth:`bench_time_func` methods are recommended if ``func(*args)`` takes
      less than ``1`` millisecond (``0.001`` second).

      To call ``func()`` with keyword arguments, use ``functools.partial``.

      Return a :class:`Benchmark` instance.

      See the :ref:`bench_func() example <bench_func_example>`.

   .. method:: bench_async_func(name, func, \*args, inner_loops=None, metadata=None)

      Benchmark the function ``await func(*args)`` in asyncio event loop.

      *name* is the benchmark name, it must be unique in the same script.

      The *inner_loops* parameter is used to normalize timing per loop
      iteration.

      To call ``func()`` with keyword arguments, use ``functools.partial``.

      Return a :class:`Benchmark` instance.

      See the :ref:`bench_async_func() example <bench_async_func_example>`.

   .. method:: timeit(name, stmt=None, setup="pass", teardown="pass", inner_loops=None, duplicate=None, metadata=None, globals=None)

      Run a benchmark on ``timeit.Timer(stmt, setup, globals=globals)``.

      *name* is the benchmark name, it must be unique in the same script.

      *stmt* is a Python statement. It can be a non-empty string or a non-empty
      sequence of strings.

      *setup* is a Python statement used to setup the benchmark: it is executed
      before computing each benchmark value. It can be a string or a sequence
      of strings.

      *teardown* is a Python statement used to teardown the benchmark: it is
      executed after computing each benchmark value. It can be a string or a
      sequence of strings.

      Parameters:

      * *inner_loops*: Number of inner-loops. Can be used when *stmt* manually
        duplicates the same expression *inner_loops* times.
      * *duplicate*: Duplicate the *stmt* statement *duplicate* times to reduce
        the cost of the outer loop.
      * *metadata*: Metadata of this benchmark, added to the runner
        :attr:`metadata`.
      * *globals*: Namespace used to run *setup*, *teardown* and *stmt*. By
        default, an empty namespace is created. It can be used to pass variables.

      ``Runner.timeit(stmt)`` can be used to use the statement as the benchmark
      name.

      See the :ref:`timeit() example <timeit_example>`.

      .. versionchanged:: 1.6.0
         Add optional *teardown* parameter. The *stmt* parameter is now
         optional.

   .. method:: bench_command(name, command)

      Benchmark the execution time of a command using :func:`time.perf_counter`
      timer. Measure the wall-time, not CPU time.

      *command* must be a sequence of arguments, the first argument must be the
      program.

      Basically, the function measures the timing of ``Popen(command).wait()``,
      but tries to reduce the benchmark overhead.

      Standard streams (stdin, stdout and stderr) are redirected to
      ``/dev/null`` (or ``NUL`` on Windows).

      Use ``--inherit-environ`` and ``--no-locale`` :ref:`command line options
      <runner_cli>` to control environment variables.

      If the ``resource.getrusage()`` function is available, measure also the
      maximum RSS memory and stores it in ``command_max_rss`` metadata.

      See the :ref:`bench_command() example <bench_command_example>`.

      .. versionchanged:: 1.1
         Measure the maximum RSS memory (if available).

   .. method:: bench_time_func(name, time_func, \*args, inner_loops=None, metadata=None)

      Benchmark ``time_func(loops, *args)``. The *time_func* function must
      return raw timings: the total elapsed time of all loops. Runner will
      divide raw timings by ``loops x inner_loops`` (*loops* and *inner_loops*
      parameters).

      :func:`time.perf_counter` should be used to measure the elapsed time.

      *name* is the benchmark name, it must be unique in the same script.

      To call ``time_func()`` with keyword arguments, use
      ``functools.partial``.

      Return a :class:`Benchmark` instance.

      See the :ref:`bench_time_func() example <bench_time_func_example>`.

   .. method:: parse_args(args=None)

      Parse command line arguments using :attr:`argparser` and put the result
      into the :attr:`args` attribute.

      If *args* is set, the method must only be called once.

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


.. _metadata:

Metadata
========

The :class:`Run` class collects metadata by default.

Benchmark:

* ``date`` (str): date when the benchmark run started, formatted as ISO 8601
* ``duration`` (int or float >= 0): total duration of the benchmark run in seconds (``float``)
* ``name`` (non-empty str): benchmark name
* ``loops`` (``int >= 1``): number of outer-loops per value (``int``)
* ``inner_loops`` (``int >= 1``): number of inner-loops of the benchmark (``int``)
* ``timer``: Implementation of ``time.perf_counter()``, and also resolution if
  available
* ``tags``: (list of str, optional): A list of tags associated with the benchmark. If provided, the results output will be aggreggated by each tag.

Python metadata:

* ``python_compiler``: Compiler name and version.
* ``python_cflags``: Compiler flags used to compile Python.
* ``python_executable``: path to the Python executable
* ``python_hash_seed``: value of the ``PYTHONHASHSEED`` environment variable
  (``random`` string or an ``int``)
* ``python_implementation``: Python implementation. Examples: ``cpython``,
  ``pypy``, etc.
* ``python_version``: Python version, with the architecture (32 or 64 bits) if
  available, ex: ``2.7.11 (64bit)``

Memory metadata:

* ``command_max_rss`` (int): Maximum resident set size in bytes (``int``)
  measured by :meth:`Runner.bench_command`.
* ``mem_max_rss`` (int): Maximum resident set size in bytes (``int``). On Linux,
  kernel 2.6.32 or newer is required.
* ``mem_peak_pagefile_usage`` (int): Get ``PeakPagefileUsage`` of
  ``GetProcessMemoryInfo()`` (of the current process): the peak value of the
  Commit Charge during the lifetime of this process. Only available on Windows.

CPU metadata:

* ``cpu_affinity``: if set, the process is pinned to the specified list of
  CPUs
* ``cpu_config``: Configuration of CPUs (ex: scaling governor)
* ``cpu_count``: number of logical CPUs (``int``)
* ``cpu_freq``: Frequency of CPUs
* ``cpu_machine``: CPU machine
* ``cpu_model_name``: CPU model name
* ``cpu_temp``: Temperature of CPUs

System metadata:

* ``aslr``: Address Space Layout Randomization (ASLR)
* ``boot_time`` (str): Date and time of the system boot
* ``hostname``: Host name
* ``platform``: short string describing the platform
* ``load_avg_1min`` (int or float >= 0): Load average figures giving the number of jobs in the run
  queue (state ``R``) or waiting for disk I/O (state ``D``) averaged over 1
  minute
* ``runnable_threads``: number of currently runnable kernel scheduling entities
  (processes, threads). The value comes from the 4th field of
  ``/proc/loadavg``: ``1`` in ``0.20 0.22 0.24 1/596 10123`` for example
  (``596`` is the total number of threads).
* ``uptime`` (int or float >= 0): Duration since the system boot (``float``, number of seconds
  since ``boot_time``)

Other:

* ``perf_version``: Version of the ``pyperf`` module
* ``unit``: Unit of values: ``byte``, ``integer`` or ``second``
* ``calibrate_loops`` (``int >= 1``): number of loops computed in a loops
  calibration run
* ``recalibrate_loops`` (``int >= 1``): number of loops computed in a loops
  recalibration run
* ``calibrate_warmups`` (bool): True for runs used to calibrate the number of
  warmups
* ``recalibrate_warmups`` (bool): True for runs used to recalibrate the number
  of warmups



.. _json:

pyperf JSON format
==================

pyperf stores benchmark results as JSON in files. By default, the JSON is
formatted to produce small files. Use the ``python3 -m pyperf convert --indent
(...)`` command (see :ref:`pyperf convert <convert_cmd>`) to get readable
(indented) JSON.

pyperf supports JSON files compressed by gzip: use gzip if filename ends with
``.gz``.

Example of JSON, ``...`` is used in the example for readability::

    {
        "benchmarks": [
            {
                "runs": [
                    {
                        "metadata": {
                            "date": "2016-10-21 03:14:19.670631",
                            "duration": 0.33765527700597886,
                        },
                        "warmups": [
                            [
                                1,
                                0.023075559991411865
                            ],
                            [
                                2,
                                0.022522017497976776
                            ],
                            [
                                4,
                                0.02247579424874857
                            ],
                            [
                                8,
                                0.02237467262420978
                            ]
                        ]
                    },
                    {
                        "metadata": {
                            "date": "2016-10-21 03:14:20.496710",
                            "duration": 0.7234010050015058,
                        },
                        "values": [
                            0.022752201875846367,
                            0.022529058374857414,
                            0.022569017250134493
                        ],
                        "warmups": [
                            [
                                8,
                                0.02249833550013136
                            ]
                        ]
                    },
                    ...
                    {
                        "metadata": {
                            "date": "2016-10-21 03:14:52.549713",
                            "duration": 0.719920061994344,
                            ...
                        },
                        "values": [
                            0.022562820375242154,
                            0.022442164625317673,
                            0.02241712374961935
                        ],
                        "warmups": [
                            [
                                8,
                                0.02249412499986647
                            ]
                        ]
                    }
                ]
            }
        ],
        "metadata": {
            "cpu_count": 4,
            "cpu_model_name": "Intel(R) Core(TM) i7-3520M CPU @ 2.90GHz",
            "description": "Telco decimal benchmark",
            "hostname": "selma",
            "loops": 8,
            "name": "telco",
            "perf_version": "0.8.2",
            "tags": ["numeric"],
            ...
        },
        "version": "1.0"
    }

See also the `jq tool <https://stedolan.github.io/jq/>`_: "lightweight and
flexible command-line JSON processor".
