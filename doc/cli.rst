pyperf commands
===============

Commands:

* :ref:`pyperf show <show_cmd>`
* :ref:`pyperf compare_to <compare_to_cmd>`
* :ref:`pyperf stats <stats_cmd>`
* :ref:`pyperf check <check_cmd>`
* :ref:`pyperf dump <dump_cmd>`
* :ref:`pyperf hist <hist_cmd>`
* :ref:`pyperf metadata <metadata_cmd>`
* :ref:`pyperf timeit <timeit_cmd>`
* :ref:`pyperf command <command_cmd>`
* :ref:`pyperf system <system_cmd>`
* :ref:`pyperf collect_metadata <collect_metadata_cmd>`
* :ref:`pyperf slowest <slowest_cmd>`
* :ref:`pyperf convert <convert_cmd>`


The Python pyperf module comes with a ``pyperf`` program which includes different
commands. If for some reasons, ``pyperf`` program cannot be used, ``python3 -m
pyperf ...`` can be used: it is the same, it's just longer to type :-) For
example, the ``-m pyperf ...`` syntax is preferred for ``timeit`` because this
command uses the running Python program.

General note: if a filename is ``-``, read the JSON content from stdin.

.. _show_cmd:

pyperf show
-----------

Show benchmarks of one or multiple benchmark suites::

    python3 -m pyperf show
        [-q/--quiet]
        [-d/--dump]
        [-m/--metadata]
        |-g/--hist] [-t/--stats]
        [-b NAME/--benchmark NAME]
        filename.json [filename2.json ...]

* ``--quiet`` enables the quiet mode
* ``--dump`` displays the benchmark run results,
  see :ref:`pyperf dump <dump_cmd>` command
* ``--metadata`` displays benchmark metadata: see :ref:`pyperf metadata
  <metadata_cmd>` command
* ``--hist`` renders an histogram of values, see :ref:`pyperf hist <hist_cmd>`
  command
* ``--stats`` displays statistics (min, max, ...), see :ref:`pyperf stats
  <stats_cmd>` command
* ``--benchmark NAME`` only displays the benchmark called ``NAME``. The option
  can be specified multiple times.

.. versionchanged:: 1.2
   The ``--benchmark`` option can now be specified multiple times.

.. _show_cmd_metadata:

Example::

    $ python3 -m pyperf show telco.json
    Mean +- std dev: 22.5 ms +- 0.2 ms

Example with metadata::

    $ python3 -m pyperf show telco.json --metadata
    Metadata:
    - boot_time: 2016-10-19 01:10:08
    - cpu_count: 4
    - cpu_model_name: Intel(R) Core(TM) i7-3520M CPU @ 2.90GHz
    - description: Telco decimal benchmark
    - hostname: selma
    - loops: 8
    - name: telco
    - perf_version: 0.8.2
    ...

    Mean +- std dev: 22.5 ms +- 0.2 ms


.. _compare_to_cmd:

pyperf compare_to
-----------------

Compare benchmark suites, use the first file as the reference::

    python3 -m pyperf compare_to
        [-v/--verbose] [-q/--quiet]
        [-G/--group-by-speed]
        [--min-speed=MIN_SPEED]
        [--table]
        [--table-format=rest|md]
        [-b NAME/--benchmark NAME]
        reference.json changed.json [changed2.json ...]

Options:

* ``--group-by-speed``: group results by "Slower", "Faster" and "Same speed"
* ``--min-speed``: Absolute minimum of speed in percent to consider that a
  benchmark is significant (default: 0%)
* ``--table``: Render a table.
* ``--table-format``: Table rendering format.
* ``--benchmark NAME`` only displays the benchmark called ``NAME``. The option
  can be specified multiple times.

.. versionchanged:: 1.2
   The ``--benchmark`` option can now be specified multiple times.

.. versionchanged:: 2.3
   The ``--table-format`` option now can designate format between reST and markdown.

pyperf determines whether two samples differ significantly using a `Student's
two-sample, two-tailed t-test
<https://en.wikipedia.org/wiki/Student's_t-test>`_ with alpha equals to
``0.95``.

If the benchmark suites contain more than one benchmark, the `geometric mean
<https://en.wikipedia.org/wiki/Geometric_mean>`_ of benchmark results means
normalized to the reference results means is computed. It is a convenient index
to summarize benchmark suite results normalized to the reference suite. See
`How not to lie with statistics: the correct way to summarize benchmark results
<https://www.cse.unsw.edu.au/~cs9242/11/papers/Fleming_Wallace_86.pdf>`_ paper
by Philip J. Fleming and John J. Wallace (ACM, 1986).

