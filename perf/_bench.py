from __future__ import division, print_function, absolute_import

import datetime
import json
import math
import os.path
import sys

import six
import statistics

from perf._metadata import (NUMBER_TYPES, parse_metadata, Metadata,
                            _common_metadata, get_metadata_info)
from perf._utils import parse_iso8601, UNIT_FORMATTERS


# Format format history:
# 4 - warmups are now a lists of (loops, raw_sample) rather than lists of
#     samples
# 3 - add Run class
# 2 - support multiple benchmarks per file
# 1 - first version
_JSON_VERSION = 4


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

        if not isinstance(sample, float):
            return False
        if sample < 0:
            return False

    return True


class Run(object):
    # Run is immutable, so it can be shared/exchanged between two benchmarks

    def __init__(self, samples, warmups=None,
                 metadata=None, collect_metadata=True):
        if warmups is not None and not _check_warmups(warmups):
            raise ValueError("warmups must be a sequence of (loops, sample) "
                             "where loops is a int >= 1 and sample "
                             "is a float >= 0.0")

        if (not samples
           or any(not(isinstance(sample, NUMBER_TYPES) and sample > 0)
                  for sample in samples)):
            raise ValueError("samples must be a non-empty sequence "
                             "of number > 0.0")

        if warmups:
            self._warmups = tuple(warmups)
        else:
            self._warmups = None
        self._samples = tuple(samples)

        if collect_metadata:
            from perf._collect_metadata import collect_metadata as collect_func

            metadata2 = {}
            collect_func(metadata2)

            if metadata is not None:
                metadata2.update(metadata)
                metadata = metadata2
            else:
                metadata = metadata2

        # Metadata dictionary: key=>value, keys and values should be non-empty
        # strings
        if metadata:
            self._metadata = parse_metadata(metadata)
        else:
            self._metadata = None

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
        inner_loops = self._get_inner_loops()

        if warmups and self._warmups:
            # FIXME: store the number of loops in each warmup sample
            raw_samples = [raw_sample for loops, raw_sample in self._warmups]
        else:
            raw_samples = []

        sample_loops = self._get_loops() * inner_loops
        raw_samples.extend(sample * sample_loops for sample in self._samples)
        return tuple(raw_samples)

    def _remove_warmups(self):
        if not self._warmups:
            return self

        return self._replace(warmups=False)

    def _get_duration(self):
        duration = self._get_metadata('duration', None)
        if duration is not None:
            return duration
        raw_samples = self._get_raw_samples(warmups=True)
        return math.fsum(raw_samples)

    def _get_date(self):
        date = self._get_metadata('date', None)
        if not date:
            return None
        return parse_iso8601(date)

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
    def _json_load(cls, run_data, common_metadata, version):
        metadata = run_data.get('metadata', None)
        if common_metadata:
            metadata2 = dict(common_metadata)
            if metadata:
                metadata2.update(metadata)
            metadata = metadata2

        warmups = run_data.get('warmups', None)
        if warmups:
            if version == _JSON_VERSION:
                warmups = [tuple(item) for item in warmups]
            else:
                if metadata:
                    loops = metadata.get('loops', 1)
                    inner_loops = metadata.get('inner_loops', 1)
                else:
                    loops = 1
                    inner_loops = 1
                total_loops = loops * inner_loops
                warmups = [(loops, sample * total_loops)
                           for sample in warmups]
        samples = run_data['samples']

        return cls(samples,
                   warmups=warmups,
                   metadata=metadata,
                   collect_metadata=False)

    def _extract_metadata(self, name):
        value = self._get_metadata(name, None)
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
        name = self._get_metadata('name', None)
        if name:
            metadata = {'name': name}
        else:
            metadata = {}
        return self._replace(metadata=metadata)

    def _update_metadata(self, metadata):
        if 'inner_loops' in metadata:
            inner_loops = self._get_metadata('inner_loops', None)
            if (inner_loops is not None
               and metadata['inner_loops'] != inner_loops):
                raise ValueError("inner_loops metadata cannot be modified")

        metadata2 = dict(self._metadata)
        metadata2.update(metadata)
        return self._replace(metadata=metadata2)


class Benchmark(object):
    def __init__(self):
        self._clear_runs_cache()
        # list of Run objects
        self._runs = []

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
        self._dates = None

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
                'python_version',
                'unit')
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

    def format_samples(self, samples):
        unit = 'second'
        if self._runs:
            run = self._runs[0]
            unit = run._get_metadata('unit', unit)
        formatter = UNIT_FORMATTERS[unit]
        return formatter(samples)

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

    def format(self):
        nrun = self.get_nrun()
        if not nrun:
            return '<no run>'

        if self.get_nsample() >= 2:
            samples = self.get_samples()
            numbers = [self.median()]
            numbers.append(statistics.stdev(samples))
            numbers = self.format_samples(numbers)
            text = '%s +- %s' % numbers
        else:
            text = self.format_sample(self.median())
        return text

    def __str__(self):
        text = self.format()
        if self.get_nsample() >= 2:
            return 'Median +- std dev: %s' % text
        else:
            return 'Median: %s' % text

    @classmethod
    def _json_load(cls, data, version):
        bench = cls()
        common_metadata = data.get('common_metadata', None)

        for run_data in data['runs']:
            run = Run._json_load(run_data, common_metadata, version)
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

    def get_dates(self):
        if self._dates is not None:
            return self._dates

        start = None
        end = None
        for run in self._runs:
            run_start = run._get_date()
            if run_start is None:
                continue

            duration = run._get_duration()
            duration = int(math.ceil(duration))
            run_end = run_start + datetime.timedelta(seconds=duration)
            if start is None or run_start < start:
                start = run_start
            if end is None or run_end > end:
                end = run_end

        if start is not None and end is not None:
            self._dates = (start, end)
        else:
            self._dates = ()
        return self._dates

    def _extract_metadata(self, name):
        new_runs = [run._extract_metadata(name) for run in self._runs]
        self._clear_runs_cache()
        self._runs = new_runs

    def _remove_all_metadata(self):
        new_runs = [run._remove_all_metadata() for run in self._runs]
        self._clear_runs_cache()
        self._runs = new_runs

    def update_metadata(self, metadata):
        metadata = parse_metadata(metadata)
        if not metadata:
            return self

        if not self._runs:
            raise ValueError("benchmark has no run")

        self._clear_runs_cache()
        self._runs = [run._update_metadata(metadata) for run in self._runs]


class BenchmarkSuite(object):
    def __init__(self, filename=None):
        self.filename = filename
        self._benchmarks = []

    def get_benchmark_names(self):
        names = []
        for bench in self:
            name = bench.get_name()
            if not name:
                raise ValueError("a benchmark has no name")
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
        if version in (3, _JSON_VERSION):
            benchmarks_json = bench_file['benchmarks']
        else:
            raise ValueError("file format version %r not supported" % version)

        suite = cls(filename)
        for bench_data in benchmarks_json:
            benchmark = Benchmark._json_load(bench_data, version)
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
        if start is not None and end is not None:
            return (start, end)
        else:
            return ()


def add_runs(filename, result):
    if os.path.exists(filename):
        suite = BenchmarkSuite.load(filename)
    else:
        suite = BenchmarkSuite()
    suite.add_runs(result)
    suite.dump(filename)
