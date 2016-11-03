from __future__ import division, print_function, absolute_import

import statistics

from perf._formatter import (format_seconds, format_number,
                             format_timedelta, format_datetime)
from perf._metadata import format_metadata as _format_metadata


def empty_line(lines):
    if lines:
        lines.append('')


def format_title(title, level=1, lines=None):
    if lines is None:
        lines = []

    empty_line(lines)

    lines.append(title)
    if level == 1:
        char = '='
    else:
        char = '-'
    lines.append(char * len(title))
    return lines


def display_title(title, level=1):
    for line in format_title(title, level):
        print(line)
    print()


def format_metadata(metadata, prefix='- ', lines=None):
    if lines is None:
        lines = []
    for name, value in sorted(metadata.items()):
        value = _format_metadata(name, value)
        lines.append("%s%s: %s" % (prefix, name, value))
    return lines


def format_run(bench, run_index, run, common_metadata=None, raw=False,
               verbose=0, lines=None):
    if lines is None:
        lines = []

    if run._is_calibration():
        lines.append("Run %s: calibrate" % (run_index,))
        for loops, sample in run.warmups:
            lines.append("- %s: %s"
                         % (format_number(loops, 'loop'),
                            format_timedelta(sample)))
        return lines

    show_warmup = (verbose >= 0)

    total_loops = run.get_total_loops()
    inner_loops = run._get_inner_loops()

    def format_samples(samples, percent=True):
        samples_str = [bench.format_sample(sample) for sample in samples]
        if not percent:
            return samples_str

        median = bench.median()
        max_delta = median * 0.05
        for index, sample in enumerate(samples):
            if raw:
                sample = float(sample) / total_loops
            delta = float(sample) - median
            if abs(delta) > max_delta:
                samples_str[index] += ' (%+.0f%%)' % (delta * 100 / median)
        return samples_str

    samples = run.samples
    if raw:
        warmups = [('%s (%s)'
                    % (bench.format_sample(raw_sample),
                       format_number(loops, 'loop')))
                   for loops, raw_sample in run.warmups]
        samples = [sample * total_loops for sample in samples]
    else:
        warmups = run.warmups
        if warmups:
            warmups = [raw_sample / (loops * inner_loops)
                       for loops, raw_sample in warmups]
            warmups = format_samples(warmups)
    samples = format_samples(samples)

    if raw:
        name = 'raw samples'
    else:
        name = 'samples'
    text = '%s (%s): %s' % (name, len(samples), ', '.join(samples))
    if warmups and show_warmup:
        if raw:
            name = 'raw warmup'
        else:
            name = 'warmup'
        text = ('%s (%s): %s; %s'
                % (name, len(warmups), ', '.join(warmups), text))

    text = "Run %s: %s" % (run_index, text)
    lines.append(text)

    if verbose > 0:
        prefix = '  '
        metadata = run.get_metadata()
        for name, value in sorted(metadata.items()):
            if common_metadata and name in common_metadata:
                continue
            value = _format_metadata(name, value)
            lines.append('%s%s: %s' % (prefix, name, value))

    return lines


def _format_runs(bench, quiet=False, verbose=False, raw=False, lines=None):
    runs = bench.get_runs()
    if quiet:
        verbose = -1
    elif verbose:
        verbose = 1
    else:
        verbose = 0

    if lines is None:
        lines = []
    if verbose > 0:
        empty_line(lines)

        # FIXME: display metadata in format_benchmark()
        common_metadata = bench.get_metadata()
        lines.append("Metadata:")
        format_metadata(common_metadata, prefix='  ', lines=lines)
    else:
        common_metadata = None

    if runs:
        # FIXME: only if we display at least one run (count non-calibration runs)
        empty_line(lines)
    for run_index, run in enumerate(runs, 1):
        if quiet and run._is_calibration():
            continue
        format_run(bench, run_index, run,
                   common_metadata=common_metadata,
                   verbose=verbose, raw=raw, lines=lines)

    return lines


def _format_stats(bench, lines):
    fmt = bench.format_sample
    samples = bench.get_samples()

    nrun = bench.get_nrun()
    nsample = len(samples)
    median = bench.median()

    empty_line(lines)

    # Total duration
    duration = bench.get_total_duration()
    if duration:
        lines.append("Total duration: %s" % format_seconds(duration))

    # Start/End dates
    dates = bench.get_dates()
    if dates:
        start, end = dates
        lines.append("Start date: %s" % format_datetime(start, microsecond=False))
        lines.append("End date: %s" % format_datetime(end, microsecond=False))

    # Raw sample minimize/maximum
    raw_samples = bench._get_raw_samples()
    lines.append("Raw sample minimum: %s" % bench.format_sample(min(raw_samples)))
    lines.append("Raw sample maximum: %s" % bench.format_sample(max(raw_samples)))
    lines.append('')

    # Number of samples
    lines.append("Number of runs: %s" % format_number(nrun))
    lines.append("Total number of samples: %s" % format_number(nsample))

    nsample_per_run = bench._get_nsample_per_run()
    text = format_number(nsample_per_run)
    if isinstance(nsample_per_run, float):
        text += ' (average)'
    lines.append('Number of samples per run: %s' % text)

    nwarmup = bench._get_nwarmup()
    text = format_number(nwarmup)
    if isinstance(nwarmup, float):
        text += ' (average)'
    lines.append('Number of warmups per run: %s' % text)

    # Loop iterations per sample
    loops = bench._get_loops()
    inner_loops = bench._get_inner_loops()
    total_loops = loops * inner_loops
    if isinstance(total_loops, int):
        text = format_number(total_loops)
    else:
        text = "%s (average)" % total_loops

    if not(isinstance(inner_loops, int) and inner_loops == 1):
        if isinstance(loops, int):
            loops = format_number(loops, 'outer-loop')
        else:
            loops = '%.1f outer-loops (average)'

        if isinstance(inner_loops, int):
            inner_loops = format_number(inner_loops, 'inner-loop')
        else:
            inner_loops = "%.1f inner-loops (average)" % inner_loops

        text = '%s (%s x %s)' % (text, loops, inner_loops)

    lines.append("Loop iterations per sample: %s" % text)
    lines.append('')

    # Minimum
    def format_limit(median, value):
        return "%s (%+.0f%%)" % (fmt(value), (value - median) * 100.0 / median)

    lines.append("Minimum: %s" % format_limit(median, min(samples)))

    # Median +- std dev
    lines.append(str(bench))

    # Mean +- std dev
    mean = statistics.mean(samples)
    if len(samples) > 2:
        stdev = statistics.stdev(samples, mean)
        lines.append("Mean +- std dev: %s +- %s"
                     % bench.format_samples((mean, stdev)))
    else:
        lines.append("Mean: %s" % bench.format_sample(mean))

    # Maximum
    lines.append("Maximum: %s" % format_limit(median, max(samples)))
    return lines