Example 1 comparing Python 3.8 to Python 3.6::

    $ python3 -m pyperf compare_to py36.json py38.json
    Mean +- std dev: [py36] 4.70 us +- 0.18 us -> [py38] 4.22 us +- 0.08 us: 1.11x faster

On this example, py36 is the reference: py38 is faster than py36 (4.22 us is
less than 4.70 us).

Example 2 comparing two suites (Python 3.7 and Python 3.8) to a reference suite
(Python 3.6)::

    $ python3 -m pyperf compare_to --table mult_list_py36.json mult_list_py37.json mult_list_py38.json
    +----------------+----------------+-----------------------+-----------------------+
    | Benchmark      | mult_list_py36 | mult_list_py37        | mult_list_py38        |
    +================+================+=======================+=======================+
    | [1]*1000       | 2.13 us        | 2.09 us: 1.02x faster | not significant       |
    +----------------+----------------+-----------------------+-----------------------+
    | [1,2]*1000     | 3.70 us        | 5.28 us: 1.42x slower | 3.18 us: 1.16x faster |
    +----------------+----------------+-----------------------+-----------------------+
    | [1,2,3]*1000   | 4.61 us        | 6.05 us: 1.31x slower | 4.17 us: 1.11x faster |
    +----------------+----------------+-----------------------+-----------------------+
    | Geometric mean | (ref)          | 1.22x slower          | 1.09x faster          |
    +----------------+----------------+-----------------------+-----------------------+

On this example, mult_list_py36 (Python 3.6) is the reference. According to
geometric mean, mult_list_py37 (Python 3.7) is slower than
mult_list_py36, whereas mult_list_py38 (Python 3.8) is faster than
mult_list_py36.

The geometric mean is a convenient index to summarize the 3 benchmark results
of each suite as a single index which is normalized to the reference suite
results. For example, mult_list_py37 is faster on one benchmark and slower on
two others: according to the geometric mean, it is slower than the reference.

See also the ``--compare-to`` :ref:`option of the Runner CLI <runner_cli>`.


.. _stats_cmd:

pyperf stats
------------

Compute statistics on a benchmark result::

    python3 -m pyperf stats
        [-b NAME/--benchmark NAME]
        file.json [file2.json ...]

Options:

* ``--benchmark NAME`` only displays the benchmark called ``NAME``. The option
  can be specified multiple times.

.. versionchanged:: 1.2
   Count the number of outlier values. The ``--benchmark`` option can now be
   specified multiple times.

Computed values:

* Mean and standard deviation: see :meth:`Benchmark.mean`
  and :meth:`Benchmark.stdev`
* Median and median absolute deviation (MAD): see :meth:`Benchmark.median` and
  :meth:`Benchmark.median_abs_dev`
* Percentiles: see :meth:`Benchmark.percentile`
* Outliers: number of values out of the range ``[Q1 - 1.5*IQR; Q3 + 1.5*IQR]``
  where IQR stands for the `interquartile range
  <https://en.wikipedia.org/wiki/Interquartile_range>`_.

Example::

    $ python3 -m pyperf stats telco.json
    Total duration: 29.2 sec
    Start date: 2016-10-21 03:14:19
    End date: 2016-10-21 03:14:53
    Raw value minimum: 177 ms
    Raw value maximum: 183 ms

    Number of calibration run: 1
    Number of run with values: 40
    Total number of run: 41

    Number of warmup per run: 1
    Number of value per run: 3
    Loop iterations per value: 8
    Total number of values: 120

    Minimum:         22.1 ms
    Median +- MAD:   22.5 ms +- 0.1 ms
    Mean +- std dev: 22.5 ms +- 0.2 ms
    Maximum:         22.9 ms

      0th percentile: 22.1 ms (-2% of the mean) -- minimum
      5th percentile: 22.3 ms (-1% of the mean)
     25th percentile: 22.4 ms (-1% of the mean) -- Q1
     50th percentile: 22.5 ms (-0% of the mean) -- median
     75th percentile: 22.7 ms (+1% of the mean) -- Q3
     95th percentile: 22.9 ms (+2% of the mean)
    100th percentile: 22.9 ms (+2% of the mean) -- maximum

    Number of outlier (out of 22.0 ms..23.0 ms): 0

Values:

