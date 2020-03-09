#!/usr/bin/env python3
import argparse
import csv
import pyperf
import statistics


def export_csv(args, bench):
    runs = bench.get_runs()
    runs_values = [run.values for run in runs if run.values]

    rows = []
    for run_values in zip(*runs_values):
        mean = statistics.mean(run_values)
        rows.append([mean])

    with open(args.csv_filename, 'w', newline='', encoding='ascii') as fp:
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
        suite = pyperf.BenchmarkSuite.load(args.json_filename)
        bench = suite.get_benchmark(args.benchmark)
    else:
        bench = pyperf.Benchmark.load(args.json_filename)

    export_csv(args, bench)


if __name__ == "__main__":
    main()
