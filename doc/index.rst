++++++++++++++++++++++++++++++++++++++
perf: Toolkit to run Python benchmarks
++++++++++++++++++++++++++++++++++++++

* `perf project homepage at GitHub
  <https://github.com/haypo/perf>`_ (code, bugs)
* `perf documentation
  <https://perf.readthedocs.io/>`_ (this documentation)
* `Download latest perf release at the Python Cheeseshop (PyPI)
  <https://pypi.python.org/pypi/perf>`_
* License: MIT


Install perf
============

Command to install perf on Python 3::

    python3 -m pip install perf

Command to install perf on Python 2::

    python2 -m pip install perf

Python 2.7 or Python 3 are supported.


Command line interface
======================

perf.timeit CLI
---------------

Microbenchmark::

    python3 -m perf.timeit
        [-p PROCESSES] [-n SAMPLES] [-l LOOPS] [-w WARMUPS]
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

Options:

* ``-v`` enables verbose mode
* ``-vv`` enables very verbose mode
* ``--metadata`` displays metadata
* ``--raw`` runs a single process
* ``--json`` writes result as JSON into stdout, and write other messages
  into stderr
* ``--json-file=FILENAME`` writes result as JSON into *FILENAME*, and write
  other messages into stdout

Example::

    $ python3 -m perf.timeit 1+1
    .........................
    Average: 18.3 ns +- 0.3 ns

Use ``-v`` to enable verbose mode::

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

Try also ``-vv`` to enable very verbose mode.

.. note::
   timeit ``-n`` (number) and ``-r`` (repeat) options become ``-l`` (loops) and
   ``-n`` (runs) in perf.timeit.


perf CLI
--------

Display a result file::

    python3 -m perf
        [-v/--verbose] [-M/--no-metadata]
        show filename.json [filename2.json ...]

Compare two result files::

    python3 -m perf
        [-v/--verbose] [-M/--no-metadata]
        compare ref.json changed.json

If a filename is "-", read its JSON content from stdin.

Example: first create a JSON file using timeit::

    $ python3 -m perf.timeit --json-file=run.json 1+1
    .........................
    Average: 18.6 ns +- 0.4 ns (25 runs x 3 samples)

Display the JSON file::

    $ python3 -m perf show run.json
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

    Average: 17.4 ns +- 0.8 ns

Metadata is displayed by default, whereas timeit hides them by default. Use
``-M`` (``--no-metadata``) to hide metadata and ``-v`` (``--verbose``) to enable
the verbose mode::

    $ python3 -m perf show -M -v run.json
    Run 1/25: warmup (1): 19.4 ns; runs (3): 18.2 ns, 18.2 ns, 18.2 ns
    Run 2/25: warmup (1): 18.2 ns; runs (3): 18.2 ns, 18.2 ns, 18.2 ns
    Run 3/25: warmup (1): 18.2 ns; runs (3): 18.2 ns, 18.2 ns, 18.2 ns
    (...)
    Run 25/25: warmup (1): 18.2 ns; runs (3): 18.2 ns, 18.2 ns, 18.2 ns
    Average: 18.6 ns +- 0.4 ns (25 runs x 3 samples; 1 warmup)

Try also ``-vv`` to enable very verbose mode.


perf.metadata CLI
-----------------

Display collected metadata::

    python3 -m perf.metadata

Example::

    $ python3 -m perf.metadata
    aslr: enabled
    cpu_count: 4
    cpu_model_name: Intel(R) Core(TM) i7-3520M CPU @ 2.90GHz
    date: 2016-06-09T21:39:57
    hostname: selma
    platform: Linux-4.4.8-300.fc23.x86_64-x86_64-with-fedora-23-Twenty_Three
    python_executable: /usr/bin/python3
    python_implementation: cpython
    python_version: 3.4.3


timeit versus perf.timeit
=========================

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

The article `My journey to stable benchmark, part 3 (average)
<https://haypo.github.io/journey-to-stable-benchmark-average.html>`_ explains
in depth the multiple issues of being focused on the minimum.


Metadata
========

* Python metadata:

  - ``python_implementation``: Python implementation. Examples: ``cpython``,
    ``pypy``, etc.
  - ``python_version``: Python version, ex: ``2.7.11``
  - ``python_executable``: path to the Python binary program
  - ``python_unicode``: Implementation of Unicode, ``UTF-16`` or ``UCS-4``,
    only set on Pyhon 2.7, Python 3.2 and older

* System metadata:

  - ``hostname``: Host name
  - ``platform``: short string describing the platform
  - ``cpu_count``: number of CPUs

* Linux metadata:

  - ``cpu_model_name``: CPU model name
  - ``aslr``: Address Space Layout Randomization (ASLR), ``enabled`` or
    ``disabled``
  - ``cpu_affinity``: if set, the process is pinned to the specified list of
    CPUs

* Misc metadata:

  - ``date``: date when the benchmark started, formatted as ISO 8601

See the :func:`metadata.collect_metadata` function.


API
===

Statistics
----------

.. function:: perf.mean(data)

   Return the sample arithmetic mean of *data*, a sequence or iterator of
   real-valued numbers.

   The arithmetic mean is the sum of the data divided by the number of data
   points.  It is commonly called "the average", although it is only one of many
   different mathematical averages.  It is a measure of the central location of
   the data.

   If *data* is empty, an exception will be raised.

   On Python 3.4 and newer, it's :func:`statistics.mean`. On older versions,
   it is implemented with ``float(sum(data)) / len(data)``.

.. function:: perf.stdev(data)

   Return the sample standard deviation (the square root of the sample
   variance).

   ::

      >>> perf.stdev([1.5, 2.5, 2.5, 2.75, 3.25, 4.75])
      1.0810874155219827

   On Python 3.4 and newer, it is implemented with :func:`statistics.stdev`.