def format_histogram(benchmarks, bins=20, extend=False, lines=None):
    import collections
    import shutil

    if hasattr(shutil, 'get_terminal_size'):
        columns, nline = shutil.get_terminal_size()
    else:
        columns, nline = (80, 25)

    if not bins:
        bins = max(nline - 3, 3)
        if not extend:
            bins = min(bins, 25)

    all_samples = []
    for bench, title in benchmarks:
        all_samples.extend(bench.get_samples())
    all_min = min(all_samples)
    all_max = max(all_samples)
    sample_k = float(all_max - all_min) / bins
    if not sample_k:
        sample_k = 1.0

    def sample_bucket(value):
        # round towards zero (ROUND_DOWN)
        return int(value / sample_k)

    bucket_min = sample_bucket(all_min)
    bucket_max = sample_bucket(all_max)
    if lines is None:
        lines = []

    for item in benchmarks:
        empty_line(lines)

        bench, title = item
        if title:
            lines.append("[ %s ]" % title)

        samples = bench.get_samples()

        buckets = [sample_bucket(value) for value in samples]
        counter = collections.Counter(buckets)
        count_max = max(counter.values())
        count_width = len(str(count_max))

        sample_width = max([len(bench.format_sample(bucket * sample_k))
                            for bucket in range(bucket_min, bucket_max + 1)])
        width = columns - sample_width

        line = ': %s #' % count_max
        width = columns - (sample_width + len(line))
        if not extend:
            width = min(width, 79)
        width = max(width, 3)
        line_k = float(width) / max(counter.values())
        for bucket in range(bucket_min, bucket_max + 1):
            count = counter.get(bucket, 0)
            linelen = int(round(count * line_k))
            text = bench.format_sample(bucket * sample_k)
            line = ('#' * linelen) or '|'
            lines.append("{:>{}}: {:>{}} {}".format(text, sample_width,
                                                    count, count_width, line))

    return lines


def format_checks(bench, lines=None):
    if lines is None:
        lines = []
    warn = lines.append
    samples = bench.get_samples()

    # Display a warning if the standard deviation is larger than 10%
    median = bench.median()
    # Avoid division by zero
    if median and len(samples) > 1:
        k = statistics.stdev(samples) / median
        if k > 0.10:
            empty_line(lines)

            if k > 0.20:
                warn("ERROR: the benchmark is very unstable, the standard "
                     "deviation is very high (stdev/median: %.0f%%)!"
                     % (k * 100))
            else:
                warn("WARNING: the benchmark seems unstable, the standard "
                     "deviation is high (stdev/median: %.0f%%)"
                     % (k * 100))
            warn("Try to rerun the benchmark with more runs, samples "
                 "and/or loops")

    # Check that the shortest sample took at least 1 ms
    shortest = min(bench._get_raw_samples())
    text = bench.format_sample(shortest)
    if shortest < 1e-3:
        empty_line(lines)

        if shortest < 1e-6:
            warn("ERROR: the benchmark may be very unstable, "
                 "the shortest raw sample only took %s" % text)
        else:
            warn("WARNING: the benchmark may be unstable, "
                 "the shortest raw sample only took %s" % text)
        warn("Try to rerun the benchmark with more loops "
             "or increase --min-time")

    return lines


def format_benchmark(bench, checks=True, metadata=False,
                     dump=False, stats=False, hist=False, show_name=False,
                     result=True, display_runs_args=None):
    lines = []

    if metadata:
        lines.append("Metadata:")
        format_metadata(bench.get_metadata(), lines=lines)

    if dump:
        if display_runs_args is None:
            display_runs_args = {}
        _format_runs(bench, lines=lines, **display_runs_args)

    if hist:
        format_histogram([(bench, None)], lines=lines)

    if stats:
        _format_stats(bench, lines=lines)

    if checks:
        format_checks(bench, lines=lines)

    if result:
        empty_line(lines)

        if show_name:
            name = bench.get_name()
            text = "%s: %s" % (name, bench)
        else:
            text = str(bench)
        lines.append(text)

    return lines


def get_benchmark_name(benchmark):
    # FIXME: better fallback value
    return benchmark.get_name() or '<no name>'


# FIXME: remove this function?
def multiline_output(args):
    return (args.hist or args.stats or args.dump or args.metadata)
