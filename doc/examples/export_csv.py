#!/usr/bin/env python3
import argparse
import csv
import perf
import six
import statistics


def export_csv(args, bench):
    runs = bench.get_runs()
    runs_values = [run.values for run in runs if run.values]

    rows = []
    for run_values in zip(*runs_values):
        mean = statistics.mean(run_values)
        rows.append([mean])

    if six.PY3:
        fp = open(args.csv_filename, 'w', newline='', encoding='ascii')
    else:
        fp = open(args.csv_filename, 'w')
    with fp:
        writer = csv.writer(fp)
        writer.writerows(rows)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-b', '--benchmark')
    parser.add_argument('json_filename')
    parser.add_argument('csv_filename')
    return parser.parse_args()


def main():
    args = parse_args()
    if args.benchmark:
        suite = perf.BenchmarkSuite.load(args.json_filename)
        bench = suite.get_benchmark(args.benchmark)
    else:
        bench = perf.Benchmark.load(args.json_filename)

    export_csv(args, bench)


if __name__ == "__main__":
    main()
