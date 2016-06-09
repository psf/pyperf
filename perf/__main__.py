from __future__ import print_function
import argparse
import json
import sys

import perf.metadata


def parse_args():
    parser = argparse.ArgumentParser(description='Display benchmark results.')
    parser.add_argument('action', choices=('show',),
                        help='Command action')
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help='an integer for the accumulator')
    parser.add_argument('-M', '--no-metadata', dest='metadata', action="store_false",
                        default=True,
                        help="Don't show metadata.")
    parser.add_argument('filename', type=str,
                        help='Result JSON file')
    return parser.parse_args()


def parse_results(args):
    filename = args.filename
    if filename != '-':
        fp = open(filename)
    else:
        fp = sys.stdin
    with fp:
        return perf.Results.json_load_from(fp)


def display_result(args, results):
    if args.metadata:
        perf.metadata._display_metadata(result.get_metadata())

    if args.verbose:
        nrun = len(result.runs)
        for index, run in enumerate(result.runs, 1):
            text = perf._very_verbose_run(run)
            print("Run %s/%s: %s" % (index, nrun, text))
        print()

    print("Average: %s" % result.format(verbose=args.verbose))


args = parse_args()
result = parse_results(args)
display_result(args, result)
