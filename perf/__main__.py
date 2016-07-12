from __future__ import print_function
import argparse
import collections
import functools
import errno
import os.path
import sys

import statistics

import perf.text_runner


def create_parser():
    parser = argparse.ArgumentParser(description='Display benchmark results.',
                                     prog='-m perf')
    subparsers = parser.add_subparsers(dest='action')

    def input_filenames(cmd):
        cmd.add_argument('-b', '--name',
                         help='only display the benchmark called NAME')
        cmd.add_argument('filenames', metavar='file.json',
                         type=str, nargs='+',
                         help='Benchmark file')

    # show
    cmd = subparsers.add_parser('show', help='Display a benchmark')
    cmd.add_argument('-q', '--quiet', action="store_true",
                     help='enable quiet mode')
    cmd.add_argument('-m', '--metadata', dest='metadata',
                     action="store_true",
                     help="Show metadata.")
    cmd.add_argument('-g', '--hist', action="store_true",
                     help='display an histogram of samples')
    cmd.add_argument('-t', '--stats', action="store_true",
                     help='display statistics (min, max, ...)')
    cmd.add_argument('-d', '--dump', action="store_true",
                     help='display benchmark run results')
    input_filenames(cmd)

    # hist
    cmd = subparsers.add_parser('hist', help='Render an histogram')
    cmd.add_argument('--extend', action="store_true",
                     help="Extend the histogram to fit the terminal")
    cmd.add_argument('-n', '--bins', type=int, default=None,
                     help='Number of histogram bars (default: 25, or less '
                          'depeding on the terminal size)')
    input_filenames(cmd)

    # compare, compare_to
    for command in ('compare', 'compare_to'):
        cmd = subparsers.add_parser(command, help='Compare benchmarks')
        cmd.add_argument('-q', '--quiet', action="store_true",
                         help='enable quiet mode')
        cmd.add_argument('-v', '--verbose', action="store_true",
                         help='enable verbose mode')
        input_filenames(cmd)

    # stats
    cmd = subparsers.add_parser('stats', help='Compute statistics')
    input_filenames(cmd)

    # metadata
    subparsers.add_parser('metadata')

    # timeit
    cmd = subparsers.add_parser('timeit', help='Quick Python microbenchmark')
    timeit_runner = perf.text_runner.TextRunner(name='timeit', _argparser=cmd)
    cmd.add_argument('-s', '--setup', action='append', default=[],
                     help='setup statements')
    cmd.add_argument('stmt', nargs='+',
                     help='executed statements')

    # convert
    cmd = subparsers.add_parser('convert', help='Modify benchmarks')
    cmd.add_argument('input_filename',
                     help='Filename of the input benchmark suite')
    output = cmd.add_mutually_exclusive_group(required=True)
    output.add_argument('-o', '--output', metavar='OUTPUT_FILENAME',
                     dest='output_filename',
                     help='Filename where the output benchmark suite '
                          'is written')
    output.add_argument('--stdout', action='store_true',
                        help='Write benchmark encoded to JSON into stdout')
    cmd.add_argument('--include-benchmark', metavar='NAME',
                     help='Only keep benchmark called NAME')
    cmd.add_argument('--exclude-benchmark', metavar='NAME',
                     help='Remove the benchmark called NAMED')
    cmd.add_argument('--include-runs',
                     help='Only keep benchmark runs RUNS')
    cmd.add_argument('--exclude-runs',
                     help='Remove specified benchmark runs')
    cmd.add_argument('--remove-outliers', action='store_true',
                     help='Remove outlier runs')
    cmd.add_argument('--indent', action='store_true',
                     help='Indent JSON (rather using compact JSON)')
    cmd.add_argument('--remove-warmups', action='store_true',
                     help='Remove warmup samples')
    cmd.add_argument('--add', metavar='FILE',
                     help='Add benchmark runs of benchmark FILE')

    # dump
    cmd = subparsers.add_parser('dump', help='Dump the runs')
    cmd.add_argument('-v', '--verbose', action="store_true",
                     help='enable verbose mode')
    cmd.add_argument('-q', '--quiet', action="store_true",
                     help='enable quiet mode')
    cmd.add_argument('--raw', action="store_true",
                     help='display raw samples')
    input_filenames(cmd)

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
        for key in set(metadata) - set(run_metadata):
            del metadata[key]
        for key in set(run_metadata) & set(metadata):
            if run_metadata[key] != metadata[key]:
                del metadata[key]
    return metadata


