#!/usr/bin/env python3
import argparse
import matplotlib.pyplot as plt
import pyperf
import pylab
import scipy.stats as stats


def display_histogram_scipy(bench, mean, bins):
    values = bench.get_values()
    values = sorted(values)

    if mean:
        fit = stats.norm.pdf(values, bench.mean(), bench.stdev())
        pylab.plot(values, fit, '-o', label='mean-stdev')
    else:
        fit = stats.norm.pdf(values, bench.mean(), bench.stdev())
        pylab.plot(values, fit, '-o', label='mean-stdev')

    plt.legend(loc='upper right', shadow=True, fontsize='x-large')
    pylab.hist(values, bins=bins)
    pylab.show()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--bins', type=int, default=25,
                        help="Number of histogram bars (default: 25)")
    parser.add_argument('--mean', action="store_true",
                        help="Use mean-stdev, instead of median-mad")
    parser.add_argument('-b', '--benchmark')
    parser.add_argument('filename')
    args = parser.parse_args()

    if args.benchmark:
        suite = pyperf.BenchmarkSuite.load(args.filename)
        bench = suite.get_benchmark(args.benchmark)
    else:
        bench = pyperf.Benchmark.load(args.filename)

    display_histogram_scipy(bench, args.mean, args.bins)


if __name__ == "__main__":
    main()
