Examples
========

bench_sample_func() example
---------------------------

Microbenchmark using the :meth:`~perf.text_runner.TextRunner.bench_sample_func`
method to measure the performance of ``dict[key]``:

.. literalinclude:: examples/bench_sample_func.py

Pass ``--help`` to the script to see the command line options automatically
added by ``perf``.

The ``mydict[key]`` instruction is repeated 10 times to reduce the cost of the
outter ``range(loops)`` loop. To adjust the final result,
``runner.inner_loops`` is set to ``10``, the number of times that
``mydict[key]`` is repeated.

The repeatition is needed on such microbenchmark where the measured instruction
takes less than 1 microsecond. In this case, the cost the outter loop is non
negligible.


bench_func() example
--------------------

Benchmark using the :meth:`~perf.text_runner.TextRunner.bench_func` method to
measure the time elasped when sleeping 1 ms:

.. literalinclude:: examples/bench_func.py

``time.sleep()`` is used to simulate a real workload taking at least 1 ms.

The :meth:`~perf.text_runner.TextRunner.bench_sample_func` method is
recommended if ``func()`` takes less than 1 ms. The
:meth:`~perf.text_runner.TextRunner.bench_func` method has a non negligible
overhead on microbenchmarks.


API
===

Statistics
----------

.. function:: perf.mean(samples)

   Return the sample arithmetic mean of *samples*, a sequence or iterator of
   real-valued numbers.

   The arithmetic mean is the sum of the samples divided by the number of samples
   points.  It is commonly called "the average", although it is only one of many
   different mathematical averages.  It is a measure of the central location of
   the samples.

   If *samples* is empty, an exception will be raised.

   On Python 3.4 and newer, it's :func:`statistics.mean`. On older versions,
   it is implemented with ``float(sum(samples)) / len(samples)``.


.. function:: perf.stdev(samples)

   Return the sample standard deviation (the square root of the sample
   variance).

   ::

      >>> perf.stdev([1.5, 2.5, 2.5, 2.75, 3.25, 4.75])
      1.0810874155219827

   On Python 3.4 and newer, it is implemented with :func:`statistics.stdev`.


.. function:: perf.is_significant(samples1, samples2)

    Determine whether two samples differ significantly.

    This uses a `Student's two-sample, two-tailed t-test
    <https://en.wikipedia.org/wiki/Student's_t-test>`_ with alpha=0.95.

    Returns ``(significant, t_score)`` where significant is a ``bool``
    indicating whether the two samples differ significantly; ``t_score`` is the
    score from the two-sample T test.


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


Benchmark
---------

.. class:: perf.Benchmark(name=None, loops=None, inner_loops=None, metadata=None)

   A benchmark is made of multiple run results.

   Methods:

   .. method:: add_run(samples)

      Add the raw result of a benchmark run.

      *samples* is a non-empty sequence of numbers (``float``) ``>= 0``.
      Usually, *samples* is a list of number of seconds.

      *samples* must contains at least ``warmups + 1`` samples. The first
      :attr:`warmups` samples are excluded from the :meth:`get_samples` result.

      Samples are raw values of all loops. The :meth:`get_samples` method
      divides samples by ``loops x inner_loops`` (see :attr:`loops` and
      :attr:`inner_loops` attributes).

      All runs must have the same number of samples.

   .. method:: get_nrun()

      Get the number of runs (``int``).

   .. method:: get_runs()

      Get raw samples of all runs as a list of raw samples tuples, including
      warmup samples.

      Samples are raw values of all samples: use the :meth:`get_samples` method
      to get normalized samples per loop iteration.

   .. method:: get_samples()

      Get samples of all runs: values are normalized per loop iteration.

      Raw run samples are divided by ``loops x inner_loops``: see :attr:`loops`
      and :attr:`inner_loops` attributes.

   .. method:: get_metadata()

      Get all metadata.

   .. method:: format(verbose=False)

      Format the result as a string (``str``).

   .. method:: json()

      Encode the result as a JSON string (``str``).

   .. classmethod:: json_load(text)

      Load a result from a JSON string (``str``) which was encoded by :meth:`json`.

   .. method:: json_dump_into(file)

      Encode the result as JSON into the *file*.

   .. classmethod:: json_load_from(file)

      Load a result from the JSON file *file* which was created by
      :meth:`json_dump_into`.

   .. method:: mean()

      Get the mean of :meth:`get_samples`.

   Attributes:

   .. attribute:: inner_loops

      Number of inner-loop iterations of the benchmark samples
      (``int``, default: ``None``).

   .. attribute:: loops

      Number of outter-loop iterations of the benchmark samples
      (``int``, default: ``None``).

   .. attribute:: metadata

      Dictionary of metadata (``dict``): key=>value, where keys and values are
      non-empty strings.

   .. attribute:: name

      Benchmark name (``str`` or ``None``).



