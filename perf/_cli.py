from __future__ import division, print_function, absolute_import

import os.path
import sys

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
        for loops, value in run.warmups:
            lines.append("- %s: %s"
                         % (format_number(loops, 'loop'),
                            format_timedelta(value)))
        return lines

    show_warmup = (verbose >= 0)

    total_loops = run.get_total_loops()
    inner_loops = run._get_inner_loops()

    def format_values(values, percent=True):
        values_str = [bench.format_value(value) for value in values]
        if not percent:
            return values_str

        mean = bench.mean()
        max_delta = mean * 0.05
        for index, value in enumerate(values):
            if raw:
                value = float(value) / total_loops
            delta = float(value) - mean
            if abs(delta) > max_delta:
                values_str[index] += ' (%+.0f%%)' % (delta * 100 / mean)
        return values_str

    values = run.values
    if raw:
        warmups = [('%s (%s)'
                    % (bench.format_value(raw_value),
                       format_number(loops, 'loop')))
                   for loops, raw_value in run.warmups]
        values = [value * total_loops for value in values]
    else:
        warmups = run.warmups
        if warmups:
            warmups = [raw_value / (loops * inner_loops)
                       for loops, raw_value in warmups]
            warmups = format_values(warmups)
    values = format_values(values)

    if raw:
        name = 'raw values'
    else:
        name = 'values'
    text = '%s (%s): %s' % (name, len(values), ', '.join(values))
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

    empty_line_written = False
    for run_index, run in enumerate(runs, 1):
        if quiet and run._is_calibration():
            continue
        if not empty_line_written:
            empty_line_written = True
            empty_line(lines)
        format_run(bench, run_index, run,
                   common_metadata=common_metadata,
                   verbose=verbose, raw=raw, lines=lines)

    return lines


def _format_stats(bench, lines):
    fmt = bench.format_value
    values = bench.get_values()

    nrun = bench.get_nrun()
    nvalue = len(values)
    mean = bench.mean()

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

    # Raw value minimize/maximum
    raw_values = bench._get_raw_values()
    lines.append("Raw value minimum: %s" % bench.format_value(min(raw_values)))
    lines.append("Raw value maximum: %s" % bench.format_value(max(raw_values)))
    lines.append('')

    # Number of values
    lines.append("Number of runs: %s" % format_number(nrun))
    lines.append("Total number of values: %s" % format_number(nvalue))

    nvalue_per_run = bench._get_nvalue_per_run()
    text = format_number(nvalue_per_run)
    if isinstance(nvalue_per_run, float):
        text += ' (average)'
    lines.append('Number of values per run: %s' % text)

    nwarmup = bench._get_nwarmup()
    text = format_number(nwarmup)
    if isinstance(nwarmup, float):
        text += ' (average)'
    lines.append('Number of warmups per run: %s' % text)

    # Loop iterations per value
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

    lines.append("Loop iterations per value: %s" % text)
    lines.append('')

    # Minimum
    def format_limit(mean, value):
        return ("%s (%+.0f%% of the mean)"
                % (fmt(value), (value - mean) * 100.0 / mean))

    lines.append("Minimum: %s" % format_limit(mean, min(values)))

    # Median +- MAD
    median = bench.median()
    if len(values) > 2:
        median_abs_dev = bench.median_abs_dev()
        lines.append("Median +- MAD: %s +- %s"
                     % bench.format_values((median, median_abs_dev)))
    else:
        lines.append("Mean: %s" % bench.format_value(median))

    # Mean +- std dev
    mean = bench.mean()
    if len(values) > 2:
        stdev = bench.stdev()
        lines.append("Mean +- std dev: %s +- %s"
                     % bench.format_values((mean, stdev)))
    else:
        lines.append("Mean: %s" % bench.format_value(mean))

    # Maximum
    lines.append("Maximum: %s" % format_limit(mean, max(values)))
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

    all_values = []
    for bench, title in benchmarks:
        all_values.extend(bench.get_values())
    all_min = min(all_values)
    all_max = max(all_values)
    value_k = float(all_max - all_min) / bins
    if not value_k:
        value_k = 1.0

    def value_bucket(value):
        # round towards zero (ROUND_DOWN)
        return int(value / value_k)

    bucket_min = value_bucket(all_min)
    bucket_max = value_bucket(all_max)
    if lines is None:
        lines = []

    for item in benchmarks:
        empty_line(lines)

        bench, title = item
        if title:
            lines.append("[ %s ]" % title)

        values = bench.get_values()

        buckets = [value_bucket(value) for value in values]
        counter = collections.Counter(buckets)
        count_max = max(counter.values())
        count_width = len(str(count_max))

        value_width = max([len(bench.format_value(bucket * value_k))
                           for bucket in range(bucket_min, bucket_max + 1)])
        width = columns - value_width

        line = ': %s #' % count_max
        width = columns - (value_width + len(line))
        if not extend:
            width = min(width, 79)
        width = max(width, 3)
        line_k = float(width) / max(counter.values())
        for bucket in range(bucket_min, bucket_max + 1):
            count = counter.get(bucket, 0)
            linelen = int(round(count * line_k))
            text = bench.format_value(bucket * value_k)
            line = ('#' * linelen) or '|'
            lines.append("{:>{}}: {:>{}} {}".format(text, value_width,
                                                    count, count_width, line))

    return lines


