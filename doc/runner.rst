.. _runner_cli:

Runner CLI
==========

Command line options of the :class:`Runner` class.

Loop iterations
---------------

Options::

    --rigorous
    --fast
    -p PROCESSES/--processes=PROCESSES
    -n VALUES/--values=VALUES
    -l LOOPS/--loops=LOOPS
    -w WARMUPS/--warmups=WARMUPS
    --min-time=MIN_TIME

Default without JIT (ex: CPython): 20 processes, 3 values per process (total: 60
values), and 1 warmup.

Default with a JIT (ex: PyPy): 6 processes, 10 values per process (total: 60
values), and 10 warmups.

* ``--rigorous``: Spend longer running tests to get more accurate results.
  Multiply the number of ``PROCESSES`` by 2. Default: 40 processes and 3
  values per process (120 values).
* ``--fast``: Get rough answers quickly. Divide the number of ``PROCESSES`` by
  2 and multiply the number of ``VALUES`` by 2/3 (0.6). Default: 10 processes
  and 2 values per process (total: 20 values).
* ``PROCESSES``: number of processes used to run the benchmark
  (default: ``20``, or ``6`` with a JIT)
* ``VALUES``: number of values per process
  (default: ``3``, or ``10`` with a JIT)
* ``WARMUPS``: the number of ignored values used to warmup to benchmark
  (default: ``1``, or ``10`` with a JIT)
* ``LOOPS``: number of loops per value. ``x^y`` syntax is accepted, example:
  ``--loops=2^8`` uses ``256`` iterations. By default, the timer is calibrated
  to get raw values taking at least ``MIN_TIME`` seconds.
* ``MIN_TIME``: Minimum duration of a single raw value in seconds
  (default: ``100 ms``)

The :ref:`Runs, values, warmups, outer and inner loops <loops>` section
explains the purpose of these parameters and how to configure them.


Output options
--------------

Options::

    -d/--dump
    -m/--metadata
    -g/--hist
    -t/--stats
    -v/--verbose
    -q/--quiet

* ``--dump`` displays the benchmark run results,
  see :ref:`perf dump <dump_cmd>` command
* ``--metadata`` displays metadata: see :ref:`perf show metadata
  <show_cmd_metadata>` command
* ``--hist`` renders an histogram of values, see :ref:`perf hist <hist_cmd>`
  command
* ``--stats`` displays statistics (min, max, ...), see :ref:`perf stats
  <stats_cmd>` command
* ``--verbose`` enables the verbose mode
* ``--quiet`` enables the quiet mode


JSON output
-----------

Options::

    -o FILENAME/--output=FILENAME
    --append=FILENAME
    --pipe=FD

* ``--output=FILENAME`` writes the benchmark result as JSON into *FILENAME*
* ``--append=FILENAME`` appends the benchmark runs to benchmarks of the JSON
  file *FILENAME*. The file is created if it doesn't exist.
* ``--pipe=FD`` writes benchmarks encoded as JSON into the pipe FD.


Misc
----

Option::

    -h/--help
    --python=PYTHON
    --compare-to REF_PYTHON
    --python-names REF_NAME:CHANGED_NAME
    --affinity=CPU_LIST
    --inherit-environ=VARS
    --track-memory
    --tracemalloc

* ``--python=PYTHON``: Python executable. By default, use the running Python
  (``sys.executable``). The Python executable must have the ``perf`` module
  installed.
* ``--compare-to=REF_PYTHON``: Run benchmark on the Python executable ``REF_PYTHON``,
  run benchmark on Python executable ``PYTHON``, and then compare
  ``REF_PYTHON`` result to ``PYTHON`` result.
* ``--python-names=REF_NAME:CHANGED_NAME``: Option used with ``--compare-to``
  to name ``PYTHON`` as ``CHANGED_NAME`` and name ``REF_PYTHON`` as
  ``REF_NAME`` in results. For example, ``./python ...
  --compare-to=../ref/python --python-names=ref:patch`` uses "ref" name for
  ``../ref/python`` and use "patch" name for ``./python``.
* ``--affinity=CPU_LIST``: Specify CPU affinity for worker processes. This way,
  benchmarks can be forced to run on a given set of CPUs to minimize run to run
  variation. By default, worker processes are pinned to isolate CPUs if
  isolated CPUs are found. See :ref:`CPU pinning and CPU isolation <pin-cpu>`.
* ``--inherit-environ=VARS``: ``VARS`` is a comma-separated list of environment
  variable names which are inherited by worker child processes. By default,
  only the following variables are inherited: ``PATH``, ``HOME``, ``TEMP``,
  ``COMSPEC``, ``SystemRoot`` and locale environment variables. See the
  ``--no-locale`` below for locale environment variables.
* ``--no-locale``: Don't inherit locale environment variables:

  - ``LANG``
  - ``LC_ADDRESS``
  - ``LC_ALL``
  - ``LC_COLLATE``
  - ``LC_CTYPE``
  - ``LC_IDENTIFICATION``
  - ``LC_MEASUREMENT``
  - ``LC_MESSAGES``
  - ``LC_MONETARY``
  - ``LC_NAME``
  - ``LC_NUMERIC``
  - ``LC_PAPER``
  - ``LC_TELEPHONE``
  - ``LC_TIME``

* ``--tracemalloc``: Use the ``tracemalloc`` module to track Python memory
  allocation and get the peak of memory usage in metadata
  (``tracemalloc_peak``). The module is only available on Python 3.4 and newer.
  See the `tracemalloc module
  <https://docs.python.org/dev/library/tracemalloc.html>`_.
* ``--track-memory``: get the memory peak usage. it is less accurate than
  ``tracemalloc``, but has a lower overhead. On Linux, compute the sum of
  ``Private_Clean`` and ``Private_Dirty`` memory mappings of
  ``/proc/self/smaps``. On Windows, get ``PeakPagefileUsage`` of
  ``GetProcessMemoryInfo()`` (of the current process): the peak value of the
  Commit Charge during the lifetime of this process.


Internal usage only
-------------------

The following options are used internally by perf and should not be used
explicitly::

    --worker
    --worker-task=TASK_ID
    --calibrate-loops
    --recalibrate-loops
    --calibrate-warmups
    --recalibrate-warmups
    --debug-single-value

* ``--worker``: a worker process, run the benchmark in the running processs
* ``--worker-task``: Identifier of the worker task, only execute the benchmark
  function number ``TASK_ID``.
* ``--calibrate-loops``: calibrate the number of loops
* ``--recalibrate-loops``: recalibrate the number of loops. Option used with
  JIT compilers to validate the number of loops.
* ``--calibrate-warmups``: calibrate the number of warmups
* ``--recalibrate-warmups``: recalibrate the number of warmups
* ``--debug-single-value``: Debug mode, only produce a single value
