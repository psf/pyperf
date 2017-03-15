++++++++++
perf usage
++++++++++

Run a benchmark
===============

The simplest way to run a benchmark is to use the :ref:`timeit command
<timeit_cmd>`::

    $ python3 -m perf timeit '[1,2]*1000'
    .....................
    Median +- std dev: 5.19 us +- 0.11 us

perf measures the performance of the Python instruction ``[1,2]*1000``: 5.19
microseconds (us) in average with a standard deviation of 0.11 microseconds.


Analyze results
===============

To analyze benchmark results, write the output into a JSON file using
``--output`` (``-o``)::

    $ python3 -m perf timeit '[1,2]*1000' -o bench.json
    .....................
    Median +- std dev: 5.22 us +- 0.22 us

show
----

The simplest command is :ref:`show <show_cmd>`, display the average in one
line::

    $ python3 -m perf show bench.json
    Median +- std dev: 5.22 us +- 0.22 us

Note: The command has many options to display much more information.

metadata
--------

perf collects various metadata which can be used to check when the benchmark
was run, on which computer, etc. Use the :ref:`metadata <metadata_cmd>` command
to display saved metadata::

    $ python3 -m perf metadata bench.json
    Metadata:
    - boot_time: 2017-02-22 01:35:13
    - cpu_config: 0=driver:intel_pstate, intel_pstate:no turbo, governor:performance; ...
    - cpu_count: 4
    - cpu_model_name: Intel(R) Core(TM) i7-3520M CPU @ 2.90GHz
    - hostname: selma
    - loops: 2^15
    - name: timeit
    - perf_version: 0.9.4
    ...
    - python_executable: /usr/bin/python3
    - python_implementation: cpython
    - python_version: 3.5.2 (64-bit)
    - timeit_stmt: '[1,2]*1000'
    - timer: clock_gettime(CLOCK_MONOTONIC), resolution: 1.00 ns

dump
----

Use the :ref:`dump <dump_cmd>` command to see all timings::

    $ python3 -m perf dump bench.json
    Run 1: calibrate
    - 1 loop: 10.6 us
    - 2 loops: 19.2 us
    ...
    - 2^14 loops: 84.4 ms
    - 2^15 loops: 170 ms
    Run 2: warmup (1): 5.42 us; values (3): 5.16 us, 5.16 us, 6.15 us (+18%)
    Run 3: warmup (1): 5.41 us; values (3): 5.19 us, 5.29 us, 5.27 us
    Run 4: warmup (1): 5.20 us; values (3): 5.31 us, 5.27 us, 5.62 us (+8%)
    ...
    Run 9: warmup (1): 5.37 us; values (3): 5.60 us (+7%), 5.52 us (+6%), 5.25 us
    ...
    Run 21: warmup (1): 5.48 us; values (3): 5.21 us, 5.16 us, 5.18 us

* perf starts by spawning a first worker process (Run 1) only to calibrate the
  benchmark: compute the number of outer loops: 2^15 loops on the example.
* Then perf spawns 20 worker processes (Run 2 .. Run 21).
* Each worker starts by running the benchmark once to "warmup" the process,
  but this result is ignored in the final result.
* Then each worker runs the benchmark 3 times.

Processes and benchmarks are run sequentially: perf does not run two benchmarks
at the same time. Try ``python3 -m perf dump --verbose bench.json`` to see
dates when each process was started.

To only see values used to compute the result, use the ``--quiet`` (``-q``)
option::

    $ python3 -m perf dump bench.json -q
    Run 2: values (3): 5.16 us, 5.16 us, 6.15 us (+18%)
    Run 3: values (3): 5.19 us, 5.29 us, 5.27 us
    Run 4: values (3): 5.31 us, 5.27 us, 5.62 us (+8%)
    ...
    Run 9: values (3): 5.60 us (+7%), 5.52 us (+6%), 5.25 us
    ...
    Run 21: values (3): 5.21 us, 5.16 us, 5.18 us

It's interesting to see small variations between values: up to 18% slower. But
the stats command is better to analyze variations.

stats
-----

The :ref:`stats <stats_cmd>` command computes various kinds of statistics on
values::

    $ python3 -m perf stats bench.json
    Total duration: 14.3 sec
    Start date: 2017-03-01 17:01:35
    End date: 2017-03-01 17:01:53
    Raw value minimum: 168 ms
    Raw value maximum: 202 ms

    Number of runs: 21
    Total number of values: 60
    Number of values per run: 3
    Number of warmups per run: 1
    Loop iterations per value: 2^15

    Minimum: 5.11 us (-2% of the mean)
    Median +- std dev: 5.22 us +- 0.22 us
    Mean +- std dev: 5.31 us +- 0.22 us
    Maximum: 6.15 us (+18% of the mean)

The last section is the most interesting. It shows that the minimum (5.11 us)
is 2% faster than the mean (5.31 us), and the maximum (6.15 us) is 18%
slower than the mean.

The mean (5.31 us) is also different than the median (5.22 us).

hist
----

Another way to analyze timings is the render an histogram to see the shape of
the distribution::

    $ python3 -m perf hist bench.json
    5.06 us:  1 ###
    5.12 us: 13 ########################################
    5.18 us: 19 ###########################################################
    5.24 us: 10 ###############################
    5.30 us:  3 #########
    5.36 us:  3 #########
    5.42 us:  3 #########
    5.48 us:  1 ###
    5.54 us:  1 ###
    5.60 us:  2 ######
    5.67 us:  0 |
    5.73 us:  1 ###
    5.79 us:  0 |
    5.85 us:  0 |
    5.91 us:  1 ###
    5.97 us:  0 |
    6.03 us:  0 |
    6.09 us:  2 ######

On the histogram, the center is around 5.18 us (the mean is 5.31 us).

The shape of the the curve looks like a skewed gaussian curve: the right side
([5.18 us; 6.09 us]: 0.91 us) is longer than the left side ([5.06 us; 5.18 us]:
0.12 us). This information can also be seen with the Minimum/Maximum of the
stats command.


Compare benchmarks
==================

Let's use Python 2 and Python 3 to generate two different benchmark results::

    $ python2 -m perf timeit '[1,2]*1000' -o py2.json
    .....................
    Median +- std dev: 6.27 us +- 0.20 us

    $ python3 -m perf timeit '[1,2]*1000' -o py3.json
    .....................
    Median +- std dev: 5.25 us +- 0.11 us

The :ref:`compare <compare_cmd>` command uses the fastest version as the reference::

    $ python3 -m perf compare py2.json py3.json
    Median +- std dev: [py3] 5.25 us +- 0.11 us -> [py2] 6.27 us +- 0.20 us: 1.20x slower (+20%)

Python 2 is slower than Python 3 on this benchmark. ::

The :ref:`compare_to <compare_cmd>` command always use the first file as the
reference::

    $ python3 -m perf compare_to py2.json py3.json
    Median +- std dev: [py2] 6.27 us +- 0.20 us -> [py3] 5.25 us +- 0.11 us: 1.20x faster (-16%)

Variant: render a table::

    $ python3 -m perf compare_to py2.json py3.json --table
    +-----------+---------+------------------------------+
    | Benchmark | py2     | py3                          |
    +===========+=========+==============================+
    | timeit    | 6.27 us | 5.25 us: 1.20x faster (-16%) |
    +-----------+---------+------------------------------+
