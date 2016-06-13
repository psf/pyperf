from __future__ import print_function
import argparse
import json
import sys

import perf


def create_parser():
    parser = argparse.ArgumentParser(description='Display benchmark results.',
                                     prog='-m perf')
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help='an integer for the accumulator')
    parser.add_argument('-M', '--no-metadata', dest='metadata', action="store_false",
                        default=True,
                        help="Don't show metadata.")
    subparsers = parser.add_subparsers(dest='action')

    show = subparsers.add_parser('show')
    show.add_argument('filename', type=str,
                      help='Result JSON file')

    hist = subparsers.add_parser('hist')
    hist.add_argument('--scipy', action="store_true",
                      help="Draw the histogram using numy, scipy and pylab")
    hist.add_argument('filename', type=str,
                      help='Result JSON file')

    compare = subparsers.add_parser('compare')
    compare.add_argument('ref_filename', type=str,
                         help='Reference JSON file')
    compare.add_argument('changed_filenames', metavar="changed_filename",
                         type=str, nargs='+',
                         help='Changed JSON file')

    compare_to = subparsers.add_parser('compare_to')
    compare_to.add_argument('ref_filename', type=str,
                            help='Reference JSON file')
    compare_to.add_argument('changed_filenames', metavar="changed_filename",
                            type=str, nargs='+',
                            help='Changed JSON file')

    stats = subparsers.add_parser('stats')
    stats.add_argument('filename', type=str,
                       help='Result JSON file')

    return parser


def parse_results(filename, default_name=None):
    if filename != '-':
        fp = open(filename)
    else:
        fp = sys.stdin
    with fp:
        result = perf.Benchmark.json_load_from(fp)

    if not result.name and filename != "-":
        name = filename
        if name.lower().endswith('.json'):
            name = name[:-5]
        if name:
            result.name = name
    if not result.name and default_name:
        result.name = default_name

    return result


def display_result(args, result):
    if args.metadata:
        perf._display_metadata(result.get_metadata())

    if args.verbose:
        nrun = len(result.runs)
        for index, run in enumerate(result.runs, 1):
            text = perf._very_verbose_run(run)
            print("Run %s/%s: %s" % (index, nrun, text))
        print()

    perf._display_benchmark_avg(result, verbose=args.verbose)


def _result_sort_key(result):
    samples = result.get_samples()
    return perf.mean(samples)


def compare_results(args, results, sort_results):
    if sort_results:
        results.sort(key=_result_sort_key)

    ref_result = results[0]

    if sort_results:
        print("Reference (best): %s" % ref_result.name)
    else:
        print("Reference: %s" % ref_result.name)
        for index, result in enumerate(results[1:], 1):
            if index > 1:
                prefix = 'Changed #%s' % index
            else:
                prefix = 'Changed'
            print("%s: %s" % (prefix, result.name))
    print()

    if args.metadata:
        metadatas = [result.get_metadata() for result in results]

        common_metadata = perf._common_metadata(metadatas)
        perf._display_metadata(common_metadata,
                               header='Common metadata:')

        for key in common_metadata:
            for metadata in metadatas:
                metadata.pop(key, None)

        for result, metadata in zip(results, metadatas):
            perf._display_metadata(metadata,
                                   header='%s metadata:' % result.name)

    # Compute means
    ref_samples = ref_result.get_samples()
    ref_avg = perf.mean(ref_samples)
    last_index = len(results) - 1
    for index, changed_result in enumerate(results[1:], 1):
        changed_samples = changed_result.get_samples()
        changed_avg = perf.mean(changed_samples)
        text = ("Average: [%s] %s -> [%s] %s"
                % (ref_result.name,
                   ref_result.format(verbose=args.verbose),
                   changed_result.name,
                   changed_result.format(verbose=args.verbose)))

        # avoid division by zero
        if ref_avg and changed_avg:
            if changed_avg < ref_avg:
                text = "%s: %.1fx faster" % (text, ref_avg /  changed_avg)
            else:
                text= "%s: %.1fx slower" % (text, changed_avg / ref_avg)
        print(text)

        # significant?
        significant, t_score = perf.is_significant(ref_samples, changed_samples)
        if significant:
            print("Significant (t=%.2f)" % t_score)
        else:
            print("Not significant!")

        if index != last_index:
            print()


