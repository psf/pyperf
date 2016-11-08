++++
perf
++++

.. _install:

Install perf
============

perf supports Python 2.7 and Python 3. To install perf on Python 3::

    python3 -m pip install perf

It installs the ``six`` dependency if needed. On Python 2.7, the ``statistics``
dependency is also installed: backport of Python 3.4 `statistics module
<https://docs.python.org/dev/library/statistics.html>`_.

If you get the error ``'install_requires' must be a string ...`` or
``RequirementParseError: Expected version spec in ...``: you must upgrade
setuptools to support environment markers in ``install_requires`` of
``setup.py``. Try::

    python3 -m pip install -U setuptools

Optional dependencies:

* Python module ``psutil``: needed for :ref:`CPU affinity <pin-cpu>` on Python
  2.7. Install: ``python2 -m pip install -U psutil``.


.. _loops:

Runs, samples, warmups, outer and inner loops
==============================================

The ``perf`` module uses 5 options to configure benchmarks:

* "runs": Number of spawned processes, ``-p/--processes`` command line option
* "samples": Number of samples per run,  ``-n/--samples`` command line option:
  calls "samples"
* "warmups": Number of samples per run used to warmup the benchmark,
  ``-w/--warmups`` command line option
* "loops": Number of outer-loop iterations per sample,  ``-l/--loops`` command
  line option
* "inner_loops": Number of inner-loop iterations per sample, hardcoded in
  benchmark.

See also :ref:`Runner CLI <runner_cli>` for default values.

The number of runs should be large enough to reduce the effect of random
factors like randomized address space layer (ASLR) and the Python randomized
hash function.

The total number of samples (runs x samples) should be large enough to get
an uniform distribution.

The "warmups" parameter should be configured by analyzing manually samples.
Usually, skipping the first sample is enough to warmup the benchmark.
Sometimes, more samples should be skipped to warmup the benchmark.

By default, the number of outer-loops is automatically computed by calibrating
the benchmark: a sample should take betwen 100 ms and 1 sec (values
configurable using ``--min-time`` and ``--max-time`` command line options).

The number of inner-loops microbenchmarks when the tested instruction is
manually duplicated to limit the cost of Python loops. See the
:attr:`~Runner.inner_loops` attribute of the
:class:`Runner` class.

Example of unstable benchmark because the number of loops is too low::

    $ python3 -m perf timeit --loops=10 pass
    .........................
    WARNING: the benchmark seems unstable, the standard deviation is high (11%)
    Try to rerun the benchmark with more runs, samples and/or loops

    ERROR: the benchmark may be very unstable, the shortest sample only took 310 ns
    Try to rerun the benchmark with more loops or increase --min-time

    Average: 36.9 ns +- 4.2 ns

See also the :ref:`check command <check_cmd>`.


.. _min:

Minimum versus average and standard deviation
=============================================

Links:

* `Statistically Rigorous Java Performance Evaluation
  <http://buytaert.net/statistically-rigorous-java-performance-evaluation>`_
  by Andy Georges, Dries Buytaert and Lieven Eeckhout, 2007
* `Benchmarking: minimum vs average
  <http://blog.kevmod.com/2016/06/benchmarking-minimum-vs-average/>`_
  (June 2016) by Kevin Modzelewski
* `My journey to stable benchmark, part 3 (average)
  <https://haypo.github.io/journey-to-stable-benchmark-average.html>`_
  (May 2016) by Victor Stinner
* Median versus Mean: `perf issue #1: Use a better measures than average and
  standard <https://github.com/haypo/perf/issues/1>`_
* timeit module of PyPy now uses average:
  `change timeit to report the average +- stdandard deviation
  <https://bitbucket.org/pypy/pypy/commits/fb6bb835369e>`_


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

See also `Multimodal distribution
<https://en.wikipedia.org/wiki/Multimodal_distribution>`_.


.. _json:

perf JSON
=========

perf stores benchmark results as JSON in files. By default, the JSON is
formatted to produce small files. Use the ``python3 -m perf convert --indent
(...)`` command (see :ref:`perf convert <convert_cmd>`) to get readable
(indented) JSON.

perf supports JSON files compressed by gzip: use gzip if filename ends with
``.gz``.

Example of JSON, ``...`` is used in the example for readability::

    {
        "benchmarks": [
            {
                "common_metadata": {
                    "name": "telco",
                    "perf_version": "0.7",
                    "platform": "Linux-4.6.3-300.fc24.x86_64-x86_64-with-fedora-24-Twenty_Four",
                    ...
                },
                "runs": [
                    {
                        "metadata": {
                            "date": "2016-07-17T22:50:27",
                            ...
                        },
                        "samples": [
                            0.0244653635,
                            0.02445928275,
                            0.02450589075
                        ],
                        "warmups": [
                            [
                                4,
                                0.098872539
                            ]
                        ]
                    },
                    ...
                    {
                        "metadata": {
                            "date": "2016-07-17T22:50:45",
                            ...
                        },
                        "samples": [
                            0.024512332,
                            0.02449233075,
                            0.02454807875
                        ],
                        "warmups": [
                            [
                                4,
                                0.098347475
                            ]
                        ]
                    }
                ]
            }
        ],
        "version": 4
    }

