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
    compare.add_argument('changed_filenames', metavar="changed_filename",
                         type=str, nargs='+',
                         help='Changed JSON file')

    compare_to = subparsers.add_parser('compare_to')
    compare_to.add_argument('ref_filename', type=str,
                            help='Reference JSON file')
    compare_to.add_argument('changed_filenames', metavar="changed_filename",
                            type=str, nargs='+',
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


def _result_sort_key(result):
    samples = result.get_samples()
    return perf.mean(samples)


def compare_results(args, results, sort_results):
    if sort_results:
        results.sort(key=_result_sort_key)

    ref_result = results[0]

    if sort_results:
        print("Reference (best): %s" % ref_result.name)
    else:
        print("Reference: %s" % ref_result.name)
        for index, result in enumerate(results[1:], 1):
            if index > 1:
                prefix = 'Changed #%s' % index
            else:
                prefix = 'Changed'
            print("%s: %s" % (prefix, result.name))
    print()

    if args.metadata:
        metadatas = [result.get_metadata() for result in results]

        common_metadata = perf._common_metadata(metadatas)
        perf._display_metadata(common_metadata,
                               header='Common metadata:')

        for key in common_metadata:
            for metadata in metadatas:
                metadata.pop(key, None)

        for result, metadata in zip(results, metadatas):
            perf._display_metadata(metadata,
                                   header='%s metadata:' % result.name)

    # Compute means
    ref_samples = ref_result.get_samples()
    ref_avg = perf.mean(ref_samples)
    last_index = len(results) - 1
    for index, changed_result in enumerate(results[1:], 1):
        changed_samples = changed_result.get_samples()
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

        if index != last_index:
            print()


parser = create_parser()
args = parser.parse_args()
action = args.action
if action == 'show':
    result = parse_results(args.filename)
    display_result(args, result)
elif action in ('compare', 'compare_to'):
    ref_result = parse_results(args.ref_filename, '<file#1>')
    results = [ref_result]
    for index, filename in enumerate(args.changed_filenames, 2):
        result = parse_results(filename, '<file#%s>' % index)
        results.append(result)
    compare_results(args, results, action == 'compare')
else:
    parser.print_usage()
    sys.exit(1)
