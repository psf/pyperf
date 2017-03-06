from __future__ import division, print_function, absolute_import

import datetime
import errno
import json
import math
import os.path
import sys

import six
import statistics

from perf._metadata import (NUMBER_TYPES, parse_metadata,
                            _common_metadata, get_metadata_info)
from perf._formatter import format_number, DEFAULT_UNIT, format_samples
from perf._utils import parse_iso8601, median_abs_dev


# JSON format history:
#
# 5 - (perf 0.8.3) timestamps in metadata are now formatted using a space
#      separator
# 4 - (perf 0.7.4) warmups are now a lists of (loops, raw_sample)
#     rather than lists of samples
# 3 - (perf 0.7) add Run class
# 2 - (perf 0.6) support multiple benchmarks per file
# 1 - first version
_JSON_VERSION = 5

# Metadata checked by add_run(): all runs have must have the same
# value for these metadata (or no run must have this metadata)
_CHECKED_METADATA = (
    'aslr',
    'cpu_count',
    'cpu_model_name',
    'hostname',
    'inner_loops',
    'name',
    'platform',
    'python_executable',
    'python_implementation',
    'python_unicode',
    'python_version',
    'unit')


_UNSET = object()


def _check_warmups(warmups):
    for item in warmups:
        if not isinstance(item, tuple):
            return False
        if len(item) != 2:
            return False

        loops, sample = item
        if not isinstance(loops, int):
            return False
        if loops < 1:
            return False

        if not isinstance(sample, NUMBER_TYPES):
            return False
        if sample < 0:
            return False

    return True


def _cached_attr(func):
    attr = '_' + func.__name__

    def method(self):
        value = getattr(self, attr)
        if value is not None:
            return value

        value = func(self)
        setattr(self, attr, value)
        return value

    return method


class Run(object):
    # Run is immutable, so it can be shared/exchanged between two benchmarks

    def __init__(self, samples, warmups=None,
                 metadata=None, collect_metadata=True):
        if any(not(isinstance(sample, NUMBER_TYPES) and sample > 0)
               for sample in samples):
            raise ValueError("samples must be a sequence of number > 0.0")

        if warmups is not None and not _check_warmups(warmups):
            raise ValueError("warmups must be a sequence of (loops, sample) "
                             "where loops is a int >= 1 and sample "
                             "is a float >= 0.0")

        if warmups:
            self._warmups = tuple(warmups)
        else:
            self._warmups = None
        self._samples = tuple(samples)

        if not self._samples and not self._warmups:
            raise ValueError("samples and warmups are empty sequence")

        if collect_metadata:
            from perf._collect_metadata import collect_metadata as collect_func

            metadata2 = {}
            collect_func(metadata2)

            if metadata is not None:
                metadata2.update(metadata)
                metadata = metadata2
            else:
                metadata = metadata2

        # Metadata dictionary
        if metadata:
            self._metadata = parse_metadata(metadata)
        else:
            self._metadata = {}

    def _replace(self, samples=None, warmups=True, metadata=None):
        if samples is None:
            samples = self._samples
        if warmups:
            warmups = self._warmups
        else:
            warmups = None
        if metadata is None:
            # share metadata dict since Run metadata is immutable
            metadata = self._metadata
        run = Run(samples, warmups=warmups, collect_metadata=False)
        run._metadata = metadata
        return run

    def _is_calibration(self):
        return (not self.samples)

    def _has_metadata(self, name):
        return (name in self._metadata)

    def _get_name(self):
        return self._metadata.get('name', None)

    def get_metadata(self):
        return dict(self._metadata)

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
        return self._metadata.get('loops', 1)

    def _get_inner_loops(self):
        return self._metadata.get('inner_loops', 1)

    def get_total_loops(self):
        return self._get_loops() * self._get_inner_loops()

    def _get_raw_samples(self, warmups=False):
        if warmups and self._warmups:
            raw_samples = [raw_sample for loops, raw_sample in self._warmups]
        else:
            raw_samples = []

        total_loops = self.get_total_loops()
        raw_samples.extend(sample * total_loops for sample in self._samples)
        return tuple(raw_samples)

    def _remove_warmups(self):
        if not self._warmups:
            return self

        return self._replace(warmups=False)

    def _get_duration(self):
        duration = self._metadata.get('duration', None)
        if duration is not None:
            return duration
        raw_samples = self._get_raw_samples(warmups=True)
        return math.fsum(raw_samples)

    def _get_date(self):
        return self._metadata.get('date', None)

    def _as_json(self, common_metadata):
        data = {'samples': self._samples}
        if self._warmups:
            data['warmups'] = self._warmups

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
        metadata = run_data.get('metadata', None)
        if common_metadata:
            metadata2 = dict(common_metadata)
            if metadata:
                metadata2.update(metadata)
            metadata = metadata2

        warmups = run_data.get('warmups', None)
        if warmups:
            warmups = [tuple(item) for item in warmups]
        samples = run_data['samples']

        return cls(samples,
                   warmups=warmups,
                   metadata=metadata,
                   collect_metadata=False)

    def _extract_metadata(self, name):
        value = self._metadata.get(name, None)
        if value is None:
            raise KeyError("run has no metadata %r" % name)

        info = get_metadata_info(name)
        if info.unit:
            metadata = dict(self._metadata, unit=info.unit)
        else:
            metadata = None

        if not isinstance(value, NUMBER_TYPES):
            raise TypeError("metadata %r value is not an integer: got %s"
                            % (name, type(value).__name__))

        return self._replace(samples=(value,), warmups=False, metadata=metadata)

    def _remove_all_metadata(self):
        name = self._metadata.get('name', None)
        unit = self._metadata.get('unit', None)
        metadata = {}
        if name:
            metadata['name'] = name
        if unit:
            metadata['unit'] = unit
        return self._replace(metadata=metadata)

    def _update_metadata(self, metadata):
        if 'inner_loops' in metadata:
            inner_loops = self._metadata.get('inner_loops', None)
            if (inner_loops is not None
               and metadata['inner_loops'] != inner_loops):
                raise ValueError("inner_loops metadata cannot be modified")

        metadata2 = dict(self._metadata)
        metadata2.update(metadata)
        return self._replace(metadata=metadata2)


