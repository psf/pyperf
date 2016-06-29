from __future__ import print_function
import argparse
import sys

import statistics

import perf


def create_parser():
    parser = argparse.ArgumentParser(description='Display benchmark results.',
                                     prog='-m perf')
    subparsers = parser.add_subparsers(dest='action')

    show = subparsers.add_parser('show')
    show.add_argument('filename', type=str,
                      help='Result JSON file')

    hist = subparsers.add_parser('hist')
    hist.add_argument('--extend', action="store_true",
                      help="Extend the histogram to fit the terminal")
    hist.add_argument('-n', '--bins', type=int, default=None,
                      help='Number of histogram bars (default: 25, or less '
                           'depeding on the terminal size)')
    hist.add_argument('filenames', metavar='filename',
                      type=str, nargs='+',
                      help='Result JSON file')

    hist_scipy = subparsers.add_parser('hist_scipy')
    hist_scipy.add_argument('-n', '--bins', type=int, default=25,
                            help="Number of histogram bars (default: 25)")
    hist_scipy.add_argument('filename', type=str,
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

    metadata = subparsers.add_parser('metadata')

    # Add arguments to multiple commands
    for cmd in (show, compare, compare_to):
        cmd.add_argument('-v', '--verbose', action='count', default=0,
                         help='an integer for the accumulator')

    for cmd in (show, compare, compare_to):
        cmd.add_argument('-m', '--metadata', dest='metadata',
                         action="store_true",
                         help="Show metadata.")

    return parser


def load_result(filename, default_name=None):
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
        perf._display_metadata(result.metadata)
        print()

    if args.verbose > 1:
        perf._display_runs(result)
        print()

    perf._display_benchmark_avg(result, verbose=args.verbose)


def _result_sort_key(result):
    return (result.median(), result.name or '')


def _common_metadata(metadatas):
    if not metadatas:
        return dict()

    metadata = dict(metadatas[0])
    for run_metadata in metadatas[1:]:
        for key, run_value in run_metadata.items():
            try:
                value = metadata[key]
            except KeyError:
                pass
            else:
                if run_value != value:
                    del metadata[key]
    return metadata


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
        metadatas = [result.metadata for result in results]

        common_metadata = _common_metadata(metadatas)
        perf._display_metadata(common_metadata,
                               header='Common metadata:')
        print()

        for key in common_metadata:
            for metadata in metadatas:
                metadata.pop(key, None)

        for result, metadata in zip(results, metadatas):
            perf._display_metadata(metadata,
                                   header='%s metadata:' % result.name)
            print()

    # Compute medians
    ref_samples = ref_result.get_samples()
    ref_avg = ref_result.median()
    last_index = len(results) - 1
    for index, changed_result in enumerate(results[1:], 1):
        changed_samples = changed_result.get_samples()
        changed_avg = changed_result.median()
        text = ("Median +- std dev: [%s] %s -> [%s] %s"
                % (ref_result.name,
                   ref_result.format(verbose=args.verbose),
                   changed_result.name,
                   changed_result.format(verbose=args.verbose)))

        # avoid division by zero
        if changed_avg == ref_avg:
            text = "%s: no change" % text
        elif changed_avg < ref_avg:
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


def display_histogram_scipy(args, result):
    import matplotlib.pyplot as plt
    import pylab
    import scipy.stats as stats

    samples = result.get_samples()
    samples = sorted(samples)

    median = result.median()
    fit = stats.norm.pdf(samples, median, statistics.stdev(samples, median))
    pylab.plot(samples, fit, '-o', label='median-stdev')

    plt.legend(loc='upper right', shadow=True, fontsize='x-large')
    pylab.hist(samples, bins=args.bins, normed=True)
    pylab.show()

def display_histogram_text(args, results):
    import collections
    import shutil

    if hasattr(shutil, 'get_terminal_size'):
        columns, lines = shutil.get_terminal_size()
    else:
        columns = 80
        lines = 25

    bins = args.bins
    if not bins:
        bins = max(lines - 3, 3)
        if not args.extend:
            bins = min(bins, 25)

    all_samples = []
    for result in results:
        all_samples.extend(result.get_samples())
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

    for index, result in enumerate(results):
        if len(results) > 1:
            print("[ %s ]" % result.name)

        samples = result.get_samples()

        counter = collections.Counter([sample_bucket(value) for value in samples])
        count_max = max(counter.values())
        count_width = len(str(count_max))

        line = '%s: %s #' % (result._format_sample(max(samples)), count_max)
        width = columns - len(line)
        if not args.extend:
            width = min(width, 79)
        width = max(width, 3)
        line_k = float(width) / max(counter.values())
        for bucket in range(bucket_min, bucket_max + 1):
            count = counter.get(bucket, 0)
            linelen = int(round(count * line_k))
            text = result._format_sample(float(bucket) * sample_k)
            line = ('#' * linelen) or '|'
            print("{}: {:>{}} {}".format(text, count, count_width, line))

        if index != len(results) -1:
            print()



def display_stats(args, result):
    fmt = result._format_sample
    samples = result.get_samples()

    nsample = len(samples)
    print("Number of samples: %s" % perf._format_number(nsample))
    print()

    median = result.median()

    def format_min(median, value):
        return "%s (%+.1f%%)" % (fmt(value), (value - median) * 100 / median)

    print("Minimum: %s" % format_min(median, min(samples)))

    def fmt_stdev(value, dev):
        left = median - dev
        right = median + dev
        return ("%s +- %s (%s .. %s)"
                % perf._format_timedeltas((median, dev, left, right)))

    print("Median +- std dev: %s"
          % fmt_stdev(median, statistics.stdev(samples, median)))

    print("Maximum: %s" % format_min(median, max(samples)))


def collect_metadata():
    from perf import metadata as perf_metadata
    metadata = {}
    perf_metadata.collect_metadata(metadata)
    perf._display_metadata(metadata)


def main():
    parser = create_parser()
    args = parser.parse_args()
    action = args.action
    if action == 'show':
        result = load_result(args.filename)
        display_result(args, result)
    elif action in ('compare', 'compare_to'):
        ref_result = load_result(args.ref_filename, '<file#1>')
        results = [ref_result]
        for index, filename in enumerate(args.changed_filenames, 2):
            result = load_result(filename, '<file#%s>' % index)
            results.append(result)
        compare_results(args, results, action == 'compare')
    elif action == 'hist':
        results = [load_result(filename) for filename in args.filenames]
        display_histogram_text(args, results)
    elif action == 'hist_scipy':
        result = load_result(args.filename)
        display_histogram_scipy(args, result)
    elif action == 'stats':
        result = load_result(args.filename)
        display_stats(args, result)
    elif action == 'metadata':
        collect_metadata()
    else:
        parser.print_usage()
        sys.exit(1)


main()
