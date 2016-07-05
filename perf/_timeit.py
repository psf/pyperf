"""
"perf timeit" microbenchmark command based on the Python timeit module.
"""
from __future__ import absolute_import, print_function
import itertools
import sys
import timeit

import perf


def _format_stmt(statements):
    result = []
    for stmt in statements:
        stmt = stmt.rstrip()
        if stmt:
            result.append(stmt)
    if not result:
        result.append('pass')
    return result


def _stmt_metadata(statements):
    return ' '.join(repr(stmt) for stmt in statements)


def create_timer(runner):
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


def prepare_args(runner, args):
    for setup in runner.args.setup:
        args.extend(("--setup", setup))
    args.extend(runner.args.stmt)


def sample_func(loops, timer):
    it = itertools.repeat(None, loops)
    return timer.inner(it, timer.timer)


def main(runner):
    runner.args.setup = _format_stmt(runner.args.setup)
    runner.args.stmt = _format_stmt(runner.args.stmt)

    runner.metadata['timeit_setup'] = _stmt_metadata(runner.args.setup)
    runner.metadata['timeit_stmt'] = _stmt_metadata(runner.args.stmt)

    runner.program_args = (sys.executable, '-m', 'perf', 'timeit')
    runner.prepare_subprocess_args = prepare_args

    timer = create_timer(runner)

    try:
        runner.bench_sample_func(sample_func, timer)
    except SystemExit:
        raise
    except:
        timer.print_exc()
        sys.exit(1)
