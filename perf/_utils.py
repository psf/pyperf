from __future__ import division, print_function, absolute_import

import datetime
import math
import os
import platform
import sys

import six
import statistics


MS_WINDOWS = (sys.platform == 'win32')


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


if sys.version_info < (3, 4):
    try:
        import fcntl
    except ImportError:
        fcntl = None

    def _set_cloexec(fd):
        if fcntl is None:
            return

        flags = fcntl.fcntl(fd, fcntl.F_GETFD)
        flags |= os.O_CLOEXEC
        fcntl.fcntl(fd, fcntl.F_SETFD, flags)

    def pipe_cloexec():
        rfd, wfd = os.pipe()
        return (rfd, wfd)
else:
    pipe_cloexec = os.pipe

    # In Python 3.4, file descriptors are non-inheritable by default (PEP 446)
