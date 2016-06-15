from __future__ import print_function
import math
import sys

import statistics   # Python 3.4+, or backport on Python 2.7


__version__ = '0.4'
_PY3 = (sys.version_info >= (3,))
_JSON_VERSION = 1


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


def _import_json():
    """Import json module on demand."""
    global json
    if json is None:
        import json
    return json
json = None


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


class Benchmark(object):
    def __init__(self, name=None, loops=None, inner_loops=None,
                 warmups=1, metadata=None):
        self.name = name
        self.loops = loops
        self.inner_loops = inner_loops
        self.warmups = warmups

        # list of samples where samples are a non-empty tuples
        # of float >= 0, see add_run()
        self._runs = []

        self._clear_stats_cache()

        # Metadata dictionary: key=>value, keys and values are non-empty
        # strings
        if metadata is not None:
            self.metadata = metadata
        else:
            self.metadata = {}

        # FIXME: add a configurable sample formatter
        self._format_samples = _format_timedeltas

    @property
    def warmups(self):
        return self._warmups

    @warmups.setter
    def warmups(self, value):
        if not(isinstance(value, int) and value >= 0):
            raise ValueError("warmups must be an int >= 0")
        self._clear_stats_cache()
        self._warmups = value

    def _formatter(self, values, verbose=0):
        numbers = [statistics.mean(values)]
        with_stdev = (len(values) >= 2)
        if with_stdev:
            numbers.append(statistics.stdev(values))
        if verbose > 1:
            numbers.append(min(values))
            numbers.append(max(values))

        numbers = self._format_samples(numbers)
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

    def _clear_stats_cache(self):
        self._samples = None
        self._mean = None

    def mean(self):
        if self._mean is None:
            self._mean = statistics.mean(self.get_samples())
        return self._mean

    def add_run(self, samples):
        if (not samples
        or any(not(isinstance(value, (int, float)) and value >= 0)
                for value in samples)):
            raise ValueError("samples must be a non-empty list "
                             "of float >= 0")

        if self.warmups is not None and (len(samples) - self.warmups) < 1:
            raise ValueError("provided %s samples, but benchmark uses "
                             "%s warmups" % (len(samples), self.warmups))

        run = tuple(samples)
        if self._runs:
            if len(run) != len(self._runs[0]):
                raise ValueError("different number of samples")

        self._clear_stats_cache()
        self._runs.append(run)

    def _get_worker_samples(self, run_bench):
        if len(run_bench._runs) != 1:
            raise ValueError("A worker result must have exactly one run")
        for attr in 'loops inner_loops warmups'.split():
            if getattr(run_bench, attr) != getattr(self, attr):
                raise ValueError("%s value is different" % attr)

        return run_bench._runs[0]

    def _format_sample(self, sample):
        return self._format_samples((sample,))[0]

    # FIXME: remove it?
    def _format_run_samples(self, samples, verbose=False):
        return self._formatter(samples, verbose)

    def get_nrun(self):
        return len(self._runs)

    def get_runs(self):
        return list(self._runs)

    def get_samples(self):
        if self._samples is not None:
            return self._samples

        factor = 1.0
        if self.loops is not None:
            # FIXME: move these checks inside a property?
            if self.loops <= 0:
                raise ValueError("loops must be >=0")
            factor *= self.loops
        if self.inner_loops is not None:
            if self.inner_loops <= 0:
                raise ValueError("inner_loops must be >=0")
            factor *= self.inner_loops

        samples = []
        for run_samples in self._runs:
            for sample in run_samples[self.warmups:]:
                samples.append(sample / factor)
        samples = tuple(samples)
        self._samples = samples
        return samples

    def _get_raw_samples(self):
        # Exclude warmup samples
        samples = []
        for run_samples in self._runs:
            samples.extend(run_samples[self.warmups:])
        return samples

    # FIXME: remove the method, use directly metadata attribute
    def get_metadata(self):
        metadata = dict(self.metadata)
        # FIXME: don't expose loops/inner_loops as metadata
        if self.loops is not None:
            metadata['loops'] = _format_number(self.loops)
        if self.inner_loops is not None:
            metadata['inner_loops'] = _format_number(self.inner_loops)
        return metadata

    def format(self, verbose=0):
        nrun = self.get_nrun()
        if not nrun:
            return '<no run>'

        samples = self.get_samples()
        text = self._formatter(samples, verbose)
        if not verbose:
            return text

        iterations = []
        if nrun > 1:
            iterations.append(_format_number(nrun, 'run'))

        nsample = len(self._runs[0]) - self.warmups
        iterations.append(_format_number(nsample, 'sample'))

        iterations = ' x '.join(iterations)
        if self.warmups:
            iterations += '; %s' % _format_number(self.warmups, 'warmup')

        if iterations:
            text = '%s (%s)' % (text, iterations)
        return text

    def __str__(self):
        text = self.format()
        if self.name:
            text = '%s: %s' % (self.name, text)
        return text

    @classmethod
    def _json_load(cls, data):
        version = data.get('version')
        if version != _JSON_VERSION:
            raise ValueError("version %r not supported" % version)

        try:
            data = data['benchmark']
        except KeyError:
            raise ValueError("JSON doesn't contain results")

        name = data.get('name')
        warmups = data['warmups']
        loops = data.get('loops')
        inner_loops = data.get('inner_loops')
        metadata = data.get('metadata')

        bench = cls(name=name, warmups=warmups,
                    loops=loops, inner_loops=inner_loops,
                    metadata=metadata)
        for run_data in data['runs']:
            bench.add_run(run_data)

        return bench

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
        data = {'runs': self._runs, 'warmups': self.warmups}
        if self.name:
            data['name'] = self.name
        if self.loops is not None:
            data['loops'] = self.loops
        if self.inner_loops is not None:
            data['inner_loops'] = self.inner_loops
        if self.metadata:
            data['metadata'] = self.metadata
        return {'benchmark': data, 'version': _JSON_VERSION}

    def json(self):
        json = _import_json()
        # set separators to produce compact JSON
        return json.dumps(self._as_json(), separators=(',', ':')) + '\n'

    def json_dump_into(self, file):
        json = _import_json()
        # set separators to produce compact JSON
        json.dump(self._as_json(), file, separators=(',', ':'))
        file.write('\n')


