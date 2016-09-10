from __future__ import print_function
import argparse
import collections
import functools
import errno
import os.path
import sys

from perf._metadata import _common_metadata
from perf._cli import (display_runs, display_stats, display_metadata,
                       warn_if_bench_unstable, display_histogram,
                       display_benchmark)
from perf._utils import (format_timedelta, format_seconds, parse_run_list,
                         get_isolated_cpus, set_cpu_affinity)
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
    cmd.add_argument('-q', '--quiet',
                     action="store_true", help='enable quiet mode')
    cmd.add_argument('-m', '--metadata', dest='metadata', action="store_true",
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
        if command == 'compare_to':
            cmd.add_argument('-G', '--group-by-speed', action="store_true",
                             help='group slower/faster/same speed')
            cmd.add_argument('--min-speed', type=float,
                             help='Absolute minimum of speed in percent to '
                                  'consider that a benchmark is significant '
                                  '(default: 0%%)')
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
    cmd.add_argument('stmt', nargs='+', help='executed statements')

    # convert
    cmd = subparsers.add_parser('convert', help='Modify benchmarks')
    cmd.add_argument(
        'input_filename', help='Filename of the input benchmark suite')
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
    cmd.add_argument('--include-runs', help='Only keep benchmark runs RUNS')
    cmd.add_argument('--exclude-runs', help='Remove specified benchmark runs')
    cmd.add_argument('--remove-outliers', action='store_true',
                     help='Remove outlier runs')
    cmd.add_argument('--indent', action='store_true',
                     help='Indent JSON (rather using compact JSON)')
    cmd.add_argument('--remove-warmups', action='store_true',
                     help='Remove warmup samples')
    cmd.add_argument('--add', metavar='FILE',
                     help='Add benchmark runs of benchmark FILE')
    cmd.add_argument('--extract-metadata', metavar='NAME',
                     help='Use metadata NAME as the new run values')
    cmd.add_argument('--remove-all-metadata', action="store_true",
                     help='Remove all benchmarks metadata, but keep '
                          'the benchmarks name')
    cmd.add_argument('--update-metadata', metavar='METADATA',
                     help='Update metadata: METADATA is a comma-separated '
                          'list of KEY=VALUE')

    # dump
    cmd = subparsers.add_parser('dump', help='Dump the runs')
    cmd.add_argument('-v', '--verbose', action='store_true',
                     help='enable verbose mode')
    cmd.add_argument('-q', '--quiet', action='store_true',
                     help='enable quiet mode')
    cmd.add_argument('--raw', action='store_true',
                     help='display raw samples')
    input_filenames(cmd)

    # slowest
    cmd = subparsers.add_parser('slowest', help='List benchmarks which took most of the time')
    cmd.add_argument('-n', type=int, default=5,
                     help='Number of slow benchmarks to display (default: 5)')
    input_filenames(cmd)

    return parser, timeit_runner


DataItem = collections.namedtuple('DataItem', 'suite filename benchmark name title is_last')
GroupItem = collections.namedtuple('GroupItem', 'benchmark title filename')
GroupItem2 = collections.namedtuple('GroupItem2', 'name benchmarks is_last')
IterSuite = collections.namedtuple('IterSuite', 'filename suite')


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

    def include_benchmark(self, name):
        for suite in self.suites:
            try:
                suite._convert_include_benchmark(name)
            except KeyError:
                fatal_missing_benchmark(suite, name)

    def get_nsuite(self):
        return len(self.suites)

    def __len__(self):
        return sum(len(suite) for suite in self.suites)

    def iter_suites(self):
        format_filename = format_filename_func(self.suites)
        for suite in self.suites:
            filename = format_filename(suite.filename)
            yield IterSuite(filename, suite)

    def __iter__(self):
        format_filename = format_filename_func(self.suites)

        show_name = (len(self) > 1)
        show_filename = (self.get_nsuite() > 1)

        for suite_index, suite in enumerate(self.suites):
            filename = format_filename(suite.filename)
            last_suite = (suite_index == (len(self.suites) - 1))

            benchmarks = suite.get_benchmarks()
            for bench_index, benchmark in enumerate(benchmarks):
                name = get_benchmark_name(benchmark)
                # FIXME: remove title, move logic to the caller?
                if show_name:
                    title = name
                    if show_filename:
                        title = "%s:%s" % (filename, title)
                else:
                    title = None
                last_benchmark = (bench_index == (len(benchmarks) - 1))
                is_last = (last_suite and last_benchmark)

                yield DataItem(suite, filename, benchmark, name, title, is_last)

    def _group_by_name_names(self):
        def suite_to_name_set(suite):
            result = set()
            for  bench in suite:
                name = bench.get_name()
                if name:
                    result.add(name)
            return result

        names = suite_to_name_set(self.suites[0])
        for suite in self.suites[1:]:
            names &= suite_to_name_set(suite)
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
                benchmark = suite.get_benchmark(name)
                filename = format_filename(suite.filename)
                if show_name:
                    if not show_filename:
                        title = name
                    else:
                        # name is displayed in the group title
                        title = filename
                else:
                    title = None
                benchmarks.append(GroupItem(benchmark, title, filename))

            is_last = (index == (len(names) - 1))
            group = GroupItem2(name, benchmarks, is_last)
            groups.append(group)

        return groups

    def group_by_name_ignored(self):
        names = self._group_by_name_names()
        for suite in self.suites:
            ignored = []
            for bench in suite:
                if bench.get_name() not in names:
                    ignored.append(bench)
            if ignored:
                yield (suite, ignored)


def load_benchmarks(args):
    data = Benchmarks()
    data.load_benchmark_suites(args.filenames)
    if args.name:
        data.include_benchmark(args.name)
    return data


def display_title(title, level=1):
    print(title)
    if level == 1:
        char = '='
    else:
        char = '-'
    print(char * len(title))
    print()


def _display_common_metadata(metadatas):
    if len(metadatas) < 2:
        return

    for metadata in metadatas:
        # don't display name as metadata, it's already displayed
        metadata.pop('name', None)

    common_metadata = _common_metadata(metadatas)
    if common_metadata:
        display_metadata(common_metadata, header='Common metadata:')
        print()

    for key in common_metadata:
        for metadata in metadatas:
            metadata.pop(key, None)


def _bench_sort_key(item):
    return (item.benchmark.median(), item.filename or '')


class CompareData:
    def __init__(self, name, benchmark):
        self.name = name
        self.benchmark = benchmark


class CompareResult(object):
    def __init__(self, ref, changed):
        self.ref = ref
        self.changed = changed
        self._significant = None
        self._t_score = None
        self._speed = None

    def _get_significant(self):
        ref_samples = self.ref.benchmark.get_samples()
        changed_samples = self.changed.benchmark.get_samples()

        if len(ref_samples) == 1 and len(changed_samples) == 1:
            # FIXME: is it ok to consider that comparison between two samples
            # is significant?
            self._significant = True
            self._tscore = None
            return

        try:
            significant, t_score = perf.is_significant(ref_samples,
                                                       changed_samples)
            self._significant = significant
            self._t_score = t_score
        except Exception:
            # FIXME: fix the root bug, don't work around it
            self._significant = True
            self._t_score = None

    @property
    def significant(self):
        if self._significant is None:
            self._get_significant()
        return self._significant

    @property
    def t_score(self):
        if self._significant is None:
            self._get_significant()
        return self._t_score

    @property
    def speed(self):
        if self._speed is None:
            ref_avg = self.ref.benchmark.median()
            changed_avg = self.changed.benchmark.median()
            self._speed = ref_avg / changed_avg
        return self._speed

    def oneliner(self, verbose=True):
        ref_text = self.ref.benchmark.format()
        chg_text = self.changed.benchmark.format()
        if verbose:
            text = ("Median +- std dev: [%s] %s -> [%s] %s"
                    % (self.ref.name, ref_text,
                       self.changed.name, chg_text))
        else:
            text = "%s -> %s" % (ref_text, chg_text)

        speed = self.speed
        if speed == 1.0:
            text = "%s: no change" % text
        elif speed > 1.0:
            text = "%s: %.2fx faster" % (text, speed)
        else:
            text = "%s: %.2fx slower" % (text, 1.0 / speed)
        return text

    def format(self, verbose=True):
        text = self.oneliner()
        lines = [text]

        # significant?
        if self.t_score is None:
            lines.append("ERROR when testing if samples are significant")

        if self.significant:
            if verbose:
                if self.t_score is not None:
                    lines.append("Significant (t=%.2f)" % self.t_score)
                else:
                    lines.append("Significant")
        else:
            lines.append("Not significant!")
        return lines


def get_benchmark_name(benchmark):
    # FIXME: better fallback value
    return benchmark.get_name() or '<no name>'


class CompareResults(list):
    def __init__(self, name):
        self.name = name


def compare_benchmarks(name, benchmarks):
    results = CompareResults(name)

    ref_item = benchmarks[0]
    ref = CompareData(ref_item.filename, ref_item.benchmark)

    for item in benchmarks[1:]:
        changed = CompareData(item.filename, item.benchmark)
        result = CompareResult(ref, changed)
        results.append(result)

    return results


def compare_suites_list(all_results, show_name, args):
    not_significant = []
    for index, results in enumerate(all_results):
        significant = any(result.significant for result in results)
        lines = []
        for result in results:
            lines.extend(result.format(args.verbose))

        if not(significant or args.verbose):
            not_significant.append(results.name)
            continue

        if len(lines) != 1:
            if show_name:
                display_title(results.name)
            for line in lines:
                print(line)
            if index != len(all_results) - 1:
                print()
        else:
            text = lines[0]
            if show_name:
                text = '%s: %s' % (results.name, text)
            print(text)

    if not args.quiet:
        if not_significant:
            print("Benchmark hidden because not significant (%s): %s"
                  % (len(not_significant), ', '.join(not_significant)))


def compare_suites_by_speed(all_results, show_name, args):
    not_significant = []
    slower = []
    faster = []
    same = []
    for results in all_results:
        result = results[0]
        if not result.significant:
            not_significant.append(results.name)
            continue

        speed = result.speed
        if args.min_speed and abs(speed - 1.0) * 100 < args.min_speed:
            not_significant.append(results.name)
            continue

        item = (results.name, result)
        if speed == 1.0:
            same.append(item)
        elif speed > 1.0:
            faster.append(item)
        else:
            slower.append(item)

    for title, results, sort_reverse in (
        ('Slower', slower, False),
        ('Faster', faster, True),
        ('Same speed', same, False),
    ):
        if not results:
            continue

        results.sort(key=lambda item: item[1].speed, reverse=sort_reverse)

        print("%s (%s):" % (title, len(results)))
        for name, result in results:
            text = result.oneliner(verbose=False)
            print("- %s: %s" % (name, text))
        print()



    if not args.quiet and not_significant:
        print("Benchmark hidden because not significant (%s): %s"
              % (len(not_significant), ', '.join(not_significant)))


def compare_suites(benchmarks, sort_benchmarks, by_speed, args):
    grouped_by_name = benchmarks.group_by_name()
    if not grouped_by_name:
        print("ERROR: Benchmark suites have no benchmark in common",
              file=sys.stderr)
        sys.exit(1)

    all_results = []
    for item in grouped_by_name:
        cmp_benchmarks = item.benchmarks
        if sort_benchmarks:
            cmp_benchmarks.sort(key=_bench_sort_key)
        results = compare_benchmarks(item.name, cmp_benchmarks)
        all_results.append(results)

    show_name = (len(grouped_by_name) > 1)
    if by_speed:
        compare_suites_by_speed(all_results, show_name, args)
    else:
        compare_suites_list(all_results, show_name, args)

    if not args.quiet:
        for suite, hidden in benchmarks.group_by_name_ignored():
            if not hidden:
                continue
            hidden_names = [get_benchmark_name(bench) for bench in hidden]
            print("Ignored benchmarks (%s) of %s: %s"
                  % (len(hidden), suite.filename, ', '.join(sorted(hidden_names))))


def cmd_compare(args):
    data = load_benchmarks(args)
    if data.get_nsuite() < 2:
        print("ERROR: need at least two benchmark files")
        sys.exit(1)

    if args.action == 'compare_to':
        by_speed = args.group_by_speed
    else:
        by_speed = False
    if by_speed and data.get_nsuite() != 2:
        print("ERROR: by_speed only works on two benchmark files",
              file=sys.stderr)
        sys.exit(1)

    compare_suites(data, args.action == 'compare', by_speed, args)


def cmd_metadata():
    from perf._metadata import Metadata
    from perf._collect_metadata import collect_metadata

    cpus = get_isolated_cpus()
    if cpus:
        set_cpu_affinity(cpus)
        # ignore if set_cpu_affinity() failed

    metadata = {}
    collect_metadata(metadata)
    metadata = {name: Metadata(name, value)
                for name, value in metadata.items()}
    display_metadata(metadata)


def cmd_show(args):
    data = load_benchmarks(args)

    if args.metadata:
        metadatas = [item.benchmark.get_metadata() for item in data]
        _display_common_metadata(metadatas)

    if args.hist or args.stats or args.dump or args.metadata:
        use_title = True
    else:
        use_title = False
        if not args.quiet:
            for index, item in enumerate(data):
                warnings = warn_if_bench_unstable(item.benchmark)

                if warnings:
                    use_title = True
                    break

    if use_title:
        show_filename = (data.get_nsuite() > 1)
        show_name = show_filename or (len(data.suites[0]) > 1)

        suite = None
        for index, item in enumerate(data):
            if show_filename and item.suite is not suite:
                suite = item.suite
                display_title(item.filename, 1)

            if show_name:
                display_title(item.name, 2)

            if args.metadata:
                metadata = metadatas[index]
                if metadata:
                    display_metadata(metadata)
                    print()

            display_benchmark(item.benchmark,
                              hist=args.hist,
                              stats=args.stats,
                              dump=args.dump,
                              check_unstable=not args.quiet)

            if not item.is_last:
                print()
    else:
        use_titles = (data.get_nsuite() > 1)

        suite = None
        for item in data:
            if use_titles and item.suite is not suite:
                if suite is not None:
                    print()

                suite = item.suite
                display_title(item.filename, 1)

            line = str(item.benchmark)
            if item.title:
                line = '%s: %s' % (item.name, line)
            print(line)


def cmd_dump(args):
    data = load_benchmarks(args)

    use_titles = (data.get_nsuite() > 1) or (len(data.suites[0]) > 1)
    suite = None
    for item in data:
        if item.suite is not suite:
            suite = item.suite
            if use_titles:
                display_title(item.filename, 1)

        if use_titles:
            display_title(item.name, 2)

        display_runs(item.benchmark,
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

    use_titles = (data.get_nsuite() > 1) or (len(data.suites[0]) > 1)
    suite = None
    for item in data:
        if item.suite is not suite:
            suite = item.suite

            if use_titles:
                display_title(item.filename, 1)

                duration = suite.get_total_duration()
                print("Number of benchmarks: %s" % len(suite))
                print("Total duration: %s" % format_seconds(duration))
                dates = suite.get_dates()
                if dates:
                    start, end = dates
                    print("Start date: %s" % start.isoformat())
                    print("End date: %s" % end.isoformat())
                print()

        if use_titles:
            display_title(item.name, 2)
        display_stats(item.benchmark)
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

        display_histogram(benchmarks, bins=args.bins,
                          extend=args.extend)

        if not(is_last or ignored):
            print()

    for suite, ignored in ignored:
        for bench in ignored:
            name = get_benchmark_name(bench)
            print("[ %s ]" % name)
            display_histogram([name], bins=args.bins,
                              extend=args.extend)


def fatal_missing_benchmark(suite, name):
    print("ERROR: The benchmark suite %s doesn't contain "
          "a benchmark called %r"
          % (suite.filename, name),
          file=sys.stderr)
    sys.exit(1)


def fatal_no_more_benchmark(suite):
    print("ERROR: After modification, the benchmark suite %s has no "
          "more benchmark!"
          % suite.filename,
          file=sys.stderr)
    sys.exit(1)


def cmd_convert(args):
    suite = perf.BenchmarkSuite.load(args.input_filename)

    if args.add:
        suite2 = perf.BenchmarkSuite.load(args.add)
        for bench in suite2.get_benchmarks():
            suite._add_benchmark_runs(bench)

    if args.include_benchmark:
        name = args.include_benchmark
        try:
            suite._convert_include_benchmark(name)
        except KeyError:
            fatal_missing_benchmark(suite, name)

    elif args.exclude_benchmark:
        name = args.exclude_benchmark
        try:
            suite._convert_exclude_benchmark(name)
        except ValueError:
            fatal_no_more_benchmark(suite)

    if args.include_runs or args.exclude_runs:
        if args.include_runs:
            runs = args.include_runs
            include = True
        else:
            runs = args.exclude_runs
            include = False
        try:
            only_runs = parse_run_list(runs)
        except ValueError as exc:
            print("ERROR: %s (runs: %r)" % (exc, runs), file=sys.stderr)
            sys.exit(1)
        for benchmark in suite:
            try:
                benchmark._filter_runs(include, only_runs)
            except ValueError:
                print("ERROR: Benchmark %r has no more run"
                      % get_benchmark_name(benchmark),
                      file=sys.stderr)
                sys.exit(1)

    if args.remove_warmups:
        for benchmark in suite:
            benchmark._remove_warmups()

    if args.update_metadata:
        items = [item.strip()
                 for item in args.update_metadata.split(',')]

        metadata = {}
        for item in items:
            if not item:
                continue
            key, _, value = item.partition('=')
            metadata[key] = value

        for benchmark in suite:
            benchmark.update_metadata(metadata)

    if args.extract_metadata:
        name = args.extract_metadata
        for benchmark in suite:
            try:
                benchmark._extract_metadata(name)
            except KeyError:
                print("ERROR: Benchmark %r has no metadata %r"
                      % (get_benchmark_name(benchmark), name),
                      file=sys.stderr)
                sys.exit(1)
            except TypeError:
                raise
                print("ERROR: Metadata %r of benchmark %r is not an integer"
                      % (name, get_benchmark_name(benchmark)),
                      file=sys.stderr)
                sys.exit(1)

    if args.remove_all_metadata:
        for benchmark in suite:
            benchmark._remove_all_metadata()

    if args.remove_outliers:
        for benchmark in suite:
            try:
                benchmark._remove_outliers()
            except ValueError:
                print("ERROR: Benchmark %r has no more run after removing "
                      "outliers" % get_benchmark_name(benchmark),
                      file=sys.stderr)
                sys.exit(1)

    compact = not(args.indent)
    if args.output_filename:
        suite.dump(args.output_filename, compact=compact)
    else:
        suite.dump(sys.stdout, compact=compact)


def cmd_slowest(args):
    data = load_benchmarks(args)
    nslowest = args.n

    use_title = (data.get_nsuite() > 1)
    for item in data.iter_suites():
        if use_title:
            display_title(item.filename, 1)

        benchs = []
        for bench in item.suite:
            duration = bench.get_total_duration()
            benchs.append((duration, bench))
        benchs.sort(key=lambda item: item[0], reverse=True)

        for index, item in enumerate(benchs[:nslowest], 1):
            duration, bench = item
            name = get_benchmark_name(bench)
            print("#%s: %s (%s)"
                  % (index, name, format_timedelta(duration)))


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
            'slowest': functools.partial(cmd_slowest, args),
        }

        try:
            func = dispatch[action]
        except KeyError:
            parser.print_usage()
            sys.exit(1)
        else:
            func()
    except IOError as exc:
        if exc.errno != errno.EPIPE:
            raise
        # ignore broken pipe error


if __name__ == "__main__":
    main()
