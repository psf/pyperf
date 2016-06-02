import sys


__version__ = '0.2'

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


def _format_timedelta(values):
    if any(dt < 0 for dt in values):
        raise ValueError("numbers must be positive")

    ref_value = values[0]
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


def _format_timedeltas(values, verbose):
    numbers = [mean(values)]
    with_stdev = (len(values) >= 2)
    if with_stdev:
        numbers.append(stdev(values))
    if verbose:
        numbers.append(min(values))
        numbers.append(max(values))

    numbers = _format_timedelta(numbers)
    if verbose:
        if with_stdev:
            text = '%s +- %s (min: %s, max: %s)' % numbers
        else:
            text = '%s (min: %s, max: %s)' % numbers
    else:
        if with_stdev:
            text = '%s +- %s' % numbers
        else:
            text = numbers[0]
    return text


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
            self._formatter = formatter
        else:
            self._formatter = _format_timedeltas

    def format(self, verbose=False):
        if self.runs:
            values = []
            first_run = self.runs[0]
            samples = len(first_run.values)
            loops = first_run.loops
            for run in self.runs:
                # FIXME: handle the case where final values is empty
                values.extend(run.values[run.warmup:])
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

            text = self._formatter(values, verbose)
            if iterations:
                text = '%s: %s' % (' x '.join(iterations), text)
        else:
            text = '<no run>'
        if self.name:
            text = '%s: %s' % (self.name, text)
        return text

    def __str__(self):
        return self.format()


class RunResult:
    def __init__(self, values=None, loops=None, warmup=0, formatter=None):
        self.values = []
        if values:
            self.values.extend(values)
        self.loops = loops
        if formatter is not None:
            self._formatter = formatter
        else:
            self._formatter = _format_timedeltas
        self.warmup = warmup

    def format(self, verbose=False):
        values = self.values[self.warmup:]
        return self._formatter(values, verbose)

    def __str__(self):
        return self.format()
