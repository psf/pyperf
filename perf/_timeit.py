"""
"perf timeit" microbenchmark command based on the Python timeit module.
"""
from __future__ import division, print_function, absolute_import

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

    return timeit.Timer(stmt, setup, timer=perf.perf_counter)


def prepare_args(runner, cmd):
    cmd.extend(('--name', runner.name))
    for setup in runner.args.setup:
        cmd.extend(("--setup", setup))
    cmd.extend(runner.args.stmt)


def sample_func(loops, timer):
    if perf.python_implementation() == 'pypy':
        inner = timer.make_inner()
        return inner(loops, timer.timer)
    else:
        it = itertools.repeat(None, loops)
        return timer.inner(it, timer.timer)


def main(runner):
    args = runner.args

    args.setup = _format_stmt(args.setup)
    args.stmt = _format_stmt(args.stmt)

    if args.name:
        runner.name = args.name
    runner.metadata['timeit_setup'] = _stmt_metadata(args.setup)
    runner.metadata['timeit_stmt'] = _stmt_metadata(args.stmt)

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
