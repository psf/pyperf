import sys


__version__ = '0.1'

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
    import math

    def mean(data):
        if not data:
            raise ValueError("data must be non-empty")
        return float(sum(data)) / len(data)

    def stdev(data):
        data = [float(value) for value in data]
        n = len(data)
        if n < 2:
            raise ValueError('stdev requires at least two data points')

        c = mean(data)

        total = sum((x - c) ** 2 for x in data)
        total2 = sum((x - c) for x in data)
        ss = total - total2**2 / n
        variance = ss / (n - 1)

        return math.sqrt(variance)


# FIXME: simplify this code
_FORMAT_DELTA = (
    # sec
    (100.0,    1, "%.0f sec", "%.0f sec +- %.0f sec"),
    (10.0,     1, "%.1f sec", "%.1f sec +- %.1f sec"),
    (1.0,      1, "%.2f sec", "%.2f sec +- %.2f sec"),
    # ms
    (100e-3, 1e3, "%.0f ms", "%.0f ms +- %.0f ms"),
    (10e-3,  1e3, "%.1f ms", "%.1f ms +- %.1f ms"),
    (1e-3,   1e3, "%.2f ms", "%.2f ms +- %.2f ms"),
    # us
    (100e-6, 1e6, "%.0f us", "%.0f us +- %.0f us"),
    (10e-6,  1e6, "%.1f us", "%.1f us +- %.1f us"),
    (1e-6,   1e6, "%.2f us", "%.2f us +- %.2f us"),
    # ns
    (100e-9, 1e9, "%.0f ns", "%.0f ns +- %.0f ns"),
    (10e-9,  1e9, "%.1f ns", "%.1f ns +- %.1f ns"),
    (1e-9,   1e9, "%.2f ns", "%.2f ns +- %.2f ns"),
)


def format_timedelta(seconds, stdev=None):
    for min_dt, factor, fmt, fmt_stdev in _FORMAT_DELTA:
        if seconds >= min_dt:
            break

    if stdev is not None:
        return fmt_stdev % (seconds * factor, stdev * factor)
    else:
        return fmt % (seconds * factor,)


class Result:
    def __init__(self, values=None, name=None, metadata=None):
        self.values = []
        if values:
            self.values.extend(values)
        self.name = name
        # Raw metadata dictionary, key=>value, keys and values are non-empty
        # strings
        if metadata is not None:
            self.metadata = metadata
        else:
            self.metadata = {}

    def mean(self):
        return mean(self.values)

    def stdev(self):
        return stdev(self.values)

    def _format(self):
        text = str(self.mean())
        if len(self.values) >= 2:
            text = "%s +- %s" % (text, self.stdev())
        return text

    def __str__(self):
        text = self._format()
        if self.name:
            text = '%s: %s' % (self.name, text)
        return text

    def merge_result(self, result):
        self.values.extend(result.values)
        if self.name is None:
            self.name = result.name
        self.metadata.update(result.metadata)
