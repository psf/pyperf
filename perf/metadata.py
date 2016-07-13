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

    # timer
    if (hasattr(time, 'perf_counter')
       and perf.perf_counter == time.perf_counter):

        info = time.get_clock_info('perf_counter')
        metadata['timer'] = ('%s, resolution: %s'
                             % (info.implementation,
                                perf._format_timedelta(info.resolution)))
    elif perf.perf_counter == time.clock:
        metadata['timer'] = 'time.clock()'
    elif perf.perf_counter == time.time:
        metadata['timer'] = 'time.time()'



def _open_text(path):
    if six.PY3:
        return open(path, encoding="utf-8")
    else:
        return open(path)


def _first_line(path, default=None):
    try:
        fp = _open_text(path)
        try:
            line = fp.readline()
        finally:
            fp.close()
        return line.rstrip()
    except IOError:
        if default is not None:
            return default
        raise

def _read_proc(path):
    path = os.path.join('/proc', path)
    try:
        fp = _open_text(path)
        try:
            for line in fp:
                yield line.rstrip()
        finally:
            fp.close()
    except (OSError, IOError):
        return


def _sys_path(path):
    return os.path.join("/sys", path)


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

    # on linux, load average over 1 minute
    for line in _read_proc("loadavg"):
        loadavg = line.split()[0]
        metadata['load_avg_1min'] = loadavg

    # Hostname
    hostname = socket.gethostname()
    _add(metadata, 'hostname', hostname)


def _get_cpu_frequencies(cpus):
    sys_path = _sys_path("devices/system/cpu")

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
            value = float(value)
            value = int(round(value))
            value = '%s MHz' % value

            info = []

            path = os.path.join(sys_path, "cpu%s/cpufreq/scaling_driver" % cpu)
            scaling_driver = _first_line(path, default='')
            if scaling_driver:
                info.append('driver:%s' % scaling_driver)

            path = os.path.join(sys_path, "cpu%s/cpufreq/scaling_governor" % cpu)
            scaling_governor = _first_line(path, default='')
            if scaling_governor:
                info.append('governor:%s' % scaling_governor)

            if info:
                value += ' (%s)' % ', '.join(info)

            cpu_freq[cpu] = value
    return cpu_freq


def _get_cpu_temperature(path, cpu_temp):
    hwmon_name = _first_line(os.path.join(path, 'name'), default='')
    if not hwmon_name.startswith('coretemp'):
        return

    index = 1
    while True:
        template = os.path.join(path, "temp%s_%%s" % index)

        try:
            temp_label = _first_line(template % 'label')
        except IOError:
            break

        temp_input = _first_line(template % 'input')
        temp_input = float(temp_input) / 1000
        # FIXME: On Python 2, u"%.0f\xb0C" introduces unicode errors if the
        # locale encoding is ASCII
        temp_input = "%.0f C" % temp_input

        item = '%s:%s=%s' % (hwmon_name, temp_label, temp_input)
        cpu_temp.append(item)

        index += 1


def _get_cpu_temperatures():
    path = _sys_path("class/hwmon")
    try:
        names = os.listdir(path)
    except OSError:
        return None

    cpu_temp = []
    for name in names:
        hwmon = os.path.join(path, name)
        _get_cpu_temperature(hwmon, cpu_temp)
    if not cpu_temp:
        return None
    return ', '.join(cpu_temp)


def _collect_cpu_metadata(metadata):
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

    # cpu_freq
    cpus = _get_cpu_affinity()
    if not cpus:
        cpus = _get_logical_cpu_count()
    if cpus:
        cpu_freq = _get_cpu_frequencies(cpus)
    else:
        cpu_freq = none
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

    cpu_temp = _get_cpu_temperatures()
    if cpu_temp:
        metadata['cpu_temp'] = cpu_temp


def _collect_metadata(metadata):
    metadata['perf_version'] = perf.__version__

    date = datetime.datetime.now().isoformat()
    # fixme: move date to a regular run attribute with type datetime.datetime?
    metadata['date'] = date.split('.', 1)[0]

    _collect_python_metadata(metadata)
    _collect_system_metadata(metadata)
    _collect_cpu_metadata(metadata)