* `Median <https://en.wikipedia.org/wiki/Median>`_
* "std dev": `Standard deviation
  <https://en.wikipedia.org/wiki/Standard_deviation>`_

See also `Outlier (Wikipedia) <https://en.wikipedia.org/wiki/Outlier>`_.


.. _check_cmd:

pyperf check
------------

Check if benchmarks are stable::

    python3 -m pyperf check
        [-b NAME/--benchmark NAME]
        filename [filename2 ...]

Options:

* ``--benchmark NAME`` only check the benchmark called ``NAME``. The option
  can be specified multiple times.

.. versionchanged:: 1.2
   The ``--benchmark`` option can now be specified multiple times.

Checks:

* Warn if the standard deviation is greater than 10% of the mean
* Warn if the minimum or the maximum is 50% smaller or greater than the mean
* Warn if the shortest raw value took less than 1 millisecond
* Warn if ``nohz_full`` Linux kernel option and the Linux ``intel_pstate`` CPU
  driver if found in the ``cpu_config`` metadata

Example of a stable benchmark::

    $ python3 -m pyperf check telco.json
    The benchmark seem to be stable

Example of an unstable benchmark::

    $ python3 -m pyperf timeit -l1 -p3 '"abc".strip()' -o timeit_strip.json -q
    Mean +- std dev: 750 ns +- 89 ns

    $ python3 -m pyperf check timeit_strip.json
    WARNING: the benchmark result may be unstable
    * the standard deviation (89.4 ns) is 12% of the mean (750 ns)
    * the shortest raw value is only 636 ns

    Try to rerun the benchmark with more runs, values and/or loops.
    Run 'python3 -m pyperf system tune' command to reduce the system jitter.
    Use pyperf stats, pyperf dump and pyperf hist to analyze results.
    Use --quiet option to hide these warnings.


.. _dump_cmd:

pyperf dump
-----------

Display the benchmark run results::

    python3 -m pyperf dump
        [-q/--quiet]
        [-v/--verbose]
        [--raw]
        [-b NAME/--benchmark NAME]
        file.json [file2.json ...]

Options:

* ``--quiet`` enables the quiet mode: hide warmup values
* ``--verbose`` enables the verbose mode: show run metadata
* ``--raw`` displays raw values rather than values
* ``--benchmark NAME`` only displays the benchmark called ``NAME``. The option
  can be specified multiple times.

.. versionchanged:: 1.2
   The ``--benchmark`` option can now be specified multiple times.

Example::

    $ python3 -m pyperf dump telco.json
    Run 1: calibrate the number of loops: 8
    - calibrate 1: 23.1 ms (loops: 1, raw: 23.1 ms)
    - calibrate 2: 22.5 ms (loops: 2, raw: 45.0 ms)
    - calibrate 3: 22.5 ms (loops: 4, raw: 89.9 ms)
    - calibrate 4: 22.4 ms (loops: 8, raw: 179 ms)
    Run 2: 1 warmup, 3 values, 8 loops
    - warmup 1: 22.5 ms
    - value 1: 22.8 ms
    - value 2: 22.5 ms
    - value 3: 22.6 ms
    (...)
    Run 41: 1 warmup, 3 values, 8 loops
    - warmup 1: 22.5 ms
    - value 1: 22.6 ms
    - value 2: 22.4 ms
    - value 3: 22.4 ms

Example in verbose mode::

    $ python3 -m pyperf dump telco.json -v
    Metadata:
      cpu_affinity: 2-3
      cpu_config: 2-3=driver:intel_pstate, intel_pstate:turbo, governor:performance, isolated; idle:intel_idle
      cpu_count: 4
      cpu_model_name: Intel(R) Core(TM) i7-3520M CPU @ 2.90GHz
      hostname: selma
      loops: 8
      name: telco
      perf_version: 0.8.2
      ...

    Run 1: calibrate the number of loops
    - calibrate 1: 23.1 ms (loops: 1, raw: 23.1 ms)
    - calibrate 2: 22.5 ms (loops: 2, raw: 45.0 ms)
    - calibrate 3: 22.5 ms (loops: 4, raw: 89.9 ms)
    - calibrate 4: 22.4 ms (loops: 8, raw: 179 ms)
    - Metadata:
      cpu_freq: 2=3596 MHz, 3=1352 MHz
      cpu_temp: coretemp:Physical id 0=67 C, coretemp:Core 0=51 C, coretemp:Core 1=67 C
      date: 2016-10-21 03:14:19.670631
      duration: 338 ms
      load_avg_1min: 0.29
      ...
    Run 2:
    - warmup 1: 22.5 ms
    - value 1: 22.8 ms
    - value 2: 22.5 ms
    - value 3: 22.6 ms
    - Metadata:
      cpu_freq: 2=3596 MHz, 3=2998 MHz
      cpu_temp: coretemp:Physical id 0=67 C, coretemp:Core 0=51 C, coretemp:Core 1=67 C
      date: 2016-10-21 03:14:20.496710
      duration: 723 ms
      load_avg_1min: 0.29
      ...
    ...


