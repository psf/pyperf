.. _textrunner_cli:

TextRunner CLI
==============

:class:`perf.text_runner.TextRunner` command line options.

Loop iterations
---------------

Options::

    [-p PROCESSES/--processes=PROCESSES]
    [-n SAMPLES/--samples=SAMPLES]
    [-l LOOPS/--loops=LOOPS]
    [-w WARMUPS/--warmups=WARMUPS]
    [--min-time=MIN_TIME] [--max-time=MAX_TIME]

* ``PROCESSES``: number of processes used to run the benchmark
  (default: ``25``)
* ``SAMPLES``: number of samples per process
  (default: ``3``)
* ``WARMUPS``: the number of ignored samples used to warmup to benchmark
  (default: ``1``)
* ``LOOPS``: number of loops per sample. By default, the timer is calibrated
  to get raw samples taking between ``MIN_TIME`` and ``MAX_TIME``.
* ``MIN_TIME``: Minimum duration of a single raw sample (default: ``100 ms``)
* ``MAX_TIME``: Maximum duration of a single raw sample (default: ``1 sec``)

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

    [--json]
    [--json-file=FILENAME]
    [--json-append=FILENAME]

* ``--json`` writes the benchmark result as JSON into stdout
* ``--json-file=FILENAME`` writes the benchmark result as JSON into *FILENAME*,
* ``--json-file=FILENAME`` appends the benchmark result as JSON into
  *FILENAME*. The file is created if it doesn't exist.

If ``--json`` is used, other messages are written into stderr rather than
stdout.


Misc
----

Option::

    [-h/--help]
    [--raw]
    [--affinity=CPU_LIST]

* ``--raw`` runs a single process (must only be used internally)
* ``--affinity=CPU_LIST``: Specify CPU affinity for worker processes. This way,
  benchmarks can be forced to run on a given set of CPUs to minimize run to run
  variation. By default, worker processes are pinned to isolate CPUs if
  isolated CPUs are found. See :ref:`CPU pinning and CPU isolation <pin-cpu>`.
