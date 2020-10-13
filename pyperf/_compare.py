import sys

from pyperf._cli import display_title, format_result_value
from pyperf._utils import is_significant


def is_significant_benchs(bench1, bench2):
    values1 = bench1.get_values()
    values2 = bench2.get_values()

    if len(values1) == 1 and len(values2) == 1:
        # FIXME: is it ok to consider that comparison between two values
        # is significant?
        return (True, None)

    try:
        significant, t_score = is_significant(values1, values2)
        return (significant, t_score)
    except Exception:
        # FIXME: fix the root bug, don't work around it
        return (True, None)


class CompareData:
    def __init__(self, name, benchmark):
        self.name = name
        self.benchmark = benchmark

    def __repr__(self):
        return '<CompareData name=%r value#=%s>' % (self.name, self.benchmark.get_nvalue())


def compute_normalized_mean(bench, ref):
    ref_avg = ref.mean()
    bench_avg = bench.mean()
    # Note: means cannot be zero, it's a warranty of pyperf API
    norm_mean = bench_avg / ref_avg
    percent = (bench_avg - ref_avg) * 100.0 / ref_avg
    return (norm_mean, percent)


def format_normalized_mean(norm_mean, percent):
    if norm_mean == 1.0:
        return "no change"
    elif norm_mean < 1.0:
        return "%.2fx faster (%+.0f%%)" % (1.0 / norm_mean, percent)
    else:
        return "%.2fx slower (%+.0f%%)" % (norm_mean, percent)


class CompareResult(object):
    def __init__(self, ref, changed, min_speed=None):
        # CompareData object
        self.ref = ref
        # CompareData object
        self.changed = changed
        self._min_speed = min_speed
        self._significant = None
        self._t_score = None
        self._norm_mean = None
        self._percent = None

    def __repr__(self):
        return '<CompareResult ref=%r changed=%r>' % (self.ref, self.changed)

    def _set_significant(self):
        bench1 = self.ref.benchmark
        bench2 = self.changed.benchmark
        self._significant, self._t_score = is_significant_benchs(bench1, bench2)

        if self._min_speed is not None:
            norm_mean = self.norm_mean
            if norm_mean < 1.0:
                # faster uses the inverse
                norm_mean = 1.0 / norm_mean
            if (norm_mean - 1.0) * 100 < self._min_speed:
                self._significant = False

    @property
    def significant(self):
        if self._significant is None:
            self._set_significant()
        return self._significant

    @property
    def t_score(self):
        if self._significant is None:
            self._set_significant()
        return self._t_score

    def _compute_norm_mean(self):
        ref = self.ref.benchmark
        bench = self.changed.benchmark
        self._norm_mean, self._percent = compute_normalized_mean(bench, ref)

    # mean normalized to the reference benchmark mean
    @property
    def norm_mean(self):
        if self._norm_mean is None:
            self._compute_norm_mean()
        return self._norm_mean

    @property
    def percent(self):
        if self._percent is None:
            self._compute_norm_mean()
        return self._percent

    def oneliner(self, verbose=True, show_name=True, check_significant=True):
        if check_significant and not self.significant:
            return "Not significant!"

        ref_text = format_result_value(self.ref.benchmark)
        chg_text = format_result_value(self.changed.benchmark)
        if verbose:
            if show_name:
                ref_text = "[%s] %s" % (self.ref.name, ref_text)
                chg_text = "[%s] %s" % (self.changed.name, chg_text)
            if (self.ref.benchmark.get_nvalue() > 1
               or self.changed.benchmark.get_nvalue() > 1):
                text = "Mean +- std dev: %s -> %s" % (ref_text, chg_text)
            else:
                text = "%s -> %s" % (ref_text, chg_text)
        else:
            text = "%s -> %s" % (ref_text, chg_text)

        text = "%s: %s" % (text, format_normalized_mean(self.norm_mean, self.percent))
        return text

    def format(self, verbose=True, show_name=True):
        text = self.oneliner(show_name=show_name, check_significant=False)
        lines = [text]

        # significant?
        if self.t_score is None:
            lines.append("ERROR when testing if values are significant")

        if self.significant:
            if verbose:
                if self.t_score is not None:
                    lines.append("Significant (t=%.2f)" % self.t_score)
                else:
                    lines.append("Significant")
        else:
            lines.append("Not significant!")
        return lines


class CompareResults(list):
    # list of CompareResult objects
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<CompareResult %r>' % (list(self),)


def compare_benchmarks(name, benchmarks, min_speed):
    results = CompareResults(name)

    ref_item = benchmarks[0]
    ref = CompareData(ref_item.filename, ref_item.benchmark)

    for item in benchmarks[1:]:
        changed = CompareData(item.filename, item.benchmark)
        result = CompareResult(ref, changed, min_speed)
        results.append(result)

    return results


