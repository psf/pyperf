perf commands
=============

Commands:

* :ref:`show <show_cmd>`
* :ref:`compare and compare_to <compare_cmd>`
* :ref:`stats <stats_cmd>`
* :ref:`check <check_cmd>`
* :ref:`dump <dump_cmd>`
* :ref:`hist <hist_cmd>`
* :ref:`metadata <metadata_cmd>`
* :ref:`timeit <timeit_cmd>`
* :ref:`system <system_cmd>`
* :ref:`collect_metadata <collect_metadata_cmd>`
* :ref:`slowest <slowest_cmd>`
* :ref:`convert <convert_cmd>`


The Python perf module comes with a ``pyperf`` program which includes different
commands. If for some reasons, ``pyperf`` program cannot be used, ``python3 -m
perf ...`` can be used: it is the same, it's just longer to type :-) For
example, the ``-m perf ...`` syntax is preferred for ``timeit`` because this
command uses the running Python program.

General note: if a filename is ``-``, read the JSON content from stdin.

.. _show_cmd:

show
----

Show benchmarks of one or multiple benchmark suites::

    python3 -m perf show
        [-q/--quiet]
        [-d/--dump]
        [-m/--metadata]
        |-g/--hist] [-t/--stats]
        [-b NAME/--name NAME]
        filename.json [filename2.json ...]

* ``--quiet`` enables the quiet mode
* ``--dump`` displays the benchmark run results,
  see :ref:`perf dump <dump_cmd>` command
* ``--metadata`` displays benchmark metadata: see :ref:`perf metadata
  <metadata_cmd>` command
* ``--hist`` renders an histogram of samples, see :ref:`perf hist <hist_cmd>`
  command
* ``--stats`` displays statistics (min, max, ...), see :ref:`perf stats
  <stats_cmd>` command
* ``--name NAME`` only displays the benchmark called ``NAME``

.. _show_cmd_metadata:

Example::

    $ python3 -m perf show telco.json
    Median +- std dev: 24.6 ms +- 0.2 ms

Example with metadata::

    $ python3 -m perf show telco.json --metadata
    Metadata:
    - aslr: Full randomization
    - cpu_affinity: 1 (isolated)
    - cpu_count: 2
    - cpu_model_name: Intel(R) Core(TM) i7-3520M CPU @ 2.90GHz
    - perf_version: 0.7
    ...

    Median +- std dev: 24.6 ms +- 0.2 ms

.. _compare_cmd:

compare and compare_to
----------------------

Compare benchmark suites, compute the minimum of each benchmark to use it as
the reference::

    python3 -m perf compare
        [-v/--verbose] [-m/--metadata]
        filename.json filename2.json [filename3.json ...]

Compare benchmark suites, use the first file as the reference::

    python3 -m perf compare_to
        [-v/--verbose] [-q/--quiet]
        [-G/--group-by-speed]
        [--min-speed=MIN_SPEED]
        [--table]
        reference.json changed.json [changed2.json ...]

Options:

* ``--group-by-speed``: group results by "Slower", "Faster" and "Same speed"
* ``--min-speed``: Absolute minimum of speed in percent to consider that a
  benchmark is significant (default: 0%)
* ``--table``: Render a table.

Example::

    $ python3 -m perf compare py2.json py3.json
    Median +- std dev: [py2] 11.4 ms +- 2.1 ms -> [py3] 13.6 ms +- 1.3 ms: 1.19x slower (+19%)

On this example, py2 is faster and so used as the reference.

.. versionchanged:: 0.9.3
   Added ``--table`` option.


.. _stats_cmd:

stats
-----

Compute statistics on a benchmark result::

    python3 -m perf stats
        file.json [file2.json ...]

Example::

    $ python3 -m perf stats telco.json
    Total duration: 16.0 sec
    Start date: 2016-07-17 22:50:27
    End date: 2016-07-17 22:50:46
    Raw sample minimum: 96.9 ms
    Raw sample maximum: 100 ms

    Number of runs: 40
    Total number of samples: 120
    Number of samples per run: 3
    Number of warmups per run: 1
    Loop iterations per sample: 4

    Minimum: 24.2 ms (-1%)
    Median +- std dev: 24.6 ms +- 0.2 ms
    Mean +- std dev: 24.6 ms +- 0.2 ms
    Maximum: 25.0 ms (+2%)