TextRunner
----------

.. class:: perf.text_runner.TextRunner(name=None, nsample=3, nwarmup=1, nprocess=25, nloop=0, min_time=0.1, max_time=1.0, metadata=None, inner_loops=None)

   Tool to run a benchmark in text mode.

   *name* is the name of the benchmark.

   *metadata* is passed to the :class:`~perf.Benchmark` constructor: see
   :ref:`Metadata <metadata>`.

   *nsample*, *nwarmup* and *nprocess* are the default number of samples,
   warmup samples and processes. These values can be changed with command line
   options.

   If isolated CPUs are detected, the CPU affinity is automatically
   set to these isolated CPUs. See :ref:`CPU pinning and CPU isolation
   <pin-cpu>`.

   Samples are rounded to 9 digits using ``round(sample, 9)``. The most
   accurate clock has a precision of 1 nanosecond. But a time difference can
   produce more than 9 decimal digits after the dot, because of rounding issues
   (time delta is stored as base 2, binary, but formatted in the base 10,
   decimal).

   Methods:

   .. method:: bench_func(func, \*args)

      Benchmark the function ``func(*args)``.

      The :meth:`get_samples` method will divide samples by ``loops x
      inner_loops`` (see :attr:`~perf.Benchmark.loops` and
      :attr:`~perf.Benchmark.inner_loops` attributes of
      :class:`perf.Benchmark`).

      The design of :meth:`bench_func` has a non negligible overhead on
      microbenchmarks: each loop iteration calls ``func(*args)`` but Python
      function calls are expensive. The :meth:`bench_sample_func` method is
      recommended if ``func(*args)`` takes less than 1 millisecond (0.001 sec).

      Return a :class:`~perf.Benchmark` instance.

   .. method:: bench_sample_func(sample_func, \*args)

      Benchmark ``sample_func(loops, *args)``.

      The function must return the total elapsed time of all loops. The
      :meth:`get_samples` method will divide samples by ``loops x inner_loops``
      (see :attr:`~perf.Benchmark.loops` and
      :attr:`~perf.Benchmark.inner_loops` attributes of
      :class:`perf.Benchmark`).

      :func:`perf.perf_counter` should be used to measure the elapsed time.

      Return a :class:`~perf.Benchmark` instance.

   .. method:: parse_args(args=None)

      Parse command line arguments using :attr:`argparser` and put the result
      into :attr:`args`.

   Attributes:

   .. attribute:: args

      Namespace of arguments, see the :meth:`parse_args` method, ``None``
      before :meth:`parse_args` is called.

   .. attribute:: argparser

      :class:`argparse.ArgumentParser` instance.

   .. attribute:: name

      Name of the benchmark.

      The value is passed to the :class:`~perf.Benchmark` object created by
      the :meth:`bench_sample_func` method.

   .. attribute:: inner_loops

      Number of inner-loops of the *sample_func* of :meth:`bench_sample_func`.
      This number is compute the final sample from the result of *sample_func*.

      The value is is passed to the :class:`~perf.Benchmark` constructor.

   .. attribute:: prepare_subprocess_args

      Callback used to prepare command line arguments to spawn a worker child
      process. The callback is called with ``prepare(runner, args)``, args must
      be modified in-place.

      For example, the callback can be used to add arguments not handled
      directly by :class:`~perf.text_runner.TextRunner`.

   .. attribute:: program_args

      Command list arguments to call the program:
      ``(sys.executable, sys.argv[0])`` by default.

      For example, "python3 -m perf.timeit" sets program_args to
      ``('-m', 'perf.timeit')``.


Metadata functions
------------------

.. function:: perf.metadata.collect_metadata(metadata)

   Collect metadata: date, python, system, etc.: see :ref:`Metadata
   <metadata>`.

   *metadata* must be a dictionary.
