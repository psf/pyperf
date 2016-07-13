Examples
========

bench_sample_func()
-------------------

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


bench_func()
------------

Benchmark using the :meth:`~perf.text_runner.TextRunner.bench_func` method to
measure the time elasped when sleeping 1 ms:

.. literalinclude:: examples/bench_func.py

``time.sleep()`` is used to simulate a real workload taking at least 1 ms.

The :meth:`~perf.text_runner.TextRunner.bench_sample_func` method is
recommended if ``func()`` takes less than 1 ms. The
:meth:`~perf.text_runner.TextRunner.bench_func` method has a non negligible
overhead on microbenchmarks.


.. _hist_scipy_cmd:

hist_scipy
----------

Example to render an histogram in graphical mode using the ``scipy`` module:

.. literalinclude:: examples/hist_scipy.py

Usage::

    python3 hist_scipy.py [-n BINS/--bins=BINS] filename.json

* ``--bins`` is the number of histogram bars (default: 25)

This command requires the ``scipy`` dependency: see :ref:`Install perf
<install>`.

Example::

    $ python3 -m perf hist_scipy telco.json

Output:

.. image:: hist_scipy_telco.png


API
===

Statistics
----------

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


Run
---

.. class:: perf.Run(warmups: int, raw_samples: List[float], loops: int=1, inner_loops: int=1, metadata: dict=None, collect_metadata=True)

   A benchmark run result is made of multiple samples.

   *raw_samples* must be a non-empty sequence of numbers (``float``) greater
   than zero. Usually, *raw_samples* is a list of number of seconds.

   Raw samples must not be equal to zero. If a raw sample is zero, use more
   loop iterations: see :ref:`Runs, samples, warmups, outter and inner loops
   <loops>`.

   *raw_samples* must contains at least ``warmups + 1`` samples. The first
   :attr:`warmups` samples are excluded from the :meth:`Benchmark.get_samples`
   result.

   Raw samples are total for all loops. The :meth:`get_samples` method divides
   raw samples by :meth:`get_loops`.

   Set *collect_metadata* to false to not collect system metadata.


Benchmark
---------

.. class:: perf.Benchmark(name=None, metadata=None)

   A benchmark is made of multiple :class:`Run` objects.

   Methods:

   .. method:: add_metadata(key: str, value: int|str)

      Add a metadata.

   .. method:: add_run(run: Run)

      Add a run: *run* must a :class:`Run` object.

   .. method:: dump(file, compact=True)

      Dump the benchmark as JSON into *file*.

      *file* can be a filename, or an open file object.

      If *compact* is true, generate small file. Otherwise, indent JSON.

   .. method:: format()

      Format the result as ``... +- ...`` (median +- standard deviation) string
      (``str``).

   .. method:: get_loops()

      Get the total number of loops per sample (``int``):
      :attr:`loops` x :attr:`inner_loops`.

   .. method:: get_metadata()

      Get benchmark metadata. Return also metadata which are common to all
      runs.

   .. method:: get_nrun()

      Get the number of runs (``int``).

   .. method:: get_runs()

      Get the list of :class:`perf.Run` objects.

   .. method:: get_samples()

      Get samples of all runs: values are normalized per loop iteration.

      Raw run samples are divided by ``loops x inner_loops``: see :attr:`loops`
      and :attr:`inner_loops` attributes.

   .. method:: get_warmups()

      Get the number of warmup samples per run.

      Return an ``int`` if all runs use the same number of warmups, or return
      the average as a ``float``.

   .. classmethod:: load(file) -> Benchmark

      Load a benchmark from a JSON file which was created by :meth:`dump`.

      *file* can be a filename, ``'-'`` string to load from :data:`sys.stdin`,
      or an open file object.

   .. classmethod:: loads(string) -> Benchmark

      Load a benchmark from a JSON string.

   .. method:: median()

      Get the `median <https://en.wikipedia.org/wiki/Median>`_ of
      :meth:`get_samples`.

      The median cannot be zero: :meth:`add_run` rejects null samples.

   .. method:: __str__()

      Format the result as ``Median +- std dev: ... +- ...`` (median +-
      standard deviation) a string (``str``).

   Attributes:

   .. attribute:: metadata

      Dictionary of metadata (``dict``): key=>value, where keys and values must
      be non-empty strings.

   .. attribute:: name

      Benchmark name (``str`` or ``None``).


BenchmarkSuite
--------------

.. class:: perf.BenchmarkSuite

   A benchmark suite is made of :class:`perf.Benchmark` objects.

   The class inherits from the ``dict`` type and so has the same methods than a
   regular Python dictionary.

   .. method:: add_benchmark(benchmark)

      Add a :class:`perf.Benchmark` object.

   .. function:: dump(file, compact=True)

      Dump the benchmark suite as JSON into *file*.

      *file* can be a filename, or an open file object.

      If *compact* is true, generate small file. Otherwise, indent JSON.

   .. method:: get_benchmarks()

      Get the list of benchmarks sorted by their name.

   .. classmethod:: load(file)

      Load a benchmark suite from a JSON file which was created by
      :meth:`dump`.

      *file* can be a filename, ``'-'`` string to load from :data:`sys.stdin`,
      or an open file object.

   .. classmethod:: loads(string) -> Benchmark

      Load a benchmark suite from a JSON string.

   .. attribute:: filename

      Name of the file from which the benchmark suite was loaded.
      It can be ``None``.


TextRunner
----------

.. class:: perf.text_runner.TextRunner(name=None, samples=3, warmups=1, processes=25, nloop=0, min_time=0.1, max_time=1.0, metadata=None, inner_loops=None)

   Tool to run a benchmark in text mode.

   *name* is the name of the benchmark.

   *metadata* is passed to the :class:`~perf.Benchmark` constructor: see
   :ref:`Metadata <metadata>`.

   *samples*, *warmups* and *processes* are the default number of samples,
   warmup samples and processes. These values can be changed with command line
   options.

   See :ref:`TextRunner CLI <textrunner_cli>` for command line options.

   If isolated CPUs are detected, the CPU affinity is automatically
   set to these isolated CPUs. See :ref:`CPU pinning and CPU isolation
   <pin-cpu>`.

   Samples are rounded to 9 digits using ``round(sample, 9)``. The most
   accurate clock has a precision of 1 nanosecond. But a time difference can
   produce more than 9 decimal digits after the dot, because of rounding issues
   (time delta is stored in base 2, binary, but formatted in base 10,
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

      Return arguments.

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

      For example, ``python3 -m perf.timeit`` sets program_args to
      ``(sys.executable, '-m', 'perf.timeit')``.
