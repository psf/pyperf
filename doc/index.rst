perf: Toolkit to run Python benchmarks.

* `perf project homepage at GitHub
  <https://github.com/haypo/perf>`_ (code, bugs)
* `Download latest perf release at the Python Cheeseshop (PyPI)
  <https://pypi.python.org/pypi/perf>`_
* License: MIT

Install perf: ``python3 -m pip install perf``. It requires Python 2.7
or Python 3.


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
   variance).  See :func:`variance` for arguments and other details.

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
