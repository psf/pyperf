from __future__ import absolute_import, print_function
import itertools
import sys
import timeit

import perf.text_runner


_DEFAULT_NPROCESS = 25
_DEFAULT_WARMUPS = 1
_DEFAULT_SAMPLES = 3
_MIN_TIME = 0.1
_MAX_TIME = 1.0


def _format_stmt(statements):
    result = []
    for stmt in statements:
        stmt = stmt.rstrip()
        if stmt:
            result.append(stmt)
    if not result:
        result.append('pass')
    return result


def _create_runner():
    runner = perf.text_runner.TextRunner('timeit')
    parser = runner.argparser
    parser.add_argument('-s', '--setup', action='append', default=[],
                        help='setup statements')
    parser.add_argument('stmt', nargs='+',
                        help='executed statements')

    runner.parse_args()

    runner.args.setup = _format_stmt(runner.args.setup)
    runner.args.stmt = _format_stmt(runner.args.stmt)

    runner.metadata['timeit_setup'] = ' '.join(repr(stmt) for stmt in runner.args.setup)
    runner.metadata['timeit_stmt'] = ' '.join(repr(stmt) for stmt in runner.args.stmt)

    runner.program_args = (sys.executable, '-m', 'perf.timeit')
    runner.prepare_subprocess_args = _prepare_args
    return runner


def _create_timer(runner):
    # Include the current directory, so that local imports work (sys.path
    # contains the directory of this script, rather than the current
    # directory)
    import os
    sys.path.insert(0, os.curdir)

    stmt = "\n".join(runner.args.stmt)
    setup = "\n".join(runner.args.setup)

    timer = timeit.Timer(stmt, setup, perf.perf_counter)
    if runner.args.loops == 0:
        try:
            runner.args.loops = runner._calibrate_sample_func(timer.timeit)
        except:
            timer.print_exc()
            sys.exit(1)
    return timer


def _prepare_args(runner, args):
    for setup in runner.args.setup:
        args.extend(("--setup", setup))
    args.extend(runner.args.stmt)


def _sample_func(loops, timer):
    it = itertools.repeat(None, loops)
    return timer.inner(it, timer.timer)


def _run_benchmark(runner, timer):
    try:
        runner.bench_sample_func(_sample_func, timer)
    except SystemExit:
        raise
    except:
        timer.print_exc()
        sys.exit(1)


def _main():
    runner = _create_runner()
    timer = _create_timer(runner)
    _run_benchmark(runner, timer)


if __name__ == "__main__":
    _main()