def _display_common_metadata(metadatas):
    if len(metadatas) < 2:
        return

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


def compare_benchmarks(benchmarks, sort_benchmarks, args):
    # FIXME: remove this, use directly benchmarks
    new_benchmarks = []
    for benchmark, title, filename in benchmarks:
        benchmark.name = filename
        new_benchmarks.append(benchmark)
    benchmarks = new_benchmarks

    if sort_benchmarks:
        benchmarks.sort(key=_result_sort_key)

    ref_result = benchmarks[0]

    # Compute medians
    ref_samples = ref_result.get_samples()
    ref_avg = ref_result.median()
    last_index = len(benchmarks) - 1
    lines = []
    print = lines.append
    all_significant = False
    for index, changed_result in enumerate(benchmarks[1:], 1):
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
        two_lines = False

        # significant?
        if len(ref_samples) != 1 and len(changed_samples) != 1:
            try:
                significant, t_score = perf.is_significant(ref_samples, changed_samples)
            except Exception as exc:
                print("ERROR when testing if samples are significant")
                all_significant = True
            else:
                if significant:
                    if args.verbose:
                        print("Significant (t=%.2f)" % t_score)
                        two_lines = True
                    all_significant = True
                else:
                    print("Not significant!")
                    two_lines = True
        else:
            # FIXME: is it ok to consider that comparison between two samples
            # is significant?
            all_significant = True

        if index != last_index and two_lines:
            print("")

    return (all_significant, lines)


def compare_suites(benchmarks, sort_benchmarks, args):
    grouped_by_name = benchmarks.group_by_name()
    # FIXME: remove if and use the iterator?
    if not grouped_by_name:
        print("ERROR: Benchmark suites have no benchmark in common",
              file=sys.stderr)
        sys.exit(1)

    not_significant = []
    # FIXME: add "is_last" to grouped_by_name
    for index, item in enumerate(grouped_by_name):
        # FIXME: use namedtuple()
        name, cmp_benchmarks, is_last = item
        significant, lines = compare_benchmarks(cmp_benchmarks, sort_benchmarks, args)

        if len(grouped_by_name) > 1:
            title = name
        else:
            title = None

        if not(significant or args.verbose):
            not_significant.append(name)
            continue

        if len(lines) != 1:
            if title:
                display_title(title)
            for line in lines:
                print(line)
            if index != len(grouped_by_name) - 1:
                print()
        else:
            text = lines[0]
            if title:
                text = '%s: %s' % (title, text)
            print(text)

    if not args.quiet:
        if not_significant:
            print("Benchmark hidden because not significant (%s): %s"
                  % (len(not_significant), ', '.join(not_significant)))

        for suite, hidden in benchmarks.group_by_name_ignored():
            if not hidden:
                continue
            print("Ignored benchmarks (%s) of %s: %s"
                  % (len(hidden), suite.filename, ', '.join(sorted(hidden))))

def cmd_compare(args):
    data = load_benchmarks(args)
    if data.get_nsuite() < 2:
        print("ERROR: need at least two benchmark files")
        sys.exit(1)

    compare_suites(data, args.action == 'compare', args)


def cmd_metadata():
    from perf import metadata as perf_metadata
    metadata = {}
    perf_metadata.collect_run_metadata(metadata)
    perf_metadata.collect_benchmark_metadata(metadata)
    perf.text_runner._display_metadata(metadata)


DataItem = collections.namedtuple('DataItem', 'benchmark title is_last')


def format_filename_func(suites):
    filenames = [suite.filename for suite in suites]

    base_filenames = {os.path.basename(filename) for filename in filenames}
    if len(base_filenames) != len(filenames):
        # FIXME: try harder: try to get differente names by keeping only
        # the parent directory?
        return lambda filename: filename

    noext_filenames = {os.path.splitext(filename)[0]
                       for filename in base_filenames}
    if len(noext_filenames) != len(base_filenames):
        return os.path.basename

    def format_filename(filename):
        filename = os.path.basename(filename)
        filename = os.path.splitext(filename)[0]
        return filename

    return format_filename


