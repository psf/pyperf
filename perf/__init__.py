from __future__ import print_function
import json
import math
import operator
import sys

import six
import statistics   # Python 3.4+, or backport on Python 2.7


__version__ = '0.7'
# Format format history:
# 3 - add Run class
# 2 - support multiple benchmarks per file
# 1 - first version
_JSON_VERSION = 3


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
    ref_value = abs(values[0])
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
            x, r = divmod(x, 10)
            pow10 += 1
            if r:
                break
        if not r:
            number = '10^%s' % pow10

    if isinstance(number, int) and number > 8192:
        pow2 = 0
        x = number
        while x >= 2:
            x, r = divmod(x, 2)
            pow2 += 1
            if r:
                break
        if not r:
            number = '2^%s' % pow2

    if not unit:
        return str(number)

    if plural:
        if not units:
            units = unit + 's'
        return '%s %s' % (number, units)
    else:
        return '%s %s' % (number, unit)


class Run(object):
    # Run is immutable, so it can be shared/exchanged between two benchmarks

    def __init__(self, warmups, raw_samples, loops=1, inner_loops=1,
                 metadata=None):
        if (not raw_samples
        or any(not(isinstance(sample, float) and sample > 0)
               for sample in raw_samples)):
            raise ValueError("raw_samples must be a non-empty list of float > 0")

        if not(isinstance(warmups, int) and warmups >= 0):
            raise ValueError("warmups must be an int >= 0")

        if (len(raw_samples) - warmups) < 1:
            raise ValueError("provided %s raw_samples, but run uses "
                             "%s warmups" % (len(raw_samples), warmups))

        self._warmups = warmups
        # non-empty tuple of float > 0
        self._raw_samples = tuple(raw_samples)

        if not(isinstance(loops, int) and loops >= 1):
            raise ValueError("loops must be an int >= 1")
        self._loops = loops

        if not(isinstance(inner_loops, int) and inner_loops >= 1):
            raise ValueError("inner_loops must be an int >= 1")
        self._inner_loops = inner_loops

        if metadata is not None:
            self.metadata = dict(metadata)
        else:
            from perf import metadata as perf_metadata
            self.metadata = {}
            perf_metadata.collect_run_metadata(self.metadata)

    @property
    def loops(self):
        return self._loops

    @property
    def inner_loops(self):
        return self._inner_loops

    def _get_nsample(self):
        "Get the number of samples, excluding wamrup samples."
        return (len(self._raw_samples) - self._warmups)

    def _get_samples(self):
        total_loops = self._loops * self._inner_loops
        return [sample / total_loops for sample in self._get_raw_samples()]

    def _get_raw_samples(self, warmups=False):
        if warmups or not self._warmups:
            return self._raw_samples
        return self._raw_samples[self._warmups:]

    def _remove_warmups(self):
        if not self._warmups:
            return self

        return Run(0, self._get_raw_samples())

    def _as_json(self):
        data = {'raw_samples': self._raw_samples}
        if self._warmups:
            data['warmups'] = self._warmups
        if self._loops != 1:
            data['loops'] = self._loops
        if self._inner_loops != 1:
            data['inner_loops'] = self._inner_loops
        if self.metadata:
            data['metadata'] = self.metadata
        return data

    @classmethod
    def _json_load(cls, run_data):
        warmups = run_data.get('warmups', 0)
        raw_samples = run_data['raw_samples']
        loops = run_data.get('loops', 1)
        inner_loops = run_data.get('inner_loops', 1)
        metadata = run_data.get('metadata', None)
        return cls(warmups, raw_samples,
                   loops=loops,
                   inner_loops=inner_loops,
                   metadata=metadata)


