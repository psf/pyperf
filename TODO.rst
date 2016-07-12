TODO
====

* Move more benchmark metadata as run metadata.
  Need to develop something to move equal run metadata to benchmark metadata
  in add_run()
* Detect Intel Turbo Mode: kernel-tools, kernel: tools/power/cpupower::

        static const char *cpu_vendor_table[X86_VENDOR_MAX] = {
                "Unknown", "GenuineIntel", "AuthenticAMD",
        };

        /* parse /proc/cpuinfo */
        if (!strncmp(value, "vendor_id", 9)) {
                for (x = 1; x < X86_VENDOR_MAX; x++) {
                        if (strstr(value, cpu_vendor_table[x]))
                                cpu_info->vendor = x;
                }
        }

        cpuid_level = cpuid_eax(0);
        if (cpu_info->vendor == X86_VENDOR_INTEL) {
            if (cpuid_level >= 6 &&
                    (cpuid_eax(6) & (1 << 1)))
                cpu_info->caps |= CPUPOWER_CAP_INTEL_IDA;
        }

        if (cpupower_cpu_info.caps & CPUPOWER_CAP_INTEL_IDA)
            *support = *active = 1;



* collect more metadata in each worker *but* add_run() and
  _add_benchmark_runs() should limit data duplication by storing common
  metadata in the benchmark metadata
* cleanup --verbose in CLIs
* really avoid removing existing file: open(name, 'x')
* support 2^15 and/or 2**15 syntax for --loops
* support --fast + -p1
* configurable clock? see pybench
* metadata: sys.getcheckinterval? GC enabled? Python3: GIL milliseconds
* fix hist if benchmark only contains one sample
* reimplement metdata for compare?
* convert: save operations in metadata?
* Fix hist command for a benchmark suite with multiple benchmarks: don't
  use the same scale for unrelated benchmarks
* "smart" JSON append:

  - add new runs to an existing JSON file. rerun exactly the same benchmark
    using --json-append
  - use metadata as the key to check if the benchmark is the same?
    ignore date? ignore CPU affinity?

* "merge" two JSON files: cumulate benchmarks, add runs if two files have the
  same benchmark, etc.


Blocker for perf 1.0 (stable API)
=================================

* Clarify run vs process in TextRunner CLI
* "samples" is not the best term, "a data sample is a set of data":
  https://en.wikipedia.org/wiki/Sample_%28statistics%29


Low priority
============

* convert --remove-outliers: more serious algorithm? or configurable percent?
* support multiple units, or remove _format_samples.
  Track memory usage in CPython benchmark suite?
* use the calibration at the first warmup sample in raw mode
* metadata: implement time.get_time_info() on Python 2

  * Call QueryPerformanceFrequency() on Windows using ctypes?



Ideas
=====

* limit the number of processes when a single sample takes 5 seconds
* rework parameters (processes, samples, loops) depending on max time,
  not hardcoded parameters
* Metrics measured before and/or after each run:

  * CPU frequency, system load
  * only store min and max?
  * use them to detect unstable benchmark

