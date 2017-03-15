import argparse
import statistics

import matplotlib.pyplot as plt
import pylab
import scipy.stats as stats

import perf


def display_histogram_scipy(bench, mean, bins):
    values = bench.get_values()
    values = sorted(values)

    if mean:
        fit = stats.norm.pdf(values, bench.mean(), bench.stdev())
        pylab.plot(values, fit, '-o', label='mean-stdev')
    else:
        fit = stats.norm.pdf(values, bench.median(), bench.median_abs_dev())
        pylab.plot(values, fit, '-o', label='median-mad')

    plt.legend(loc='upper right', shadow=True, fontsize='x-large')
    pylab.hist(values, bins=bins, normed=True)
    pylab.show()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--bins', type=int, default=25,
                        help="Number of histogram bars (default: 25)")
    parser.add_argument('--mean', action="store_true",
                        help="Use mean-stdev, instead of median-mad")
    parser.add_argument('filename')
    args = parser.parse_args()

    bench = perf.Benchmark.load(args.filename)
    display_histogram_scipy(bench, args.mean, args.bins)


if __name__ == "__main__":
    main()
