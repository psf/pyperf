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


def _format_timedeltas(values):
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


def _format_timedelta(value):
    return _format_timedeltas((value,))[0]


def _format_run_result(values, verbose=0):
    numbers = [mean(values)]
    with_stdev = (len(values) >= 2)
    if with_stdev:
        numbers.append(stdev(values))
    if verbose:
        numbers.append(min(values))
        numbers.append(max(values))

    numbers = _format_timedeltas(numbers)
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


def _format_number(number, unit, units=None):
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
        if not units:
            units = unit + 's'
        return '%s %s' % (number, units)
    else:
        return '%s %s' % (number, unit)
