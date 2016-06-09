from __future__ import print_function
import argparse
import json
import sys

import perf


def create_parser():
    parser = argparse.ArgumentParser(description='Display benchmark results.',
                                     prog='-m perf')
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help='an integer for the accumulator')
    parser.add_argument('-M', '--no-metadata', dest='metadata', action="store_false",
                        default=True,
                        help="Don't show metadata.")
    subparsers = parser.add_subparsers(dest='action')

    show = subparsers.add_parser('show')
    show.add_argument('filename', type=str,
                      help='Result JSON file')

    compare = subparsers.add_parser('compare')
    compare.add_argument('ref_filename', type=str,
                         help='Reference JSON file')
    compare.add_argument('changed_filename', type=str,
                         help='Changed JSON file')

    return parser


def parse_results(filename, default_name=None):
    if filename != '-':
        fp = open(filename)
    else:
        fp = sys.stdin
    with fp:
        result = perf.Results.json_load_from(fp)

    if not result.name and filename != "-":
        name = filename
        if name.lower().endswith('.json'):
            name = name[:-5]
        if name:
            result.name = name
    if not result.name and default_name:
        result.name = default_name

    return result


def display_result(args, results):
    if args.metadata:
        perf._display_metadata(result.get_metadata())

    if args.verbose:
        nrun = len(result.runs)
        for index, run in enumerate(result.runs, 1):
            text = perf._very_verbose_run(run)
            print("Run %s/%s: %s" % (index, nrun, text))
        print()

    print("Average: %s" % result.format(verbose=args.verbose))


def compare_results(args, ref_result, changed_result):
    print("Reference: %s" % ref_result.name)
    print("Changed: %s" % changed_result.name)
    print()

    if args.metadata:
        perf._display_metadata(ref_result.get_metadata(),
                               header='%s metadata:' % ref_result.name)
        perf._display_metadata(changed_result.get_metadata(),
                               header='%s metadata:' % changed_result.name)

    # Compute means
    ref_samples = ref_result.get_samples()
    changed_samples = changed_result.get_samples()
    ref_avg = perf.mean(ref_samples)
    changed_avg = perf.mean(changed_samples)
    text = ("Average: [%s] %s -> [%s] %s"
            % (ref_result.name,
               ref_result.format(verbose=args.verbose),
               changed_result.name,
               changed_result.format(verbose=args.verbose)))

    # avoid division by zero
    if ref_avg and changed_avg:
        if changed_avg < ref_avg:
            text = "%s: %.1fx faster" % (text, ref_avg /  changed_avg)
        else:
            text= "%s: %.1fx slower" % (text, changed_avg / ref_avg)
    print(text)

    # significant?
    significant, t_score = perf.is_significant(ref_samples, changed_samples)
    if significant:
        print("Significant (t=%.2f)" % t_score)
    else:
        print("Not significant!")


parser = create_parser()
args = parser.parse_args()
action = args.action
if action == 'show':
    result = parse_results(args.filename)
    display_result(args, result)
elif action == 'compare':
    ref_result = parse_results(args.ref_filename, '<ref>')
    changed_result = parse_results(args.changed_filename, '<changed>')
    compare_results(args, ref_result, changed_result)
else:
    parser.print_usage()
    sys.exit(1)