.. _hist_cmd:

pyperf hist
-----------

Render an histogram in text mode::

    python3 -m pyperf hist
        [-n BINS/--bins=BINS] [--extend]
        [-b NAME/--benchmark NAME]
        filename.json [filename2.json ...]

* ``--bins`` is the number of histogram bars. By default, it renders up to 25
  bars, or less depending on the terminal size.
* ``--extend``: don't limit to 80 columns x 25 lines but fill the whole
  terminal if it is wider.
* ``--benchmark NAME`` only displays the benchmark called ``NAME``. The option
  can be specified multiple times.

.. versionchanged:: 1.2
   The ``--benchmark`` option can now be specified multiple times.

If multiple files are used, the histogram is normalized on the minimum and
maximum of all files to be able to easily compare them.

Example::

    $ python3 -m pyperf hist telco.json
    26.4 ms:  1 ##
    26.4 ms:  1 ##
    26.4 ms:  2 #####
    26.5 ms:  1 ##
    26.5 ms:  1 ##
    26.5 ms:  4 #########
    26.6 ms:  8 ###################
    26.6 ms:  6 ##############
    26.7 ms: 11 ##########################
    26.7 ms: 13 ##############################
    26.7 ms: 18 ##########################################
    26.8 ms: 21 #################################################
    26.8 ms: 34 ###############################################################################
    26.8 ms: 26 ############################################################
    26.9 ms: 11 ##########################
    26.9 ms: 14 #################################
    27.0 ms: 17 ########################################
    27.0 ms: 14 #################################
    27.0 ms: 10 #######################
    27.1 ms: 10 #######################
    27.1 ms:  7 ################
    27.1 ms: 12 ############################
    27.2 ms:  5 ############
    27.2 ms:  2 #####
    27.3 ms:  0 |
    27.3 ms:  1 ##

See `Gaussian function <https://en.wikipedia.org/wiki/Gaussian_function>`_ and
`Probability density function (PDF)
<https://en.wikipedia.org/wiki/Probability_density_function>`_.


.. _metadata_cmd:

pyperf metadata
---------------

Display metadata of benchmark files::

    python3 -m pyperf metadata
        [-b NAME/--benchmark NAME]
        filename [filename2 ...]

Options:

* ``--benchmark NAME`` only displays the benchmark called ``NAME``. The option
  can be specified multiple times.

.. versionchanged:: 1.2
   The ``--benchmark`` option can now be specified multiple times.

Example::

    $ python3 -m pyperf metadata telco.json
    Metadata:
    - aslr: Full randomization
    - boot_time: 2016-10-19 01:10:08
    - cpu_affinity: 2-3
    - cpu_config: 2-3=driver:intel_pstate, intel_pstate:turbo, governor:performance, isolated; idle:intel_idle
    - cpu_count: 4
    - cpu_model_name: Intel(R) Core(TM) i7-3520M CPU @ 2.90GHz
    - description: Telco decimal benchmark
    - hostname: selma
    - loops: 8
    - name: telco
    - perf_version: 0.8.2
    - performance_version: 0.3.3
    - platform: Linux-4.7.4-200.fc24.x86_64-x86_64-with-fedora-24-Twenty_Four
    - python_cflags: -Wno-unused-result -Wsign-compare -Wunreachable-code -DDYNAMIC_ANNOTATIONS_ENABLED=1 -DNDEBUG -O2 -g -pipe -Wall -Werror=format-security -Wp,-D_FORTIFY_SOURCE=2 -fexceptions -fstack-protector-strong --param=ssp-buffer-size=4 -grecord-gcc-switches -specs=/usr/lib/rpm/redhat/redhat-hardened-cc1 -m64 -mtune=generic -D_GNU_SOURCE -fPIC -fwrapv
    - python_executable: /home/haypo/prog/python/performance/venv/cpython3.5-68b776ee7e79/bin/python
    - python_implementation: cpython
    - python_version: 3.5.1 (64-bit)
    - timer: clock_gettime(CLOCK_MONOTONIC), resolution: 1.00 ns


