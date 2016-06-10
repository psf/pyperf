API Examples
============

TextRunner.bench_sample_func() example
--------------------------------------

Simple microbenchmark to measure the performance of ``dict[key]``::

    import perf.text_runner

    mydict = {str(k): k for k in range(1000)}

    def func(loops):
        t0 = perf.perf_counter()
        for loops in range(loops):
            mydict['0']
            mydict['100']
            mydict['200']
            mydict['300']
            mydict['400']
            mydict['500']
            mydict['600']
            mydict['800']
            mydict['900']
        return perf.perf_counter() - t0

    runner = perf.text_runner.TextRunner()
    runner.bench_sample_func(func)

Running the script without argument should return a reliable average. Pass the
``--help`` command line argument to see the whole list of options. ``perf``
adds many options by default to control the benchmark.


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

   .. method:: bench_sample_func(sample_func, \*args)

      Benchmark ``sample_func(loops, *args)``.

      The function must return the total elapsed time (not the average time per
      loop iteration). The total elapsed time is required to be able to
      automatically calibrate the number of loops.

      :func:`perf.perf_counter` should be used to measure the elapsed time.

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

   Collect metadata: date, python, system, etc.: see :ref:`Metadata
   <metadata>`.

   *metadata* must be a dictionary.