Clocks
------

.. function:: perf.perf_counter()

   Return the value (in fractional seconds) of a performance counter, i.e. a
   clock with the highest available resolution to measure a short duration.  It
   does include time elapsed during sleep and is system-wide.  The reference
   point of the returned value is undefined, so that only the difference between
   the results of consecutive calls is valid.

   On Python 3.3 and newer, it's :func:`time.perf_counter`. On older versions,
   it's :func:`time.clock` on Windows and :func:`time.time` on other
   platforms. See the PEP 418 for more information on Python clocks.

.. function:: perf.monotonic_clock()

   Return the value (in fractional seconds) of a monotonic clock, i.e. a clock
   that cannot go backwards.  The clock is not affected by system clock updates.
   The reference point of the returned value is undefined, so that only the
   difference between the results of consecutive calls is valid.

   On Python 3.3 and newer, it's :func:`time.monotonic`. On older versions,
   it's :func:`time.time` and so is not monotonic. See the PEP 418 for more
   information on Python clocks.


RunResult
---------

.. class:: perf.RunResult(samples=None, warmups=None, formatter=None)

   Result of a single benchmark run.

   Methods:

   .. method:: format(verbose=False):

      Format samples.

   .. method:: json()

      Encode the run result as a JSON string (``str``).

   .. classmethod:: json_load(text)

      Load a result from a JSON string (``str``) which was encoded by
      :meth:`json`.

   .. method:: json_dump_into(file)

      Encode the run result as JSON into the *file*.

   .. classmethod:: json_load_from(file)

      Load a run result from the JSON file *file* which was created by
      :meth:`json_dump_into`.

   .. classmethod:: from_subprocess(args, \**kwargs)

      Run a child process and create a result from its standard output decoded
      from JSON


   Attributes:

   .. attribute:: formatter

      Function to format a list of numbers.

   .. attribute:: metadata

      Dictionary of metadata (``dict``): key=>value, where keys and values are
      non-empty strings.

   .. attribute:: samples

      List of numbers (``float``). Usually, :attr:`samples` is a list of number
      of seconds.

   .. attribute:: warmups

      Similar to :attr:`samples`: samples run to "warmup" the benchmark. These
      numbers are ignored when computing the average and standard deviation.


Results
-------

.. class:: perf.Results(runs=None, name=None, formatter=None)

   Result of multiple benchmark runs.

   Methods:

   .. method:: get_samples():

      Get samples from all runs.

   .. method:: get_metadata():

      Get metadata of all runs. Skip metadata with different values or not
      existing in all run. Return an empty dictionary if :attr:`runs` is empty.

   .. method:: format(verbose=False):

      Format runs as a string (``str``).

   .. method:: json()

      Encode the result as a JSON string (``str``).

   .. classmethod:: json_load(text)

      Load a result from a JSON string (``str``) which was encoded by :meth:`json`.

   .. method:: json_dump_into(file)

      Encode the result as JSON into the *file*.

   .. classmethod:: json_load_from(file)

      Load a result from the JSON file *file* which was created by
      :meth:`json_dump_into`.

   Attributes:

   .. attribute:: formatter

      Function to format a list of numbers.

   .. attribute:: name

      Benchmark name (``str`` or ``None``).

   .. attribute:: runs

      List of :class:`RunResult` instances.



TextRunner
----------

.. class:: perf.text_runner.TextRunner(nsample=3, nwarmup=1, nprocess=25)

   Tool to run a benchmark in text mode.

   *nsample*, *nwarmup* and *nprocess* are the default number of samples,
   warmup samples and processes. These values can be changed with command line
   options.

   If isolated CPUs are detected, the CPU affinity is automatically
   set to these isolated CPUs. On Linux, see the ``isolcpus`` kernel command
   line argument and the ``/sys/devices/system/cpu/isolated`` file.

   Methods:

   .. method:: bench_func(func, \*args)

      Benchmark the function ``func(*args)``.

   .. method:: bench_sample_func(func, \*args)

      Benchmark a function ``func(*args)``, the function must return
      the sample value (ex: elapsed time).

   .. method:: parse_args(args=None)

      Parse command line arguments using :attr:`argparser` and put the result
      into :attr:`args`.

   Attributes:

   .. attribute:: args

      Namespace of arguments, see the :meth:`parse_args` method, ``None``
      before :meth:`parse_args` is called.

   .. attribute:: argparser

      :class:`argparse.ArgumentParser` instance.

   .. attribute:: result

      :class:`RunResult` instance.



Metadata functions
------------------

.. function:: perf.metadata.collect_metadata(metadata)

   Collect metadata: date, python, system, etc.: see `Metadata`_.

   *metadata* must be a dictionary.


Changelog
=========

* Version 0.3

  - Add ``compare`` command to ``-m perf`` CLI
  - TextRunner is now able to spawn child processes, parse command arguments
    and more features
  - If TextRunner detects isolated CPUs, it sets automatically the CPU affinity
    to these isolated CPUs
  - Add ``--json-file`` command line option
  - Add :meth:`TextRunner.bench_sample_func` method
  - Move metadata from :class:`Results` to :class:`RunResult`
  - Add metadata ``cpu_affinity``

* Version 0.2 (2016-06-07)

  - use JSON to exchange results between processes
  - new ``python3 -m perf`` CLI
  - new :class:`TextRunner` class
  - huge enhancement of the timeit module
  - timeit has a better output format in verbose mode and now also supports a
    ``-vv`` (very verbose) mode. Minimum and maximum are not more shown in
    verbose module, only in very verbose mode.
  - metadata: add ``python_implementation`` and ``aslr``

* Version 0.1 (2016-06-02)

  - First public release