.. _timeit_cmd:

pyperf timeit
-------------

Usage
^^^^^

``pyperf timeit`` usage::

    python3 -m pyperf timeit
        [options]
        [--name BENCHMARK_NAME]
        [--python PYTHON]
        [--compare-to REF_PYTHON]
        [--inner-loops INNER_LOOPS]
        [--duplicate DUPLICATE]
        [-s SETUP]
        [--teardown TEARDOWN]
        [--profile PROFILE]
        stmt [stmt ...]

Options:

* ``[options]``: see :ref:`Runner CLI <runner_cli>` for more options.
* ``stmt``: Python code executed in the benchmark.
  Multiple statements can be used.
* ``-s SETUP``, ``--setup SETUP``: statement run before the tested statement.
  The option can be specified multiple times.
* ``--teardown TEARDOWN``: statement run after the tested statement.
  The option can be specified multiple times.
* ``--name=BENCHMARK_NAME``: Benchmark name (default: ``timeit``).
* ``--inner-loops=INNER_LOOPS``: Number of inner loops per value. For example,
  the number of times that the code is copied manually multiple times to reduce
  the overhead of the outer loop.
* ``--compare-to=REF_PYTHON``: Run benchmark on the Python executable ``REF_PYTHON``,
  run benchmark on Python executable ``PYTHON``, and then compare
  ``REF_PYTHON`` result to ``PYTHON`` result.
* ``--duplicate=DUPLICATE``: Duplicate statements (``stmt`` statements, not
  ``SETUP``) to reduce the overhead of the outer loop and multiply
  inner loops by DUPLICATE (see ``--inner-loops`` option).
* ``--profile=PROFILE``: Run the benchmark inside the cProfile profiler and output to the given file. This is a convenient way to profile a specific benchmark, but it will make the actual benchmark timings much less accurate.

.. note::
   timeit ``-n`` (number) and ``-r`` (repeat) options become ``-l`` (loops) and
   ``-n`` (runs) in pyperf timeit.

Example::

    $ python3 -m pyperf timeit '" abc ".strip()' --duplicate=1024
    .........................
    Mean +- std dev: 104 ns +- 1 ns

Compare Python 3.8 to Python 3.6::

    $ python3.8 -m pyperf timeit '" abc ".strip()' --duplicate=1024 --compare-to=python3.6
    python3.6: ..................... 84.6 ns +- 4.4 ns
    python3.8: ..................... 104 ns +- 0 ns

    Mean +- std dev: [python3.6] 84.6 ns +- 4.4 ns -> [python3.8] 104 ns +- 0 ns: 1.23x slower (+23%)

.. versionchanged:: 1.6.0
   Add ``--teardown`` option.


timeit versus pyperf timeit
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The timeit module of the Python standard library has multiple issues:

* It displays the minimum
* It only runs the benchmark 3 times using a single process (1 run, 3 values)
* It disables the garbage collector

pyperf timeit is more reliable and gives a result more representative of a real
use case:

* It displays the average and the standard deviation
* It runs the benchmark in multiple processes
* By default, it skips the first value in each process to warmup the benchmark
* It does not disable the garbage collector

If a benchmark is run using a single process, we get the performance for one
specific case, whereas many parameters are random:

* Since Python 3, the hash function is now randomized and so the number of
  hash collision in dictionaries is different in each process
* Linux uses address space layout randomization (ASLR) by default and so
  the performance of memory accesses is different in each process

See the :ref:`Minimum versus average and standard deviation <min>` section.


.. _command_cmd:

pyperf command
--------------

.. versionadded:: 1.1

Measure the wall clock time to run a command, similar to Unix ``time`` command.

If the ``resource.getrusage()`` function is available, measure also the maximum
RSS memory and stores it in ``command_max_rss`` metadata. In that case,
``--track-memory`` option can be used to use the RSS memory for benchmark
values.

Usage
^^^^^

``pyperf command`` usage::

    python3 -m pyperf command
        [options]
        [--name NAME]
        [--track-memory]
        program [arg1 arg2 ...]

Options:

* ``[options]``: see :ref:`Runner CLI <runner_cli>` for more options.
* ``--track-memory``: use the maximum RSS memory of the command instead of the
  time.
* ``--name=BENCHMARK_NAME``: Benchmark name (default: ``command``).
* ``program [arg1 arg2 ...]``: the tested command.

