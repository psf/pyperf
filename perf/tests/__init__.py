import contextlib
import io
import sys


@contextlib.contextmanager
def _capture_stream(name):
    old_stream = getattr(sys, name)
    try:
        stream = io.StringIO()
        setattr(sys, name, stream)
        yield stream
    finally:
        setattr(sys, name, old_stream)


def capture_stdout():
    return _capture_stream('stdout')


def capture_stderr():
    return _capture_stream('stderr')
