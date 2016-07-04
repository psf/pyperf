perf.timeit command
===================

Usage
-----

``perf.timeit`` usage::

    python3 -m perf.timeit
        [-p PROCESSES] [-n SAMPLES] [-l LOOPS] [-w WARMUPS]
        [--affinity=CPU_LIST]
        [--metadata] [-g/--hist] [-t/--stats]
        [--json]
        [--json-file=FILENAME]
        [--json-append=FILENAME]
        [--raw]
        [-h/--help] [-v/--verbose] [-q/--quiet]
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

* ``--verbose`` enables verbose mode
* ``--verbose`` enables quiet mode
* ``--metadata`` displays metadata
* ``--hist`` displays an histogram of samples
* ``--stats`` displays statistics (min, max, ...)
* ``--raw`` runs a single process (must only be used internally)
* ``--json`` writes result as JSON into stdout, and write other messages
  into stderr
* ``--json-file=FILENAME`` writes result as JSON into *FILENAME*, and write
  other messages into stdout
* ``--json-file=FILENAME`` appends benchmark result as JSON into *FILENAME*,
  and write other messages into stdout. Create the file if it doesn't exist.
* ``--affinity=CPU_LIST``: Specify CPU affinity for worker processes. This way,
  benchmarks can be forced to run on a given set of CPUs to minimize run to run
  variation. By default, worker processes are pinned to isolate CPUs if
  isolated CPUs are found. See :ref:`CPU pinning and CPU isolation <pin-cpu>`.

.. note::
   timeit ``-n`` (number) and ``-r`` (repeat) options become ``-l`` (loops) and
   ``-n`` (runs) in perf.timeit.

Example
-------

Example::

    $ python3 -m perf.timeit 1+1
    .........................
    Median +- std dev: 11.7 ns +- 0.1 ns

Use ``-v`` to enable the verbose mode::

    $ python3 -m perf.timeit -v 1+1
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



timeit versus perf.timeit
-------------------------

The timeit module of the Python standard library has multiple issues:

* It displays the minimum
* It only runs the benchmark 3 times using a single process (1 run, 3 samples)
* It disables the garbage collector

perf.timeit is more reliable and gives a result more representative of a real
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
