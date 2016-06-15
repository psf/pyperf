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
    hist.add_argument('filename', type=str,
                      help='Result JSON file')

    hist_scipy = subparsers.add_parser('hist_scipy')
    hist_scipy.add_argument('--scipy', action="store_true",
                            help="Draw the histogram using numy, scipy and pylab")
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
        perf._display_metadata(result.metadata)
        print()

    if args.verbose > 1:
        perf._display_runs(result)
        print()

    perf._display_benchmark_avg(result, verbose=args.verbose)


def _result_sort_key(result):
    return (result.mean(), result.name or '')


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

    # Compute means
    ref_samples = ref_result.get_samples()
    ref_avg = ref_result.mean()
    last_index = len(results) - 1
    for index, changed_result in enumerate(results[1:], 1):
        changed_samples = changed_result.get_samples()
        changed_avg = changed_result.mean()
        text = ("Median +- std dev: [%s] %s -> [%s] %s"
                % (ref_result.name,
                   ref_result.format(verbose=args.verbose),
                   changed_result.name,
                   changed_result.format(verbose=args.verbose)))

        # avoid division by zero
        if ref_avg and changed_avg:
            if changed_avg == ref_avg:
                text = "%s: same speed" % (text,)
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
    try:
        import boltons.statsutils
    except ImportError:
        boltons = None
    import matplotlib.pyplot as plt
    import pylab
    import scipy.stats as stats

    samples = result.get_samples()
    samples = sorted(samples)

    if boltons is not None:
        # median +- MAD
        median = statistics.median(samples)
        mad = boltons.statsutils.Stats(samples).median_abs_dev
        fit = stats.norm.pdf(samples, median, mad)
        pylab.plot(samples, fit, '-o', label='median-mad')

    # median +- std dev
    fit2 = stats.norm.pdf(samples, median, statistics.stdev(samples, median))
    pylab.plot(samples, fit2, '-v', label='median-stdev')

    # mean + std dev
    fit3 = stats.norm.pdf(samples, result.mean(), statistics.stdev(samples))
    pylab.plot(samples, fit3, '-+', label='mean-stdev')

    plt.legend(loc='upper right', shadow=True, fontsize='x-large')
    pylab.hist(samples, bins=25, normed=True)
    pylab.show()

def display_histogram_text(args, result):
    import collections
    import shutil

    samples = result.get_samples()
    avg = result.mean()
    if hasattr(shutil, 'get_terminal_size'):
        columns, lines = shutil.get_terminal_size()
    else:
        columns = 80
        lines = 25

    bins = max(lines - 3, 3)
    if not args.extend:
        bins = min(bins, 25)
    sample_k = float(max(samples) - min(samples)) / bins

    def bucket(value):
        # round towards zero (ROUND_DOWN)
        return int(value / sample_k)

    counter = collections.Counter([bucket(value) for value in samples])
    count_max = max(counter.values())
    count_width = len(str(count_max))

    line = '%s: %s #' % (result._format_sample(avg), count_max)
    width = columns - len(line)
    if not args.extend:
        width = min(width, 79)
    width = max(width, 3)
    line_k = float(width) / max(counter.values())
    for ms in range(min(counter), max(counter)+1):
        count = counter.get(ms, 0)
        linelen = int(round(count * line_k))
        text = result._format_sample(float(ms) * sample_k)
        line = ('#' * linelen) or '|'
        print("{}: {:>{}} {}".format(text, count, count_width, line))


def display_stats(args, result):
    try:
        import boltons.statsutils
    except ImportError:
        boltons = None

    fmt = result._format_sample
    samples = result.get_samples()

    nsample = len(samples)
    print("Number of samples: %s" % perf._format_number(nsample))
    # FIXME: add % compared to median/mean to min&max
    print("Minimum %s" % fmt(min(samples)))
    print("Maximum %s" % fmt(max(samples)))
    print()

    median = result.median()
    print("Median +- std dev: %s +- %s"
          % perf._format_timedeltas([median, statistics.stdev(samples, median)]))

    print("Mean + std dev: %s +- %s"
          % perf._format_timedeltas([result.mean(),
                                     statistics.stdev(samples)]))
    if boltons is not None:
        stats = boltons.statsutils.Stats(samples)
        print("Median +- MAD: %s +- %s"
              % perf._format_timedeltas([median, stats.median_abs_dev]))

    if boltons is not None:
        print()
        print("Skewness: %.2f"
              % boltons.statsutils.skewness(samples))


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
        display_histogram_text(args, result)
    elif action == 'hist_scipy':
        result = parse_results(args.filename)
        display_histogram_scipy(args, result)
    elif action == 'stats':
        result = parse_results(args.filename)
        display_stats(args, result)
    elif action == 'metadata':
        collect_metadata()
    else:
        parser.print_usage()
        sys.exit(1)


main()
