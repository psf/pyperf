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


_TIMEDELTA_UNITS = ('sec', 'ms', 'us', 'ns')


def _format_timedelta(seconds, stdev=None):
    if seconds < 0:
        raise ValueError("seconds must be positive")
    if stdev is not None and stdev < 0:
        raise ValueError("stdev must be positive")

    for i in range(2, -9, -1):
        if seconds >= 10.0 ** i:
            break
    else:
        i = -9

    precision = 2 - i % 3
    k = -(i // 3) if i < 0 else 0
    factor = 10 ** (k * 3)
    unit = _TIMEDELTA_UNITS[k]
    fmt = "%%.%sf %s" % (precision, unit)

    text = fmt % (seconds * factor,)
    if stdev is not None:
        text = "%s +- %s" % (text, fmt % (stdev * factor,))
    return text


def _format_timedeltas(values):
    value = mean(values)
    if len(values) >= 2:
        dev = stdev(values)
    else:
        dev = None
    return _format_timedelta(value, dev)


def _format_number(number, unit):
    plural = (abs(number) > 1)
    if number >= 10000:
        pow10 = 0
        x = number
        while x >= 10:
            x, digit = divmod(x, 10)
            if digit != 0:
                break
            pow10 += 1
        if x == 1 and digit == 0:
            number = '10^%s' % pow10

    # FIXME: add min and max
    if plural:
        return '%s %ss' % (number, unit)
    else:
        return '%s %s' % (number, unit)


class Results:
    def __init__(self, runs=None, name=None, metadata=None, formatter=None):
        if runs is not None:
            self.runs = runs
        else:
            self.runs = []
        self.name = name
        # Raw metadata dictionary, key=>value, keys and values are non-empty
        # strings
        if metadata is not None:
            self.metadata = metadata
        else:
            self.metadata = {}
        if formatter is not None:
            self.formatter = formatter
        else:
            self.formatter = _format_timedeltas

    def __str__(self):
        if self.runs:
            values = []
            first_run = self.runs[0]
            samples = len(first_run.values)
            loops = first_run.loops
            for run in self.runs:
                values.extend(run.values)
                if loops is not None and run.loops != loops:
                    loops = None
                run_samples = len(run.values)
                if samples is not None and samples != run_samples:
                    samples = None

            iterations = []
            nrun = len(self.runs)
            if nrun > 1:
                iterations.append(_format_number(nrun, 'run'))
            if samples:
                iterations.append(_format_number(samples, 'sample'))
            if loops:
                iterations.append(_format_number(loops, 'loop'))

            text = self.formatter(values)
            if iterations:
                text = '%s: %s' % (' x '.join(iterations), text)
        else:
            text = '<no run>'
        if self.name:
            text = '%s: %s' % (self.name, text)
        return text


class RunResult:
    def __init__(self, values=None, loops=None, formatter=None):
        self.values = []
        if values:
            self.values.extend(values)
        self.loops = loops
        if formatter is not None:
            self.formatter = formatter
        else:
            self.formatter = _format_timedeltas
        # FIXME: skip warmup iterations

    def __str__(self):
        return self.formatter(self.values)