Example measuring Python 3.6 startup time::

    $ python3 -m pyperf command -- python3.6 -c pass
    .....................
    command: Mean +- std dev: 21.2 ms +- 3.2 ms


.. _system_cmd:

pyperf system
-------------

Get or set the system state for benchmarks::

    python3 -m pyperf system
        [--affinity=CPU_LIST]
        [{show,tune,reset}]

Commands:

* ``pyperf system show`` (or just ``pyperf system``) shows the current state
  of the system
* ``pyperf system tune`` tunes the system to run benchmarks
* ``pyperf system reset`` resets the system to the default state

Options:

* ``--affinity=CPU_LIST``: Specify CPU affinity. By default, use isolate CPUs.
  See :ref:`CPU pinning and CPU isolation <pin-cpu>`.

See :ref:`operations and checks of the pyperf system command <system_cmd_ops>`
and the :ref:`Tune the system for benchmarks <system>` section.


.. _collect_metadata_cmd:

pyperf collect_metadata
-----------------------

Collect metadata::

    python3 -m pyperf collect_metadata
        [--affinity=CPU_LIST]
        [-o FILENAME/--output FILENAME]

Options:

* ``--affinity=CPU_LIST``: Specify CPU affinity. By default, use isolate CPUs.
  See :ref:`CPU pinning and CPU isolation <pin-cpu>`.
* ``--output=FILENAME``: Save metadata as JSON into FILENAME.

Example::

    $ python3 -m pyperf collect_metadata
    Metadata:
    - aslr: Full randomization
    - cpu_config: 0-3=driver:intel_pstate, intel_pstate:turbo, governor:powersave
    - cpu_count: 4
    - cpu_freq: 0=2181 MHz, 1=2270 MHz, 2=2191 MHz, 3=2198 MHz
    - cpu_model_name:  Intel(R) Core(TM) i7-3520M CPU @ 2.90GHz
    - cpu_temp: coretemp:Physical id 0=51 C, coretemp:Core 0=50 C, coretemp:Core 1=51 C
    - date: 2016-07-18T22:57:06
    - hostname: selma
    - load_avg_1min: 0.02
    - perf_version: 0.8
    - platform: Linux-4.6.3-300.fc24.x86_64-x86_64-with-fedora-24-Twenty_Four
    - python_executable: /usr/bin/python3
    - python_implementation: cpython
    - python_version: 3.5.1 (64bit)
    - timer: clock_gettime(CLOCK_MONOTONIC), resolution: 1.00 ns


.. _slowest_cmd:

pyperf slowest
--------------

Display the 5 benchmarks which took the most time to be run. This command
should not be used to compare performances, but only to find "slow" benchmarks
which makes running benchmarks taking too long.

Options:

* ``-n``: Number of slow benchmarks to display (default: ``5``)

.. _convert_cmd:

pyperf convert
--------------

Convert or modify a benchmark suite::

    python3 -m pyperf convert
        [--include-benchmark=NAME]
        [--exclude-benchmark=NAME]
        [--include-runs=RUNS]
        [--indent]
        [--remove-warmups]
        [--add=FILE]
        [--extract-metadata=NAME]
        [--remove-all-metadata]
        [--update-metadata=METADATA]
        input_filename.json
        (-o output_filename.json/--output=output_filename.json
        | --stdout)

Operations:

* ``--include-benchmark=NAME`` only keeps the benchmark called ``NAME``.
  The option can be specified multiple times.
* ``--exclude-benchmark=NAME`` removes the benchmark called ``NAME``.
  The option can be specified multiple times.
* ``--include-runs=RUNS`` only keeps benchmark runs ``RUNS``. ``RUNS`` is a
  list of runs separated by commas, it can include a range using format
  ``first-last`` which includes ``first`` and ``last`` values. Example:
  ``1-3,7`` (1, 2, 3, 7).
* ``--remove-warmups``: remove warmup values
* ``--add=FILE``: Add benchmark runs of benchmark *FILE*
* ``--extract-metadata=NAME``: Use metadata *NAME* as the new run values
* ``--remove-all-metadata``: Remove all benchmarks metadata except ``name`` and
  ``unit``.
* ``--update-metadata=METADATA``: Update metadata: ``METADATA`` is a
  comma-separated list of ``KEY=VALUE``

Options:

* ``--indent``: Indent JSON (rather using compact JSON)
* ``--stdout`` writes the result encoded as JSON into stdout

.. versionchanged:: 1.2
   The ``--include-benchmark`` and ``--exclude-benchmark`` operations can now
   be specified multiple times.