Values:

* `Median <https://en.wikipedia.org/wiki/Median>`_
* "std dev": `Standard deviation (standard error)
  <https://en.wikipedia.org/wiki/Standard_error>`_


.. _check_cmd:

check
-----

Check if benchmarks are stable::

    python3 -m perf check
        [-b NAME/--name NAME]
        filename [filename2 ...]

Options:

* ``--name NAME`` only check the benchmark called ``NAME``

Example of stable benchmark::

    $ python3 -m perf check telco.json
    The benchmark seem to be stable

Example of unstable benchmark::

    $ python3 -m perf timeit -l1 -p3 '"abc".strip()' -o json
    (...)

    $ python3 -m perf check json
    ERROR: the benchmark is very unstable, the standard deviation is very high (stdev/median: 42%)!
    Try to rerun the benchmark with more runs, samples and/or loops

    ERROR: the benchmark may be very unstable, the shortest raw sample only took 303 ns
    Try to rerun the benchmark with more loops or increase --min-time


.. _dump_cmd:

dump
----

Display the benchmark run results::

    python3 -m perf dump
        [-q/--quiet]
        [-v/--verbose]
        [--raw]
        file.json [file2.json ...]

Options:

* ``--quiet`` enables the quiet mode: hide warmup samples
* ``--verbose`` enables the verbose mode: show run metadata
* ``--raw`` displays raw samples rather than samples

Example::

    $ python3 -m perf dump telco.json
    Run 1/50: warmup (1): 24.9 ms; samples (3): 24.6 ms, 24.6 ms, 24.6 ms
    Run 2/50: warmup (1): 25.0 ms; samples (3): 24.8 ms, 24.8 ms, 24.6 ms
    Run 3/50: warmup (1): 24.6 ms; samples (3): 24.6 ms, 24.5 ms, 24.3 ms
    (...)
    Run 50/50: warmup (1): 24.8 ms; samples (3): 24.6 ms, 24.8 ms, 24.8 ms

Example in verbose mode::

    $ python3 -m perf dump telco.json -v
    Metadata:
      cpu_count: 2
      cpu_model_name: Intel(R) Core(TM) i7-3520M CPU @ 2.90GHz
      hostname: selma
      loops: 4
      name: telco
      ...

    Run 1: warmup (1): 24.7 ms; samples (3): 24.5 ms, 24.5 ms, 24.5 ms
      cpu_freq: 1=3588 MHz
      date: 2016-07-17T22:50:27
      load_avg_1min: 0.12
    Run 2: warmup (1): 25.0 ms; samples (3): 24.8 ms, 24.6 ms, 24.8 ms
      cpu_freq: 1=3586 MHz
      date: 2016-07-17T22:50:27
      load_avg_1min: 0.12
    ...


.. _hist_cmd:

hist
----

Render an histogram in text mode::

    python3 -m perf hist
        [-n BINS/--bins=BINS] [--extend]
        filename.json [filename2.json ...]

* ``--bins`` is the number of histogram bars. By default, it renders up to 25
  bars, or less depending on the terminal size.
* ``--extend``: don't limit to 80 colums x 25 lines but fill the whole
  terminal if it is wider.

If multiple files are used, the histogram is normalized on the minimum and
maximum of all files to be able to easily compare them.

Example::

    $ python3 -m perf hist telco.json
    26.4 ms:  1 ##
    26.4 ms:  1 ##
    26.4 ms:  2 #####
    26.5 ms:  1 ##
    26.5 ms:  1 ##
    26.5 ms:  4 #########
    26.6 ms:  8 ###################
    26.6 ms:  6 ##############
    26.7 ms: 11 ##########################
    26.7 ms: 13 ##############################
    26.7 ms: 18 ##########################################
    26.8 ms: 21 #################################################
    26.8 ms: 34 ###############################################################################
    26.8 ms: 26 ############################################################
    26.9 ms: 11 ##########################
    26.9 ms: 14 #################################
    27.0 ms: 17 ########################################
    27.0 ms: 14 #################################
    27.0 ms: 10 #######################
    27.1 ms: 10 #######################
    27.1 ms:  7 ################
    27.1 ms: 12 ############################
    27.2 ms:  5 ############
    27.2 ms:  2 #####
    27.3 ms:  0 |
    27.3 ms:  1 ##

