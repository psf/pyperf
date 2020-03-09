import collections
import contextlib
import errno
import io
import os
import shutil
import subprocess
import sys
import tempfile

from pyperf._utils import popen_communicate, popen_killer


@contextlib.contextmanager
def _capture_stream(name):
    old_stream = getattr(sys, name)
    try:
        if sys.version_info >= (3,):
            stream = io.StringIO()
        else:
            stream = io.BytesIO()
        setattr(sys, name, stream)
        yield stream
    finally:
        setattr(sys, name, old_stream)


def capture_stdout():
    return _capture_stream('stdout')


def capture_stderr():
    return _capture_stream('stderr')


@contextlib.contextmanager
def temporary_file(**kwargs):
    tmp_filename = tempfile.mktemp(**kwargs)
    try:
        yield tmp_filename
    finally:
        try:
            os.unlink(tmp_filename)
        except OSError as exc:
            if exc.errno != errno.ENOENT:
                raise


@contextlib.contextmanager
def temporary_directory():
    tmpdir = tempfile.mkdtemp()
    try:
        yield tmpdir
    finally:
        shutil.rmtree(tmpdir)


def benchmark_as_json(benchmark, compact=True):
    with temporary_file() as tmp_name:
        benchmark.dump(tmp_name, compact=compact)
        with io.open(tmp_name, 'r', encoding='utf-8') as tmp:
            return tmp.read()


def compare_benchmarks(testcase, bench1, bench2):
    json1 = benchmark_as_json(bench1, compact=False)
    json2 = benchmark_as_json(bench2, compact=False)
    testcase.assertEqual(json1, json2)


ProcResult = collections.namedtuple('ProcResult', 'returncode stdout stderr')


def get_output(cmd, **kw):
    proc = subprocess.Popen(cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            universal_newlines=True,
                            **kw)
    stdout, stderr = popen_communicate(proc)
    return ProcResult(proc.returncode, stdout, stderr)


def run_command(cmd, **kw):
    proc = subprocess.Popen(cmd, **kw)
    with popen_killer(proc):
        proc.wait()
    return proc.returncode
