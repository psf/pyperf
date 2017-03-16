Examples
========

.. _bench_func_example:

bench_func() method
-------------------

Benchmark using the :meth:`Runner.bench_func` method to
measure the time elasped when sleeping 1 ms:

.. literalinclude:: examples/bench_func.py

``time.sleep()`` is used to simulate a real workload taking at least 1 ms.

.. note::

   The :meth:`Runner.bench_time_func` method is recommended if ``func()``
   takes less than 1 ms. The :meth:`Runner.bench_func` method has a non
   negligible overhead on microbenchmarks.


.. _bench_time_func_example:

bench_time_func() method
------------------------

Microbenchmark using the :meth:`Runner.bench_time_func`
method to measure the performance of ``dict[key]``:

.. literalinclude:: examples/bench_time_func.py

Pass ``--help`` to the script to see the command line options automatically
added by ``perf``.

The ``mydict[key]`` instruction is repeated 10 times to reduce the cost of the
outer ``range(loops)`` loop. To adjust the final result,
``runner.inner_loops`` is set to ``10``, the number of times that
``mydict[key]`` is repeated.

The repeatition is needed on such microbenchmark where the measured instruction
takes less than 1 microsecond. In this case, the cost the outer loop is non
negligible.


.. _bench_timeit_example:

timeit()
--------

Benchmark using the :meth:`Runner.bench_command` method to measure the time to
run the ``python -c pass`` command:

.. literalinclude:: examples/bench_command.py


.. _timeit_example:

timeit() method
---------------

Benchmark using the :meth:`Runner.timeit` method to performance of sorting a
sorted list of 1000 numbers using a ``key`` function (which does nothing):

.. literalinclude:: examples/bench_timeit.py


.. _hist_scipy_cmd:

hist_scipy script
-----------------

Example to render an histogram in graphical mode using the ``scipy`` module:

.. literalinclude:: examples/hist_scipy.py

Usage::

    python3 hist_scipy.py [-n BINS/--bins=BINS] filename.json

* ``--bins`` is the number of histogram bars (default: 25)

This command requires the ``scipy`` dependency.

Example::

    $ python3 -m perf hist_scipy telco.json

Output:

.. image:: hist_scipy_telco.png



