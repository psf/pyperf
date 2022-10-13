+++++++++++++++
Run a benchmark
+++++++++++++++

.. _install:

Install pyperf
==============

Command to install pyperf on Python 3::

    python3 -m pip install pyperf

If you get the error ``'install_requires' must be a string ...`` or
``RequirementParseError: Expected version spec in ...``: you must upgrade
setuptools to support environment markers in ``install_requires`` of
``setup.py``. Try::

    python3 -m pip install -U setuptools

Optional dependencies:

* Python module ``psutil``. Install: ``python3 -m pip install -U psutil``.
* When you are using macOS, you need to install ``psutil`` if you want to use ``--track-memory`` option.

pyperf requires Python 3.6 or newer.

Python 2.7 users can use pyperf 1.7.1 which is the last version compatible with
Python 2.7.


Run a benchmark
===============

The simplest way to run a benchmark is to use the :ref:`pyperf timeit command
<timeit_cmd>`::

    $ python3 -m pyperf timeit '[1,2]*1000'
    .....................
    Mean +- std dev: 4.19 us +- 0.05 us

pyperf measures the performance of the Python instruction ``[1,2]*1000``: 4.19
microseconds (us) in average with a standard deviation of 0.05 microseconds.

If you get such warnings, see :ref:`How to get reproductible benchmark results
<stable_bench>`::

    $ python3 -m pyperf timeit '[1,2]*1000' -o json2
    .....................
    WARNING: the benchmark result may be unstable
    * the maximum (6.02 us) is 39% greater than the mean (4.34 us)

    Try to rerun the benchmark with more runs, values and/or loops.
    Run 'python3 -m pyperf system tune' command to reduce the system jitter.
    Use pyperf stats, pyperf dump and pyperf hist to analyze results.
    Use --quiet option to hide these warnings.

    Mean +- std dev: 4.34 us +- 0.31 us


pyperf architecture
===================

* pyperf starts by spawning a first worker process (Run 1) only to calibrate the
  benchmark: compute the number of outer loops: 2^15 loops on the example.
* Then pyperf spawns 20 worker processes (Run 2 .. Run 21).
* Each worker starts by running the benchmark once to "warmup" the process,
  but this result is ignored in the final result.
* Then each worker runs the benchmark 3 times.

Processes and benchmarks are run sequentially: pyperf does not run two benchmarks
at the same time. Use ``python3 -m pyperf dump --verbose bench.json`` command to
see dates when each process was started.


.. _loops:

Runs, values, warmups, outer and inner loops
==============================================

The ``pyperf`` module uses 5 options to configure benchmarks:

* "runs": Number of spawned processes, ``-p/--processes`` command line option
* "values": Number of value per run,  ``-n/--values`` command line option
* "warmups": Number of warmup per run used to warmup the benchmark,
  ``-w/--warmups`` command line option
* "loops": Number of outer-loop iterations per value,  ``-l/--loops`` command
  line option
* "inner_loops": Number of inner-loop iterations per value, hardcoded in
  benchmark.

See also :ref:`Runner CLI <runner_cli>` for default values.

The number of runs should be large enough to reduce the effect of random
factors like randomized address space layer (ASLR) and the Python randomized
hash function.

The total number of values (runs x values per run) should be large enough to
get a uniform distribution.

The "warmups" parameter should be configured by analyzing manually values.
Usually, skipping the first value is enough to warmup the benchmark.
Sometimes, more values should be skipped to warmup the benchmark.

By default, the number of outer-loops is automatically computed by calibrating
the benchmark: a value takes 100 ms by default (value is configurable using
``--min-time`` command line option).

The number of inner-loops microbenchmarks when the tested instruction is
manually duplicated to limit the cost of Python loops. See the
:attr:`~Runner.inner_loops` attribute of the
:class:`Runner` class.