class Benchmark(object):
    def __init__(self, name, metadata=None):
        # list of Run objects
        self._runs = []

        self._clear_stats_cache()

        self._format_samples = _format_timedeltas

        # Metadata dictionary: key=>value, keys and values should be non-empty
        # strings
        if metadata is not None:
            self.metadata = dict(metadata)
        else:
            from perf import metadata as perf_metadata
            self.metadata = {}
            perf_metadata.collect_benchmark_metadata(self.metadata)

        # use name property setter
        self.name = name

    @property
    def name(self):
        return self.metadata.get('name', None)

    @name.setter
    def name(self, value):
        if not isinstance(value, six.string_types):
            raise TypeError("name must be a non-empty string")

        value = value.strip()
        if not value:
            raise TypeError("name must be a non-empty string")

        self.metadata['name'] = value

    def _get_run_property(self, get_property):
        # FIXME: move this check to Benchmark constructor?
        if not self._runs:
            raise ValueError("no run")

        values = [get_property(run) for run in self._runs]
        if len(set(values)) == 1:
            return values[0]

        # Compute the mean (float)
        return float(sum(values)) / len(values)

    def get_warmups(self):
        return self._get_run_property(lambda run: run._warmups)

    def _get_nsample_per_run(self):
        return self._get_run_property(lambda run: run._get_nsample())

    def get_loops(self):
        return self._get_run_property(lambda run: run.loops)

    def get_inner_loops(self):
        return self._get_run_property(lambda run: run.inner_loops)

    def _clear_stats_cache(self):
        self._samples = None
        self._median = None

    def median(self):
        if self._median is None:
            self._median = statistics.median(self.get_samples())
            # add_run() ensures that all samples are greater than zero
            assert self._median != 0
        return self._median

    def add_run(self, run):
        if not isinstance(run, Run):
            raise TypeError("Run expected, got %s" % type(run).__name__)
        self._clear_stats_cache()
        self._runs.append(run)

    def _format_sample(self, sample):
        return self._format_samples((sample,))[0]

    def get_nrun(self):
        return len(self._runs)

    def get_runs(self):
        return list(self._runs)

    def get_nsample(self):
        return sum(run._get_nsample() for run in self._runs)

    def get_samples(self):
        if self._samples is not None:
            return self._samples

        samples = []
        for run in self._runs:
            samples.extend(run._get_samples())
        samples = tuple(samples)
        self._samples = samples
        return samples

    def _get_raw_samples(self, warmups=False):
        raw_samples = []
        for run in self._runs:
            raw_samples.extend(run._get_raw_samples(warmups))
        return raw_samples

    def format(self):
        nrun = self.get_nrun()
        if not nrun:
            return '<no run>'

        if self.get_nsample() >= 2:
            samples = self.get_samples()
            numbers = [self.median()]
            numbers.append(statistics.stdev(samples))
            numbers = self._format_samples(numbers)
            text = '%s +- %s' % numbers
        else:
            text = self._format_sample(self.median())
        return text

    def __str__(self):
        text = self.format()
        if self.get_nsample() >= 2:
            return 'Median +- std dev: %s' % text
        else:
            return 'Median: %s' % text

    @classmethod
    def _json_load(cls, data, version):
        metadata = data.get('metadata')
        name = metadata.get('name')

        if version == _JSON_VERSION:
            bench = cls(name, metadata=metadata)

            for run_data in data['runs']:
                run = Run._json_load(run_data)
                bench.add_run(run)
        else:
            # version 1 and 2
            warmups = data.get('warmups', 0)
            loops = data.get('loops', 1)
            inner_loops = data.get('inner_loops', 1)
            date = metadata.pop('date', None)
            if not inner_loops:
                inner_loops = 1
            if date is not None:
                run_metadata = {'date': date}
            else:
                run_metadata = {}

            bench = cls(name, metadata=metadata)

            for raw_samples in data['runs']:
                run = Run(warmups, raw_samples, loops, inner_loops, metadata=run_metadata)
                bench.add_run(run)
        return bench

    def _as_json(self):
        data = {'runs': [run._as_json() for run in self._runs]}
        if self.metadata:
            data['metadata'] = self.metadata
        return data

    @staticmethod
    def load(file):
        suite = BenchmarkSuite.load(file)
        benchmarks = suite.get_benchmarks()
        if len(benchmarks) != 1:
            raise ValueError("expected 1 benchmark, got %s" % len(benchmarks))
        return benchmarks[0]

    @staticmethod
    def loads(string):
        suite = BenchmarkSuite.loads(string)
        benchmarks = suite.get_benchmarks()
        if len(benchmarks) != 1:
            raise ValueError("expected 1 benchmark, got %s" % len(benchmarks))
        return benchmarks[0]

    def dump(self, file, compact=True):
        suite = BenchmarkSuite()
        suite.add_benchmark(self)
        suite.dump(file, compact=compact)

    def _filter_runs(self, include, only_runs):
        if include:
            old_runs = self._runs
            max_index = len(old_runs) - 1
            runs = []
            for index in only_runs:
                if index <= max_index:
                    runs.append(old_runs[index])
        else:
            runs = self._runs
            max_index = len(runs) - 1
            for index in reversed(only_runs):
                if index <= max_index:
                    del runs[index]
        if not runs:
            raise ValueError("no more runs")
        self._runs = runs

    def _remove_warmups(self):
        self._runs = [run._remove_warmups() for run in self._runs]

    def _remove_outliers(self):
        median = self.median()
        min_sample = median * 0.95
        max_sample = median * 1.05

        new_runs = []
        for run in self._runs:
            # FIXME: only remove outliers, not whole runs
            if all(min_sample <= sample <= max_sample
                   for sample in run._get_samples()):
                new_runs.append(run)
        if not new_runs:
            raise ValueError("no more runs")
        self._runs[:] = new_runs

    def _add_benchmark_runs(self, benchmark):
        if benchmark is self:
            raise ValueError("cannot add a benchmark to itself")

        # FIXME: compare metadata to make sure that benchmarks are compatible
        # FIXME: make sure that the benchmark is compatible
        # FIXME: compare metadata except date?

        if benchmark.metadata != self.metadata:
            print(benchmark.metadata)
            print(self.metadata)
            raise ValueError("incompatible benchmark: metadata are different")

        # FIXME: move this check to benchmark constructor
        nrun = benchmark.get_nrun()
        if not nrun:
            raise ValueError("benchmark has no run")

        for run in benchmark._runs:
            self.add_run(run)


