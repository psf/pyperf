from __future__ import print_function
import json
import math
import operator
import os.path
import re
import sys

import six
import statistics   # Python 3.4+, or backport on Python 2.7


__version__ = '0.8'

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


def _format_seconds(seconds):
    if seconds < 1.0:
        return _format_timedelta(seconds)

    mins, secs = divmod(seconds, 60)
    if mins:
        return '%.0f min %.0f sec' % (mins, secs)
    else:
        return '%.1f sec' % secs


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


def _common_metadata(metadatas):
    if not metadatas:
        return dict()

    metadata = dict(metadatas[0])
    for run_metadata in metadatas[1:]:
        for key in set(metadata) - set(run_metadata):
            del metadata[key]
        for key in set(run_metadata) & set(metadata):
            if run_metadata[key] != metadata[key]:
                del metadata[key]
    return metadata


def _metadata_formatter(value):
    if not isinstance(value, six.string_types):
        return str(value)

    return value


def _format_load(load):
    if isinstance(load, (int, float)):
        return '%.2f' % load
    else:
        # backward compatibility with perf 0.7.0 (load stored as string)
        return load


def _get_metadata_formatter(name):
    if name in ('loops', 'inner_loops'):
        return _format_number
    if name == 'duration':
        return _format_seconds
    if name == 'load_avg_1min':
        return _format_load
    return _metadata_formatter


_METADATA_VALUE_TYPES = six.integer_types + six.string_types + (float,)


class Metadata(object):
    def __init__(self, name, value):
        self._name = name
        self._value = value

    @property
    def name(self):
        return self._name

    @property
    def value(self):
        return self._value

    def __str__(self):
        formatter = _get_metadata_formatter(self._name)
        return formatter(self._value)

    def __eq__(self, other):
        if not isinstance(other, Metadata):
            return False
        return (self._name == other._name and self._value == other._value)

    if six.PY2:
        def __ne__(self, other):
            # negate __eq__()
            return not(self == other)

    def __repr__(self):
        return ('<perf.Metadata name=%r value=%r>'
                % (self._name, self._value))


class Run(object):
    # Run is immutable, so it can be shared/exchanged between two benchmarks

    def __init__(self, samples, warmups=None,
                 metadata=None, collect_metadata=True):
        if warmups and any(not(isinstance(sample, float) and sample > 0)
                           for sample in samples):
            raise ValueError("warmups must be a sequence of float > 0")

        if (not samples
           or any(not(isinstance(sample, float) and sample > 0)
                  for sample in samples)):
            raise ValueError("samples must be a non-empty sequence "
                             "of float > 0")

        if warmups:
            self._warmups = tuple(warmups)
        else:
            self._warmups = None
        self._samples = tuple(samples)

        if collect_metadata:
            from perf import metadata as perf_metadata

            metadata2 = {}
            perf_metadata._collect_metadata(metadata2)

            if metadata is not None:
                metadata2.update(metadata)
                metadata = metadata2
            else:
                metadata = metadata2

        # Metadata dictionary: key=>value, keys and values should be non-empty
        # strings
        if metadata:
            self._metadata = {}
            for name, value in metadata.items():
                if not isinstance(name, six.string_types):
                    raise TypeError("metadata name must be a string, got %s"
                                    % type(name).__name__)
                if not isinstance(value, _METADATA_VALUE_TYPES):
                    raise TypeError("metadata name must be str, got %s"
                                    % type(name).__name__)
                if isinstance(value, six.string_types):
                    if '\n' in value or '\r' in value:
                        raise ValueError("newline characters are not allowed "
                                         "in metadata values: %r" % value)
                    value = value.strip()
                if not value:
                    raise ValueError("metadata value is empty")
                if name in ('loops', 'inner_loops'):
                    if not(isinstance(value, six.integer_types) and value >= 1):
                        raise ValueError("%s must be an integer >= 1" % name)
                self._metadata[name] = value
        else:
            self._metadata = None

    def _get_metadata(self, name, default):
        if self._metadata:
            return self._metadata.get(name, default)
        else:
            return default

    def _get_name(self):
        return self._get_metadata('name', None)

    def get_metadata(self):
        if self._metadata:
            return {name: Metadata(name, value)
                    for name, value in self._metadata.items()}
        else:
            return {}

    @property
    def warmups(self):
        if self._warmups:
            return self._warmups
        else:
            return ()

    @property
    def samples(self):
        return self._samples

    def _get_loops(self):
        return self._get_metadata('loops', 1)

    def _get_inner_loops(self):
        return self._get_metadata('inner_loops', 1)

    def get_total_loops(self):
        return self._get_loops() * self._get_inner_loops()

    def _get_raw_samples(self, warmups=False):
        total_loops = self._get_loops() * self._get_inner_loops()
        if warmups and self._warmups:
            samples = self._warmups + self._samples
        else:
            samples = self._samples
        if total_loops != 1:
            return tuple(sample * total_loops for sample in samples)
        else:
            return samples

    def _remove_warmups(self):
        if not self._warmups:
            return self

        # don't pass self._warmups
        return Run(self._samples,
                   metadata=self._metadata,
                   collect_metadata=False)

    def _get_duration(self):
        duration = self._get_metadata('duration', None)
        if duration is not None:
            return duration
        raw_samples = self._get_raw_samples(warmups=True)
        return math.fsum(raw_samples)

    def _as_json(self, common_metadata):
        data = {'samples': self._samples}
        if self._warmups:
            data['warmups'] = self._warmups

        if self._metadata:
            if common_metadata:
                metadata = {key: value
                            for key, value in self._metadata.items()
                            if key not in common_metadata}
            else:
                metadata = self._metadata

            if metadata:
                data['metadata'] = metadata
        return data

    @classmethod
    def _json_load(cls, run_data, common_metadata):
        warmups = run_data.get('warmups', None)
        samples = run_data['samples']
        metadata = run_data.get('metadata', None)
        if common_metadata:
            metadata2 = dict(common_metadata)
            if metadata:
                metadata2.update(metadata)
            metadata = metadata2
        return cls(samples, warmups,
                   metadata=metadata,
                   collect_metadata=False)