See `Gaussian function <https://en.wikipedia.org/wiki/Gaussian_function>`_ and
`Probability density function (PDF)
<https://en.wikipedia.org/wiki/Probability_density_function>`_.


.. _metadata_cmd:

metadata
--------

Display metadata of benchmark files::

    python3 -m perf metadata
        [-b NAME/--name NAME]
        filename [filename2 ...]

Options:

* ``--name NAME`` only displays the benchmark called ``NAME``

Example::

    $ python3 -m perf metadata telco.json
    Metadata:
    - aslr: Full randomization
    - cpu_affinity: 1 (isolated)
    - cpu_config: 1=driver:intel_pstate, intel_pstate:turbo, governor:performance
    - cpu_count: 2
    - cpu_model_name: Intel(R) Core(TM) i7-3520M CPU @ 2.90GHz
    - duration: 400 ms
    - hostname: selma
    - inner_loops: 1
    - loops: 4
    - name: telco
    - perf_version: 0.7
    - platform: Linux-4.6.3-300.fc24.x86_64-x86_64-with-fedora-24-Twenty_Four
    - python_executable: /usr/bin/python3
    - python_implementation: cpython
    - python_version: 3.5.1 (64bit)
    - timer: clock_gettime(CLOCK_MONOTONIC), resolution: 1.00 ns


.. _timeit_cmd:

timeit
------

Usage
^^^^^

``perf timeit`` usage::

    python3 -m perf timeit
        [options]
        [--name NAME]
        [--python PYTHON]
        [--compare-to REF_PYTHON]
        [--inner-loops INNER_LOOPS]
        [--duplicate DUPLICATE]
        [-s SETUP]
        stmt [stmt ...]

Options:

* ``[options]``: see :ref:`Runner CLI <runner_cli>` for more options.
* ``stmt``: Python code executed in the benchmark.
  Multiple statements can be used.
* ``-s SETUP``, ``--setup SETUP``: statement run before the tested statement.
  The option can be specified multiple times.
* ``--name=NAME``: Benchmark name (default: ``timeit``).
* ``--inner-loops=INNER_LOOPS``: Number of inner loops per sample. For example,
  the number of times that the code is copied manually multiple times to reduce
  the overhead of the outer loop.
* ``--compare-to=REF_PYTHON``: Run benchmark on the Python executable ``REF_PYTHON``,
  run benchmark on Python executable ``PYTHON``, and then compare
  ``REF_PYTHON`` result to ``PYTHON`` result.
* ``--duplicate=DUPLICATE``: Duplicate statements (``stmt`` statements, not
  ``SETUP``) to reduce the overhead of the outer loop and multiply
  inner loops by DUPLICATE (see ``--inner-loops`` option).

.. note::
   timeit ``-n`` (number) and ``-r`` (repeat) options become ``-l`` (loops) and
   ``-n`` (runs) in perf timeit.

Example
^^^^^^^

Example::

    $ python3 -m perf timeit '" abc ".strip()'
    .........................
    Median +- std dev: 113 ns +- 2 ns

