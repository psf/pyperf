import contextlib
import io
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

import perf


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


def benchmark_as_json(benchmark):
    with tempfile.NamedTemporaryFile('r') as tmp:
        perf.Benchmark.dump(benchmark, tmp.name)
        tmp.seek(0)
        return tmp.read()
