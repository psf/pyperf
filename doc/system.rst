.. _system:

++++++++++++++++++++++++++++++
Tune the system for benchmarks
++++++++++++++++++++++++++++++


.. _pin-cpu:

CPU pinning and CPU isolation
=============================

On Linux with a multicore CPU, isolating at least 1 core has a significant impact
on the stability of benchmarks. The `My journey to stable benchmark, part 1
(system) <https://vstinner.github.io/journey-to-stable-benchmark-system.html>`_
article explains how to tune Linux for this and shows the effect of CPU
isolation and CPU pinning.

The perf :class:`Runner` class automatically pin worker
processes to isolated CPUs (when isolated CPUs are detected). CPU pinning can
be checked in benchmark metadata: it is enabled if the ``cpu_affinity``
:ref:`metadata <metadata>` is set.

On Python 3.3 and newer, :func:`os.sched_setaffinity` is used to pin processes.
On Python 2.7, the Python module ``psutil`` is required for
``psutil.Process().cpu_affinity()``.

Even if no CPU is isolated, CPU pining makes benchmarks more stable: use the
``--affinity`` command line option.

Check the CPU topology for HyperThreading and NUMA for best performances.

See also:

* `nohz_full=godmode ?
  <http://www.breakage.org/2013/11/15/nohz_fullgodmode/>`_ (by Jeremy Eder, November 2013)
* `cset shield - easily configure cpusets
  <http://skebanga.blogspot.it/2012/06/cset-shield-easily-configure-cpusets.html>`_
* `cpuset <https://github.com/lpechacek/cpuset>`_


Process priority
================

On Windows, worker process are set to the highest priority:
``REALTIME_PRIORITY_CLASS``. See the `SetPriorityClass function
<https://msdn.microsoft.com/en-us/library/windows/desktop/ms686219(v=vs.85).aspx>`_.


Isolate CPUs on Linux
=====================

Enable isolcpus
---------------

Identify physical CPU cores (required for Intel Hyper-Threading CPUs)::

    $ lscpu --extended
    CPU NODE SOCKET CORE L1d:L1i:L2:L3 ONLINE MAXMHZ    MINMHZ
    0   0    0      0    0:0:0:0       oui    5900,0000 1600,0000
    1   0    0      1    1:1:1:0       oui    5900,0000 1600,0000
    2   0    0      2    2:2:2:0       oui    5900,0000 1600,0000
    3   0    0      3    3:3:3:0       oui    5900,0000 1600,0000
    4   0    0      0    0:0:0:0       oui    5900,0000 1600,0000
    5   0    0      1    1:1:1:0       oui    5900,0000 1600,0000
    6   0    0      2    2:2:2:0       oui    5900,0000 1600,0000
    7   0    0      3    3:3:3:0       oui    5900,0000 1600,0000

I have a single CPU on a single socket. We will isolate physical cores 2 and 3,
and logical CPUs 2, 3, 6 and 7. Be also careful of NUMA: here all physical
cores are on the same NUMA node (0).

Reboot, enter GRUB and modify the Linux command line to add::

    isolcpus=2,3,6,7


Check stability of a benchmark
------------------------------

Download the `system_load.py
<https://github.com/vstinner/misc/raw/master/bin/system_load.py>`_: script to
simulate busy system, run enough dummy workers until the system load is higher
than the minimum specified on the command line.

* Prefix benchmark command with ``taskset -c 2,3,6,7`` to run the benchmark on
  isolated CPUs
* Run the benchmark on an idle system
* Run the benchmark with ``system_load.py 5`` running in a different window

The two results must be close. Otherwise, CPU isolation doesn't work.

You can also check the number of context switches by reading
``/proc/pid/status``: read ``voluntary_ctxt_switches`` and
``nonvoluntary_ctxt_switches``. It must be low on a CPU-bound benchmark.

On Linux, perf adds a ``runnable_threads`` metadata to runs: "number of
currently runnable kernel scheduling entities (processes, threads)" (the value
comes from the 4th field of ``/proc/loadavg``).

See also the `Visualize the system noise using perf and CPU isolation
<https://vstinner.github.io/perf-visualize-system-noise-with-cpu-isolation.html>`_
article (by Victor Stinner, June 2016).


NUMA
====

In 2017, high performance Intel and AMD CPUs can have multiple nodes of CPU
cores where each node is assigned to a memory region. The latency for a memory
region depends on the CPU node. This configuration is called `Non-uniform
memory access: NUMA
<https://en.wikipedia.org/wiki/Non-uniform_memory_access>`_.

Use ``lscpu -a -e`` command to list CPUs and their affected NUMA node.

:ref:`CPU pinning <pin-cpu>` is very important on NUMA systems to get best
performances.

See also the ``numactl`` command.


Features of Intel CPUs
======================

Modern Intel CPUs has many dynamic features impacting performances:

* HyperThreading: run two threads per CPU code, share L1 caches
* Turbo Boost: CPU frequency is optimized for best performances depending
  on the number of "active" cores, CPU temperature, etc.
* P-state and C-state: the frequency of a CPU core frequency changes depending
  of C-state and P-state which are tuned by the operating system (by the
  kernel).

Tools to measure CPU frequency, P-state and C-state:

* ``turbostat``
* ``cpupower``
* `corefreq <https://github.com/cyring/corefreq>`_

On Fedora, type ``dnf install -y kernel-tools`` to install ``turbostat`` and ``cpupower``.

See also:

* `Causes of Performance Swings Due to Code Placement in IA
  <https://llvmdevelopersmeetingbay2016.sched.org/event/8YzY/causes-of-performance-instability-due-to-code-placement-in-x86>`_
  by Zia Ansari (Intel), November 2016.