Verbose example::

    $ python3 -m perf timeit --rigorous --hist --dump --metadata '" abc ".strip()'
    ........................................
    Metadata:
    - cpu_model_name: Intel(R) Core(TM) i7-3520M CPU @ 2.90GHz
    - loops: 2^20
    - platform: Linux-4.6.3-300.fc24.x86_64-x86_64-with-fedora-24-Twenty_Four
    - python_version: 3.5.1 (64bit)
    - timeit_setup: 'pass'
    - timeit_stmt: '" abc ".strip()'
    - timer: clock_gettime(CLOCK_MONOTONIC), resolution: 1.00 ns
    ...

    Run 1: warmup (1): 135 ns (+18%); samples (3): 112 ns, 112 ns, 114 ns
    Run 2: warmup (1): 122 ns (+7%); samples (3): 121 ns (+6%), 112 ns, 112 ns
    Run 3: warmup (1): 112 ns; samples (3): 112 ns, 112 ns, 112 ns
    ...
    Run 40: warmup (1): 117 ns; samples (3): 114 ns, 137 ns (+20%), 123 ns (+8%)

    107 ns:  8 ###########
    111 ns: 59 ###############################################################################
    116 ns: 21 ############################
    120 ns: 10 #############
    125 ns:  9 ############
    129 ns:  3 ####
    133 ns:  4 #####
    138 ns:  1 #
    142 ns:  1 #
    147 ns:  1 #
    151 ns:  0 |
    156 ns:  0 |
    160 ns:  0 |
    165 ns:  2 ###
    169 ns:  0 |
    174 ns:  0 |
    178 ns:  0 |
    182 ns:  0 |
    187 ns:  0 |
    191 ns:  0 |
    196 ns:  1 #

    WARNING: the benchmark seems unstable, the standard deviation is high (stdev/median: 11%)
    Try to rerun the benchmark with more runs, samples and/or loops

    Median +- std dev: 114 ns +- 12 ns


timeit versus perf timeit
^^^^^^^^^^^^^^^^^^^^^^^^^

The timeit module of the Python standard library has multiple issues:

* It displays the minimum
* It only runs the benchmark 3 times using a single process (1 run, 3 samples)
* It disables the garbage collector

perf timeit is more reliable and gives a result more representative of a real
use case:

* It displays the average and the standard deviation
* It runs the benchmark in multiple processes
* By default, it skips the first sample in each process to warmup the benchmark
* It does not disable the garbage collector

If a benchmark is run using a single process, we get the performance for one
specific case, whereas many parameters are random:

* Since Python 3, the hash function is now randomized and so the number of
  hash collision in dictionaries is different in each process
* Linux uses address space layout randomization (ASLR) by default and so
  the performance of memory accesses is different in each process

See the :ref:`Minimum versus average and standard deviation <min>` section.


.. _system_cmd:

system
------

Get or set the system state for benchmarks::

    python3 -m perf system
        [--affinity=CPU_LIST]
        [{show,tune,reset}]

Options:

* ``--affinity=CPU_LIST``: Specify CPU affinity. By default, use isolate CPUs.
  See :ref:`CPU pinning and CPU isolation <pin-cpu>`.

Commands:

* ``system show`` (or ``system``) shows the current state of the system for
  benchmarks
* ``system tune`` tunes the system to run benchmarks
* ``system reset`` resets the system to the default state

Operations
^^^^^^^^^^

* "CPU scaling governor (intel_pstate driver)": Get/Set the CPU scaling
  governor. ``tune`` sets the governor to ``performance``, ``reset`` sets the
  governor to ``powersave``.
* "CPU Frequency": Read/Write
  ``/sys/devices/system/cpu/cpuN/cpufreq/scaling_min_freq`` sysfs.
  ``tune`` sets ``scaling_min_freq`` to the maximum frequency, ``reset`` resets
  ``scaling_min_freq`` to the minimum frequency.
* "IRQ affinity": Handle the state of the ``irqbalance service``: ``tune``
  stops the service, ``reset`` starts the service. Read/Write the CPU affinity
  of interruptions: ``/proc/irq/default_smp_affinity`` and
  ``/proc/irq/N/smp_affinity`` of all IRQs
* "Perf event": Use ``/proc/sys/kernel/perf_event_max_sample_rate`` to set
  the maximum sample rate of perf event to ``1`` for tune, or ``100,000`` for
  reset.
* "Power supply": check that the power cable is plugged. If the power cable is
  unplugged (a laptop running only on a battery), the CPU speed can change
  when the battery level becomes too low.
* "Turbo Boost (MSR)": use ``/dev/cpu/N/msr`` to read/write
  the Turbo Boost mode of Intel CPUs
