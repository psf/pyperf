from __future__ import division, print_function, absolute_import

import collections
import datetime
import os
import platform
import socket
import subprocess
import sys
import time
try:
    import resource
except ImportError:
    resource = None

import six
try:
    # Optional dependency
    import psutil
except ImportError:
    psutil = None

import perf
from perf._utils import (format_timedelta, format_cpu_list,
                         get_isolated_cpus, MS_WINDOWS)
if MS_WINDOWS:
    from perf._win_memory import check_tracking_memory, get_peak_pagefile_usage


def collect_python_metadata(metadata):
    # Implementation
    metadata['python_implementation'] = perf.python_implementation()

    version = platform.python_version()
    bits = platform.architecture()[0]
    if bits:
        version = '%s (%s)' % (version, bits)
    metadata['python_version'] = version
    if sys.executable:
        metadata['python_executable'] = sys.executable

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
                                format_timedelta(info.resolution)))
    elif perf.perf_counter == time.clock:
        metadata['timer'] = 'time.clock()'
    elif perf.perf_counter == time.time:
        metadata['timer'] = 'time.time()'

    # PYTHONHASHSEED
    if os.environ.get('PYTHONHASHSEED'):
        hash_seed = os.environ['PYTHONHASHSEED']
        try:
            if hash_seed != "random":
                hash_seed = int(hash_seed)
        except ValueError:
            pass
        else:
            metadata['python_hash_seed'] = hash_seed


def open_text(path):
    if six.PY3:
        return open(path, encoding="utf-8")
    else:
        return open(path)


def first_line(path, default=None):
    try:
        fp = open_text(path)
        try:
            line = fp.readline()
        finally:
            fp.close()
        return line.rstrip()
    except IOError:
        if default is not None:
            return default
        raise

def read_proc(path):
    path = os.path.join('/proc', path)
    try:
        fp = open_text(path)
        try:
            for line in fp:
                yield line.rstrip()
        finally:
            fp.close()
    except (OSError, IOError):
        return


def sys_path(path):
    return os.path.join("/sys", path)


def collect_linux_metadata(metadata):
    # ASLR
    for line in read_proc('sys/kernel/randomize_va_space'):
        if line == '0':
            metadata['aslr'] = 'No randomization'
        elif line == '1':
            metadata['aslr'] = 'Conservative randomization'
        elif line == '2':
            metadata['aslr'] = 'Full randomization'
        break


def get_cpu_affinity():
    if hasattr(os, 'sched_getaffinity'):
        return os.sched_getaffinity(0)

    if psutil is not None:
        proc = psutil.Process()
        # cpu_affinity() is only available on Linux, Windows and FreeBSD
        if hasattr(proc, 'cpu_affinity'):
            return proc.cpu_affinity()

    return None


def get_logical_cpu_count():
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


def collect_system_metadata(metadata):
    metadata['platform'] = platform.platform(True, False)
    if sys.platform.startswith('linux'):
        collect_linux_metadata(metadata)

    # on linux, load average over 1 minute
    for line in read_proc("loadavg"):
        fields = line.split()
        loadavg = fields[0]
        metadata['load_avg_1min'] = float(loadavg)

        if len(fields) >= 4 and '/' in fields[3]:
            runnable_threads = fields[3].split('/', 1)[0]
            runnable_threads = int(runnable_threads)
            metadata['runnable_threads'] = runnable_threads

    # Hostname
    hostname = socket.gethostname()
    if hostname:
        metadata['hostname'] = hostname


def collect_memory_metadata(metadata):
    if resource is not None:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        max_rss = usage.ru_maxrss
        if max_rss:
            metadata['mem_max_rss'] = max_rss * 1024

    # On Windows, use GetProcessMemoryInfo() if available
    if MS_WINDOWS and not check_tracking_memory():
        usage = get_peak_pagefile_usage()
        if usage:
            metadata['mem_peak_pagefile_usage'] = usage

def get_cpu_boost(cpu):
    if not get_cpu_boost.working:
        return

    env = dict(os.environ, LC_ALL='C')
    args = ['cpupower', '-c', str(cpu), 'frequency-info']
    try:
        proc = subprocess.Popen(args,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                universal_newlines=True,
                                env=env)
        stdout = proc.communicate()[0]
        if proc.returncode != 0:
            # if the command failed once, never try it again
            # (consider that the command is not installed or does not work)
            get_cpu_boost.working = False
            return None
    except OSError:
        get_cpu_boost.working = False
        return None

    # cpupower doesn't seem to work on PPC64LE:
    # see https://github.com/haypo/perf/issues/11
    if 'no or unknown cpufreq driver is active on this CPU' in stdout:
        get_cpu_boost.working = False
        return None

    boost = False
    for line in stdout.splitlines():
        if boost:
            if 'Supported:' in line:
                value = line.split(':', 1)[-1].strip()
                if value == 'no':
                    return False
                if value == 'yes':
                    return True
                raise ValueError("unable to parse: %r" % line)
        elif 'boost state support' in line:
            boost = True

    raise ValueError("unable to parse cpupower output: %r" % stdout)
get_cpu_boost.working = True


def format_cpu_infos(infos):
    groups = collections.defaultdict(list)
    for cpu, info in infos.items():
        groups[info].append(cpu)

    items = [(cpus, info) for info, cpus in  groups.items()]
    items.sort()
    text = []
    for cpus, info in items:
        cpus = format_cpu_list(cpus)
        text.append('%s=%s' % (cpus, info))
    return ', '.join(text)


