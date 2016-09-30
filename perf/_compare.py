from __future__ import division, print_function, absolute_import

import sys

import perf
from perf._cli import display_title, get_benchmark_name


def is_significant(bench1, bench2):
    samples1 = bench1.get_samples()
    samples2 = bench2.get_samples()

    if len(samples1) == 1 and len(samples2) == 1:
        # FIXME: is it ok to consider that comparison between two samples
        # is significant?
        return (True, None)

    try:
        significant, t_score = perf.is_significant(samples1, samples2)
        return (significant, t_score)
    except Exception:
        # FIXME: fix the root bug, don't work around it
        return (True, None)


class CompareResults(list):
    def __init__(self, name):
        self.name = name


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

    def _set_significant(self):
        bench1 = self.ref.benchmark
        bench2 = self.changed.benchmark
        self._significant, self._t_score = is_significant(bench1, bench2)

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

    @property
    def speed(self):
        if self._speed is None:
            ref_avg = self.ref.benchmark.median()
            changed_avg = self.changed.benchmark.median()
            self._speed = ref_avg / changed_avg
        return self._speed

    def oneliner(self, verbose=True, show_name=True, check_significant=True):
        if check_significant and not self.significant:
            return "Not significant!"

        ref_text = self.ref.benchmark.format()
        chg_text = self.changed.benchmark.format()
        if verbose:
            if show_name:
                ref_text = "[%s] %s" % (self.ref.name, ref_text)
                chg_text = "[%s] %s" % (self.changed.name, chg_text)
            if (self.ref.benchmark.get_nsample() > 1
               or self.changed.benchmark.get_nsample() > 1):
                text = "Median +- std dev: %s -> %s" % (ref_text, chg_text)
            else:
                text = "Median: %s -> %s" % (ref_text, chg_text)
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

    def format(self, verbose=True, show_name=True):
        text = self.oneliner(show_name=show_name, check_significant=False)
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


def bench_sort_key(item):
    return (item.benchmark.median(), item.filename or '')


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
            cmp_benchmarks.sort(key=bench_sort_key)
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