* "Turbo Boost (intel_pstate driver)": read from/write into
  ``/sys/devices/system/cpu/intel_pstate/no_turbo`` to control the Turbo Boost
  mode of the Intel CPU using the ``intel_pstate`` driver

"Turbo Boost (intel_pstate driver)" is used automatically if the CPU 0 uses the
``intel_pstate`` driver.

Checks
^^^^^^

* "ASLR": Check that Full randomization (``2``) is enabled
  in ``/proc/sys/kernel/randomize_va_space``
* "Check nohz_full": Make sure that nohz_full kernel option is not used with
  the CPU driver intel_pstate. The intel_pstate drive is incompatible
  with nohz_full: see https://bugzilla.redhat.com/show_bug.cgi?id=1378529 bug
  report.
* "Linux scheduler": Check that CPUs are isolated using the
  ``isolcpus=<cpu list>`` parameter of the Linux kernel. Check that
  ``rcu_nocbs=<cpu list>`` paramater is used to no schedule RCU on isolated
  CPUs.

Linux documentation
^^^^^^^^^^^^^^^^^^^

* CPUFreq: CPU frequency and voltage scaling code in the Linux kernel

  * `Linux CPUFreq User Guide
    <https://www.kernel.org/doc/Documentation/cpu-freq/user-guide.txt>`_
  * `CPUFreq Governors
    <https://www.kernel.org/doc/Documentation/cpu-freq/governors.txt>`_
  * `Processor boosting control
    <https://www.kernel.org/doc/Documentation/cpu-freq/boost.txt>`_
  * `Intel P-State driver
    <https://www.kernel.org/doc/Documentation/cpu-freq/intel-pstate.txt>`_

* CPU pinning, real-time:

  * `SMP IRQ affinity
    <https://www.kernel.org/doc/Documentation/IRQ-affinity.txt>`_
  * `NO_HZ: Reducing Scheduling-Clock Ticks
    <https://www.kernel.org/doc/Documentation/timers/NO_HZ.txt>`_

Articles
^^^^^^^^

* Intel: `How to Benchmark Code Execution Times on Intel ® IA-32 and IA -64
  Instruction Set Architectures
  <http://www.intel.com/content/dam/www/public/us/en/documents/white-papers/ia-32-ia-64-benchmark-code-execution-paper.pdf>`_
* `nohz_full=godmode ?
  <http://www.breakage.org/2013/11/15/nohz_fullgodmode/>`_ (Nov 2013)
* Linux-RT: `HOWTO: Build an RT-application
  <https://rt.wiki.kernel.org/index.php/HOWTO:_Build_an_RT-application>`_
* The `Linux realtime wiki <https://rt.wiki.kernel.org/>`_

See also the `Krun program <https://github.com/softdevteam/krun/>`_ which
tunes Linux and OpenBSD to run benchmarks.


More options
^^^^^^^^^^^^

The following options were not tested by perf developers.

* Disable HyperThreading in the BIOS
* Disable Turbo Boost in the BIOS
* CPU pinning on IRQ: /proc/irq/N/smp_affinity
* writeback:

  * /sys/bus/workqueue/devices/writeback/cpumask
  * /sys/bus/workqueue/devices/writeback/numa

* numactl command
* ``for i in $(pgrep rcu); do taskset -pc 0 $i ; done`` (is it useful if
  rcu_nocbs is already used?)
* nohz_full=cpu_list: be careful of P-state/C-state bug (see below)
* intel_pstate=disable: force the usage of the legacy CPU frequency driver
* Non-maskable interrupts (NMI): ``nmi_watchdog=0 nowatchdog nosoftlockup``
* `cset shield - easily configure cpusets
  <http://skebanga.blogspot.it/2012/06/cset-shield-easily-configure-cpusets.html>`_
* `cpuset <https://github.com/lpechacek/cpuset>`_

Misc::

    echo "Disable realtime bandwidth reservation"
    echo -1 > /proc/sys/kernel/sched_rt_runtime_us

    echo "Reduce hung_task_check_count"
    echo 1 > /proc/sys/kernel/hung_task_check_count

    echo "Disable software watchdog"
    echo -1 > /proc/sys/kernel/softlockup_thresh

    echo "Reduce vmstat polling"
    echo 20 > /proc/sys/vm/stat_interval