def _display_run(bench, index, nrun, samples, file=None):
    warmups = samples[:bench.warmups]
    samples = samples[bench.warmups:]

    text = ', '.join(bench._format_samples(samples))
    text = 'raw samples (%s): %s' % (len(samples), text)
    if warmups:
        text = ('warmup (%s): %s; %s'
                % (len(warmups),
                   ', '.join(bench._format_samples(warmups)),
                   text))

    text = "Run %s/%s: %s" % (index, nrun, text)
    print(text, file=file)


def _display_runs(result):
    runs = result.get_runs()
    nrun = len(runs)
    for index, samples in enumerate(runs, 1):
        _display_run(result, index, nrun, samples)


def _display_benchmark_avg(bench, verbose=0, file=None):
    if not bench.get_nrun():
        raise ValueError("benchmark has no run")
    samples = bench.get_samples()

    # Display a warning if the standard deviation is larger than 10%
    avg = bench.mean()
    # Avoid division by zero
    if avg and len(samples) > 1:
        k = statistics.stdev(samples) / avg
        if k > 0.10:
            if k > 0.20:
                print("ERROR: the benchmark is very unstable, the standard "
                      "deviation is very high (%.0f%%)!" % (k * 100),
                      file=file)
            else:
                print("WARNING: the benchmark seems unstable, the standard "
                      "deviation is high (%.0f%%)" % (k * 100),
                      file=file)
            print("Try to rerun the benchmark with more runs, samples "
                  "and/or loops",
                  file=file)
            print(file=file)
        elif verbose > 1:
            print("Standard deviation: %.0f%%" % (k * 100), file=file)

    # Check that the shortest sample took at least 1 ms
    shortest = min(bench._get_raw_samples())
    text = bench._format_sample(shortest)
    if shortest < 1e-3:
        if shortest < 1e-6:
            print("ERROR: the benchmark may be very unstable, "
                  "the shortest sample only took %s" % text)
        else:
            print("WARNING: the benchmark may be unstable, "
                  "the shortest sample only took %s" % text)
        print("Try to rerun the benchmark with more loops "
              "or increase --min-time",
              file=file)
        print(file=file)
    elif verbose > 1:
        print("Shortest sample: %s" % text, file=file)
        print(file=file)

    # Display the average +- stdev
    print("Average: %s" % bench.format(verbose=verbose), file=file)


def _display_metadata(metadata, file=None, header="Metadata:"):
    if not metadata:
        return
    print(header, file=file)
    for key, value in sorted(metadata.items()):
        print("- %s: %s" % (key, value), file=file)
    print(file=file)


def _format_cpu_list(cpus):
    cpus = sorted(cpus)
    parts = []
    first = None
    last = None
    for cpu in cpus:
        if first is None:
            first = cpu
        elif cpu != last+1:
            if first != last:
                parts.append('%s-%s' % (first, last))
            else:
                parts.append(str(last))
            first = cpu
        last = cpu
    if first != last:
        parts.append('%s-%s' % (first, last))
    else:
        parts.append(str(last))
    return ','.join(parts)


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
    mean1 = statistics.mean(sample1)
    squares1 = ((x - mean1) ** 2 for x in sample1)
    mean2 = statistics.mean(sample2)
    squares2 = ((x - mean2) ** 2 for x in sample2)

    return (math.fsum(squares1) + math.fsum(squares2)) / float(deg_freedom)


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
    return (statistics.mean(sample1) - statistics.mean(sample2)) / math.sqrt(error * 2)


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