class BenchmarkSuite(dict):
    def __init__(self, filename=None):
        super(BenchmarkSuite, self).__init__()
        self.filename = filename

    def _add_benchmark_runs(self, benchmark):
        try:
            existing = self[benchmark.name]
        except KeyError:
            self.add_benchmark(benchmark)
            return

        existing._add_benchmark_runs(benchmark)

    def get_benchmarks(self):
        return sorted(self.values(), key=operator.attrgetter('name'))

    def _add_benchmark(self, name, benchmark):
        if name in self:
            raise ValueError("duplicate benchmark name: %r" % name)
        self[name] = benchmark

    def add_benchmark(self, benchmark):
        self._add_benchmark(benchmark.name, benchmark)

    @classmethod
    def _load_json(cls, filename, bench_file):
        version = bench_file.get('version')
        if version in (_JSON_VERSION, 2):
            benchmarks_json = bench_file['benchmarks']
        elif version == 1:
            # Backward compatibility with perf 0.5
            bench_data = bench_file['benchmark']
            # name must be non-empty
            name = bench_data['name'] or "benchmark"
            if 'name' not in bench_data['metadata']:
                bench_data['metadata']['name'] = name
            benchmarks_json = {name: bench_data}
        else:
            raise ValueError("file format version %r not supported" % version)

        suite = cls(filename)
        for name, bench_data in benchmarks_json.items():
            benchmark = Benchmark._json_load(bench_data, version)
            suite._add_benchmark(name, benchmark)

        if not suite:
            raise ValueError("the file doesn't contain any benchmark")

        return suite

    @classmethod
    def load(cls, file):
        if isinstance(file, (bytes, six.text_type)):
            if file != '-':
                filename = file
                if six.PY3:
                    fp = open(file, "r", encoding="utf-8")
                else:
                    fp = open(file, "rb")
                with fp:
                    bench_file = json.load(fp)
            else:
                filename = '<stdin>'
                bench_file = json.load(sys.stdin)
        else:
            # file is a file object
            filename = getattr(file, 'name', None)
            bench_file = json.load(file)

        return cls._load_json(filename, bench_file)

    @classmethod
    def loads(cls, string):
        bench_file = json.loads(string)
        return cls._load_json(None, bench_file)

    def dump(self, file, compact=True):
        benchmarks_json = {}
        for name, benchmark in self.items():
            benchmarks_json[name] = benchmark._as_json()
        data = {'version': _JSON_VERSION, 'benchmarks': benchmarks_json}

        def dump(data, fp, compact):
            if compact:
                json.dump(data, fp, separators=(',', ':'), sort_keys=True)
            else:
                json.dump(data, fp, indent=4, sort_keys=True)
            fp.write("\n")
            fp.flush()

        if isinstance(file, (bytes, six.text_type)):
            if six.PY3:
                fp = open(file, "w", encoding="utf-8")
            else:
                fp = open(file, "wb")
            with fp:
                dump(data, fp, compact)
        else:
            # file is a file object
            dump(data, file, compact)


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
    # FIXME: use median?
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
    if len(sample1) != len(sample2):
        raise ValueError("different number of samples")
    error = _pooled_sample_variance(sample1, sample2) / len(sample1)
    # FIXME: use median?
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


def _parse_run_list(run_list):
    run_list = run_list.strip()

    runs = []
    for part in run_list.split(','):
        part = part.strip()
        try:
            if '-' in part:
                parts = part.split('-', 1)
                first = int(parts[0])
                last = int(parts[1])
                for run in range(first, last+1):
                    runs.append(run)
            else:
                runs.append(int(part))
        except ValueError:
            raise ValueError("invalid list of runs")

    if not runs:
        raise ValueError("empty list of runs")

    if min(runs) < 1:
        raise ValueError("number of runs starts at 1")

    return [run-1 for run in runs]


def _parse_cpu_list(cpu_list):
    cpu_list = cpu_list.strip()
    if not cpu_list:
        return

    cpus = []
    for part in cpu_list.split(','):
        part = part.strip()
        if '-' in part:
            parts = part.split('-', 1)
            first = int(parts[0])
            last = int(parts[1])
            for cpu in range(first, last+1):
                cpus.append(cpu)
        else:
            cpus.append(int(part))
    return cpus


def _get_isolated_cpus():
    path = '/sys/devices/system/cpu/isolated'
    try:
        if six.PY3:
            fp = open(path, encoding='ascii')
        else:
            fp = open(path)
        with fp:
            isolated = fp.readline().rstrip()
    except (OSError, IOError):
        # missing file
        return

    return _parse_cpu_list(isolated)