class Table:
    def __init__(self, headers, rows):
        self.headers = headers
        self.rows = rows
        self.widths = [len(header) for header in self.headers]
        for row in self.rows:
            for column, cell in enumerate(row):
                self.widths[column] = max(self.widths[column], len(cell))

    def _render_line(self, char='-'):
        parts = ['']
        for width in self.widths:
            parts.append(char * (width + 2))
        parts.append('')
        return '+'.join(parts)

    def _render_row(self, row):
        parts = ['']
        for width, cell in zip(self.widths, row):
            parts.append(' %s ' % cell.ljust(width))
        parts.append('')
        return '|'.join(parts)

    def render(self, write_line):
        write_line(self._render_line('-'))
        write_line(self._render_row(self.headers))
        write_line(self._render_line('='))
        for row in self.rows:
            write_line(self._render_row(row))
            write_line(self._render_line('-'))


def compare_suites_table(all_results, by_speed, args):
    if by_speed:
        def sort_key(results):
            result = results[0]
            return result.norm_mean

        all_results.sort(key=sort_key)

    headers = ['Benchmark', all_results[0][0].ref.name]
    for item in all_results[0]:
        headers.append(item.changed.name)

    rows = []
    not_significant = []
    for results in all_results:
        row = [results.name]

        ref_bench = results[0].ref.benchmark
        text = ref_bench.format_value(ref_bench.mean())
        row.append(text)

        significants = []
        for index, result in enumerate(results):
            bench = result.changed.benchmark
            significant = result.significant
            if significant:
                text = format_normalized_mean(result.norm_mean, result.percent)
                if not args.quiet:
                    text = "%s: %s" % (bench.format_value(bench.mean()), text)
            else:
                text = "not significant"
            significants.append(significant)
            row.append(text)

        if any(significants):
            rows.append(row)
        else:
            not_significant.append(results.name)

    if rows:
        table = Table(headers, rows)
        table.render(print)

    if not_significant:
        if rows:
            print()
        print("Not significant (%s): %s"
              % (len(not_significant), '; '.join(not_significant)))


def compare_suites_list(all_results, show_name, args):
    not_significant = []
    empty_line = False
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
        empty_line = True

    if not args.quiet and not_significant:
        if empty_line:
            print()
        print("Benchmark hidden because not significant (%s): %s"
              % (len(not_significant), ', '.join(not_significant)))


def compare_suites_by_speed(all_results, args):
    not_significant = []
    slower = []
    faster = []
    same = []
    for results in all_results:
        result = results[0]
        if not result.significant:
            not_significant.append(results.name)
            continue

        item = (results.name, result)
        norm_mean = result.norm_mean
        if norm_mean == 1.0:
            same.append(item)
        elif norm_mean < 1.0:
            faster.append(item)
        else:
            slower.append(item)

    def sort_key(item):
        return item[1].norm_mean

    slower.sort(key=sort_key, reverse=True)
    faster.sort(key=sort_key)

    empty_line = False
    for title, results, sort_reverse in (
        ('Slower', slower, True),
        ('Faster', faster, False),
        ('Same speed', same, False),
    ):
        if not results:
            continue

        if empty_line:
            print()
        print("%s (%s):" % (title, len(results)))
        for name, result in results:
            text = result.oneliner(verbose=False)
            print("- %s: %s" % (name, text))
        empty_line = True

    if not args.quiet and not_significant:
        if empty_line:
            print()
        print("Benchmark hidden because not significant (%s): %s"
              % (len(not_significant), ', '.join(not_significant)))


def compare_suites(benchmarks, args):
    grouped_by_name = benchmarks.group_by_name()
    if not grouped_by_name:
        print("ERROR: Benchmark suites have no benchmark in common",
              file=sys.stderr)
        sys.exit(1)

    # List of CompareResults
    all_results = []
    for item in grouped_by_name:
        cmp_benchmarks = item.benchmarks
        results = compare_benchmarks(item.name, cmp_benchmarks,
                                     args.min_speed)
        all_results.append(results)

    if args.table:
        compare_suites_table(all_results, args.group_by_speed, args)
    else:
        show_name = (len(grouped_by_name) > 1)
        if args.group_by_speed:
            compare_suites_by_speed(all_results, args)
        else:
            compare_suites_list(all_results, show_name, args)

    if not args.quiet:
        for suite, hidden in benchmarks.group_by_name_ignored():
            if not hidden:
                continue
            hidden_names = [bench.get_name() for bench in hidden]
            print("Ignored benchmarks (%s) of %s: %s"
                  % (len(hidden), suite.filename, ', '.join(sorted(hidden_names))))


def timeit_compare_benchs(name1, bench1, name2, bench2, args):
    data1 = CompareData(name1, bench1)
    data2 = CompareData(name2, bench2)
    compare = CompareResult(data1, data2)
    if not args.quiet:
        lines = compare.format(verbose=args.verbose)
        for line in lines:
            print(line)
    else:
        line = compare.oneliner()
        print(line)
