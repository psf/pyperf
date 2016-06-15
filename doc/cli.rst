Command line interface
======================

General note: if a filename is ``-``, read the JSON content from stdin.

perf.timeit command
-------------------

Microbenchmark::

    python3 -m perf.timeit
        [-p PROCESSES] [-n SAMPLES] [-l LOOPS] [-w WARMUPS]
        [--affinity=CPU_LIST]
        [--metadata] [--json [FILENAME]] [--raw]
        [-h/--help] [-v]
        [-s SETUP]
        stmt [stmt ...]

Iterations:

* ``PROCESSES``: number of processes used to run the benchmark (default: 25)
* ``SAMPLES``: number of samples per process (default: 3)
* ``WARMUPS``: the number of samples used to warmup to benchmark (default: 1)
* ``LOOPS``: number of loops per sample. By default, the timer is calibrated
  to get samples taking between 100 ms and 1 sec.

The :ref:`Runs, samples, warmups, outter and inner loops <loops>` section
explains the purpose of these parameters and how to configure them.

Options:

* ``-v`` enables verbose mode
* ``-vv`` enables very verbose mode
* ``--metadata`` displays metadata
* ``--raw`` runs a single process (must only be used internally)
* ``--json`` writes result as JSON into stdout, and write other messages
  into stderr
* ``--json-file=FILENAME`` writes result as JSON into *FILENAME*, and write
  other messages into stdout
* ``--affinity=CPU_LIST``: Specify CPU affinity for worker processes. This way,
  benchmarks can be forced to run on a given set of CPUs to minimize run to run
  variation. By default, worker processes are pinned to isolate CPUs if
  isolated CPUs are found. See :ref:`CPU pinning and CPU isolation <pin-cpu>`.

.. note::
   timeit ``-n`` (number) and ``-r`` (repeat) options become ``-l`` (loops) and
   ``-n`` (runs) in perf.timeit.

Example::

    $ python3 -m perf.timeit 1+1
    .........................
    Average: 18.3 ns +- 0.3 ns

Use ``-v`` to enable the verbose mode::

    $ python3 -m perf.timeit -v 1+1
    .........................
    Metadata:
    - aslr: enabled
    - cpu_count: 4
    - cpu_model_name: Intel(R) Core(TM) i7-3520M CPU @ 2.90GHz
    - platform: Linux-4.4.8-300.fc23.x86_64-x86_64-with-fedora-23-Twenty_Three
    - python_executable: /usr/bin/python3
    - python_implementation: cpython
    - python_version: 3.4.3
    - timeit_loops: 10^7
    - timeit_setup: 'pass'
    - timeit_stmt: '1+1'

    Average: 18.3 ns +- 0.3 ns (25 runs x 3 samples; 1 warmup)

Try also ``-vv`` to enable the very verbose mode.


show command
------------

Display a result file::

    python3 -m perf show [-v/--verbose] [-M/--no-metadata] filename.json

Display the benchmark result::

    $ python3 -m perf show run.json
    Metadata:
    - duration: 59.1 sec
    - loops: 10^7
    - timeit_setup: 'pass'
    - timeit_stmt: 'len("abc")'

    Average: 56.3 ns +- 2.5 ns

Metadata is displayed by default, whereas perf.timeit hides them by default.
Use ``-M`` (``--no-metadata``) to hide metadata and ``-v`` (``--verbose``) to
enable the verbose mode::

    $ python3 -m perf show -M -v run.json
    Average: 56.3 ns +- 2.5 ns (25 runs x 3 samples; 1 warmup)

Very verbose mode::

    $ python3 -m perf show -M -vv run.json
    Run 1/25: warmup (1): 555 ms; raw samples (3): 546 ms, 630 ms, 553 ms
    Run 2/25: warmup (1): 572 ms; raw samples (3): 546 ms, 546 ms, 547 ms
    (...)
    Run 25/25: warmup (1): 602 ms; raw samples (3): 649 ms, 642 ms, 607 ms

    Standard deviation: 4%
    Shortest raw sample: 545 ms

    Average: 56.3 ns +- 2.5 ns (min: 54.5 ns, max: 64.9 ns) (25 runs x 3 samples; 1 warmup)

compare and compare_to commands
-------------------------------

Compare two result files::

    python3 -m perf
        [-v/--verbose] [-M/--no-metadata]
        compare ref.json changed.json

Example::

    $ python3 -m perf compare -M py2.json py3.json
    Reference (best): py2

    Average: [py2] 46.3 ns +- 2.2 ns -> [py3] 56.3 ns +- 2.5 ns: 1.2x slower
    Significant (t=-25.90)


stats command
-------------

Display statistics::

    python3 -m perf [-v/--verbose] stats result.json

Example::

    $ python3 -m perf stats perf/tests/telco.json
    Number of samples: 250
    Minimum 26.4 ms
    Maximum 27.3 ms

    Mean + std dev: 26.9 ms +- 0.2 ms
    Median +- std dev: 26.9 ms +- 0.2 ms
    Median +- MAD: 26.9 ms +- 0.1 ms

    Skewness: 0.04

Values:

* `Median <https://en.wikipedia.org/wiki/Median>`_
* `Mean <https://en.wikipedia.org/wiki/Mean>`_
* "std dev": `Standard deviation (standard error)
  <https://en.wikipedia.org/wiki/Standard_error>`_
* "MAD": `Median Absolute Deviation
  <https://en.wikipedia.org/wiki/Median_absolute_deviation>`_
* `Skewness <https://en.wikipedia.org/wiki/Skewness>`_.

.. note::
   The ``boltons`` optional dependency is needed for MAD and Skewness.


hist and hist_scipy commands
----------------------------

Display an histogram in text mode::

    python3 -m perf [-v/--verbose] hist filename.json

Display an histogram in graphical mode using the ``matplotlib``, ``pylab``
and ``scipy`` modules::

    python3 -m perf [-v/--verbose] hist_scipy filename.json

Example::

    $ python3 -m perf hist perf/tests/telco.json
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

See `Gaussian function <https://en.wikipedia.org/wiki/Gaussian_function>`_.


metadata command
----------------

Collect metadata::

    python3 -m perf metadata

Example::

    $ python3 -m perf metadata
    aslr: enabled
    cpu_count: 4
    cpu_model_name: Intel(R) Core(TM) i7-3520M CPU @ 2.90GHz
    date: 2016-06-09T21:39:57
    hostname: selma
    platform: Linux-4.4.8-300.fc23.x86_64-x86_64-with-fedora-23-Twenty_Three
    python_executable: /usr/bin/python3
    python_implementation: cpython
    python_version: 3.4.3
