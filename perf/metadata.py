from __future__ import print_function
import datetime
import os
import platform
import re
import socket
import subprocess
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
    path = os.path.join('/proc', path)
    try:
        if six.PY3:
            fp = open(path, encoding="utf-8")
        else:
            fp = open(path)
        try:
            for line in fp:
                yield line.rstrip()
        finally:
            fp.close()
    except (OSError, IOError):
        return


def _collect_linux_metadata(metadata):
    # CPU model
    for line in _read_proc("cpuinfo"):
        if line.startswith('model name'):
            model_name = line.split(':', 1)[1]
            _add(metadata, 'cpu_model_name', model_name)
            break

    # ASLR
    for line in _read_proc('sys/kernel/randomize_va_space'):
        if line == '0':
            metadata['aslr'] = 'No randomization'
        elif line == '1':
            metadata['aslr'] = 'Conservative randomization'
        elif line == '2':
            metadata['aslr'] = 'Full randomization'
        break


def _get_cpu_affinity():
    if hasattr(os, 'sched_getaffinity'):
        return os.sched_getaffinity(0)

    if psutil is not None:
        proc = psutil.Process()
        # cpu_affinity() is only available on Linux, Windows and FreeBSD
        if hasattr(proc, 'cpu_affinity'):
            return proc.cpu_affinity()

    return None


def _get_logical_cpu_count():
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
    if cpu_count is not None and cpu_count < 1:
        return None
    return cpu_count


def _collect_system_metadata(metadata):
    metadata['platform'] = platform.platform(True, False)
    if sys.platform.startswith('linux'):
        _collect_linux_metadata(metadata)

    # CPU count
    cpu_count = _get_logical_cpu_count()
    if cpu_count:
        metadata['cpu_count'] = str(cpu_count)

    # CPU affinity
    cpus = _get_cpu_affinity()
    if cpus is not None and cpu_count:
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


def _get_cpu_boost(cpu):
    if not _get_cpu_boost.working:
        return

    env = dict(os.environ, LC_ALL='C')
    args = ['cpupower', '-c', str(cpu), 'frequency-info']
    proc = subprocess.Popen(args,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            universal_newlines=True,
                            env=env)
    stdout = proc.communicate()[0]
    if proc.returncode != 0:
        # if the command failed once, never try it again
        # (consider that the command is not installed or does not work)
        _get_cpu_boost.working = False
        return None

    boost = False
    for line in stdout.splitlines():
        if boost:
            if 'Active:' in line:
                value = line.split(':', 1)[-1].strip()
                if value == 'no':
                    return False
                if value == 'yes':
                    return True
                raise ValueError("unable to parse: %r" % line)
        elif 'boost state support' in line:
            boost = True

    raise ValueError("unable to parse cpupower output: %r" % stdout)
_get_cpu_boost.working = True


def _get_cpu_frequencies(cpus):
    cpus = set(cpus)
    cpu_freq = {}
    cpu = None
    for line in _read_proc('cpuinfo'):
        if line.startswith('processor'):
            value = line.split(':', 1)[-1].strip()
            cpu = int(value)
            if cpu not in cpus:
                # skip this CPU
                cpu = None
        elif line.startswith('cpu MHz') and cpu is not None:
            value = line.split(':', 1)[-1].strip()
            if value.endswith('.000'):
                value = value[:-4]
            value = '%s MHz' % value

            boost = _get_cpu_boost(cpu)
            if boost:
                value += ' (boost)'

            cpu_freq[cpu] = value
    return cpu_freq


def collect_run_metadata(metadata):
    date = datetime.datetime.now().isoformat()
    # FIXME: move date to a regular Run attribute with type datetime.datetime?
    metadata['date'] = date.split('.', 1)[0]

    # On Linux, load average over 1 minute
    for line in _read_proc("loadavg"):
        loadavg = line.split()[0]
        metadata['load_avg_1min'] = loadavg

    cpus = _get_cpu_affinity()
    if not cpus:
        cpus = _get_logical_cpu_count()
    if cpus:
        cpu_freq = _get_cpu_frequencies(cpus)
    else:
        cpu_freq = None
    if cpu_freq:
        merge = (len(set(cpu_freq[cpu] for cpu in cpus)) == 1)
        if not merge:
            text = []
            for cpu in cpus:
                freq = cpu_freq[cpu]
                text.append('%s:%s' % (cpu, freq))
            text = ', '.join(text)
        else:
            # compact output if all CPUs have the same frequency
            cpu = list(cpus)[0]
            freq = cpu_freq[cpu]
            cpus = perf._format_cpu_list(cpus)
            text = '%s:%s' % (cpus, freq)
        metadata['cpu_freq'] = text


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