class Benchmarks:
    def __init__(self):
        self.suites = []

    def load_benchmark_suite(self, filename):
        suite = perf.BenchmarkSuite.load(filename)
        self.suites.append(suite)

    def load_benchmark_suites(self, filenames):
        for filename in filenames:
            self.load_benchmark_suite(filename)

    # FIXME: move this method to BenchmarkSuite?
    def include_benchmark(self, name):
        for suite in self.suites:
            if name not in suite:
                fatal_missing_benchmark(suite, name)
            for key in list(suite):
                if key != name:
                    del suite[key]

    def get_nsuite(self):
        return len(self.suites)

    def __len__(self):
        return sum(len(suite) for suite in self.suites)

    def __iter__(self):
        format_filename = format_filename_func(self.suites)

        show_name = (len(self) > 1)
        show_filename = (self.get_nsuite() > 1)

        for suite_index, suite in enumerate(self.suites):
            filename = format_filename(suite.filename)
            last_suite = (suite_index == (len(self.suites) - 1))

            benchmarks = suite.get_benchmarks()
            for bench_index, benchmark in enumerate(benchmarks):
                if show_name:
                    title = benchmark.name
                    if show_filename:
                        title = "%s:%s" % (filename, title)
                else:
                    title = None
                last_benchmark = (bench_index == (len(benchmarks) - 1))
                is_last = (last_suite and last_benchmark)

                yield DataItem(benchmark, title, is_last)

    def _group_by_name_names(self):
        names = set(self.suites[0])
        for suite in self.suites[1:]:
            names &= set(suite)
        return names

    def group_by_name(self):
        format_filename = format_filename_func(self.suites)

        show_filename = (self.get_nsuite() > 1)

        names = self._group_by_name_names()
        names = sorted(names)
        show_name = (len(names) > 1)

        groups = []
        for index, name in enumerate(names):
            benchmarks = []
            for suite in self.suites:
                benchmark = suite[name]
                filename = format_filename(suite.filename)
                if show_name:
                    if not show_filename:
                        title = name
                    else:
                        # name is displayed in the group title
                        title = filename
                else:
                    title = None
                benchmarks.append((benchmark, title, filename))

            is_last = (index == (len(names) - 1))
            group = (name, benchmarks, is_last)
            groups.append(group)

        return groups

    def group_by_name_ignored(self):
        names = self._group_by_name_names()
        for suite in self.suites:
            ignored = set(suite) - names
            if ignored:
                yield (suite, ignored)


def display_title(title):
    print(title)
    print("=" * len(title))
    print()


def load_benchmarks(args):
    data = Benchmarks()
    data.load_benchmark_suites(args.filenames)
    if args.name:
        data.include_benchmark(args.name)
    return data


def cmd_show(args):
    data = load_benchmarks(args)

    if args.metadata:
        metadatas = [dict(item.benchmark.metadata) for item in data]
        _display_common_metadata(metadatas)

    if args.hist or args.stats or args.dump:
        use_title = True
    else:
        use_title = False
        if not args.quiet:
            for index, item in enumerate(data):
                warnings = perf.text_runner._warn_if_bench_unstable(item.benchmark)
                if warnings:
                    use_title = True
                    break

    if use_title:
        for index, item in enumerate(data):
            if item.title:
                display_title(item.title)

            if args.metadata:
                metadata = metadatas[index]
                if metadata:
                    perf.text_runner._display_metadata(metadata)
                    print()

            perf.text_runner._display_benchmark(item.benchmark,
                                                hist=args.hist,
                                                stats=args.stats,
                                                dump=args.dump,
                                                check_unstable=not args.quiet)

            if not item.is_last:
                print()
    else:
        for item in data:
            line = str(item.benchmark)
            if item.title:
                line = '%s: %s' % (item.title, line)
            print(line)


def cmd_dump(args):
    data = load_benchmarks(args)

    for item in data:
        if item.title:
            display_title(item.title)

        perf.text_runner._display_runs(item.benchmark,
                                       quiet=args.quiet,
                                       verbose=args.verbose,
                                       raw=args.raw)
        if not item.is_last:
            print()