def _display_histogram_scipy(args, samples):
    import boltons.statsutils
    import matplotlib.pyplot as plt
    import numpy
    import pylab
    import scipy.stats as stats
    import statistics

    avg = numpy.mean(samples)
    for i in range(2, -9, -1):
        if avg >= 10.0 ** i:
            i -= 1
            break
    else:
        i = -9
    sample_k = 10.0 ** i
    print("Sample factor: 10^%s" % i)
    samples = [sample / sample_k for sample in samples]
    samples.sort()

    samples_stats = boltons.statsutils.Stats(samples)

    # median +- MAD
    fit = stats.norm.pdf(samples, samples_stats.median, samples_stats.median_abs_dev)
    pylab.plot(samples, fit, '-o', label='median-mad')

    # median +- std dev
    fit2 = stats.norm.pdf(samples, samples_stats.median, statistics.stdev(samples, samples_stats.median))
    pylab.plot(samples, fit2, '-v', label='median-stdev')

    # mean + std dev
    fit3 = stats.norm.pdf(samples, perf.mean(samples), perf.stdev(samples))
    pylab.plot(samples, fit3, '-+', label='mean-stdev')

    legend = plt.legend(loc='upper right', shadow=True, fontsize='x-large')
    pylab.hist(samples, bins=25, normed=True)
    pylab.show()

def _display_histogram_text(args, samples):
    import collections
    import shutil

    if hasattr(shutil, 'get_terminal_size'):
        columns = shutil.get_terminal_size()[0]
    else:
        columns = 80

    nsample = len(samples)
    avg = perf.mean(samples)
    stdev = perf.stdev(samples)

    for i in range(2, -9, -1):
        if avg >= 10.0 ** i:
            break
    else:
        i = -9
    sample_k = 10.0 ** (i - 2)

    def bucket(value):
        return int(round(value / sample_k))

    counter = collections.Counter([bucket(value) for value in samples])
    count_max = max(counter.values())
    count_width = len(str(count_max))

    line = '%s: %s #' % (perf._format_timedelta(avg), count_max)
    width = max(columns - len(line), 3)
    line_k = float(width) / max(counter.values())
    for ms in range(min(counter), max(counter)+1):
        count = counter.get(ms, 0)
        linelen = int(round(count * line_k))
        text = perf._format_timedelta(float(ms) * sample_k)
        line = ('#' * linelen) or '|'
        print("{}: {:>{}} {}".format(text, count, count_width, line))

    print()
    print("Total number of samples: %s" % perf._format_number(len(samples)))


def display_histogram(args, result):
    samples = result.get_samples()
    if args.scipy:
        _display_histogram_scipy(args, samples)
    else:
        _display_histogram_text(args, samples)


def display_stats(args, result):
    import boltons.statsutils
    # FIXME: statistics doesn't exist in Python 2
    import statistics

    fmt = perf._format_timedelta
    samples = result.get_samples()
    stats = boltons.statsutils.Stats(samples)

    nsample = len(samples)
    print("Number of samples: %s" % perf._format_number(nsample))
    # FIXME: add % compared to median/mean to min&max
    print("Minimum %s" % fmt(min(samples)))
    print("Maximum %s" % fmt(max(samples)))
    print()
    print("Mean + std dev: %s +- %s"
          % perf._format_timedeltas([perf.mean(samples),
                                     perf.stdev(samples)]))
    print("Median +- std dev: %s +- %s"
          % perf._format_timedeltas([stats.median, statistics.stdev(samples, stats.median)]))
    print("Median +- MAD: %s +- %s"
          % perf._format_timedeltas([stats.median, stats.median_abs_dev]))
    print()

    print("Skewness: %.2f"
          % boltons.statsutils.skewness(samples))
    print()

    def format_count(count):
        return ("%.1f%% (%s/%s)"
                % (float(count) * 100 / nsample,
                   count, nsample))

    def counters(avg, stdev):
        left = avg - stdev
        right = avg + stdev
        count = 0
        for sample in samples:
            if left <= sample <= right:
                count += 1
        return format_count(count)

    median = stats.median
    print("Mean+stdev range buckets: %s" % counters(perf.mean(samples), perf.stdev(samples)))
    print("Median+mad range buckets: %s" % counters(median, stats.median_abs_dev))
    print("Median+stdev range buckets: %s" % counters(median, statistics.stdev(samples, median)))


def main():
    parser = create_parser()
    args = parser.parse_args()
    action = args.action
    if action == 'show':
        result = parse_results(args.filename)
        display_result(args, result)
    elif action in ('compare', 'compare_to'):
        ref_result = parse_results(args.ref_filename, '<file#1>')
        results = [ref_result]
        for index, filename in enumerate(args.changed_filenames, 2):
            result = parse_results(filename, '<file#%s>' % index)
            results.append(result)
        compare_results(args, results, action == 'compare')
    elif action == 'hist':
        result = parse_results(args.filename)
        display_histogram(args, result)
    elif action == 'stats':
        result = parse_results(args.filename)
        display_stats(args, result)
    else:
        parser.print_usage()
        sys.exit(1)


main()