class Benchmark(object):
    def __init__(self):
        self._clear_runs_cache()
        # list of Run objects
        self._runs = []
        self._format_samples = _format_timedeltas

    def get_name(self):
        if not self._runs:
            return None
        run = self._runs[0]
        return run._get_name()

    def get_metadata(self):
        if self._common_metadata is None:
            run_metadatas = [run.get_metadata() for run in self._runs]
            self._common_metadata = _common_metadata(run_metadatas)
        return dict(self._common_metadata)

    def get_total_duration(self):
        durations = [run._get_duration() for run in self._runs]
        return math.fsum(durations)

    def _get_run_property(self, get_property):
        if not self._runs:
            raise ValueError("the benchmark has no run")

        values = [get_property(run) for run in self._runs]
        if len(set(values)) == 1:
            return values[0]

        # Compute the mean (float)
        return float(sum(values)) / len(values)

    def _get_nwarmup(self):
        return self._get_run_property(lambda run: len(run.warmups))

    def _get_nsample_per_run(self):
        return self._get_run_property(lambda run: len(run.samples))

    def _get_loops(self):
        return self._get_run_property(lambda run: run._get_loops())

    def get_total_loops(self):
        return self._get_run_property(lambda run: run.get_total_loops())

    def _get_inner_loops(self):
        return self._get_run_property(lambda run: run._get_inner_loops())

    def _clear_runs_cache(self):
        self._samples = None
        self._median = None
        self._common_metadata = None

    def median(self):
        if self._median is None:
            self._median = statistics.median(self.get_samples())
            # add_run() ensures that all samples are greater than zero
            assert self._median != 0
        return self._median

    def add_run(self, run):
        if not isinstance(run, Run):
            raise TypeError("Run expected, got %s" % type(run).__name__)

        keys = ('aslr',
                'cpu_count',
                'cpu_model_name',
                'hostname',
                'inner_loops',
                'name',
                'platform',
                'python_executable',
                'python_implementation',
                'python_unicode',
                'python_version')
        # ignored:
        # - cpu_affinity
        # - cpu_config
        # - cpu_freq
        # - cpu_temp
        # - date
        # - duration
        # - timer

        # FIXME: check loops? or maybe emit a warning in show?

        # don't check the first run
        if self._runs:
            metadata = self.get_metadata()
            run_metata = run.get_metadata()
            for key in keys:
                value = metadata.get(key, None)
                run_value = run_metata.get(key, None)
                if run_value != value:
                    raise ValueError("incompatible benchmark, metadata %s is "
                                     "different: current=%s, run=%s"
                                     % (key, value, run_value))

        self._clear_runs_cache()
        self._runs.append(run)

    def _format_sample(self, sample):
        return self._format_samples((sample,))[0]

    def get_nrun(self):
        return len(self._runs)

    def get_runs(self):
        return list(self._runs)

    def get_nsample(self):
        if self._samples is not None:
            return len(self._samples)
        else:
            return sum(len(run.samples) for run in self._runs)

    def get_samples(self):
        if self._samples is not None:
            return self._samples

        samples = []
        for run in self._runs:
            samples.extend(run.samples)
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
    def _json_load(cls, data):
        bench = cls()
        common_metadata = data.get('common_metadata', None)

        for run_data in data['runs']:
            run = Run._json_load(run_data, common_metadata)
            # Don't call add_run() to avoid O(n) complexity:
            # expect that runs were already validated before being written
            # into a JSON file
            bench._runs.append(run)

        if common_metadata:
            bench._common_metadata = {name: Metadata(name, value)
                                     for name, value in common_metadata.items()}
        else:
            bench._common_metadata = {}
        return bench

    def _as_json(self):
        data = {}
        common_metadata = self.get_metadata()
        if common_metadata:
            data['common_metadata'] = {name: obj.value
                                       for name, obj in common_metadata.items()}
        data['runs'] = [run._as_json(common_metadata) for run in self._runs]
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
                   for sample in run.samples):
                new_runs.append(run)
        if not new_runs:
            raise ValueError("no more runs")
        self._runs[:] = new_runs

    def add_runs(self, benchmark):
        if not isinstance(benchmark, Benchmark):
            raise TypeError("expected Benchmark, got %s"
                            % type(benchmark).__name__)

        if benchmark is self:
            raise ValueError("cannot add a benchmark to itself")

        nrun = benchmark.get_nrun()
        if not nrun:
            raise ValueError("the benchmark has no run")

        for run in benchmark._runs:
            self.add_run(run)