Example of unstable benchmark because the number of loops is too low::

    $ python3 -m pyperf timeit --loops=10 pass
    ....................
    WARNING: the benchmark result may be unstable
    * the standard deviation (10.8 ns) is 19% of the mean (56.8 ns)
    * the maximum (99.5 ns) is 75% greater than the mean (56.8 ns)
    * the shortest raw value only took 451 ns

    Try to rerun the benchmark with more runs, values and/or loops.
    Run 'python3 -m pyperf system tune' command to reduce the system jitter.
    Use pyperf stats, pyperf dump and pyperf hist to analyze results.
    Use --quiet option to hide these warnings.

    Mean +- std dev: 56.8 ns +- 10.8 ns


See also the :ref:`check command <check_cmd>`.


.. _stable_bench:

How to get reproducible benchmark results
=========================================

Getting stable and reliable benchmark results requires to tune the system and to
analyze manually results to adjust :ref:`benchmark parameters <loops>`. The
first goal is to avoid :ref:`outliers <outlier>` only caused by other "noisy"
applications, and not the benchmark itself.

Use the :ref:`pyperf system tune command <system_cmd>` and see the :ref:`Tune the
system for benchmarks <system>` section to reduce the system jitter.

The ``--no-locale`` option may be used to use the POSIX locale and so not
have a result depending on the current locale.

See also:

* `Microbenchmarks article
  <http://vstinner.readthedocs.io/benchmark.html>`_ (by Victor Stinner)
  contains misc information on how to run stable benchmarks.
* `SPEC CPU2000: Measuring CPU Performance in the New Millennium
  <https://open.spec.org/cpu2000/papers/COMPUTER_200007.JLH.pdf>`_ by John L.
  Henning (Compaq), 2000.
* `Stabilizer <https://emeryberger.com/research/stabilizer/>`_: "Stabilizer is a
  compiler and runtime system that enables statistically rigorous performance
  evaluation. Stabilizer eliminates measurement bias by comprehensively and
  repeatedly randomizing the placement of functions, stack frames, and heap
  objects in memory. Random placement makes anomalous layouts unlikely and
  independent of the environment; re-randomization ensures they are short-lived
  when they do occur." This project seems experimental and seems to be related
  to performance issues with code placement.


JIT compilers
=============

PyPy uses a JIT compiler. It is more complex to benchmark a Python
implementation using a JIT compiler, see this paper for more information:
`Virtual Machine Warmup Blows Hot and Cold <https://arxiv.org/abs/1602.00602>`_
(Feb 2016) by Edd Barrett, Carl Friedrich Bolz, Rebecca Killick, Vincent
Knight, Sarah Mount, Laurence Tratt.

Don't tune the JIT to force compilation: ``pypy --jit
threshold=1,function_threshold=1`` is a bad idea:

* It causes a lot of tracing and compilation.
* Benchmark results would not be representative of an application: such
  parameters are not used in production.
* It probably increases the pressure on the garbage collector.

See the `pyperf issue #14 <https://github.com/psf/pyperf/issues/14>`_ for more
information.

pyperf does not implement a function to warmup the benchmark until results seem
to be stable. On some benchmarks, performances are never stable: see the paper
mentioned above. Running an arbitrary number of warmup values may also make
the benchmark less reliable since two runs may use a different number of warmup
values.

Specializer statistics (`pystats`)
==================================

If running benchmarks on a CPython built with the ``--enable-pystats`` flag, pyperf will automatically collect statistics from about the bytecode specializer during the run of benchmark code.

Due to the overhead of collecting the statistics, it is unlikely the timing results will be useful.

The `Tools/scripts/summarize_stats.py <https://github.com/python/cpython/blob/main/Tools/scripts/summarize_stats.py>`_ script can be used to summarize the statistics in a human-readable form.

Statistics are not cleared between runs.
If you need to delete statistics from a previous run, remove the files in `/tmp/py_stats` (Unix) or `C:\temp\py_stats` (Windows).
