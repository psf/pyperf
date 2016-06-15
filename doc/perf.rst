++++
perf
++++


Install perf
============

perf supports Python 2.7 and Python 3. Install perf on Python 3::

    python3 -m pip install perf

On Python 2.7, the ``statistics`` dependency is installed.

Optional dependencies:

* ``boltons``: if available, ``hist_scipy`` and ``stats`` commands also
  display median absolute deviation (MAD) and the skewness
* ``psutil``: needed for CPU affinity on Python 2.7
* The ``-m perf hist_scipy`` command requires ``scipy`` and ``matplotlib``.
  Command to install these packages on Fedora:
  ``sudo dnf install -y python3-{scipy,matplotlib}``

If you get the error ``'install_requires' must be a string ...``, you must
upgrade setuptools to support environment markers in ``install_requires`` of
``setup.py``. Try::

    python3 -m pip install -U setuptools


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

Articles:

* `Benchmarking: minimum vs average
  <http://blog.kevmod.com/2016/06/benchmarking-minimum-vs-average/>`_
  (June 2016) by Kevin Modzelewski
* `My journey to stable benchmark, part 3 (average)
  <https://haypo.github.io/journey-to-stable-benchmark-average.html>`_
  (May 2016) by Victor Stinner


Distribution
============

The ``-m perf hist`` command shows an histogram of the distribution of all
samples. Example::

    $ python3 -m perf hist telco.json
    26.2 ms:   6 ###
    26.3 ms:  29 ###############
    26.4 ms:  34 #################
    26.5 ms:  61 ###############################
    26.6 ms: 131 ##################################################################
    26.7 ms:  93 ###############################################
    26.8 ms:  73 #####################################
    26.9 ms:  45 #######################
    27.0 ms:  21 ###########
    27.1 ms:   2 #
    27.2 ms:   4 ##
    27.3 ms:   0 |
    27.4 ms:   1 #

    Average 26.7 ms +- 0.2 ms: 71.6% (358/500)

The distribution looks like a `gaussian curve
<https://en.wikipedia.org/wiki/Gaussian_function>`_ with a `positive skewness
<https://en.wikipedia.org/wiki/Skewness>`_.

The "26.7 ms +- 0.2 ms" average contains 72% of samples.

See also:

* `"How NOT to Measure Latency" by Gil Tene
  <https://www.youtube.com/watch?v=lJ8ydIuPFeU>`_ (video at Youtube)
* `HdrHistogram: A High Dynamic Range Histogram.
  <http://hdrhistogram.github.io/HdrHistogram/>`_: "look at the entire
  percentile spectrum"


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

Benchmark:

* ``inner_loops``: number of inner iterations per sample, see the
  :attr:`~perf.text_runner.TextRunner.inner_loops` attribute of
  :class:`~perf.text_runner.TextRunner`
* ``loops``: number of (outter) iterations per sample

Python metadata:

* ``python_implementation``: Python implementation. Examples: ``cpython``,
  ``pypy``, etc.
* ``python_version``: Python version, ex: ``2.7.11``
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

* ``perf_version``: Version of the ``perf`` module

See the :func:`perf.metadata.collect_metadata` function.
