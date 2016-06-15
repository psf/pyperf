perf.timeit command
===================

Usage
-----

``perf.timeit`` usage::

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

Example
-------

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

Use ``-vv`` (very verbose mode) to see even more details.

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
