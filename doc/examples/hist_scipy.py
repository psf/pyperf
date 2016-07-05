import argparse
import statistics

import matplotlib.pyplot as plt
import pylab
import scipy.stats as stats

import perf


def display_histogram_scipy(bench, bins):
    samples = bench.get_samples()
    samples = sorted(samples)

    median = bench.median()
    fit = stats.norm.pdf(samples, median, statistics.stdev(samples, median))
    pylab.plot(samples, fit, '-o', label='median-stdev')

    plt.legend(loc='upper right', shadow=True, fontsize='x-large')
    pylab.hist(samples, bins=bins, normed=True)
    pylab.show()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--bins', type=int, default=25,
                            help="Number of histogram bars (default: 25)")
    parser.add_argument('filename')
    args = parser.parse_args()

    bench = perf.Benchmark.load(args.filename)
    display_histogram_scipy(bench, args.bins)


if __name__ == "__main__":
    main()
