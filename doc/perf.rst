++++
perf
++++

.. _install:

Install perf
============

perf supports Python 2.7 and Python 3. To install perf on Python 3::

    python3 -m pip install perf

It installs the ``six`` dependency if needed. On Python 2.7, the ``statistics``
dependency is installed: backport of Python 3.4 `statistics module
<https://docs.python.org/dev/library/statistics.html>`_.

If you get the error ``'install_requires' must be a string ...``: you must
upgrade setuptools to support environment markers in ``install_requires`` of
``setup.py``. Try::

    python3 -m pip install -U setuptools

Optional dependencies:

* ``psutil``: needed for CPU affinity on Python 2.7


.. _loops:

Runs, samples, warmups, outter and inner loops
==============================================

The ``perf`` module uses 5 options to configure benchmarks:

* "runs": Number of spawned processes, ``-p/--processes`` command line option
  (default: 25)
* "samples": Number of samples per run,  ``-n/--samples`` command line option:
  calls "samples" (default: 3)
* "warmups": Number of skipped samples per run,  ``-w/--warmups`` command
  line option (default: 1)
* "loops": Number of outter-loop iterations per sample,  ``-l/--loops`` command
  line option (default: calibrate)
* "inner_loops": Number of inner-loop iterations per sample, hardcoded in
  benchmark (default: 1).

The number of runs should be large enough to reduce the effect of random
factors like randomized address space layer (ASLR) and the Python randomized
hash function.

The total number of samples (runs x samples/run) should be large enough to get
an uniform distribution.

The warmup parameter should be configured by analyzing manually samples.
Usually, skipping the first sample is enough to warmup the benchmark.
Sometimes, the benchmark requires the skip the first 5 samples to become
stable.

By default, the number of outter-loops is automatically computed by calibrating
the benchmark: a sample should take betwen 100 ms and 1 sec (values
configurable using ``--min-time`` and ``--max-time`` command line options).

The number of inner-loops microbenchmarks when the tested instruction is
manually duplicated to limit the cost of Python loops. See the
:attr:`~perf.text_runner.TextRunner.inner_loops` attribute of the
:class:`~perf.text_runner.TextRunner` class.

Example of unstable benchmark because the number of loops is too low::

    $ python3 -m perf.timeit --loops=10 pass
    .........................
    WARNING: the benchmark seems unstable, the standard deviation is high (11%)
    Try to rerun the benchmark with more runs, samples and/or loops

    ERROR: the benchmark may be very unstable, the shortest sample only took 310 ns
    Try to rerun the benchmark with more loops or increase --min-time

    Average: 36.9 ns +- 4.2 ns


.. _min:

Minimum versus average and standard deviation
=============================================

Links:

* `Benchmarking: minimum vs average
  <http://blog.kevmod.com/2016/06/benchmarking-minimum-vs-average/>`_
  (June 2016) by Kevin Modzelewski
* `My journey to stable benchmark, part 3 (average)
  <https://haypo.github.io/journey-to-stable-benchmark-average.html>`_
  (May 2016) by Victor Stinner
* Median versus Mean: `perf issue #1: Use a better measures than average and
  standard <https://github.com/haypo/perf/issues/1>`_


Distribution
============

The :ref:`hist command <hist_cmd>` renders an histogram of the distribution of
all samples.

See also:

* `"How NOT to Measure Latency" by Gil Tene
  <https://www.youtube.com/watch?v=lJ8ydIuPFeU>`_ (video at Youtube)
* `HdrHistogram: A High Dynamic Range Histogram.
  <http://hdrhistogram.github.io/HdrHistogram/>`_: "look at the entire
  percentile spectrum"


.. _stable_bench:

Stable and reliable benchmarks
==============================

Getting stable and reliable benchark results requires to tune the system and to
analyze manually results to adjust :ref:`benchmark parameters <loops>`.

.. _pin-cpu:

CPU pinning and CPU isolation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

On Linux with a multicore CPU, isolate at least 1 core has a significant impact
on the stability of benchmarks. The `My journey to stable benchmark, part 1
(system) <https://haypo.github.io/journey-to-stable-benchmark-system.html>`_
article explains how to tune Linux for this and shows the effect of CPU
isolation and CPU pinning.

The :class:`~perf.text_runner.TextRunner` class automatically pin worker
processes to isolated CPUs (when isolated are detected). CPU pinning can be
checked in benchmark metadata: it is enabled if the ``cpu_affinity``
:ref:`metadata <metadata>` is set.

On Python 3.3 and newer, :func:`os.sched_setaffinity` is used to pin processes.
On Python 2.7, the ``psutil`` is required for
``psutil.Process().cpu_affinity``.

Even if no CPU is isolated, CPU pining makes benchmarks more stable: use the
``--affinity`` command line option.

See also the `Microbenchmarks article
<http://haypo-notes.readthedocs.io/microbenchmark.html>`_ which contains misc
information on running benchmarks.


.. _metadata:

Metadata
========

The :class:`~perf.text_runner.TextRunner` class collects metadata in each
worker process.

Python metadata:

* ``python_implementation``: Python implementation. Examples: ``cpython``,
  ``pypy``, etc.
* ``python_version``: Python version, with the architecture (32 or 64 bits) if
  available, ex: ``2.7.11 (64bit)``
* ``python_executable``: path to the Python binary program
* ``python_unicode``: Implementation of Unicode, ``UTF-16`` or ``UCS-4``,
  only set on Pyhon 2.7, Python 3.2 and older

System metadata:

* ``hostname``: Host name
* ``platform``: short string describing the platform
* ``cpu_count``: number of CPUs

Linux metadata:

* ``cpu_model_name``: CPU model name
* ``aslr``: Address Space Layout Randomization (ASLR), ``enabled`` or
  ``disabled``
* ``cpu_affinity``: if set, the process is pinned to the specified list of
  CPUs

Other:

* ``date``: date when the benchmark started, formatted as ISO 8601
* ``duration``: total duration of the benchmark
* ``perf_version``: Version of the ``perf`` module
* ``timer``: Implementation of ``perf.perf_counter()``, and also resolution if
  available

See the :func:`perf.metadata.collect_metadata` function.


What is perf so slow?
=====================

``--fast`` and ``--rigorous`` options indirectly have an impact on the total
duration of benchmarks. The ``perf`` module is optimized for the total duration
but to produce :ref:reliable benchmarks <stable_bench>`.

The ``--fast`` is designed to be fast, but remain reliable enough to be useful.
Using less worker processes and less samples per worker would produce unstable
results.
