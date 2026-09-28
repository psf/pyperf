from typing import Literal
from collections.abc import Sequence
import collections
import os
import re

from pyperf._utils import sysfs_path, proc_path, read_first_line, USE_PSUTIL

try:
    if not USE_PSUTIL:
        raise ImportError
    import psutil
except ImportError:
    psutil = None  # type: ignore[assignment]


def get_logical_cpu_count() -> int | None:
    if psutil is not None:
        # Number of logical CPUs
        cpu_count = psutil.cpu_count()
    else:
        # Python 3.4
        # Python 3.13+: capped by -X cpu_count=n or $PYTHON_CPU_COUNT if set
        cpu_count = os.cpu_count()

    if cpu_count is not None and cpu_count < 1:
        return None

    return cpu_count


def format_cpu_list(cpus: Sequence[int]) -> str:
    if len(cpus)==0:
        return "None"
    cpus = sorted(cpus)
    parts = []
    first = cpus[0]
    last = cpus[0]
    for cpu in cpus[1:]:
        if cpu != last + 1:
            if first != last:
                parts.append('%s-%s' % (first, last))
            else:
                parts.append(str(last))
            first = cpu
        last = cpu
    if first != last:
        parts.append('%s-%s' % (first, last))
    else:
        parts.append(str(last))
    return ','.join(parts)


def format_cpu_infos(infos: dict[int, str]) -> list[str]:
    groups = collections.defaultdict(list)
    for cpu, info in infos.items():
        groups[info].append(cpu)

    items = [(cpus, info) for info, cpus in groups.items()]
    items.sort()
    text = []
    for cpus, info in items:
        cpu_str = format_cpu_list(cpus)
        text.append('%s=%s' % (cpu_str, info))
    return text


def parse_cpu_list(cpu_list: str) -> list[int] | None:
    cpu_list = cpu_list.strip(' \x00')
    # /sys/devices/system/cpu/nohz_full returns ' (null)\n' when NOHZ full
    # is not used
    if cpu_list == '(null)':
        return None
    if not cpu_list:
        return None

    cpus = []
    for part in cpu_list.split(','):
        part = part.strip()
        if '-' in part:
            parts = part.split('-', 1)
            first = int(parts[0])
            last = int(parts[1])
            for cpu in range(first, last + 1):
                cpus.append(cpu)
        else:
            cpus.append(int(part))
    cpus.sort()
    return cpus


def parse_cpu_mask(line: str) -> int:
    mask = 0
    for part in line.split(','):
        mask <<= 32
        mask |= int(part, 16)
    return mask


def format_cpu_mask(mask: int) -> str:
    parts = []
    while 1:
        part = "%08x" % (mask & 0xffffffff)
        parts.append(part)
        mask >>= 32
        if not mask:
            break
    return ','.join(reversed(parts))


def format_cpus_as_mask(cpus: Sequence[int]) -> str:
    mask = 0
    for cpu in cpus:
        mask |= (1 << cpu)
    return format_cpu_mask(mask)


def get_isolated_cpus() -> list[int] | None:
    """Get the list of isolated CPUs.

    Return a sorted list of CPU identifiers, or return None if no CPU is
    isolated.
    """
    # The cpu/isolated sysfs was added in Linux 4.2
    # (commit 59f30abe94bff50636c8cad45207a01fdcb2ee49)
    path = sysfs_path('devices/system/cpu/isolated')
    isolated = read_first_line(path)
    if isolated:
        return parse_cpu_list(isolated)

    cmdline = read_first_line(proc_path('cmdline'))
    if cmdline:
        match = re.search(r'\bisolcpus=([^ ]+)', cmdline)
        if match:
            isolated = match.group(1)
            return parse_cpu_list(isolated)

    return None


def set_cpu_affinity(cpus: list[int]) -> Literal[True] | None:
    # Availability: some Unix platforms
    if hasattr(os, 'sched_setaffinity'):
        os.sched_setaffinity(0, cpus)
        return True

    try:
        if not USE_PSUTIL:
            raise ImportError
        import psutil
    except ImportError:
        return None

    # Availability: Linux, Windows, FreeBSD (psutil 2.2.0+)
    # https://psutil.rtfd.io/en/latest/index.html#psutil.Process.cpu_affinity
    proc = psutil.Process()
    if not hasattr(proc, 'cpu_affinity'):
        return None

    proc.cpu_affinity(cpus)
    return True


def set_highest_priority() -> Literal[True] | None:
    try:
        if not USE_PSUTIL:
            raise ImportError
        import psutil
    except ImportError:
        return None

    proc = psutil.Process()
    if not hasattr(proc, 'nice'):
        return None

    # Want to set realtime on Windows.
    # Fail hard for anything else right now, so it is obvious what to fix
    # when adding other OS support.
    try:
        proc.nice(psutil.REALTIME_PRIORITY_CLASS) # type: ignore[attr-defined,unused-ignore]
        return True
    except psutil.AccessDenied:
        pass
    return None
