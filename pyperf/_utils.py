from __future__ import division, print_function, absolute_import

import contextlib
import datetime
import math
import os
import sys

import six
import statistics

if sys.version_info < (3, 4):
    try:
        import fcntl
    except ImportError:
        fcntl = None

try:
    from shlex import quote as shell_quote   # noqa
except ImportError:
    # Python 2
    from pipes import quote as shell_quote   # noqa


MS_WINDOWS = (sys.platform == 'win32')

if MS_WINDOWS:
    import msvcrt


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
        raise ValueError("different number of values")
    error = pooled_sample_variance(sample1, sample2) / len(sample1)
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


def python_implementation():
    if hasattr(sys, 'implementation'):
        # PEP 421, Python 3.3
        name = sys.implementation.name
    else:
        # Code extracted from platform.python_implementation().
        # Don't import platform to avoid the subprocess import.
        sys_version = sys.version
        if 'IronPython' in sys_version:
            name = 'IronPython'
        elif sys.platform.startswith('java'):
            name = 'Jython'
        elif "PyPy" in sys_version:
            name = "PyPy"
        else:
            name = 'CPython'
    return name.lower()


def python_has_jit():
    if python_implementation() == 'pypy':
        return sys.pypy_translation_info["translation.jit"]

    return False


@contextlib.contextmanager
def popen_killer(proc):
    try:
        yield
    except:   # noqa: E722
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


def popen_communicate(proc):
    with popen_killer(proc):
        return proc.communicate()


def get_python_names(python1, python2):
    # FIXME: merge with format_filename_func() of __main__.py
    name1 = os.path.basename(python1)
    name2 = os.path.basename(python2)
    if name1 != name2:
        return (name1, name2)

    return (python1, python2)


_which = None


def which(*args, **kw):
    # Wrapper to which() to use lazy import for 'import shutil'
    global _which

    if _which is None:
        try:
            # Python 3.3
            from shutil import which as _which
        except ImportError:
            # Backport shutil.which() from Python 3.6,
            # comments/docstring stripped
            def _which(cmd, mode=os.F_OK | os.X_OK, path=None):
                def _access_check(fn, mode):
                    return (os.path.exists(fn) and os.access(fn, mode)
                            and not os.path.isdir(fn))

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
                    if os.curdir not in path:
                        path.insert(0, os.curdir)

                    pathext = os.environ.get("PATHEXT", "").split(os.pathsep)
                    if any(cmd.lower().endswith(ext.lower()) for ext in pathext):
                        files = [cmd]
                    else:
                        files = [cmd + ext for ext in pathext]
                else:
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

    return _which(*args, **kw)


def abs_executable(python):
    orig_python = python

    # Replace "~" with the user home directory
    python = os.path.expanduser(python)

    if os.path.dirname(python):
        # Get the absolute path to the directory of the program.
        #
        # Don't try to get the absolute path to the program, because symlink
        # must not be followed. The venv module of Python can use a symlink for
        # the "python" executable of the virtual environment. Running the
        # symlink adds the venv to sys.path, whereas running the real program
        # doesn't.
        path, python = os.path.split(python)
        path = os.path.realpath(path)
        python = os.path.join(path, python)
    else:
        python = which(python)
    if not python:
        print("ERROR: Unable to locate the Python executable: %r" % orig_python)
        sys.exit(1)

    return os.path.normpath(python)


def create_environ(inherit_environ, locale):
    env = {}

    copy_env = ["PATH", "HOME", "TEMP", "COMSPEC", "SystemRoot", "SystemDrive"]
    if locale:
        copy_env.extend(('LANG', 'LC_ADDRESS', 'LC_ALL', 'LC_COLLATE',
                         'LC_CTYPE', 'LC_IDENTIFICATION', 'LC_MEASUREMENT',
                         'LC_MESSAGES', 'LC_MONETARY', 'LC_NAME', 'LC_NUMERIC',
                         'LC_PAPER', 'LC_TELEPHONE', 'LC_TIME'))
    if inherit_environ:
        copy_env.extend(inherit_environ)

    for name in copy_env:
        if name in os.environ:
            env[name] = os.environ[name]
    return env