def cmd_timeit(args, timeit_runner):
    import perf._timeit
    timeit_runner.args = args
    timeit_runner._process_args()
    perf._timeit.main(timeit_runner)


def cmd_stats(args):
    data = load_benchmarks(args)

    for item in data:
        if item.title:
            display_title(item.title)
        perf.text_runner._display_stats(item.benchmark)
        if not item.is_last:
            print()


def cmd_hist(args):
    data = load_benchmarks(args)

    ignored = list(data.group_by_name_ignored())

    groups = data.group_by_name()
    show_filename = (data.get_nsuite() > 1)
    show_group_name = (len(groups) > 1)

    for name, benchmarks, is_last in groups:
        if show_group_name:
            display_title(name)

        benchmarks = [(benchmark, filename if show_filename else None)
                      for benchmark, title, filename in benchmarks]

        perf.text_runner._display_histogram(benchmarks, bins=args.bins,
                                            extend=args.extend)

        if not(is_last or ignored):
            print()

    for suite, ignored in ignored:
        for name in ignored:
            print("[ %s ]" % name)
            perf.text_runner._display_histogram([name], bins=args.bins,
                                                extend=args.extend)


def fatal_missing_benchmark(suite, name):
    print("ERROR: The benchmark suite %s doesn't contain "
          "a benchmark called %r"
          % (suite.filename, name),
          file=sys.stderr)
    sys.exit(1)


def cmd_convert(args):
    suite = perf.BenchmarkSuite.load(args.input_filename)

    if args.add:
        suite2 = perf.BenchmarkSuite.load(args.add)
        for bench in suite2.get_benchmarks():
            suite._add_benchmark_runs(bench)

    if args.include_benchmark:
        remove = set(suite)
        name = args.include_benchmark
        try:
            remove.remove(name)
        except KeyError:
            fatal_missing_benchmark(suite, name)
        for name in remove:
            del suite[name]

    elif args.exclude_benchmark:
        name = args.exclude_benchmark
        try:
            del suite[name]
        except KeyError:
            fatal_missing_benchmark(suite, name)

    if args.include_runs or args.exclude_runs:
        if args.include_runs:
            runs = args.include_runs
            include = True
        else:
            runs = args.exclude_runs
            include = False
        try:
            only_runs = perf._parse_run_list(runs)
        except ValueError as exc:
            print("ERROR: %s (runs: %r)" % (exc, runs), file=sys.stderr)
            sys.exit(1)
        for benchmark in suite.values():
            try:
                benchmark._filter_runs(include, only_runs)
            except ValueError:
                print("ERROR: Benchmark %r has no more run" % benchmark.name,
                      file=sys.stderr)
                sys.exit(1)

    if args.remove_warmups:
        for benchmark in suite.values():
            benchmark._remove_warmups()

    if args.remove_outliers:
        for benchmark in suite.values():
            try:
                benchmark._remove_outliers()
            except ValueError:
                print("ERROR: Benchmark %r has no more run after removing "
                      "outliers" % benchmark.name,
                      file=sys.stderr)
                sys.exit(1)

    compact = not(args.indent)
    if args.output_filename:
        suite.dump(args.output_filename, compact=compact)
    else:
        suite.dump(sys.stdout, compact=compact)


def main():
    parser, timeit_runner = create_parser()
    args = parser.parse_args()
    action = args.action
    try:
        dispatch = {
            'show': functools.partial(cmd_show, args),
            'compare': functools.partial(cmd_compare, args),
            'compare_to': functools.partial(cmd_compare, args),
            'hist': functools.partial(cmd_hist, args),
            'stats': functools.partial(cmd_stats, args),
            'metadata': cmd_metadata,
            'timeit': functools.partial(cmd_timeit, args, timeit_runner),
            'convert': functools.partial(cmd_convert, args),
            'dump': functools.partial(cmd_dump, args),
        }

        try:
            dispatch[action]()
        except KeyError:
            parser.print_usage()
            sys.exit(1)
    except IOError as exc:
        if exc.errno != errno.EPIPE:
            raise
        # ignore broken pipe error


main()
