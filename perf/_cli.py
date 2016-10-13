from __future__ import division, print_function, absolute_import

import statistics

from perf._utils import format_seconds, format_number, format_timedelta


def display_title(title, level=1):
    print(title)
    if level == 1:
        char = '='
    else:
        char = '-'
    print(char * len(title))
    print()


def display_run(bench, run_index, run,
                common_metadata=None, raw=False, verbose=0, file=None):
    if run._is_calibration():
        print("Run %s: calibrate" % (run_index,), file=file)
        for loops, sample in run.warmups:
            print("- %s: %s" % (format_number(loops, 'loop'),
                                format_timedelta(sample)))
        return

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
    print(text, file=file)

    if verbose > 0:
        prefix = '  '
        metadata = run.get_metadata()
        for key in sorted(metadata):
            if common_metadata and key in common_metadata:
                continue
            value = metadata[key]
            print('%s%s: %s' % (prefix, key, value))


def display_runs(bench, quiet=False, verbose=False, raw=False, file=None):
    runs = bench.get_runs()
    if quiet:
        verbose = -1
    elif verbose:
        verbose = 1
    else:
        verbose = 0

    if verbose > 0:
        common_metadata = bench.get_metadata()
        print("Metadata:", file=file)
        for key in sorted(common_metadata):
            value = common_metadata[key]
            print('  %s: %s' % (key, value), file=file)
        print(file=file)
    else:
        common_metadata = None

    for run_index, run in enumerate(runs, 1):
        display_run(bench, run_index, run,
                    common_metadata=common_metadata,
                    verbose=verbose, raw=raw, file=file)


def display_stats(bench, file=None):
    fmt = bench.format_sample
    samples = bench.get_samples()

    nrun = bench.get_nrun()
    nsample = len(samples)
    median = bench.median()

    # Total duration
    duration = bench.get_total_duration()
    if duration:
        print("Total duration: %s" % format_seconds(duration),
              file=file)

    # Start/End dates
    dates = bench.get_dates()
    if dates:
        start, end = dates
        print("Start date: %s" % start.isoformat())
        print("End date: %s" % end.isoformat())

    # Raw sample minimize/maximum
    raw_samples = bench._get_raw_samples()
    print("Raw sample minimum: %s" % bench.format_sample(min(raw_samples)),
          file=file)
    print("Raw sample maximum: %s" % bench.format_sample(max(raw_samples)),
          file=file)
    print(file=file)

    # Number of samples
    print("Number of runs: %s" % format_number(nrun), file=file)
    print("Total number of samples: %s" % format_number(nsample),
          file=file)

    nsample_per_run = bench._get_nsample_per_run()
    text = format_number(nsample_per_run)
    if isinstance(nsample_per_run, float):
        text += ' (average)'
    print('Number of samples per run: %s' % text, file=file)

    nwarmup = bench._get_nwarmup()
    text = format_number(nwarmup)
    if isinstance(nwarmup, float):
        text += ' (average)'
    print('Number of warmups per run: %s' % text, file=file)

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

    print("Loop iterations per sample: %s" % text, file=file)
    print(file=file)

    # Minimum
    def format_limit(median, value):
        return "%s (%+.0f%%)" % (fmt(value), (value - median) * 100.0 / median)

    print("Minimum: %s" % format_limit(median, min(samples)), file=file)

    # Median +- std dev
    print(str(bench), file=file)

    # Mean +- std dev
    mean = statistics.mean(samples)
    if len(samples) > 2:
        stdev = statistics.stdev(samples, mean)
        print("Mean +- std dev: %s +- %s"
              % bench.format_samples((mean, stdev)),
              file=file)
    else:
        print("Mean: %s" % bench.format_sample(mean), file=file)

    # Maximum
    print("Maximum: %s" % format_limit(median, max(samples)), file=file)


def display_histogram(benchmarks, bins=20, extend=False, file=None):
    import collections
    import shutil

    if hasattr(shutil, 'get_terminal_size'):
        columns, lines = shutil.get_terminal_size()
    else:
        columns = 80
        lines = 25

    if not bins:
        bins = max(lines - 3, 3)
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

    for index, item in enumerate(benchmarks):
        bench, title = item
        if title:
            print("[ %s ]" % title, file=file)

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
            print("{:>{}}: {:>{}} {}".format(text, sample_width,
                                             count, count_width, line),
                  file=file)

        if index != len(benchmarks) - 1:
            print(file=file)


def warn_if_bench_unstable(bench):
    warnings = []
    warn = warnings.append
    samples = bench.get_samples()

    # Display a warning if the standard deviation is larger than 10%
    median = bench.median()
    # Avoid division by zero
    if median and len(samples) > 1:
        k = statistics.stdev(samples) / median
        if k > 0.10:
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
            warn("")

    # Check that the shortest sample took at least 1 ms
    shortest = min(bench._get_raw_samples())
    text = bench.format_sample(shortest)
    if shortest < 1e-3:
        if shortest < 1e-6:
            warn("ERROR: the benchmark may be very unstable, "
                 "the shortest raw sample only took %s" % text)
        else:
            warn("WARNING: the benchmark may be unstable, "
                 "the shortest raw sample only took %s" % text)
        warn("Try to rerun the benchmark with more loops "
             "or increase --min-time")
        warn("")

    return warnings


def display_metadata(metadata, header="Metadata:", file=None):
    if not metadata:
        return
    print(header, file=file)
    for key, value in sorted(metadata.items()):
        print("- %s: %s" % (key, value), file=file)


def display_benchmark(bench, file=None, check_unstable=True, metadata=False,
                      dump=False, stats=False, hist=False):
    if metadata:
        display_metadata(bench.get_metadata(), file=file)
        print(file=file)

    if dump:
        display_runs(bench, file=file)
        print(file=file)

    if hist:
        display_histogram([(bench, None)], file=file)
        print(file=file)

    if stats:
        display_stats(bench, file=file)
        print(file=file)

    if check_unstable:
        warnings = warn_if_bench_unstable(bench)
        for line in warnings:
            print(line, file=file)

    print(str(bench), file=file)


def get_benchmark_name(benchmark):
    # FIXME: better fallback value
    return benchmark.get_name() or '<no name>'


def multiline_output(args):
    return (args.hist or args.stats or args.dump or args.metadata)
