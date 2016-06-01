perf: Toolkit to run Python benchmarks.

* `perf project homepage at GitHub
  <https://github.com/haypo/perf>`_ (code, bugs)
* `Download latest perf release at the Python Cheeseshop (PyPI)
  <https://pypi.python.org/pypi/perf>`_
* License: MIT


Install perf
============

Command to install::

    python3 -m pip install perf

It requires Python 2.7 or Python 3.


Command line
============

timeit
------

Microbenchmark::

    python3 -m perf.timeit [-n NUMBER] [-r REPEAT] [-s SETUP_STMT] STMT [STMT2 ...]

Example::

    $ python3 -m perf.timeit 1+1
    Average on 3 process x 3 runs (100000000 loops): 1.8316385942194353 +- 0.015524183699811928


Metadata
--------

Display collected metadata::

    python3 -m perf.metadata

Example::

    $ python3 -m perf.metadata
    cpu_count: 4
    cpu_model_name: Intel(R) Core(TM) i7-2600 CPU @ 3.40GHz
    date: 2016-06-01T17:00:48
    platform: Linux-4.4.9-300.fc23.x86_64-x86_64-with-fedora-23-Twenty_Three
    python_version: 3.4.3


API
===

Statistics
----------

.. function:: mean(data)

   Return the sample arithmetic mean of *data*, a sequence or iterator of
   real-valued numbers.

   The arithmetic mean is the sum of the data divided by the number of data
   points.  It is commonly called "the average", although it is only one of many
   different mathematical averages.  It is a measure of the central location of
   the data.

   If *data* is empty, an exception will be raised.

   On Python 3.4 and newer, it's :func:`statistics.mean`. On older versions,
   it is implemented with ``float(sum(data)) / len(data)``.

.. function:: stdev(data)

   Return the sample standard deviation (the square root of the sample
   variance).

   ::

      >>> stdev([1.5, 2.5, 2.5, 2.75, 3.25, 4.75])
      1.0810874155219827

   On Python 3.4 and newer, it is implemented with :func:`statistics.stdev`.


Clocks
------

.. function:: monotonic_clock()

   Return the value (in fractional seconds) of a monotonic clock, i.e. a clock
   that cannot go backwards.  The clock is not affected by system clock updates.
   The reference point of the returned value is undefined, so that only the
   difference between the results of consecutive calls is valid.

   On Python 3.3 and newer, it's :func:`time.monotonic`. On older versions,
   it's :func:`time.time`. See the PEP 418 for more information on Python
   clocks.

.. function:: perf_counter()

   Return the value (in fractional seconds) of a performance counter, i.e. a
   clock with the highest available resolution to measure a short duration.  It
   does include time elapsed during sleep and is system-wide.  The reference
   point of the returned value is undefined, so that only the difference between
   the results of consecutive calls is valid.

   On Python 3.3 and newer, it's :func:`time.perf_counter`. On older versions,
   it's it's :func:`time.clock` on Windows and :func:`time.time` on other
   platforms. See the PEP 418 for more information on Python clocks.


RunResult
---------

.. class:: RunResult(values=None, loops=None, formatter=None)

   Attributes:

   .. attribute:: formatter

      Function to format a list of numbers.

   .. attribute:: loops

      Number of loops (``int`` or ``None``).

   .. attribute:: values

      List of numbers (``float``).


Result
------

.. class:: Result(runs=None, name=None, metadata=None, formatter=None)

   Attributes:

   .. attribute:: formatter

      Function to format a list of numbers.

   .. attribute:: name

      Benchmark name (``str`` or ``None``).

   .. attribute:: metadata

      Raw dictionary of metadata (``dict``): key=>value, where keys and values
      are strings.

   .. attribute:: runs

      List of :class:`RunResult`.



Metadata
--------

* Python metadata:

  - ``python_version``: Python version, ex: ``2.7.11``
  - ``python_executable``: path to the Python binary program
  - ``python_hashseed``: value of ``PYTHONHASHSEED`` environment variable
  - ``python_unicode``: Implementation of Unicode, ``UTF-16`` or ``UCS-4``,
    only set on Pyhon 2.7, Python 3.2 and older

* System metadata:

  - ``platform``: short string describing the platform
  - ``cpu_count``: number of CPUs
  - ``cpu_model_name``: CPU model name (currently only supported on Linux)

* Misc metadata:

  - ``date``: date when the benchmark started, formatted as ISO 8601


Metadata functions
------------------

.. function:: metadata.collect_all_metadata(metadata)

   Collect all metadata: date, python, system, etc.

   *metadata* must be a dictionary.

.. function:: metadata.collect_python_metadata(metadata)

   Collect metadata about the running Python binary: version, etc.

   *metadata* must be a dictionary.

.. function:: metadata.collect_system_metadata(metadata)

   Collect metadata about the system: CPU count, platform, etc.

   *metadata* must be a dictionary.


Changelog
=========

* Version 0.1

  - First public release

