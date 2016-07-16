perf commands
=============

General note: if a filename is ``-``, read the JSON content from stdin.

show
----

Show benchmarks of one or multiple benchmark suites::

    pybench show
        [-q/--quiet]
        [-d/--dump]
        [-m/--metadata]
        |-g/--hist] [-t/--stats]
        [-b NAME/--name NAME]
        filename.json [filename2.json ...]

* ``--quiet`` enables the quiet mode
* ``--dump`` displays the benchmark run results,
  see :ref:`perf dump <dump_cmd>` command
* ``--metadata`` displays metadata: see :ref:`perf metadata
  <metadata_cmd>` command
* ``--hist`` displays an histogram of samples, see :ref:`perf hist <hist_cmd>`
  command
* ``--stats`` displays statistics (min, max, ...), see :ref:`perf stats
  <stats_cmd>` command
* ``--name NAME`` only displays the benchmark called ``NAME``

.. _show_cmd_metadata:

Example in verbose mode::

    $ pybench show -v run.json
    Run 1/25: warmup (1): 555 ms; raw samples (3): 546 ms, 630 ms, 553 ms
    Run 2/25: warmup (1): 572 ms; raw samples (3): 546 ms, 546 ms, 547 ms
    (...)
    Run 25/25: warmup (1): 602 ms; raw samples (3): 649 ms, 642 ms, 607 ms

    Average: 56.3 ns +- 2.5 ns (25 runs x 3 samples; 1 warmup)

Example with metadata::

    $ pybench show --metadata run.json
    Metadata:
    - duration: 59.1 sec
    - loops: 10^7
    - timeit_setup: 'pass'
    - timeit_stmt: 'len("abc")'

    Average: 56.3 ns +- 2.5 ns


compare and compare_to
----------------------

Compare benchmark results::

    pybench
        [-v/--verbose] [-m/--metadata]
        compare reference.json filename.json filename2.json [filename3.json ...]

Compare benchmark results to a reference::

    pybench
        [-v/--verbose] [-m/--metadata]
        compare_to reference.json changed.json [changed2.json ...]

Example::

    $ pybench compare py2.json py3.json
    Reference (best): py2

    Average: [py2] 46.3 ns +- 2.2 ns -> [py3] 56.3 ns +- 2.5 ns: 1.2x slower
    Significant (t=-25.90)

.. _stats_cmd:

stats
-----

Compute statistics on a benchmark result::

    pybench stats
        file.json [file2.json ...]

Example::

    $ pybench stats telco.json
    Raw sample minimum: 97.2 ms
    Raw sample maximum: 101 ms

    Number of runs: 50
    Total number of samples: 150
    Number of samples per run: 3
    Number of warmups per run: 1
    Loop iterations per sample: 4

    Minimum: 24.3 ms (-2%)
    Median +- std dev: 24.7 ms +- 0.2 ms
    Mean +- std dev: 24.7 ms +- 0.2 ms
    Maximum: 25.2 ms (+2%)

Values:

* `Median <https://en.wikipedia.org/wiki/Median>`_
* "std dev": `Standard deviation (standard error)
  <https://en.wikipedia.org/wiki/Standard_error>`_


.. _dump_cmd:

dump
----

Display the benchmark run results::

    pybench dump
        [-q/--quiet]
        [-v/--verbose]
        [--raw]
        file.json [file2.json ...]

Options:

* ``--quiet`` enables the quiet mode: hide warmup samples
* ``--verbose`` enables the verbose mode: show run metadata
* ``--raw`` displays raw samples rather than samples

Example::

    $ pybench dump telco.json
    Run 1/50: warmup (1): 24.9 ms; samples (3): 24.6 ms, 24.6 ms, 24.6 ms
    Run 2/50: warmup (1): 25.0 ms; samples (3): 24.8 ms, 24.8 ms, 24.6 ms
    Run 3/50: warmup (1): 24.6 ms; samples (3): 24.6 ms, 24.5 ms, 24.3 ms
    (...)
    Run 50/50: warmup (1): 24.8 ms; samples (3): 24.6 ms, 24.8 ms, 24.8 ms

Example in verbose mode::

    $ pybench dump telco.json -v
    Run 1/50: warmup (1): 24.9 ms; samples (3): 24.6 ms, 24.6 ms, 24.6 ms
      loops=4 inner_loops=1 date=2016-07-11T15:39:37
    Run 2/50: warmup (1): 25.0 ms; samples (3): 24.8 ms, 24.8 ms, 24.6 ms
      loops=4 inner_loops=1 date=2016-07-11T15:39:37
    Run 3/50: warmup (1): 24.6 ms; samples (3): 24.6 ms, 24.5 ms, 24.3 ms
      loops=4 inner_loops=1 date=2016-07-11T15:39:37
    (...)
    Run 50/50: warmup (1): 24.8 ms; samples (3): 24.6 ms, 24.8 ms, 24.8 ms
      loops=4 inner_loops=1 date=2016-07-11T15:40:00

