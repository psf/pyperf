from __future__ import print_function
import math
import sys


__version__ = '0.3'
_PY3 = (sys.version_info >= (3,))


def _import_json():
    """Import json module on demand."""
    global json
    if json is None:
        import json
    return json
json = None


def _import_subprocess():
    """Import subprocess module on demand."""
    global subprocess
    if subprocess is None:
        import subprocess
    return subprocess
subprocess = None


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

    def mean(seq):
        if not seq:
            raise ValueError("sequence seq must be non-empty")
        return float(sum(seq)) / len(seq)

    def stdev(seq):
        seq = [float(value) for value in seq]
        if len(seq) < 2:
            raise ValueError('stdev requires at least two data points')

        c = mean(seq)
        squares = ((x - c) ** 2 for x in seq)
        return math.sqrt(sum(squares) / (len(seq) - 1))


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


# FIXME: put this code into RunResult, and pass _format_timedeltas as formatter
# to RunResult
def _format_run_result(values, verbose=0):
    numbers = [mean(values)]
    with_stdev = (len(values) >= 2)
    if with_stdev:
        numbers.append(stdev(values))
    if verbose > 1:
        numbers.append(min(values))
        numbers.append(max(values))

    numbers = _format_timedeltas(numbers)
    if verbose > 1:
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


def _format_number(number, unit=None, units=None):
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

    if not unit:
        return str(number)

    if plural:
        if not units:
            units = unit + 's'
        return '%s %s' % (number, units)
    else:
        return '%s %s' % (number, unit)


def _common_metadata(metadatas):
    if not metadatas:
        return dict()

    metadata = dict(metadatas[0])
    for run_metadata in metadatas[1:]:
        for key, run_value in run_metadata.items():
            try:
                value = metadata[key]
            except KeyError:
                pass
            else:
                if run_value != value:
                    del metadata[key]
    return metadata


class Benchmark:
    def __init__(self, runs=None, name=None):
        if runs is not None:
            self.runs = runs
        else:
            self.runs = []
        self.name = name
        # FIXME: make the formatter configurable
        self._formatter = _format_run_result

    def get_samples(self):
        samples = []
        for run in self.runs:
            samples.extend(run.samples)
        return samples

    def get_metadata(self):
        metadatas = [run.metadata for run in self.runs]
        return _common_metadata(metadatas)

    def format(self, verbose=0):
        if self.runs:
            first_run = self.runs[0]
            warmup = len(first_run.warmups)
            nsample = len(first_run.samples)
            for run in self.runs:
                run_nsample = len(run.samples)
                if nsample is not None and nsample != run_nsample:
                    nsample = None
                run_warmup = len(run.warmups)
                if warmup is not None and warmup != run_warmup:
                    warmup = None

            # FIXME: handle the case where all samples are empty
            samples = self.get_samples()
            text = self._formatter(samples, verbose)

            if verbose:
                iterations = []
                nrun = len(self.runs)
                if nrun > 1:
                    iterations.append(_format_number(nrun, 'run'))
                if nsample:
                    iterations.append(_format_number(nsample, 'sample'))
                iterations = ' x '.join(iterations)
                if warmup:
                    iterations += '; %s' % _format_number(warmup, 'warmup')
                if iterations:
                    text = '%s (%s)' % (text, iterations)
        else:
            text = '<no run>'
        return text

    def __str__(self):
        text = self.format()
        if self.name:
            text = '%s: %s' % (self.name, text)
        return text

    @classmethod
    def _json_load(cls, data):
        version = data.get('version')
        if version != 1:
            raise ValueError("version %r not supported" % version)

        if 'results' not in data:
            raise ValueError("JSON doesn't contain results")
        data = data['results']

        runs = [RunResult._json_load(run) for run in data['runs']]
        name = data.get('name')

        return cls(runs=runs, name=name)

    @classmethod
    def json_load_from(cls, file):
        json = _import_json()
        data = json.load(file)
        return cls._json_load(data)

    @classmethod
    def json_load(cls, text):
        json = _import_json()
        data = json.loads(text)
        return cls._json_load(data)

    def _as_json(self):
        runs = [run._as_json() for run in self.runs]
        data = {'runs': runs}
        if self.name:
            data['name'] = self.name
        return {'results': data, 'version': 1}

    def json(self):
        json = _import_json()
        return json.dumps(self._as_json()) + '\n'

    def json_dump_into(self, file):
        json = _import_json()
        json.dump(self._as_json(), file)
        file.write('\n')


