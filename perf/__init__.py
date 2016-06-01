import sys


__version__ = '0.0'

# Clocks
try:
    # Python 3.3+ (PEP 418)
    from time import monotonic as monotonic_clock, perf_counter
except ImportError:
    import time

    monotonic_clock = time.time
    if sys.platform == "win32":
        perf_counter = time.clock
    else:
        perf_counter = time.time


# Statistics
try:
    from statistics import mean, stdev as _stdev   # Python 3.4+

    def stdev(data):
        # Wrapper to hide the xbar parameter, to be portable with Python 2
        return _stdev(data)
except ImportError:
    def mean(data):
        if not data:
            raise ValueError("data must be non-empty")
        return float(sum(data)) / len(data)
    def stdev(data):
        # FIXME: implement it for Python < 3.4!
        return 'FIXME'


class Result:
    def __init__(self):
        self.runtimes = []
        # Raw key=>value metadata dictionary, keys and values are strings
        self.metadata = {}
