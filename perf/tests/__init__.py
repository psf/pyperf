import contextlib
import io
import shutil
import sys
import tempfile

try:
    from unittest import mock   # Python 3.3
except ImportError:
    import mock   # noqa
try:
    import unittest2 as unittest   # Python 2.7
except ImportError:
    import unittest   # noqa


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


def benchmark_as_json(benchmark, compact=True):
    with tempfile.NamedTemporaryFile('r') as tmp:
        benchmark.dump(tmp.name, compact=compact)
        tmp.seek(0)
        return tmp.read()


def compare_benchmarks(testcase, bench1, bench2):
    json1 = benchmark_as_json(bench1, compact=False)
    json2 = benchmark_as_json(bench2, compact=False)
    testcase.assertEqual(json1, json2)


@contextlib.contextmanager
def temporary_directory():
    tmpdir = tempfile.mkdtemp()
    try:
        yield tmpdir
    finally:
        shutil.rmtree(tmpdir)
