from __future__ import print_function
import math
import sys

import statistics   # Python 3.4+, or backport on Python 2.7


__version__ = '0.4'
_PY3 = (sys.version_info >= (3,))
_JSON_VERSION = 1


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
    numbers = [statistics.mean(values)]
    with_stdev = (len(values) >= 2)
    if with_stdev:
        numbers.append(statistics.stdev(values))
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


def _common_value(values):
    if not values:
        return None

    value = values[0]
    if value is None:
        return None

    for other in values[1:]:
        if value != other:
            return None

    return value


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

    def _as_json(self):
        # FIXME: remove 'run_result' useless layer
        return {'run_result': {'samples': self.samples, 'warmups': self.warmups}}

    @classmethod
    def _json_load(cls, data, raw=False):
        if not raw:
            version = data.get('version')
            if version != _JSON_VERSION:
                raise ValueError("version %r not supported" % version)

        # FIXME: move this inside raw
        if 'run_result' not in data:
            raise ValueError("JSON doesn't contain run_result")
        data = data['run_result']
        return cls(samples=data['samples'], warmups=data['warmups'])


class Benchmark:
    def __init__(self, runs=None, name=None, loops=None, inner_loops=None,
                 metadata=None):
        if runs is not None:
            self.runs = runs
        else:
            self.runs = []
        self.name = name
        self.loops = loops
        self.inner_loops = inner_loops

        # Metadata dictionary: key=>value, keys and values are non-empty
        # strings
        if metadata is not None:
            self.metadata = metadata
        else:
            self.metadata = {}

        # FIXME: make the formatter configurable
        self._formatter = _format_run_result

    def _get_worker_run(self, run_bench):
        if len(run_bench.runs) != 1:
            raise ValueError("A worker must return exactly one run")
        for attr in 'loops inner_loops metadata'.split():
            if getattr(run_bench, attr) != getattr(self, attr):
                raise ValueError("%s value is different" % attr)
        # FIXME: check the number of samples and number of warmups

        return run_bench.runs[0]

    def _format_sample(self, sample, verbose=False):
        return self._formatter([sample], verbose)

    def _format_run(self, run, verbose=False):
        return self._formatter(run.samples, verbose)

    def get_samples(self):
        samples = []
        for run in self.runs:
            samples.extend(run.samples)
        return samples

    def _get_result_raw_samples(self, result):
        factor = 1
        if self.loops is not None:
            factor *= self.loops
        if self.inner_loops is not None:
            factor *= self.inner_loops
        if factor != 1:
            return [sample * factor for sample in result.samples]
        else:
            return result.samples

    def _get_raw_samples(self):
        samples = []
        for run in self.runs:
            samples.extend(self._get_result_raw_samples(run))
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
        if version != _JSON_VERSION:
            raise ValueError("version %r not supported" % version)

        if 'results' not in data:
            raise ValueError("JSON doesn't contain results")
        data = data['results']

        name = data.get('name')
        metadata = data.get('metadata')
        loops = data.get('loops')
        inner_loops = data.get('inner_loops')
        runs = [RunResult._json_load(run, raw=True) for run in data['runs']]

        return cls(runs=runs, name=name, metadata=metadata,
                   loops=loops, inner_loops=inner_loops)

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
        data = {'runs': [run._as_json() for run in self.runs]}
        if self.name:
            data['name'] = self.name
        if self.metadata:
            data['metadata'] = self.metadata
        if self.loops is not None:
            data['loops'] = self.loops
        if self.inner_loops is not None:
            data['inner_loops'] = self.inner_loops
        return {'results': data, 'version': _JSON_VERSION}

    def json(self):
        json = _import_json()
        return json.dumps(self._as_json()) + '\n'

    def json_dump_into(self, file):
        json = _import_json()
        json.dump(self._as_json(), file)
        file.write('\n')

    @classmethod
    def _from_subprocess(cls, args, **kwargs):
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
            raise RuntimeError("%s failed with exit code %s"
                               % (args[0], proc.returncode))

        return cls.json_load(stdout)


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


def _display_benchmark_avg(bench, verbose=0, file=None):
    samples = bench.get_samples()
    # FIXME: handle empty samples

    # Display a warning if the standard deviation is larger than 10%
    avg = statistics.mean(samples)
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
