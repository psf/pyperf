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

Runs, values, warmups, outer and inner loops
==============================================

The ``perf`` module uses 5 options to configure benchmarks:

* "runs": Number of spawned processes, ``-p/--processes`` command line option
* "values": Number of values per run,  ``-n/--values`` command line option
* "warmups": Number of values per run used to warmup the benchmark,
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
get an uniform distribution.

The "warmups" parameter should be configured by analyzing manually values.
Usually, skipping the first value is enough to warmup the benchmark.
Sometimes, more values should be skipped to warmup the benchmark.

By default, the number of outer-loops is automatically computed by calibrating
the benchmark: a value should take betwen 100 ms and 1 sec (values
configurable using ``--min-time`` and ``--max-time`` command line options).

The number of inner-loops microbenchmarks when the tested instruction is
manually duplicated to limit the cost of Python loops. See the
:attr:`~Runner.inner_loops` attribute of the
:class:`Runner` class.

Example of unstable benchmark because the number of loops is too low::

    $ python3 -m perf timeit --loops=10 pass
    .........................
    WARNING: the benchmark seems unstable, the standard deviation is high (11%)
    Try to rerun the benchmark with more runs, values and/or loops

    ERROR: the benchmark may be very unstable, the shortest value only took 310 ns
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
all values.

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
                "runs": [
                    {
                        "metadata": {
                            "date": "2016-10-21 03:14:19.670631",
                            "duration": 0.33765527700597886,
                            "load_avg_1min": 0.29,
                            ...
                        },
                        "warmups": [
                            [
                                1,
                                0.023075559991411865
                            ],
                            [
                                2,
                                0.04504403499595355
                            ],
                            ...
                        ]
                    },
                    {
                        "metadata": {
                            ...
                        },
                        "values": [
                            0.022752201875846367,
                            0.022529058374857414,
                            0.022569017250134493
                        ],
                        "warmups": [
                            [
                                8,
                                0.1799866840010509
                            ]
                        ]
                    },
                    ...
                ]
            }
        ],
        "metadata": {
            "cpu_count": 4,
            "cpu_model_name": "Intel(R) Core(TM) i7-3520M CPU @ 2.90GHz",
            "description": "Telco decimal benchmark",
            "hostname": "selma",
            "loops": 8,
            "name": "telco",
            "perf_version": "0.8.2",
            "performance_version": "0.3.3",
            ...
        },
        "version": 6
    }

See also the `jq tool <https://stedolan.github.io/jq/>`_: "lightweight and
flexible command-line JSON processor".


.. _stable_bench:

Stable and reliable benchmarks
==============================

Getting stable and reliable benchark results requires to tune the system and to
analyze manually results to adjust :ref:`benchmark parameters <loops>`.

The ``--no-locale`` option may be used to use the POSIX locale and so not
have a result depending on the current locale.

Modern Intel CPU are more and more complex: `Causes of Performance Swings Due
to Code Placement in IA
<https://llvmdevelopersmeetingbay2016.sched.org/event/8YzY/causes-of-performance-instability-due-to-code-placement-in-x86>`_
by Zia Ansari (Intel), November 2016.

Use the :ref:`perf system tune command <system_cmd>` to tune the system for
benchmarks.


See also:

* `Microbenchmarks article
  <http://haypo-notes.readthedocs.io/microbenchmark.html>`_ (by Victor Stinner)
  contains misc information on how to run stable benchmarks.
* `SPEC CPU2000: Measuring CPU Performance in the New Millennium
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

See also:

* `cset shield - easily configure cpusets
  <http://skebanga.blogspot.it/2012/06/cset-shield-easily-configure-cpusets.html>`_
* `cpuset <https://github.com/lpechacek/cpuset>`_


JIT compilers
^^^^^^^^^^^^^

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

See the `perf issue #14 <https://github.com/haypo/perf/issues/14>`_ for more
information.

perf does not implement a function to warmup the benchmark until results seem
to be stable. On some benchmarks, performances are never stable: see the paper
mentionned above. Running an arbitrary number of warmup values may also make
the benchmark less reliable since two runs may use a different number of warmup
values.


.. _metadata:

Metadata
========

The :class:`Runner` class collects metadata in each worker process.

Benchmark:

* ``date``: date when the benchmark run started, formatted as ISO 8601
* ``duration``: total duration of the benchmark run in seconds (``float``)
* ``name``: name of the benchmark
* ``loops``: number of outer-loops per value (``int``)
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
* ``unit``: Unit of values: ``byte``, ``integer`` or ``second``

See the :func:`perf.metadata.collect_metadata` function.


Why is perf so slow?
====================

``--fast`` and ``--rigorous`` options indirectly have an impact on the total
duration of benchmarks. The ``perf`` module is not optimized for the total
duration but to produce :ref:`reliable benchmarks <stable_bench>`.

The ``--fast`` is designed to be fast, but remain reliable enough to be
sensitive. Using less worker processes and less values per worker would
produce unstable results.