class BenchmarkSuite(object):
    def __init__(self, filename=None):
        self.filename = filename
        self._benchmarks = []

    def get_benchmark_names(self):
        names = []
        for bench in self:
            name = bench.get_name()
            if not name:
                raise ValuError("a benchmark has no name")
            names.append(name)
        return names

    def __len__(self):
        return len(self._benchmarks)

    def __iter__(self):
        return iter(self._benchmarks)

    def _add_benchmark_runs(self, benchmark):
        name = benchmark.get_name()
        if not name:
            raise ValueError("the benchmark has no name")

        try:
            existing = self.get_benchmark(name)
        except KeyError:
            self.add_benchmark(benchmark)
        else:
            existing.add_runs(benchmark)

    def add_runs(self, result):
        if isinstance(result, Benchmark):
            self._add_benchmark_runs(result)

        elif isinstance(result, BenchmarkSuite):
            if len(result) == 0:
                raise ValueError("the new benchmark suite does not contain "
                                 "any benchmark")

            for benchmark in result:
                self._add_benchmark_runs(benchmark)

        else:
            raise TypeError("expect Benchmark or BenchmarkSuite, got %s"
                            % type(result).__name__)


    def get_benchmark(self, name):
        if not name:
            raise ValueError("name is empty")
        for bench in self._benchmarks:
            if bench.get_name() == name:
                return bench
        raise KeyError("there is no benchmark called %r" % name)

    def get_benchmarks(self):
        return sorted(self._benchmarks,
                      key=lambda bench: bench.get_name() or '')

    def add_benchmark(self, benchmark):
        if benchmark in self._benchmarks:
            raise ValueError("benchmark already part of the suite")

        name = benchmark.get_name()
        if name:
            try:
                self.get_benchmark(name)
            except KeyError:
                pass
            else:
                raise ValueError("the suite has already a benchmark called %r"
                                 % name)

        self._benchmarks.append(benchmark)

    @classmethod
    def _json_load(cls, filename, bench_file):
        version = bench_file.get('version')
        if version == _JSON_VERSION:
            benchmarks_json = bench_file['benchmarks']
        else:
            raise ValueError("file format version %r not supported" % version)

        suite = cls(filename)
        for bench_data in benchmarks_json:
            benchmark = Benchmark._json_load(bench_data)
            suite.add_benchmark(benchmark)

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

        return cls._json_load(filename, bench_file)

    @classmethod
    def loads(cls, string):
        bench_file = json.loads(string)
        return cls._json_load(None, bench_file)

    def dump(self, file, compact=True):
        benchmarks = [benchmark._as_json() for benchmark in self._benchmarks]
        data = {'version': _JSON_VERSION, 'benchmarks': benchmarks}

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

    def _convert_include_benchmark(self, name):
        benchmarks = []
        for bench in self:
            if bench.get_name() == name:
                benchmarks.append(bench)
        if not benchmarks:
            raise KeyError("benchmark %r not found" % name)
        self._benchmarks = benchmarks

    def _convert_exclude_benchmark(self, name):
        benchmarks = []
        for bench in self:
            if bench.get_name() != name:
                benchmarks.append(bench)
        if not benchmarks:
            raise ValueError("empty suite")
        self._benchmarks = benchmarks

    def get_total_duration(self):
        durations = [benchmark.get_total_duration() for benchmark in self]
        return math.fsum(durations)


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
    diff = statistics.mean(sample1) - statistics.mean(sample2)
    return diff / math.sqrt(error * 2)


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
        elif cpu != last + 1:
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
                for run in range(first, last + 1):
                    runs.append(run)
            else:
                runs.append(int(part))
        except ValueError:
            raise ValueError("invalid list of runs")

    if not runs:
        raise ValueError("empty list of runs")

    if min(runs) < 1:
        raise ValueError("number of runs starts at 1")

    return [run - 1 for run in runs]


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
            for cpu in range(first, last + 1):
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


def add_runs(filename, result):
    if os.path.exists(filename):
        suite = BenchmarkSuite.load(filename)
    else:
        suite = BenchmarkSuite()
    suite.add_runs(result)
    suite.dump(filename)


def _set_cpu_affinity(cpus):
    # Python 3.3 or newer?
    if hasattr(os, 'sched_setaffinity'):
        os.sched_setaffinity(0, cpus)
        return True

    try:
        import psutil
    except ImportError:
        return

    proc = psutil.Process()
    if not hasattr(proc, 'cpu_affinity'):
        return

    proc.cpu_affinity(cpus)
    return True
