from __future__ import print_function
import datetime
import os
import platform
import re
import socket
import sys
import time

import six
try:
    # Optional dependency
    import psutil
except ImportError:
    psutil = None

import perf


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

    version = platform.python_version()
    bits = platform.architecture()[0]
    if bits:
        version = '%s (%s)' % (version, bits)
    metadata['python_version'] = version
    _add(metadata, 'python_executable', sys.executable)

    # Before PEP 393 (Python 3.3)
    if sys.version_info < (3, 3):
        if sys.maxunicode == 0xffff:
            unicode_impl = 'UTF-16'
        else:
            unicode_impl = 'UCS-4'
        metadata['python_unicode'] = unicode_impl


def _read_proc(path):
    try:
        if six.PY3:
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
    if psutil is not None:
        # Number of logical CPUs
        cpu_count = psutil.cpu_count()
    elif hasattr(os, 'cpu_count'):
        # Python 3.4
        cpu_count = os.cpu_count()
    else:
        cpu_count = None
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
    elif psutil is not None:
        proc = psutil.Process()
        if hasattr(proc, 'cpu_affinity'):
            cpus = proc.cpu_affinity()
        else:
            # cpu_affinity() is only available on Linux, Windows and FreeBSD
            cpus = None
    else:
        cpus = None
    if cpus is not None and cpu_count is not None and cpu_count >= 1:
        if set(cpus) == set(range(cpu_count)):
            cpus = None
    if cpus:
        isolated = perf._get_isolated_cpus()
        text = perf._format_cpu_list(cpus)
        if isolated and set(cpus) <= set(isolated):
            text = '%s (isolated)' % text
        metadata['cpu_affinity'] = text

    # Hostname
    hostname = socket.gethostname()
    _add(metadata, 'hostname', hostname)


def collect_run_metadata(metadata):
    date = datetime.datetime.now().isoformat()
    # FIXME: move date to a regular Run attribute with type datetime.datetime?
    metadata['date'] = date.split('.', 1)[0]


def collect_benchmark_metadata(metadata):
    metadata['perf_version'] = perf.__version__

    # perf.perf_counter() timer
    if (hasattr(time, 'get_clock_info')
            # check if it wasn't replaced
            and perf.perf_counter == time.perf_counter):
        info = time.get_clock_info('perf_counter')
        metadata['timer'] = ('%s, resolution: %s'
                             % (info.implementation,
                                perf._format_timedelta(info.resolution)))
    elif perf.perf_counter == time.clock:
        metadata['timer'] = 'time.clock()'
    elif perf.perf_counter == time.time:
        metadata['timer'] = 'time.time()'

    _collect_python_metadata(metadata)
    _collect_system_metadata(metadata)