See also the `jq tool <https://stedolan.github.io/jq/>`_: "lightweight and
flexible command-line JSON processor".


.. _stable_bench:

Stable and reliable benchmarks
==============================

Getting stable and reliable benchark results requires to tune the system and to
analyze manually results to adjust :ref:`benchmark parameters <loops>`.

Modern Intel CPU are more and more complex: `Causes of Performance Swings Due
to Code Placement in IA
<https://llvmdevelopersmeetingbay2016.sched.org/event/8YzY/causes-of-performance-instability-due-to-code-placement-in-x86>`_
by Zia Ansari (Intel), November 2016.

See the :ref:`system command <system_cmd>`.

See also: `SPEC CPU2000: Measuring CPU Performance in the New Millennium
<https://open.spec.org/cpu2000/papers/COMPUTER_200007.JLH.pdf>`_ by John L.
Henning (Compaq), 2000.


.. _pin-cpu:

CPU pinning and CPU isolation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

On Linux with a multicore CPU, isolating at least 1 core has a significant impact
on the stability of benchmarks. The `My journey to stable benchmark, part 1
(system) <https://haypo.github.io/journey-to-stable-benchmark-system.html>`_
article explains how to tune Linux for this and shows the effect of CPU
isolation and CPU pinning.

The :class:`Runner` class automatically pin worker
processes to isolated CPUs (when isolated CPUs are detected). CPU pinning can
be checked in benchmark metadata: it is enabled if the ``cpu_affinity``
:ref:`metadata <metadata>` is set.

On Python 3.3 and newer, :func:`os.sched_setaffinity` is used to pin processes.
On Python 2.7, the Python module ``psutil`` is required for
``psutil.Process().cpu_affinity()``.

Even if no CPU is isolated, CPU pining makes benchmarks more stable: use the
``--affinity`` command line option.

See the :ref:`system command <system_cmd>`.

See also the `Microbenchmarks article
<http://haypo-notes.readthedocs.io/microbenchmark.html>`_ which contains misc
information on running benchmarks.


.. _metadata:

Metadata
========

The :class:`Runner` class collects metadata in each worker process.

Benchmark:

* ``date``: date when the benchmark run started, formatted as ISO 8601
* ``duration``: total duration of the benchmark run in seconds (``float``)
* ``name``: name of the benchmark
* ``loops``: number of outer-loops per sample (``int``)
* ``inner_loops``: number of inner-loops of the benchmark (``int``)
* ``timer``: Implementation of ``perf.perf_counter()``, and also resolution if
  available

Python metadata:

* ``python_cflags``: Compiler flags used to compile Python.
* ``python_executable``: path to the Python executable
* ``python_hash_seed``: value of the ``PYTHONHASHSEED`` environment variable
  (``random`` string or an ``int``)
* ``python_implementation``: Python implementation. Examples: ``cpython``,
  ``pypy``, etc.
* ``python_version``: Python version, with the architecture (32 or 64 bits) if
  available, ex: ``2.7.11 (64bit)``
* ``python_unicode``: Implementation of Unicode, ``UTF-16`` or ``UCS-4``,
  only set on Pyhon 2.7, Python 3.2 and older

Memory metadata:

* ``mem_max_rss``: Maximum resident set size in bytes (``int``). On Linux,
  kernel 2.6.32 or newer is required.
* ``mem_peak_pagefile_usage``: Get ``PeakPagefileUsage`` of
  ``GetProcessMemoryInfo()`` (of the current process): the peak value of the
  Commit Charge during the lifetime of this process. Only available on Windows.

CPU metadata:

* ``cpu_affinity``: if set, the process is pinned to the specified list of
  CPUs
* ``cpu_config``: Configuration of CPUs (ex: scaling governor)
* ``cpu_count``: number of logical CPUs (``int``)
* ``cpu_freq``: Frequency of CPUs
* ``cpu_machine``: CPU machine
* ``cpu_model_name``: CPU model name
* ``cpu_temp``: Temperature of CPUs

System metadata:

* ``aslr``: Address Space Layout Randomization (ASLR), ``enabled`` or
  ``disabled``
* ``boot_time``: Datetime of the system boot
* ``hostname``: Host name
* ``platform``: short string describing the platform
* ``load_avg_1min``: Load average figures giving the number of jobs in the run
  queue (state ``R``) or waiting for disk I/O (state ``D``) averaged over 1
  minute
* ``runnable_threads``: number of currently runnable kernel scheduling entities
  (processes, threads)
* ``uptime``: Duration since the system boot (``float``, number of seconds
  since ``boot_time``)

Other:

* ``perf_version``: Version of the ``perf`` module
* ``unit``: Unit of samples: ``byte``, ``integer`` or ``second``

See the :func:`perf.metadata.collect_metadata` function.


Why is perf so slow?
====================

``--fast`` and ``--rigorous`` options indirectly have an impact on the total
duration of benchmarks. The ``perf`` module is not optimized for the total
duration but to produce :ref:`reliable benchmarks <stable_bench>`.

The ``--fast`` is designed to be fast, but remain reliable enough to be
sensitive. Using less worker processes and less samples per worker would
produce unstable results.