class Benchmark(object):
    def __init__(self, runs):
        self._runs = []   # list of Run objects
        self._clear_runs_cache()

        if not runs:
            raise ValueError("runs must be a non-empty sequence of Run objects")

        # A benchmark must have a name
        if not runs[0]._has_metadata('name'):
            raise ValueError("A benchmark must have a name: "
                             "the first run has no name metadata")

        for run in runs:
            self.add_run(run)

    def get_name(self):
        run = self._runs[0]
        return run._get_name()

    def _get_common_metadata(self):
        if self._common_metadata is None:
            runs_metadata = [run._metadata for run in self._runs]
            self._common_metadata = _common_metadata(runs_metadata)
        return self._common_metadata

    def get_metadata(self):
        return dict(self._get_common_metadata())

    def get_total_duration(self):
        durations = [run._get_duration() for run in self._runs]
        return math.fsum(durations)

    def _get_run_property(self, get_property):
        # ignore calibration runs
        values = [get_property(run) for run in self._runs
                  if not run._is_calibration()]
        if len(set(values)) == 1:
            return values[0]

        # Compute the mean (float)
        return math.fsum(values) / len(values)

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

    def _clear_runs_cache(self, keep_common_metadata=False):
        self._samples = None
        self._mean = None
        self._stdev = None
        self._median = None
        self._median_abs_dev = None
        if not keep_common_metadata:
            self._common_metadata = None
        self._dates = _UNSET

    @_cached_attr
    def mean(self):
        value = statistics.mean(self.get_samples())
        # add_run() ensures that all samples are greater than zero
        if value <= 0:
            raise ValueError("MAD must be > 0")
        return value

    @_cached_attr
    def stdev(self):
        samples = self.get_samples()
        value = statistics.stdev(samples)
        # add_run() ensures that all samples are greater than zero
        if value < 0:
            raise ValueError("std dev must be >= 0")
        return value

    @_cached_attr
    def median(self):
        value = statistics.median(self.get_samples())
        # add_run() ensures that all samples are greater than zero
        if value <= 0:
            raise ValueError("median must be > 0")
        return value

    @_cached_attr
    def median_abs_dev(self):
        value = median_abs_dev(self.get_samples())
        # add_run() ensures that all samples are greater than zero
        if value < 0:
            raise ValueError("MAD must be >= 0")
        return value

    def add_run(self, run):
        if not isinstance(run, Run):
            raise TypeError("Run expected, got %s" % type(run).__name__)

        # Don't check metadata for the first run
        if self._runs:
            metadata = self._get_common_metadata()
            run_metata = run._metadata
            for key in _CHECKED_METADATA:
                value = metadata.get(key, None)
                run_value = run_metata.get(key, None)
                if run_value != value:
                    raise ValueError("incompatible benchmark, metadata %s is "
                                     "different: current=%s, run=%s"
                                     % (key, value, run_value))

        if self._common_metadata is not None:
            # Update common metadata
            for name, value in list(self._common_metadata.items()):
                if run._metadata.get(name, None) != value:
                    del self._common_metadata[name]
        self._clear_runs_cache(keep_common_metadata=True)

        self._runs.append(run)

    def get_unit(self):
        run = self._runs[0]
        return run._metadata.get('unit', DEFAULT_UNIT)

    def format_samples(self, samples):
        unit = self.get_unit()
        return format_samples(unit, samples)

    def format_sample(self, sample):
        return self.format_samples((sample,))[0]

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

    def _only_calibration(self):
        # If the benchmark only contains a single run which is a calibration
        # run: return the number of loops, otherwise return None
        if len(self._runs) == 1:
            run = self._runs[0]
            if run._is_calibration():
                return run._get_loops()

        return None

    def format(self):
        loops = self._only_calibration()
        if loops is not None:
            return '<calibration: %s>' % format_number(loops, 'loop')

        if self.get_nsample() >= 2:
            numbers = [self.median()]
            numbers.append(self.median_abs_dev())
            numbers = self.format_samples(numbers)
            text = '%s +- %s' % numbers
        else:
            text = self.format_sample(self.median())
        return text

    def __str__(self):
        loops = self._only_calibration()
        if loops is not None:
            return 'Calibration: %s' % format_number(loops, 'loop')

        text = self.format()
        if self.get_nsample() >= 2:
            return 'Median +- MAD: %s' % text
        else:
            return 'Median: %s' % text

    @classmethod
    def _json_load(cls, data):
        common_metadata = data.get('common_metadata', None)
        if common_metadata is not None:
            common_metadata = parse_metadata(common_metadata)

        runs = []
        for run_data in data['runs']:
            run = Run._json_load(run_data, common_metadata)
            # Don't call add_run() to avoid O(n) complexity:
            # expect that runs were already validated before being written
            # into a JSON file
            runs.append(run)

        return cls(runs)

    def _as_json(self):
        data = {}
        common_metadata = self._get_common_metadata()
        if common_metadata:
            data['common_metadata'] = common_metadata
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

    def dump(self, file, compact=True, replace=False):
        suite = BenchmarkSuite([self])
        suite.dump(file, compact=compact, replace=replace)

    def _replace_runs(self, new_runs):
        if not new_runs:
            raise ValueError("no more runs")
        self._runs[:] = new_runs
        self._clear_runs_cache()

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
        self._replace_runs(runs)

    def _remove_warmups(self):
        new_runs = [run._remove_warmups() for run in self._runs]
        self._replace_runs(new_runs)

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
        self._replace_runs(new_runs)

    def add_runs(self, benchmark):
        if not isinstance(benchmark, Benchmark):
            raise TypeError("expected Benchmark, got %s"
                            % type(benchmark).__name__)

        if benchmark is self:
            raise ValueError("cannot add a benchmark to itself")

        for run in benchmark._runs:
            self.add_run(run)

    def get_dates(self):
        if self._dates is not _UNSET:
            return self._dates

        start = None
        end = None
        for run in self._runs:
            run_start = run._get_date()
            if run_start is None:
                continue
            run_start = parse_iso8601(run_start)

            duration = run._get_duration()
            duration = int(math.ceil(duration))
            run_end = run_start + datetime.timedelta(seconds=duration)
            if start is None or run_start < start:
                start = run_start
            if end is None or run_end > end:
                end = run_end

        if start is not None:
            self._dates = (start, end)
        else:
            self._dates = None
        return self._dates

    def _extract_metadata(self, name):
        new_runs = [run._extract_metadata(name) for run in self._runs]
        self._replace_runs(new_runs)

    def _remove_all_metadata(self):
        new_runs = [run._remove_all_metadata() for run in self._runs]
        self._replace_runs(new_runs)

    def update_metadata(self, metadata):
        metadata = parse_metadata(metadata)
        if not metadata:
            return self

        new_runs = [run._update_metadata(metadata) for run in self._runs]
        self._replace_runs(new_runs)