def format_checks(bench, lines=None):
    if lines is None:
        lines = []
    values = bench.get_values()
    mean = bench.mean()
    warnings = []
    warn = warnings.append

    # Display a warning if the standard deviation is larger than 10%
    if len(values) >= 2:
        stdev = bench.stdev()
        percent = stdev * 100.0 / mean
        if percent >= 10.0:
            warn("the standard deviation (%s) is %.0f%% of the mean (%s)"
                 % (bench.format_value(stdev), percent, bench.format_value(mean)))

    # Minimum and maximum, detect obvious outliers
    for minimum, value in (
        ('minimum', min(values)),
        ('maximum', max(values)),
    ):
        percent = (value - mean) * 100.0 / mean
        if abs(percent) >= 25:
            if percent >= 0:
                text = "%.0f%% greater" % (percent)
            else:
                text = "%.0f%% smaller" % (-percent)
            warn("the %s (%s) is %s than the mean (%s)"
                 % (minimum, bench.format_value(value), text, bench.format_value(mean)))

    # Check that the shortest value took at least 1 ms
    if bench.get_unit() == 'second':
        shortest = min(bench._get_raw_values())
        if shortest < 1e-3:
            warn("the shortest raw value only took %s"
                 % bench.format_value(shortest))

    if warnings:
        empty_line(lines)
        lines.append("WARNING: the benchmark result may be unstable")
        for msg in warnings:
            lines.append("* %s" % msg)
        empty_line(lines)
        lines.append("Try to rerun the benchmark with more runs, values "
                     "and/or loops.")
        lines.append("Run '%s -m perf system tune' command to reduce "
                     "the system jitter."
                     % os.path.basename(sys.executable))
        lines.append("Use perf stats, perf dump and perf hist to analyze results.")
        lines.append("Use --quiet option to hide these warnings.")

    # Warn if nohz_full+intel_pstate combo if found in cpu_config metadata
    for run in bench._runs:
        cpu_config = run._metadata.get('cpu_config')
        if not cpu_config:
            continue
        if 'nohz_full' in cpu_config and 'intel_pstate' in cpu_config:
            empty_line(lines)
            warn("WARNING: nohz_full is enabled on CPUs which use the "
                 "intel_pstate driver, whereas intel_pstate is incompatible "
                 "with nohz_full")
            warn("CPU config: %s" % cpu_config)
            warn("See https://bugzilla.redhat.com/show_bug.cgi?id=1378529")
            break

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


# FIXME: remove this function?
def multiline_output(args):
    return (args.hist or args.stats or args.dump or args.metadata)