.. _hist_cmd:

hist
----

Render an histogram in text mode::

    pybench hist
        [-n BINS/--bins=BINS] [--extend]
        filename.json [filename2.json ...]

* ``--bins`` is the number of histogram bars. By default, it renders up to 25
  bars, or less depending on the terminal size.
* ``--extend``: don't limit to 80 colums x 25 lines but fill the whole
  terminal if it is wider.

If multiple files are used, the histogram is normalized on the minimum and
maximum of all files to be able to easily compare them.

Example::

    $ pybench hist telco.json
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


convert
-------

Convert or modify a benchmark suite::

    pybench convert
        [--include-benchmark=NAME]
        [--exclude-benchmark=NAME]
        [--include-runs=RUNS]
        [--remove-outliers]
        [--indent]
        [--remove-warmups]
        [--add=FILE]
        input_filename.json
        (-o output_filename.json/--output=output_filename.json
        | --stdout)

Options:

* ``--include-benchmark=NAME`` only keeps the benchmark called ``NAME``
* ``--exclude-benchmark=NAME`` removes the benchmark called ``NAME``
* ``--include-runs=RUNS`` only keeps benchmark runs ``RUNS``. ``RUNS`` is a
  list of runs separated by commas, it can include a range using format
  ``first-last`` which includes ``first`` and ``last`` values. Example:
  ``1-3,7`` (1, 2, 3, 7).
* ``--remove-outliers`` removes "outlier runs", runs which contains at least
  one sample which is not in the range ``[median - 5%; median + 5%]``.
  See `Outlier (Wikipedia) <https://en.wikipedia.org/wiki/Outlier>`_.
* ``--remove-warmups``: remove warmup samples
* ``--add=FILE``: Add benchmark runs of benchmark *FILE*
* ``--indent``: Indent JSON (rather using compact JSON)
* ``--stdout`` writes the result encoded as JSON into stdout


.. _metadata_cmd:

metadata
--------

Collect metadata::

    pybench metadata

Example::

    $ pybench metadata
    Metadata:
    - aslr: enabled
    - cpu_count: 4
    - cpu_model_name: Intel(R) Core(TM) i7-3520M CPU @ 2.90GHz
    - date: 2016-06-15T22:08:21
    - hostname: selma
    - perf_version: 0.4
    - platform: Linux-4.4.8-300.fc23.x86_64-x86_64-with-fedora-23-Twenty_Three
    - python_executable: /usr/bin/python3
    - python_implementation: cpython
    - python_version: 3.4.3


timeit
------

Usage
^^^^^

``perf timeit`` usage::

    pybench timeit [options] [-s SETUP] stmt [stmt ...]

See :ref:`TextRunner CLI <textrunner_cli>` for options.

.. note::
   timeit ``-n`` (number) and ``-r`` (repeat) options become ``-l`` (loops) and
   ``-n`` (runs) in perf timeit.

Example
^^^^^^^

Example::

    $ pybench timeit 1+1
    .........................
    Median +- std dev: 11.7 ns +- 0.1 ns

Use ``-v`` to enable the verbose mode::

    $ pybench timeit -v 1+1
    calibration: 1 loop: 983 ns
    calibration: 10 loops: 1.47 us
    ...
    calibration: 10^7 loops: 138 ms
    calibration: use 10^7 loops
    Run 1/25: warmup (1): 117 ms; raw samples (3): 117 ms, 119 ms, 119 ms
    Run 2/25: warmup (1): 117 ms; raw samples (3): 118 ms, 117 ms, 116 ms
    ...
    Run 25/25: warmup (1): 143 ms; raw samples (3): 115 ms, 115 ms, 117 ms

    Median +- std dev: 11.7 ns +- 0.2 ns



timeit versus perf timeit
^^^^^^^^^^^^^^^^^^^^^^^^^

The timeit module of the Python standard library has multiple issues:

* It displays the minimum
* It only runs the benchmark 3 times using a single process (1 run, 3 samples)
* It disables the garbage collector

perf timeit is more reliable and gives a result more representative of a real
use case:

* It displays the average and the standard deviation
* It runs the benchmark in multiple processes (default: 25 runs, 3 samples)
* By default, it uses a first sample in each process to "warmup" the benchmark
* It does not disable the garbage collector

If a benchmark is run using a single process, we get the performance for one
specific case, whereas many parameters are random:

* Since Python 3, the hash function is now randomized and so the number of
  hash collision in dictionaries is different in each process
* Linux uses address space layout randomization (ASLR) by default and so
  the performance of memory accesses is different in each process

See the :ref:`Minimum versus average and standard deviation <min>` section.