def collect_cpu_freq(metadata, cpus):
    # Parse /proc/cpuinfo: search for 'cpu MHz' (Intel) or 'clock' (Power8)
    cpu_set = set(cpus)
    cpu_freq = {}
    cpu = None
    for line in read_proc('cpuinfo'):
        if line.startswith('processor'):
            value = line.split(':', 1)[-1].strip()
            cpu = int(value)
            if cpu not in cpu_set:
                # skip this CPU
                cpu = None

        elif line.startswith('cpu MHz') and cpu is not None:
            # Intel: 'cpu MHz : 1261.613'
            mhz = line.split(':', 1)[-1].strip()
            mhz = float(mhz)
            mhz = int(round(mhz))
            cpu_freq[cpu] = '%s MHz' % mhz

        elif line.startswith('clock') and line.endswith('MHz') and cpu is not None:
            # Power8: 'clock : 3425.000000MHz'
            mhz = line[:-3].split(':', 1)[-1].strip()
            mhz = float(mhz)
            mhz = int(round(mhz))
            cpu_freq[cpu] = '%s MHz' % mhz

    if not cpu_freq:
        return

    metadata['cpu_freq'] = format_cpu_infos(cpu_freq)


def get_cpu_config(cpu):
    sys_cpu_path = sys_path("devices/system/cpu")
    info = []

    path = os.path.join(sys_cpu_path, "cpu%s/cpufreq/scaling_driver" % cpu)
    scaling_driver = first_line(path, default='')
    if scaling_driver:
        info.append('driver:%s' % scaling_driver)

    if scaling_driver == 'intel_pstate':
        path = os.path.join(sys_cpu_path, "intel_pstate/no_turbo")
        no_turbo = first_line(path, default='')
        if no_turbo == '1':
            info.append('intel_pstate:no turbo')
        elif no_turbo == '0':
            info.append('intel_pstate:turbo')
    else:
        boost = get_cpu_boost(cpu)
        if boost is not None:
            if boost:
                info.append('boost:supported')
            else:
                info.append('boost:not suppported')

    path = os.path.join(sys_cpu_path, "cpu%s/cpufreq/scaling_governor" % cpu)
    scaling_governor = first_line(path, default='')
    if scaling_governor:
        info.append('governor:%s' % scaling_governor)

    if not info:
        return None

    return ', '.join(info)


def collect_cpu_config(metadata, cpus):
    configs = {}
    for cpu in cpus:
        config = get_cpu_config(cpu)
        if config:
            configs[cpu] = config
    if not configs:
        return
    metadata['cpu_config'] = format_cpu_infos(configs)


def get_cpu_temperature(path, cpu_temp):
    hwmon_name = first_line(os.path.join(path, 'name'), default='')
    if not hwmon_name.startswith('coretemp'):
        return

    index = 1
    while True:
        template = os.path.join(path, "temp%s_%%s" % index)

        try:
            temp_label = first_line(template % 'label')
        except IOError:
            break

        temp_input = first_line(template % 'input')
        temp_input = float(temp_input) / 1000
        # FIXME: On Python 2, u"%.0f\xb0C" introduces unicode errors if the
        # locale encoding is ASCII
        temp_input = "%.0f C" % temp_input

        item = '%s:%s=%s' % (hwmon_name, temp_label, temp_input)
        cpu_temp.append(item)

        index += 1


def collect_cpu_temperatures(metadata):
    path = sys_path("class/hwmon")
    try:
        names = os.listdir(path)
    except OSError:
        return None

    cpu_temp = []
    for name in names:
        hwmon = os.path.join(path, name)
        get_cpu_temperature(hwmon, cpu_temp)
    if not cpu_temp:
        return None

    metadata['cpu_temp'] = ', '.join(cpu_temp)


def collect_cpu_affinity(metadata, cpu_affinity, cpu_count):
    if not cpu_affinity:
        return
    if not cpu_count:
        return

    # CPU affinity
    if set(cpu_affinity) == set(range(cpu_count)):
        return

    isolated = get_isolated_cpus()
    text = format_cpu_list(cpu_affinity)
    if isolated and set(cpu_affinity) <= set(isolated):
        text = '%s (isolated)' % text
    metadata['cpu_affinity'] = text


def collect_cpu_model(metadata):
    for line in read_proc("cpuinfo"):
        if line.startswith('model name'):
            model_name = line.split(':', 1)[1].strip()
            if model_name:
                metadata['cpu_model_name'] = model_name
            break

        if line.startswith('machine'):
            machine = line.split(':', 1)[1].strip()
            if machine:
                metadata['cpu_machine'] = machine
            break


def collect_cpu_metadata(metadata):
    collect_cpu_model(metadata)

    # CPU count
    cpu_count = get_logical_cpu_count()
    if cpu_count:
        metadata['cpu_count'] = cpu_count

    cpu_affinity = get_cpu_affinity()
    collect_cpu_affinity(metadata, cpu_affinity, cpu_count)

    all_cpus = cpu_affinity
    if not all_cpus and cpu_count:
        all_cpus = tuple(range(cpu_count))

    if all_cpus:
        collect_cpu_freq(metadata, all_cpus)
        collect_cpu_config(metadata, all_cpus)

    collect_cpu_temperatures(metadata)


def collect_metadata(metadata):
    metadata['perf_version'] = perf.__version__

    date = datetime.datetime.now().isoformat()
    # FIXME: Move date to a regular run attribute with type datetime.datetime?
    metadata['date'] = date.split('.', 1)[0]

    collect_python_metadata(metadata)
    collect_system_metadata(metadata)
    collect_memory_metadata(metadata)
    collect_cpu_metadata(metadata)

    # Note: Don't collect VmPeak of /proc/self/status on Linux because it is
    # not accurate. See perf._memory for more accurate memory metrics.