class RunResult:
    def __init__(self, samples=None, warmups=None):
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
        self.warmups = []
        if warmups is not None:
            self.warmups.extend(warmups)
        # FIXME: make the formatter configurable
        self._formatter = _format_run_result

        # Metadata dictionary: key=>value, keys and values are non-empty
        # strings
        self.metadata = {}

    def _format_sample(self, sample, verbose=False):
        return self._formatter([sample], verbose)

    def format(self, verbose=False):
        return self._formatter(self.samples, verbose)

    def __str__(self):
        return self.format()

    @classmethod
    def _json_load(cls, data):
        version = data.get('version')
        if version != 1:
            raise ValueError("version %r not supported" % version)

        if 'run_result' not in data:
            raise ValueError("JSON doesn't contain run_result")
        data = data['run_result']

        samples = data['samples']
        warmups = data['warmups']
        metadata = data.get('metadata')

        run = cls(samples=samples, warmups=warmups)
        run.metadata = metadata
        return run

    @classmethod
    def json_load_from(cls, file):
        json = _import_json()
        data = json.load(file)
        return cls._json_load(data)

    @classmethod
    def json_load(cls, text):
        json = _import_json()
        data = json.loads(text)
        return cls._json_load(data)

    @classmethod
    def from_subprocess(cls, args, **kwargs):
        subprocess = _import_subprocess()

        proc = subprocess.Popen(args,
                                stdout=subprocess.PIPE,
                                universal_newlines=True,
                                **kwargs)

        if _PY3:
            with proc:
                stdout, stderr = proc.communicate()
        else:
            stdout, stderr = proc.communicate()

        if proc.returncode:
            sys.stdout.write(stdout)
            sys.stdout.flush()
            sys.stderr.write(stderr)
            sys.stderr.flush()
            raise RuntimeError("%s with with exit code %s"
                               % (args[0], proc.returncode))

        return cls.json_load(stdout)

    def _as_json(self):
        data = {'samples': self.samples,
                'warmups': self.warmups,
                'metadata': self.metadata}
        return {'run_result': data, 'version': 1}

    def json(self):
        json = _import_json()
        return json.dumps(self._as_json()) + '\n'

    def json_dump_into(self, file):
        json = _import_json()
        json.dump(self._as_json(), file)
        file.write('\n')


def _very_verbose_run(run):
    # FIXME: use run.formatter
    text = ', '.join(_format_timedeltas(run.samples))
    text = 'samples (%s): %s' % (len(run.samples), text)
    if run.warmups:
        text = ('warmup (%s): %s; %s'
                % (len(run.warmups),
                   ', '.join(_format_timedeltas(run.warmups)),
                   text))
    return text


def _display_metadata(metadata, file=None, header="Metadata:"):
    if not metadata:
        return
    print(header, file=file)
    for key, value in sorted(metadata.items()):
        print("- %s: %s" % (key, value), file=file)
    print(file=file)


# A table of 95% confidence intervals for a two-tailed t distribution, as a
# function of the degrees of freedom. For larger degrees of freedom, we
# approximate. While this may look less elegant than simply calculating the
# critical value, those calculations suck. Look at
# http://www.math.unb.ca/~knight/utility/t-table.htm if you need more values.
_T_DIST_95_CONF_LEVELS = [0, 12.706, 4.303, 3.182, 2.776,
                          2.571, 2.447, 2.365, 2.306, 2.262,
                          2.228, 2.201, 2.179, 2.160, 2.145,
                          2.131, 2.120, 2.110, 2.101, 2.093,
                          2.086, 2.080, 2.074, 2.069, 2.064,
                          2.060, 2.056, 2.052, 2.048, 2.045,
                          2.042]


def _tdist95conf_level(df):
    """Approximate the 95% confidence interval for Student's T distribution.

    Given the degrees of freedom, returns an approximation to the 95%
    confidence interval for the Student's T distribution.

    Args:
        df: An integer, the number of degrees of freedom.

    Returns:
        A float.
    """
    df = int(round(df))
    highest_table_df = len(_T_DIST_95_CONF_LEVELS)
    if df >= 200:
        return 1.960
    if df >= 100:
        return 1.984
    if df >= 80:
        return 1.990
    if df >= 60:
        return 2.000
    if df >= 50:
        return 2.009
    if df >= 40:
        return 2.021
    if df >= highest_table_df:
        return _T_DIST_95_CONF_LEVELS[highest_table_df - 1]
    return _T_DIST_95_CONF_LEVELS[df]


def _pooled_sample_variance(sample1, sample2):
    """Find the pooled sample variance for two samples.

    Args:
        sample1: one sample.
        sample2: the other sample.

    Returns:
        Pooled sample variance, as a float.
    """
    deg_freedom = len(sample1) + len(sample2) - 2
    mean1 = mean(sample1)
    squares1 = ((x - mean1) ** 2 for x in sample1)
    mean2 = mean(sample2)
    squares2 = ((x - mean2) ** 2 for x in sample2)

    return (sum(squares1) + sum(squares2)) / float(deg_freedom)


def _tscore(sample1, sample2):
    """Calculate a t-test score for the difference between two samples.

    Args:
        sample1: one sample.
        sample2: the other sample.

    Returns:
        The t-test score, as a float.
    """
    assert len(sample1) == len(sample2)
    error = _pooled_sample_variance(sample1, sample2) / len(sample1)
    return (mean(sample1) - mean(sample2)) / math.sqrt(error * 2)


def is_significant(sample1, sample2):
    """Determine whether two samples differ significantly.

    This uses a Student's two-sample, two-tailed t-test with alpha=0.95.

    Args:
        sample1: one sample.
        sample2: the other sample.

    Returns:
        (significant, t_score) where significant is a bool indicating whether
        the two samples differ significantly; t_score is the score from the
        two-sample T test.
    """
    deg_freedom = len(sample1) + len(sample2) - 2
    critical_value = _tdist95conf_level(deg_freedom)
    t_score = _tscore(sample1, sample2)
    return (abs(t_score) >= critical_value, t_score)
