import argparse
import matplotlib.pyplot as plt
import perf
import statistics


def plot_bench(args, bench):
    if not args.split_runs:
        values = bench.get_values()
        if args.skip:
            values = values[args.skip:]
        values = [value for value in values]
        plt.plot(values, label='values')

        mean = statistics.mean(values)
        plt.plot([mean] * len(values), label='mean')

        plt.legend(loc='upper right', shadow=True, fontsize='x-large')
    else:
        for run_index, run in enumerate(bench.get_runs()):
            index = 0
            x = []
            y = []
            values = run.values
            if args.skip:
                values = values[args.skip:]
            for value in values:
                x.append(index)
                y.append(value)
                index += 1
            plt.plot(x, y, color='blue')

            if args.warmups:
                values = [value for loops, value in run.warmups]
                index = -len(run.warmups) + 1
                x = []
                y = []
                for value in values:
                    x.append(index)
                    y.append(value)
                    index += 1
                plt.plot(x, y, color='red')

    plt.show()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-b', '--benchmark')
    parser.add_argument('--split-runs', action='store_true')
    parser.add_argument('--skip', type=int, help='skip first SKIP values')
    parser.add_argument('--warmups', action='store_true')
    parser.add_argument('filename')
    return parser.parse_args()


def main():
    args = parse_args()
    if args.benchmark:
        suite = perf.BenchmarkSuite.load(args.filename)
        bench = suite.get_benchmark(args.benchmark)
    else:
        bench = perf.Benchmark.load(args.filename)
    plot_bench(args, bench)


if __name__ == "__main__":
    main()
