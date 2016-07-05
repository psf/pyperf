from __future__ import print_function
import argparse
import sys

import statistics

import perf.text_runner


def create_parser():
    parser = argparse.ArgumentParser(description='Display benchmark results.',
                                     prog='-m perf')
    subparsers = parser.add_subparsers(dest='action')

    cmd = subparsers.add_parser('show')
    cmd.add_argument('-v', '--verbose', action="store_true",
                     help='enable verbose mode')
    cmd.add_argument('-m', '--metadata', dest='metadata',
                     action="store_true",
                     help="Show metadata.")
    cmd.add_argument('-g', '--hist', action="store_true",
                     help='display an histogram of samples')
    cmd.add_argument('-t', '--stats', action="store_true",
                     help='display statistics (min, max, ...)')
    cmd.add_argument('-b', '--name',
                     help='only display the benchmark called NAME '
                          '(defaut: display all benchmarks of a suite)')
    cmd.add_argument('filename', type=str,
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

    # compare, compare_to
    for command in ('compare', 'compare_to'):
        cmd= subparsers.add_parser(command)
        cmd.add_argument('-v', '--verbose', action="store_true",
                         help='enable verbose mode')
        cmd.add_argument('-m', '--metadata', dest='metadata',
                         action="store_true",
                         help="Show metadata.")
        cmd.add_argument('ref_filename', type=str,
                             help='Reference JSON file')
        cmd.add_argument('changed_filenames', metavar="changed_filename",
                             type=str, nargs='+',
                             help='Changed JSON file')

    # stats
    stats = subparsers.add_parser('stats')
    stats.add_argument('filename', type=str,
                       help='Result JSON file')

    # metadata
    subparsers.add_parser('metadata')

    # timeit
    cmd = subparsers.add_parser('timeit')
    timeit_runner = perf.text_runner.TextRunner(name='timeit', _argparser=cmd)
    cmd.add_argument('-s', '--setup', action='append', default=[],
                     help='setup statements')
    cmd.add_argument('stmt', nargs='+',
                     help='executed statements')

    return parser, timeit_runner


def load_result(filename, default_name=None):
    result = perf.Benchmark.load(filename)

    if not result.name and filename != "-":
        name = filename
        if name.lower().endswith('.json'):
            name = name[:-5]
        if name:
            result.name = name
    if not result.name and default_name:
        result.name = default_name

    return result


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


def _display_common_metadata(benchmarks):
    metadatas = [dict(result.metadata) for result in benchmarks]
    for metadata in metadatas:
        # don't display name as metadata, it's already displayed
        metadata.pop('name', None)

    common_metadata = _common_metadata(metadatas)
    if common_metadata:
        perf.text_runner._display_metadata(common_metadata,
                               header='Common metadata:')
        print()

    for key in common_metadata:
        for metadata in metadatas:
            metadata.pop(key, None)

    return metadatas


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
        metadatas = _display_common_metadata(results)

        for result, metadata in zip(results, metadatas):
            perf.text_runner._display_metadata(metadata,
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
                % (ref_result.name, ref_result.format(),
                   changed_result.name, changed_result.format()))

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


def cmd_metadata():
    from perf import metadata as perf_metadata
    metadata = {}
    perf_metadata.collect_metadata(metadata)
    perf.text_runner._display_metadata(metadata)


def cmd_show(args):
    suite = perf.BenchmarkSuite.load(args.filename)
    if args.name:
        try:
            benchmark = suite[args.name]
        except KeyError:
            print("ERROR: %s does not contain a callback called %r"
                  % (suite.filename, args.name))
            sys.exit(1)
        benchmarks = (benchmark,)
    else:
        benchmarks = suite.get_benchmarks()
    many_benchmarks = (len(benchmarks) > 1)

    if args.metadata:
        if many_benchmarks:
            metadatas = _display_common_metadata(benchmarks)
        else:
            metadatas = [benchmarks[0].metadata]

    for index, benchmark in enumerate(benchmarks):
        if not benchmark.name:
            benchmark.name = "<benchmark #%s>" % (1 + index)

        if many_benchmarks:
            print("[%s]" % benchmark.name)

        if args.metadata:
            metadata = metadatas[index]
            perf.text_runner._display_metadata(metadata)
            print()

        perf.text_runner._display_benchmark(benchmark,
                                            hist=args.hist,
                                            stats=args.stats,
                                            runs=bool(args.verbose))
        if many_benchmarks and index != len(benchmarks) - 1:
            print()


def cmd_timeit(args, timeit_runner):
    import perf._timeit
    timeit_runner.args = args
    timeit_runner._process_args()
    perf._timeit.main(timeit_runner)


def cmd_stats(args):
    bench = perf.Benchmark.load(args.filename)
    perf.text_runner._display_stats(bench)


def main():
    parser, timeit_runner = create_parser()
    args = parser.parse_args()
    action = args.action
    if action == 'show':
        cmd_show(args)
    elif action in ('compare', 'compare_to'):
        ref_result = load_result(args.ref_filename, '<file#1>')
        results = [ref_result]
        for index, filename in enumerate(args.changed_filenames, 2):
            result = load_result(filename, '<file#%s>' % index)
            results.append(result)
        compare_results(args, results, action == 'compare')
    elif action == 'hist':
        benchmarks = []
        for filename in args.filenames:
            suite = perf.BenchmarkSuite.load(filename)
            benchmarks.extend(suite.get_benchmarks())
        perf.text_runner._display_histogram(benchmarks, bins=args.bins,
                                            extend=args.extend)
    elif action == 'stats':
        cmd_stats(args)
    elif action == 'metadata':
        cmd_metadata()
    elif action == 'timeit':
        cmd_timeit(args, timeit_runner)
    else:
        parser.print_usage()
        sys.exit(1)


main()
