.. _textrunner_cli:

TextRunner CLI
==============

:class:`perf.text_runner.TextRunner` command line options.

Loop iterations
---------------

Options::

    [--rigorous]
    [--fast]
    [-p PROCESSES/--processes=PROCESSES]
    [-n SAMPLES/--samples=SAMPLES]
    [-l LOOPS/--loops=LOOPS]
    [-w WARMUPS/--warmups=WARMUPS]
    [--min-time=MIN_TIME]

* ``--rigorous``: Spend longer running tests to get more accurate results.
  Multiply the number of ``PROCESSES`` by 2 and multiply the number of
  ``SAMPLES`` by 5/3 (1.6). Default: 20 processes and 5 samples per process
  (100 samples).
* ``--fast``: Get rough answers quickly. Divide the number of ``PROCESSES`` by
  2 and multiply the number of ``SAMPLES`` by 2/3 (0.6). Default: 5 processes
  and 2 samples per process (total: 10 samples).
* ``PROCESSES``: number of processes used to run the benchmark
  (default: ``10``)
* ``SAMPLES``: number of samples per process
  (default: ``3``)
* ``WARMUPS``: the number of ignored samples used to warmup to benchmark
  (default: ``1``)
* ``LOOPS``: number of loops per sample. By default, the timer is calibrated
  to get raw samples taking at least ``MIN_TIME`` seconds.
* ``MIN_TIME``: Minimum duration of a single raw sample in seconds
  (default: ``100 ms``)

The :ref:`Runs, samples, warmups, outter and inner loops <loops>` section
explains the purpose of these parameters and how to configure them.


Output options
--------------

Options::

    [-m/--metadata]
    [-g/--hist]
    [-t/--stats]
    [-v/--verbose]
    [-q/--quiet]

* ``--metadata`` displays metadata: see :ref:`perf show metadata
  <show_cmd_metadata>` command
* ``--hist`` displays an histogram of samples, see :ref:`perf hist <hist_cmd>`
  command
* ``--stats`` displays statistics (min, max, ...), see :ref:`perf stats
  <stats_cmd>` command
* ``--verbose`` enables the verbose mode
* ``--quiet`` enables the quiet mode


JSON output
-----------

Options::

    [--stdout]
    [--json-file=FILENAME]
    [--json-append=FILENAME]

* ``--stdout`` writes the benchmark as JSON into stdout
* ``--json-file=FILENAME`` writes the benchmark result as JSON into *FILENAME*,
* ``--json-file=FILENAME`` appends the benchmark result as JSON into
  *FILENAME*. The file is created if it doesn't exist.

If ``--stdout`` is used, other messages are written into stderr rather than
stdout.


Misc
----

Option::

    [-h/--help]
    [--worker]
    [--affinity=CPU_LIST]

* ``--worker``: a worker process, run the benchmark. This option should only
  be used internally.
* ``--affinity=CPU_LIST``: Specify CPU affinity for worker processes. This way,
  benchmarks can be forced to run on a given set of CPUs to minimize run to run
  variation. By default, worker processes are pinned to isolate CPUs if
  isolated CPUs are found. See :ref:`CPU pinning and CPU isolation <pin-cpu>`.
