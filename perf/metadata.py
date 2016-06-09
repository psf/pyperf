from __future__ import print_function
import datetime
import os
import platform
import re
import sys

PY3 = (sys.version_info >= (3,))


# FIXME: collect metadata of pybench:
# * using timer: time.perf_counter
# * timer: resolution=1e-09, implementation=clock_gettime(CLOCK_MONOTONIC)
# Processor:      x86_64
#    Python:
#       Compiler:       GCC 5.3.1 20160406 (Red Hat 5.3.1-6)
#       Bits:           64bit
#       Build:          May 26 2016 12:16:43 (#default:d3d8faaaaade)


def _add(metadata, key, value):
    if value is None:
        return

    if isinstance(value, int):
        value = str(value)
    elif not isinstance(value, str):
        raise TypeError("invalid metadata type: %r" % (value,))

    value = re.sub(r'\s+', ' ', value)
    value = value.strip()
    if value:
        metadata[key] = value


def _collect_python_metadata(metadata):
    # Implementation
    if hasattr(sys, 'implementation'):
        # PEP 421, Python 3.3
        metadata['python_implementation'] = sys.implementation.name
    else:
        # Convert to lower case to use the same format than Python 3
        _add(metadata, 'python_implementation',
             platform.python_implementation().lower())

    metadata['python_version'] = platform.python_version()
    _add(metadata, 'python_executable', sys.executable)

    # Before PEP 393 (Python 3.3)
    if sys.version_info < (3, 3):
        if sys.maxunicode == 0xffff:
            unicode_impl = 'UTF-16'
        else:
            unicode_impl = 'UCS-4'
        metadata['python_unicode'] = unicode_impl

    # FIXME: add a way to hide less important metadata?
    #try:
    #    import sysconfig
    #    cflags = sysconfig.get_config_var('CFLAGS')
    #    _add(metadata, 'python_cflags', cflags)
    #except ImportError:
    #    pass


def _read_proc(path):
    try:
        if PY3:
            fp = open(path, encoding="utf-8")
        else:
            fp = open("/proc/cpuinfo")
        with fp:
            for line in fp:
                yield line.rstrip()
    except (OSError, IOError):
        return


def _collect_linux_metadata(metadata):
    # CPU model
    for line in _read_proc("/proc/cpuinfo"):
        if line.startswith('model name'):
            model_name = line.split(':', 1)[1]
            _add(metadata, 'cpu_model_name', model_name)
            break

    # ASLR
    for line in _read_proc('/proc/sys/kernel/randomize_va_space'):
        enabled = 'enabled' if line != '0' else 'disabled'
        metadata['aslr'] = enabled
        break


def _collect_system_metadata(metadata):
    metadata['platform'] = platform.platform(True, False)
    if sys.platform.startswith('linux'):
        _collect_linux_metadata(metadata)

    # CPU count
    cpu_count = None
    if hasattr(os, 'cpu_count'):
        # Python 3.4
        cpu_count = os.cpu_count()
    else:
        try:
            import multiprocessing
        except ImportError:
            pass
        else:
            try:
                cpu_count = multiprocessing.cpu_count()
            except NotImplementedError:
                pass
    if cpu_count is not None and cpu_count >= 1:
        metadata['cpu_count'] = str(cpu_count)

    # CPU affinity
    if hasattr(os, 'sched_getaffinity'):
        cpus = os.sched_getaffinity(0)
        if cpu_count is not None and cpu_count >= 1:
            if cpus == set(range(cpu_count)):
                cpus = None
        if cpus:
            metadata['cpu_affinity'] = ', '.join(sorted(map(str, cpus)))


def collect_metadata(metadata):
    date = datetime.datetime.now().isoformat()
    metadata['date'] = date.split('.', 1)[0]
    _collect_python_metadata(metadata)
    _collect_system_metadata(metadata)


def _display_metadata(metadata, file=None):
    if not metadata:
        return
    print("Metadata:", file=file)
    for key, value in sorted(metadata.items()):
        print("- %s: %s" % (key, value), file=file)
    print(file=file)


if __name__ == "__main__":
    metadata = {}
    collect_metadata(metadata)
    for key, value in sorted(metadata.items()):
        print("%s: %s" % (key, value))