Notes
^^^^^

* If ``nohz_full`` kernel option is used, the CPU frequency must be fixed,
  otherwise the CPU frequency will be instable. See `Bug 1378529: intel_pstate
  driver doesn't support NOHZ_FULL
  <https://bugzilla.redhat.com/show_bug.cgi?id=1378529>`_.
* ASLR must *not* be disabled manually! (it's enabled by default on Linux)


.. _collect_metadata_cmd:

collect_metadata
----------------

Collect metadata::

    python3 -m perf collect_metadata
        [--affinity=CPU_LIST]
        [-o FILENAME/--output FILENAME]

Options:

* ``--affinity=CPU_LIST``: Specify CPU affinity. By default, use isolate CPUs.
  See :ref:`CPU pinning and CPU isolation <pin-cpu>`.
* ``--output=FILENAME``: Save metadata as JSON into FILENAME.

Example::

    $ python3 -m perf collect_metadata
    Metadata:
    - aslr: Full randomization
    - cpu_config: 0-3=driver:intel_pstate, intel_pstate:turbo, governor:powersave
    - cpu_count: 4
    - cpu_freq: 0=2181 MHz, 1=2270 MHz, 2=2191 MHz, 3=2198 MHz
    - cpu_model_name:  Intel(R) Core(TM) i7-3520M CPU @ 2.90GHz
    - cpu_temp: coretemp:Physical id 0=51 C, coretemp:Core 0=50 C, coretemp:Core 1=51 C
    - date: 2016-07-18T22:57:06
    - hostname: selma
    - load_avg_1min: 0.02
    - perf_version: 0.8
    - platform: Linux-4.6.3-300.fc24.x86_64-x86_64-with-fedora-24-Twenty_Four
    - python_executable: /usr/bin/python3
    - python_implementation: cpython
    - python_version: 3.5.1 (64bit)
    - timer: clock_gettime(CLOCK_MONOTONIC), resolution: 1.00 ns


.. _slowest_cmd:

slowest
-------

Display the 5 benchmarks which took the most time to be run. This command
should not be used to compare performances, but only to find "slow" benchmarks
which makes running benchmarks taking too long.

Options:

* ``-n``: Number of slow benchmarks to display (default: ``5``)

.. _convert_cmd:

convert
-------

Convert or modify a benchmark suite::

    python3 -m perf convert
        [--include-benchmark=NAME]
        [--exclude-benchmark=NAME]
        [--include-runs=RUNS]
        [--remove-outliers]
        [--indent]
        [--remove-warmups]
        [--add=FILE]
        [--extract-metadata=NAME]
        [--remove-all-metadata]
        [--update-metadata=METADATA]
        input_filename.json
        (-o output_filename.json/--output=output_filename.json
        | --stdout)

Operations:

* ``--include-benchmark=NAME`` only keeps the benchmark called ``NAME``
* ``--exclude-benchmark=NAME`` removes the benchmark called ``NAME``
* ``--include-runs=RUNS`` only keeps benchmark runs ``RUNS``. ``RUNS`` is a
  list of runs separated by commas, it can include a range using format
  ``first-last`` which includes ``first`` and ``last`` values. Example:
  ``1-3,7`` (1, 2, 3, 7).
* ``--remove-outliers`` removes "outlier runs", runs which contains at least
  one sample which is not in the range ``[median - 5%; median + 5%]``.
  See `Outlier (Wikipedia) <https://en.wikipedia.org/wiki/Outlier>`_.
* ``--remove-warmups``: remove warmup samples
* ``--add=FILE``: Add benchmark runs of benchmark *FILE*
* ``--extract-metadata=NAME``: Use metadata *NAME* as the new run values
* ``--remove-all-metadata``: Remove all benchmarks metadata except ``name`` and
  ``unit``.
* ``--update-metadata=METADATA``: Update metadata: ``METADATA`` is a
  comma-separated list of ``KEY=VALUE``

Options:

* ``--indent``: Indent JSON (rather using compact JSON)
* ``--stdout`` writes the result encoded as JSON into stdout