class BenchmarkSuite(object):
    def __init__(self, benchmarks, filename=None):
        if not benchmarks:
            raise ValueError("benchmarks must be a non-empty "
                             "sequence of Benchmark objects")

        self.filename = filename
        self._benchmarks = []
        for benchmark in benchmarks:
            self.add_benchmark(benchmark)

    def get_benchmark_names(self):
        return [bench.get_name() for bench in self]

    def get_metadata(self):
        benchs_metadata = [bench._get_common_metadata()
                           for bench in self._benchmarks]
        return _common_metadata(benchs_metadata)

    def __len__(self):
        return len(self._benchmarks)

    def __iter__(self):
        return iter(self._benchmarks)

    def _add_benchmark_runs(self, benchmark):
        name = benchmark.get_name()
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
            for benchmark in result:
                self._add_benchmark_runs(benchmark)
        else:
            raise TypeError("expect Benchmark or BenchmarkSuite, got %s"
                            % type(result).__name__)

    def get_benchmark(self, name):
        for bench in self._benchmarks:
            if bench.get_name() == name:
                return bench
        raise KeyError("there is no benchmark called %r" % name)

    def get_benchmarks(self):
        return list(self._benchmarks)

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
        if version not in (4, _JSON_VERSION):
            raise ValueError("file format version %r not supported" % version)
        benchmarks_json = bench_file['benchmarks']

        benchmarks = []
        for bench_data in benchmarks_json:
            benchmark = Benchmark._json_load(bench_data)
            benchmarks.append(benchmark)
        suite = cls(benchmarks, filename=filename)

        if not suite:
            raise ValueError("the file doesn't contain any benchmark")

        return suite

    @staticmethod
    def _load_open(filename):
        if isinstance(filename, bytes):
            suffix = b'.gz'
        else:
            suffix = u'.gz'

        if filename.endswith(suffix):
            import gzip
            if six.PY3:
                return gzip.open(filename, "rt", encoding="utf-8")
            else:
                return gzip.open(filename, "rb")
        else:
            if six.PY3:
                return open(filename, "r", encoding="utf-8")
            else:
                return open(filename, "rb")

    @classmethod
    def load(cls, file):
        if isinstance(file, (bytes, six.text_type)):
            if file != '-':
                filename = file
                fp = cls._load_open(filename)
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

    @staticmethod
    def _dump_open(filename, replace):
        if isinstance(filename, bytes):
            suffix = b'.gz'
        else:
            suffix = u'.gz'

        if not replace and os.path.exists(filename):
            raise OSError(errno.EEXIST, "File already exists")

        if filename.endswith(suffix):
            import gzip

            if six.PY3:
                return gzip.open(filename, mode="wt", encoding="utf-8")
            else:
                return gzip.open(filename, mode="wb")
        else:
            if six.PY3:
                return open(filename, "w", encoding="utf-8")
            else:
                return open(filename, "wb")

    def dump(self, file, compact=True, replace=False):
        benchmarks = [benchmark._as_json() for benchmark in self._benchmarks]
        data = {'version': _JSON_VERSION, 'benchmarks': benchmarks}

        def dump(data, fp, compact):
            kw = {}
            if compact:
                kw['separators'] = (',', ':')
            else:
                kw['indent'] = 4
            json.dump(data, fp, sort_keys=True, **kw)
            fp.write("\n")
            fp.flush()

        if isinstance(file, (bytes, six.text_type)):
            fp = self._dump_open(file, replace)
            with fp:
                dump(data, fp, compact)
                fp.close()
        else:
            # file is a file object
            dump(data, file, compact)

    def _replace_benchmarks(self, benchmarks):
        if not benchmarks:
            raise ValueError("empty benchmark suite")
        self._benchmarks[:] = benchmarks

    def _convert_include_benchmark(self, name):
        benchmarks = []
        for bench in self:
            if bench.get_name() == name:
                benchmarks.append(bench)
        if not benchmarks:
            raise KeyError("benchmark %r not found" % name)
        self._replace_benchmarks(benchmarks)

    def _convert_exclude_benchmark(self, name):
        benchmarks = []
        for bench in self:
            if bench.get_name() != name:
                benchmarks.append(bench)
        self._replace_benchmarks(benchmarks)

    def get_total_duration(self):
        durations = [benchmark.get_total_duration() for benchmark in self]
        return math.fsum(durations)

    def get_dates(self):
        start = None
        end = None
        for benchmark in self:
            dates = benchmark.get_dates()
            if not dates:
                continue
            if start is None or dates[0] < start:
                start = dates[0]
            if end is None or dates[1] > end:
                end = dates[1]
        if start is not None:
            return (start, end)
        else:
            return None


def add_runs(filename, result):
    if os.path.exists(filename):
        suite = BenchmarkSuite.load(filename)
        suite.add_runs(result)
        suite.dump(filename, replace=True)
    else:
        result.dump(filename)


def _load_suite_from_pipe(bench_json):
    lines = bench_json.split("\n")
    result = None
    for line in lines:
        if not line:
            continue
        suite = BenchmarkSuite.loads(line)
        if result is not None:
            for bench in suite:
                result.add_benchmark(bench)
        else:
            result = suite
    return result
