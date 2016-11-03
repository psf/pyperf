from __future__ import division, print_function, absolute_import

import collections
import datetime
import math
import os
import platform
import re
import sys

import six
import statistics

try:
    # Optional dependency
    import psutil
except ImportError:
    psutil = None


MS_WINDOWS = (sys.platform == 'win32')

_TIMEDELTA_UNITS = ('sec', 'ms', 'us', 'ns')


def format_timedeltas(values):
    ref_value = abs(values[0])
    for i in range(2, -9, -1):
        if ref_value >= 10.0 ** i:
            break
    else:
        i = -9

    precision = 2 - i % 3
    k = -(i // 3) if i < 0 else 0
    factor = 10 ** (k * 3)
    unit = _TIMEDELTA_UNITS[k]
    fmt = "%%.%sf %s" % (precision, unit)

    return tuple(fmt % (value * factor,) for value in values)


def format_timedelta(value):
    return format_timedeltas((value,))[0]


def format_filesize(size):
    if size < 10 * 1024:
        if size != 1:
            return '%.0f bytes' % size
        else:
            return '%.0f byte' % size

    if size > 10 * 1024 * 1024:
        return '%.1f MB' % (size / (1024.0 * 1024.0))

    return '%.1f kB' % (size / 1024.0)


def format_filesizes(sizes):
    return tuple(format_filesize(size) for size in sizes)


def format_seconds(seconds):
    # Coarse but human readable duration
    if not seconds:
        return '0 sec'

    if seconds < 1.0:
        return format_timedelta(seconds)

    mins, secs = divmod(seconds, 60.0)
    mins = int(mins)
    hours, mins = divmod(mins, 60)
    days, hours = divmod(hours, 24)

    parts = []
    if days:
        parts.append("%.0f day" % days)
    if hours:
        parts.append("%.0f hour" % hours)
    if mins:
        parts.append("%.0f min" % mins)
    if secs and len(parts) <= 2:
        parts.append('%.1f sec' % secs)
    return ' '.join(parts)


def format_number(number, unit=None, units=None):
    plural = (not number or abs(number) > 1)
    if number >= 10000:
        pow10 = 0
        x = number
        while x >= 10:
            x, r = divmod(x, 10)
            pow10 += 1
            if r:
                break
        if not r:
            number = '10^%s' % pow10

    if isinstance(number, int) and number > 8192:
        pow2 = 0
        x = number
        while x >= 2:
            x, r = divmod(x, 2)
            pow2 += 1
            if r:
                break
        if not r:
            number = '2^%s' % pow2

    if not unit:
        return str(number)

    if plural:
        if not units:
            units = unit + 's'
        return '%s %s' % (number, units)
    else:
        return '%s %s' % (number, unit)


def format_integers(numbers):
    return tuple(format_number(number) for number in numbers)


DEFAULT_UNIT = 'second'
UNIT_FORMATTERS = {
    'second': format_timedeltas,
    'byte': format_filesizes,
    'integer': format_integers,
}


def format_samples(unit, samples):
    if not unit:
        unit = DEFAULT_UNIT
    formatter = UNIT_FORMATTERS[unit]
    return formatter(samples)


def format_sample(unit, sample):
    return format_samples(unit, (sample,))[0]


def format_datetime(dt, microsecond=True):
    if not microsecond:
        dt = dt.replace(microsecond=0)
    return dt.isoformat(' ')


def parse_iso8601(date):
    if '.' in date:
        date, floatpart = date.split('.', 1)
        floatpart = float('.' + floatpart)
    else:
        floatpart = 0
    try:
        dt = datetime.datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        dt = datetime.datetime.strptime(date, '%Y-%m-%dT%H:%M:%S')
    dt += datetime.timedelta(seconds=floatpart)
    return dt


# A table of 95% confidence intervals for a two-tailed t distribution, as a
# function of the degrees of freedom. For larger degrees of freedom, we
# approximate. While this may look less elegant than simply calculating the
# critical value, those calculations suck. Look at
# http://www.math.unb.ca/~knight/utility/t-table.htm if you need more values.
_T_DIST_95_CONF_LEVELS = [0, 12.706, 4.303, 3.182, 2.776,
                          2.571, 2.447, 2.365, 2.306, 2.262,
                          2.228, 2.201, 2.179, 2.160, 2.145,
                          2.131, 2.120, 2.110, 2.101, 2.093,
                          2.086, 2.080, 2.074, 2.069, 2.064,
                          2.060, 2.056, 2.052, 2.048, 2.045,
                          2.042]


def tdist95conf_level(df):
    """Approximate the 95% confidence interval for Student's T distribution.

    Given the degrees of freedom, returns an approximation to the 95%
    confidence interval for the Student's T distribution.

    Args:
        df: An integer, the number of degrees of freedom.

    Returns:
        A float.
    """
    df = int(round(df))
    highest_table_df = len(_T_DIST_95_CONF_LEVELS)
    if df >= 200:
        return 1.960
    if df >= 100:
        return 1.984
    if df >= 80:
        return 1.990
    if df >= 60:
        return 2.000
    if df >= 50:
        return 2.009
    if df >= 40:
        return 2.021
    if df >= highest_table_df:
        return _T_DIST_95_CONF_LEVELS[highest_table_df - 1]
    return _T_DIST_95_CONF_LEVELS[df]


def pooled_sample_variance(sample1, sample2):
    """Find the pooled sample variance for two samples.

    Args:
        sample1: one sample.
        sample2: the other sample.

    Returns:
        Pooled sample variance, as a float.
    """
    deg_freedom = len(sample1) + len(sample2) - 2
    # FIXME: use median?
    mean1 = statistics.mean(sample1)
    squares1 = ((x - mean1) ** 2 for x in sample1)
    mean2 = statistics.mean(sample2)
    squares2 = ((x - mean2) ** 2 for x in sample2)

    return (math.fsum(squares1) + math.fsum(squares2)) / float(deg_freedom)


def tscore(sample1, sample2):
    """Calculate a t-test score for the difference between two samples.

    Args:
        sample1: one sample.
        sample2: the other sample.

    Returns:
        The t-test score, as a float.
    """
    if len(sample1) != len(sample2):
        raise ValueError("different number of samples")
    error = pooled_sample_variance(sample1, sample2) / len(sample1)
    # FIXME: use median?
    diff = statistics.mean(sample1) - statistics.mean(sample2)
    return diff / math.sqrt(error * 2)


def is_significant(sample1, sample2):
    """Determine whether two samples differ significantly.

    This uses a Student's two-sample, two-tailed t-test with alpha=0.95.

    Args:
        sample1: one sample.
        sample2: the other sample.

    Returns:
        (significant, t_score) where significant is a bool indicating whether
        the two samples differ significantly; t_score is the score from the
        two-sample T test.
    """
    deg_freedom = len(sample1) + len(sample2) - 2
    critical_value = tdist95conf_level(deg_freedom)
    t_score = tscore(sample1, sample2)
    return (abs(t_score) >= critical_value, t_score)


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


def format_cpu_list(cpus):
    cpus = sorted(cpus)
    parts = []
    first = None
    last = None
    for cpu in cpus:
        if first is None:
            first = cpu
        elif cpu != last + 1:
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


def parse_run_list(run_list):
    run_list = run_list.strip()

    runs = []
    for part in run_list.split(','):
        part = part.strip()
        try:
            if '-' in part:
                parts = part.split('-', 1)
                first = int(parts[0])
                last = int(parts[1])
                for run in range(first, last + 1):
                    runs.append(run)
            else:
                runs.append(int(part))
        except ValueError:
            raise ValueError("invalid list of runs")

    if not runs:
        raise ValueError("empty list of runs")

    if min(runs) < 1:
        raise ValueError("number of runs starts at 1")

    return [run - 1 for run in runs]


def parse_cpu_list(cpu_list):
    cpu_list = cpu_list.strip()
    # /sys/devices/system/cpu/nohz_full returns ' (null)\n' when NOHZ full
    # is not used
    if cpu_list == '(null)':
        return
    if not cpu_list:
        return

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
    return cpus


def open_text(path, write=False):
    mode = "w" if write else "r"
    if six.PY3:
        return open(path, mode, encoding="utf-8")
    else:
        return open(path, mode)


def read_first_line(path, error=False):
    try:
        fp = open_text(path)
        try:
            line = fp.readline()
        finally:
            # don't use context manager to support StringIO on Python 2
            # for unit tests
            fp.close()
        return line.rstrip()
    except IOError:
        if error:
            raise
        else:
            return ''


def proc_path(path):
    return os.path.join("/proc", path)


def sysfs_path(path):
    return os.path.join("/sys", path)


def get_isolated_cpus():
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


def set_cpu_affinity(cpus):
    # Python 3.3 or newer?
    if hasattr(os, 'sched_setaffinity'):
        os.sched_setaffinity(0, cpus)
        return True

    try:
        import psutil
    except ImportError:
        return

    proc = psutil.Process()
    if not hasattr(proc, 'cpu_affinity'):
        return

    proc.cpu_affinity(cpus)
    return True


def python_implementation():
    if hasattr(sys, 'implementation'):
        # PEP 421, Python 3.3
        name = sys.implementation.name
    else:
        name = platform.python_implementation()
    return name.lower()


def python_has_jit():
    if python_implementation() == 'pypy':
        return sys.pypy_translation_info["translation.jit"]

    return False


def popen_communicate(proc):
    try:
        return proc.communicate()
    except:
        # Close pipes
        if proc.stdin:
            proc.stdin.close()
        if proc.stdout:
            proc.stdout.close()
        if proc.stderr:
            proc.stderr.close()
        try:
            proc.kill()
        except OSError:
            # process already terminated
            pass
        proc.wait()
        raise


def get_python_names(python1, python2):
    # FIXME: merge with format_filename_func() of __main__.py
    name1 = os.path.basename(python1)
    name2 = os.path.basename(python2)
    if name1 != name2:
        return (name1, name2)

    return (python1, python2)


try:
    # Python 3.3
    from shutil import which
except ImportError:
    # Backport shutil.which() from Python 3.6
    def which(cmd, mode=os.F_OK | os.X_OK, path=None):
        """Given a command, mode, and a PATH string, return the path which
        conforms to the given mode on the PATH, or None if there is no such
        file.

        `mode` defaults to os.F_OK | os.X_OK. `path` defaults to the result
        of os.environ.get("PATH"), or can be overridden with a custom search
        path.

        """
        # Check that a given file can be accessed with the correct mode.
        # Additionally check that `file` is not a directory, as on Windows
        # directories pass the os.access check.
        def _access_check(fn, mode):
            return (os.path.exists(fn) and os.access(fn, mode)
                    and not os.path.isdir(fn))

        # If we're given a path with a directory part, look it up directly rather
        # than referring to PATH directories. This includes checking relative to the
        # current directory, e.g. ./script
        if os.path.dirname(cmd):
            if _access_check(cmd, mode):
                return cmd
            return None

        if path is None:
            path = os.environ.get("PATH", os.defpath)
        if not path:
            return None
        path = path.split(os.pathsep)

        if sys.platform == "win32":
            # The current directory takes precedence on Windows.
            if os.curdir not in path:
                path.insert(0, os.curdir)

            # PATHEXT is necessary to check on Windows.
            pathext = os.environ.get("PATHEXT", "").split(os.pathsep)
            # See if the given file matches any of the expected path extensions.
            # This will allow us to short circuit when given "python.exe".
            # If it does match, only test that one, otherwise we have to try
            # others.
            if any(cmd.lower().endswith(ext.lower()) for ext in pathext):
                files = [cmd]
            else:
                files = [cmd + ext for ext in pathext]
        else:
            # On other platforms you don't have things like PATHEXT to tell you
            # what file suffixes are executable, so just pass on cmd as-is.
            files = [cmd]

        seen = set()
        for dir in path:
            normdir = os.path.normcase(dir)
            if normdir not in seen:
                seen.add(normdir)
                for thefile in files:
                    name = os.path.join(dir, thefile)
                    if _access_check(name, mode):
                        return name
        return None


def abs_executable(python):
    # Replace "~" with the user home directory
    python = os.path.expanduser(python)
    # Try to the absolute path to the binary
    abs_python = which(python)
    if not abs_python:
        print("ERROR: Unable to locate the Python executable: %r" % python)
        sys.exit(1)

    # Don't follow symlinks. The venv module of Python can use a symlink for
    # the "python" executable of the virtual environment. Running the symlink
    # gets the modules from the venv, running the linked executable doesn't.
    return os.path.normpath(abs_python)


def create_environ(inherit_environ):
    env = {}

    # FIXME: copy the locale? LC_ALL, LANG, LC_*
    copy_env = ["PATH", "HOME", "TEMP", "COMSPEC", "SystemRoot"]
    if inherit_environ:
        copy_env.extend(inherit_environ)

    for name in copy_env:
        if name in os.environ:
            env[name] = os.environ[name]
    return env


def format_cpu_infos(infos):
    groups = collections.defaultdict(list)
    for cpu, info in infos.items():
        groups[info].append(cpu)

    items = [(cpus, info) for info, cpus in groups.items()]
    items.sort()
    text = []
    for cpus, info in items:
        cpus = format_cpu_list(cpus)
        text.append('%s=%s' % (cpus, info))
    return text
