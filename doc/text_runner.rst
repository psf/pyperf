.. _textrunner_cli:

TextRunner CLI
==============

Command line options of the :class:`~perf.text_runner.TextRunner` class.

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

Default: 20 processes and 3 samples per process (total: 60 samples).

* ``--rigorous``: Spend longer running tests to get more accurate results.
  Multiply the number of ``PROCESSES`` by 2. Default: 40 processes and 3
  samples per process (120 samples).
* ``--fast``: Get rough answers quickly. Divide the number of ``PROCESSES`` by
  2 and multiply the number of ``SAMPLES`` by 2/3 (0.6). Default: 10 processes
  and 2 samples per process (total: 20 samples).
* ``PROCESSES``: number of processes used to run the benchmark
  (default: ``20``)
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

    [-d/--dump]
    [-m/--metadata]
    [-g/--hist]
    [-t/--stats]
    [-v/--verbose]
    [-q/--quiet]

* ``--dump`` displays the benchmark run results,
  see :ref:`perf dump <dump_cmd>` command
* ``--metadata`` displays metadata: see :ref:`perf show metadata
  <show_cmd_metadata>` command
* ``--hist`` renders an histogram of samples, see :ref:`perf hist <hist_cmd>`
  command
* ``--stats`` displays statistics (min, max, ...), see :ref:`perf stats
  <stats_cmd>` command
* ``--verbose`` enables the verbose mode
* ``--quiet`` enables the quiet mode


JSON output
-----------

Options::

    [-o FILENAME/--output=FILENAME]
    [--append=FILENAME]
    [--stdout]

* ``--output=FILENAME`` writes the benchmark result as JSON into *FILENAME*
* ``--append=FILENAME`` appends the benchmark runs to benchmarks of the JSON
  file *FILENAME*. The file is created if it doesn't exist.
* ``--stdout`` writes the benchmark as JSON into stdout

If ``--stdout`` is used, other messages are written into stderr rather than
stdout.


Misc
----

Option::

    [-h/--help]
    [--affinity=CPU_LIST]

* ``--affinity=CPU_LIST``: Specify CPU affinity for worker processes. This way,
  benchmarks can be forced to run on a given set of CPUs to minimize run to run
  variation. By default, worker processes are pinned to isolate CPUs if
  isolated CPUs are found. See :ref:`CPU pinning and CPU isolation <pin-cpu>`.


Internal usage only
-------------------

The following options are used internally by perf and should not be used
explicitly::

    [--worker]
    [--debug-single-sample]

* ``--worker``: a worker process, run the benchmark in the running processs
* ``--debug-single-sample``: Debug mode, only produce a single sample