* `Intel CPUs: P-state, C-state, Turbo Boost, CPU frequency, etc.
  <https://vstinner.github.io/intel-cpus.html>`_ by Victor Stinner, July 2016
* `Intel CPUs (part 2): Turbo Boost, temperature, frequency and Pstate C0 bug
  <https://vstinner.github.io/intel-cpus-part2.html>`_
  by Victor Stinner, September 2016

If ``nohz_full`` kernel option is used, the CPU frequency must be fixed,
otherwise the CPU frequency will be instable. See `Bug 1378529: intel_pstate
driver doesn't support NOHZ_FULL
<https://bugzilla.redhat.com/show_bug.cgi?id=1378529>`_.

`Intel i7 cores
<https://en.wikipedia.org/wiki/List_of_Intel_Core_i7_microprocessors>`_:

* Skylake: 6th generation
* Broadwell: 5th generation
* Haswell: 4th generation
* Ivy Bridge: 3rd
* Sandy Bridge: 2nd
* Nehalem: 1st

.. _system_cmd_ops:

Operations and checks of the perf system command
================================================

Operations
----------

The :ref:`perf system command <system_cmd>` implements the following operations:

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
------

The :ref:`perf system command <system_cmd>` implements the following checks:

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
===================

* CPUFreq: CPU frequency and voltage scaling code in the Linux kernel

  * `Linux CPUFreq User Guide
    <https://www.kernel.org/doc/Documentation/cpu-freq/user-guide.txt>`_
  * `CPUFreq Governors
    <https://www.kernel.org/doc/Documentation/cpu-freq/governors.txt>`_
  * `Processor boosting control
    <https://www.kernel.org/doc/Documentation/cpu-freq/boost.txt>`_
  * `Intel P-State driver
    <https://www.kernel.org/doc/Documentation/cpu-freq/intel-pstate.txt>`_

* `Power Management Quality Of Service Interface (PM QOS)
  <https://kernel.org/doc/Documentation/power/pm_qos_interface.txt>`_
  (``/dev/cpu_dma_latency`` device)

* CPU pinning, real-time:

  * `SMP IRQ affinity
    <https://www.kernel.org/doc/Documentation/IRQ-affinity.txt>`_
  * `NO_HZ: Reducing Scheduling-Clock Ticks
    <https://www.kernel.org/doc/Documentation/timers/NO_HZ.txt>`_


macOS
=====

Disable Turbo Boost of Intel CPUs:

* `Intel Power Gadget
  <https://software.intel.com/en-us/articles/intel-power-gadget-20>`_
* `Turbo Boost Switcher for OS X
  <http://www.rugarciap.com/turbo-boost-switcher-for-os-x/>`_


Articles
========

* Intel: `How to Benchmark Code Execution Times on Intel ® IA-32 and IA -64
  Instruction Set Architectures
  <http://www.intel.com/content/dam/www/public/us/en/documents/white-papers/ia-32-ia-64-benchmark-code-execution-paper.pdf>`_
* Linux-RT: `HOWTO: Build an RT-application
  <https://rt.wiki.kernel.org/index.php/HOWTO:_Build_an_RT-application>`_
* The `Linux realtime wiki <https://rt.wiki.kernel.org/>`_

See also the `Krun program <https://github.com/softdevteam/krun/>`_ which
tunes Linux and OpenBSD to run benchmarks.


More options
============

The following options were not tested by perf developers.

* Disable HyperThreading in the BIOS
* Disable Turbo Boost in the BIOS
* writeback:

  * /sys/bus/workqueue/devices/writeback/cpumask
  * /sys/bus/workqueue/devices/writeback/numa

* ``for i in $(pgrep rcu); do taskset -pc 0 $i ; done`` (is it useful if
  rcu_nocbs is already used?)
* nohz_full=cpu_list: be careful of P-state/C-state bug (see below)
* intel_pstate=disable: force the usage of the ACPI CPU driver
* Non-maskable interrupts (NMI): add ``nmi_watchdog=0 nowatchdog nosoftlockup``
  to the Linux kernel command line
* processor.max_cstate=1 idle=poll  https://access.redhat.com/articles/65410
  "You can disable all c-states by booting with idle=poll or just the deep ones
  with "processor.max_cstate=1"
* ``/dev/cpu_dma_latency`` can be used to prevent the CPU from entering deep
  C-states. Open the device, write a 32-bit ``0`` to it, then keep it open
  while your tests runs, close when you're finished. See
  `processor.max_cstate, intel_idle.max_cstate and /dev/cpu_dma_latency
  <http://www.breakage.org/2012/11/14/processor-max_cstate-intel_idle-max_cstate-and-devcpu_dma_latency/>`_.

Misc (untested) Linux commands::

    echo "Disable realtime bandwidth reservation"
    echo -1 > /proc/sys/kernel/sched_rt_runtime_us

    echo "Reduce hung_task_check_count"
    echo 1 > /proc/sys/kernel/hung_task_check_count

    echo "Disable software watchdog"
    echo -1 > /proc/sys/kernel/softlockup_thresh

    echo "Reduce vmstat polling"
    echo 20 > /proc/sys/vm/stat_interval

If available on your kernel (CONFIG_NO_HZ=y and CONFIG_NO_HZ_FULL=y), you may
also enable tickness kernel on these nodes. Add the following option to the
command line::

    nohz_full=2,3,6,7

Check that the Linux command line works::

    $ cat /sys/devices/system/cpu/isolated
    2-3,6-7
    $ cat /sys/devices/system/cpu/nohz_full
    2-3,6-7

Be careful of nohz_full using the intel_pstate CPU driver.

Notes
=====

* ASLR must *not* be disabled manually! (it's enabled by default on Linux)
