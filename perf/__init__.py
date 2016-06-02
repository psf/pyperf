import sys


__version__ = '0.2'


def _import_json():
    """Import json module on demand."""
    global json
    if json is None:
        import json
    return json
json = None


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
            self._formatter = _format_run_result

    def format(self, verbose=False):
        if self.runs:
            samples = []
            first_run = self.runs[0]
            warmup = len(first_run.warmups)
            nrun = len(first_run.samples)
            loops = first_run.loops
            for run in self.runs:
                # FIXME: handle the case where samples is empty
                samples.extend(run.samples)
                if loops is not None and run.loops != loops:
                    loops = None
                run_nrun = len(run.samples)
                if nrun is not None and nrun != run_nrun:
                    nrun = None
                run_warmup = len(run.warmups)
                if warmup is not None and warmup != run_warmup:
                    warmup = None

            iterations = []
            nprocess = len(self.runs)
            if nprocess > 1:
                iterations.append(_format_number(nprocess, 'process', 'processes'))
            if nrun:
                text = _format_number(nrun, 'run')
                if verbose and warmup:
                    text = '%s (warmup: %s)' % (text, warmup)
                iterations.append(text)
            if loops:
                iterations.append(_format_number(loops, 'loop'))

            text = self._formatter(samples, verbose)
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
    def __init__(self, samples=None, warmups=None, loops=None, formatter=None):
        if not(loops is None or (isinstance(loops, int) and loops >= 0)):
            raise TypeError("loops must be an int >= 0 or None")
        if (samples is not None
        and any(not(isinstance(value, float) and value >= 0)
                for value in samples)):
            raise TypeError("samples must be a list of float >= 0")
        if (warmups is not None
        and any(not(isinstance(value, float) and value >= 0)
                for value in warmups)):
            raise TypeError("warmups must be a list of float >= 0")

        self.samples = []
        if samples is not None:
            self.samples.extend(samples)
        self.loops = loops
        self.warmups = []
        if warmups is not None:
            self.warmups.extend(warmups)
        if formatter is not None:
            self._formatter = formatter
        else:
            self._formatter = _format_run_result

    def format(self, verbose=False):
        return self._formatter(self.samples, verbose)

    def __str__(self):
        return self.format()

    @classmethod
    def from_json(cls, text):
        json = _import_json()
        data = json.loads(text)
        if 'run_result' not in data:
            raise ValueError("JSON doesn't contain run_result")
        data = data['run_result']

        version = data.get('version', '')
        if version != 1:
            raise ValueError("version %r not supported" % version)

        samples = data['samples']
        warmups = data['warmups']
        loops = data.get('loops', None)
        return cls(loops=loops, samples=samples, warmups=warmups)

    def json(self):
        json = _import_json()
        data = {'version': 1,
                'samples': self.samples,
                'warmups': self.warmups}
        if self.loops is not None:
            data['loops'] = self.loops
        # FIXME: export formatter
        return json.dumps({'run_result': data})
