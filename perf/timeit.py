from __future__ import absolute_import, print_function
import itertools
import subprocess
import sys
import timeit

import perf.text_runner


_DEFAULT_NPROCESS = 25
_DEFAULT_WARMUPS = 1
_DEFAULT_SAMPLES = 3
_MIN_TIME = 0.1
_MAX_TIME = 1.0


def _calibrate_timer(timer, verbose=0, stream=None):
    min_dt = _MIN_TIME * 0.90
    for i in range(0, 10):
        number = 10 ** i
        dt = timer.timeit(number)
        if verbose > 1:
            print("10^%s loops: %s" % (i, perf._format_timedelta(dt)), file=stream)
        if dt >= _MAX_TIME:
            i = max(i - 1, 1)
            number = 10 ** i
            break
        if dt >= min_dt:
            break
    if verbose > 1:
        print("calibration: use %s" % perf._format_number(number, 'loop'), file=stream)
    return number


def _main_common(args=None):
    # FIXME: use top level imports?
    # FIXME: get ride of getopt! use python 3 timeit main()
    import getopt
    if args is None:
        args = sys.argv[1:]

    runner = perf.text_runner.TextRunner()
    parser = runner.argparser
    parser.add_argument('--raw', action="store_true",
                        help='run a single process')
    parser.add_argument('--metadata', action="store_true",
                        help='show metadata')
    parser.add_argument('-p', '--processes', type=int, default=_DEFAULT_NPROCESS,
                        help='number of processes used to run benchmarks (default: %s)'
                             % _DEFAULT_NPROCESS)
    parser.add_argument('-n', '--loops', type=int, default=0,
                        help='number of loops per sample (default: calibrate)')
    parser.add_argument('-r', '--repeat', type=int, default=_DEFAULT_SAMPLES,
                        help='number of samples (default: %s)'
                             % _DEFAULT_SAMPLES)
    parser.add_argument('-w', '--warmups', type=int, default=_DEFAULT_WARMUPS,
                        help='number of warmup samples per process (default: %s)'
                             % _DEFAULT_WARMUPS)
    parser.add_argument('-s', '--setup', action='append',
                        help='setup statements')
    parser.add_argument('stmt', nargs='+',
                        help='executed statements')

    runner.parse_args()
    runner.nsample = runner.args.repeat
    runner.nwarmup = runner.args.warmups

    stmt = "\n".join(runner.args.stmt) or "pass"
    # FIXME: remove "or ()"
    setup = "\n".join(runner.args.setup or ()) or "pass"

    # Include the current directory, so that local imports work (sys.path
    # contains the directory of this script, rather than the current
    # directory)
    import os
    sys.path.insert(0, os.curdir)

    timer = timeit.Timer(stmt, setup, perf.perf_counter)
    if runner.args.loops == 0:
        stream = sys.stderr if runner.json else None
        try:
            runner.args.loops = _calibrate_timer(timer, runner.verbose, stream=stream)
        except:
            timer.print_exc()
            sys.exit(1)

    return (runner, timer)


def _main_raw(runner, timer):
    loops = runner.args.loops

    def func(timer, loops):
        it = itertools.repeat(None, loops)
        return timer.inner(it, timer.timer) / loops

    runner.result.loops = loops
    try:
        runner.bench_sample_func(func, timer, loops)
    except:
        timer.print_exc()
        sys.exit(1)


def _run_subprocess(nsample, timeit_args):
    args = [sys.executable,
            '-m', 'perf.timeit',
            '--raw', '--json',
            "-n", str(nsample)]
    # FIXME: don't pass duplicate -n
    # FIXME: pass warmups?
    args.extend(timeit_args)

    return perf.RunResult.from_subprocess(args,
                                          stderr=subprocess.PIPE)


def _main():
    args = sys.argv[1:]
    runner, timer  = _main_common(args)
    if runner.args.raw:
        _main_raw(runner, timer)
        return

    result = perf.Results(collect_metadata=runner.json)
    if not runner.json:
        stream = sys.stdout
    else:
        stream = sys.stderr

    if runner.args.metadata:
        from perf import metadata as perf_metadata

        perf_metadata.collect_metadata(result.metadata)

        print("Metadata:", file=stream)
        for key, value in sorted(result.metadata.items()):
            print("- %s: %s" % (key, value), file=stream)

    nprocess = runner.args.processes
    for process in range(nprocess):
        run = _run_subprocess(runner.nsample, args)
        result.runs.append(run)
        if runner.verbose > 1:
            text = ', '.join(perf._format_timedeltas(run.samples))
            text = 'runs (%s): %s' % (len(run.samples), text)
            if run.warmups:
                text = ('warmup (%s): %s; %s'
                        % (len(run.warmups),
                           ', '.join(perf._format_timedeltas(run.warmups)),
                           text))

            print("Run %s/%s: %s" % (1 + process, nprocess, text), file=stream)
        elif runner.verbose:
            mean = perf.mean(run.samples)
            print(perf._format_timedelta(mean), end=' ', file=stream)
            stream.flush()
        else:
            print(".", end='', file=stream)
            stream.flush()
    if runner.verbose <= 1:
        print(file=stream)
    print("Average: %s" % result.format(runner.verbose > 1), file=stream)

    if runner.json:
        stream.flush()
        print(result.json())


if __name__ == "__main__":
    _main()
