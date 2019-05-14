#!/usr/bin/env python3
import argparse
import matplotlib.pyplot as plt
import pyperf
import statistics


def plot_bench(args, bench):
    if not args.split_runs:
        runs = bench.get_runs()
        if args.run:
            run = runs[args.run - 1]
            runs = [run]
        values = []
        for run in runs:
            run_values = run.values
            if args.skip:
                run_values = run_values[args.skip:]
            values.extend(run_values)
        plt.plot(values, label='values')

        mean = statistics.mean(values)
        plt.plot([mean] * len(values), label='mean')
    else:
        values = []
        width = None
        for run_index, run in enumerate(bench.get_runs()):
            index = 0
            x = []
            y = []
            run_values = run.values
            if args.skip:
                run_values = run_values[args.skip:]
            for value in run_values:
                x.append(index)
                y.append(value)
                index += 1
            plt.plot(x, y, color='blue')
            values.extend(run_values)
            width = len(run_values)

            if args.warmups:
                run_values = [value for loops, value in run.warmups]
                index = -len(run.warmups) + 1
                x = []
                y = []
                for value in run_values:
                    x.append(index)
                    y.append(value)
                    index += 1
                plt.plot(x, y, color='red')

        mean = statistics.mean(values)
        plt.plot([mean] * width, label='mean', color='green')

    plt.legend(loc='upper right', shadow=True, fontsize='x-large')
    plt.show()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-b', '--benchmark')
    parser.add_argument('--split-runs', action='store_true')
    parser.add_argument('--skip', type=int, help='skip first SKIP values')
    parser.add_argument('--warmups', action='store_true')
    parser.add_argument('--run', metavar='INDEX', type=int,
                        help='only render run number INDEX')
    parser.add_argument('filename')
    return parser.parse_args()


def main():
    args = parse_args()
    if args.benchmark:
        suite = pyperf.BenchmarkSuite.load(args.filename)
        bench = suite.get_benchmark(args.benchmark)
    else:
        bench = pyperf.Benchmark.load(args.filename)
    plot_bench(args, bench)


if __name__ == "__main__":
    main()