if MS_WINDOWS:
    if hasattr(os, 'set_handle_inheritable'):
        # Python 3.4 and newer
        set_handle_inheritable = os.set_handle_inheritable
    else:
        import ctypes
        from ctypes import WinError

        HANDLE_FLAG_INHERIT = 1
        SetHandleInformation = ctypes.windll.kernel32.SetHandleInformation

        def set_handle_inheritable(handle, inheritable):
            flags = HANDLE_FLAG_INHERIT if inheritable else 0

            ok = SetHandleInformation(handle, HANDLE_FLAG_INHERIT, flags)
            if not ok:
                raise WinError()
else:
    if hasattr(os, 'set_inheritable'):
        set_inheritable = os.set_inheritable
    elif fcntl is not None:
        def set_inheritable(fd, inheritable):
            flags = fcntl.fcntl(fd, fcntl.F_GETFD)
            if inheritable:
                flags &= ~fcntl.FD_CLOEXEC
            else:
                flags |= fcntl.FD_CLOEXEC
            fcntl.fcntl(fd, fcntl.F_SETFD, flags)
    else:
        set_inheritable = None


class _Pipe(object):
    _OPEN_MODE = "r"

    def __init__(self, fd):
        self._fd = fd
        self._file = None
        if MS_WINDOWS:
            self._handle = msvcrt.get_osfhandle(fd)

    @property
    def fd(self):
        return self._fd

    def close(self):
        fd = self._fd
        self._fd = None
        file = self._file
        self._file = None

        if file is not None:
            file.close()
        elif fd is not None:
            os.close(fd)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class ReadPipe(_Pipe):
    def open_text(self):
        if six.PY3:
            file = open(self._fd, "r", encoding="utf8")
        else:
            file = os.fdopen(self._fd, "r")
        self._file = file
        return file


class WritePipe(_Pipe):
    def to_subprocess(self):
        if MS_WINDOWS:
            set_handle_inheritable(self._handle, True)
            arg = self._handle
        else:
            set_inheritable(self._fd, True)
            arg = self._fd
        return str(arg)

    @classmethod
    def from_subprocess(cls, arg):
        arg = int(arg)
        if MS_WINDOWS:
            fd = msvcrt.open_osfhandle(arg, os.O_WRONLY)
        else:
            fd = arg
        return cls(fd)

    def open_text(self):
        if six.PY3:
            file = open(self._fd, "w", encoding="utf8")
        else:
            file = os.fdopen(self._fd, "w")
        self._file = file
        return file


def create_pipe():
    rfd, wfd = os.pipe()
    # On Windows, os.pipe() creates non-inheritable handles
    if not MS_WINDOWS:
        set_inheritable(rfd, False)
        set_inheritable(wfd, False)

    rpipe = ReadPipe(rfd)
    wpipe = WritePipe(wfd)
    return (rpipe, wpipe)


def median_abs_dev(values):
    # Median Absolute Deviation
    median = float(statistics.median(values))
    return statistics.median([abs(median - sample) for sample in values])


def percentile(values, p):
    if not isinstance(p, float) or not(0.0 <= p <= 1.0):
        raise ValueError("p must be a float in the range [0.0; 1.0]")

    values = sorted(values)
    if not values:
        raise ValueError("no value")

    k = (len(values) - 1) * p
    # Python 3 returns integers: cast explicitly to int
    # to get the same behaviour on Python 2
    f = int(math.floor(k))
    c = int(math.ceil(k))
    if f != c:
        d0 = values[f] * (c - k)
        d1 = values[c] * (k - f)
        return d0 + d1
    else:
        return values[int(k)]
