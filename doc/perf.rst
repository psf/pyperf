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

.. note::
   When the ``--raw`` command line option is explicitly used, no child process
   is spawned.


Stable and reliable benchmarks
==============================

Getting stable and reliable benchark results requires to tune the system and to
analyze manually results to adjust :ref:`benchmark parameters <loops>`.

On Linux with a multicore CPU, isolate at least 1 core has a significant impact
on the stability of benchmarks. The `My journey to stable benchmark, part 1
(system) <https://haypo.github.io/journey-to-stable-benchmark-system.html>`_
article explains how to tune Linux for this and shows the effect of CPU
isolation and CPU pinning.

The :class:`~perf.text_runner.TextRunner` class automatically pin worker
processes to isolated CPUs (when isolated are detected). Currently, Python 3.3
is needed to get automatic CPU pinning. CPU pinning can be checked in benchmark
metadata: it is enabled if the ``cpu_affinity`` :ref:`metadata <metadata>` is
set.

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

Misc:

* ``date``: date when the benchmark started, formatted as ISO 8601

See the :func:`perf.metadata.collect_metadata` function.
