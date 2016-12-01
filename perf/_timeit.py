from __future__ import division, print_function, absolute_import

import itertools
import sys
import timeit

import perf


def sample_func(loops, timer):
    if perf.python_implementation() == 'pypy':
        inner = timer.make_inner()
        return inner(loops, timer.timer)
    else:
        it = itertools.repeat(None, loops)
        return timer.inner(it, timer.timer)


def strip_statements(statements):
    result = []
    for stmt in statements:
        stmt = stmt.rstrip()
        if stmt:
            result.append(stmt)
    if not result:
        result.append('pass')
    return result


def format_statements(statements):
    return ' '.join(repr(stmt) for stmt in statements)


def create_timer(stmt, setup):
    # Include the current directory, so that local imports work (sys.path
    # contains the directory of this script, rather than the current
    # directory)
    import os
    sys.path.insert(0, os.curdir)

    stmt = "\n".join(stmt)
    setup = "\n".join(setup)

    return timeit.Timer(stmt, setup, timer=perf.perf_counter)


def bench_timeit(runner, name, stmt, setup, inner_loops, duplicate,
                 func_metadata=None):
    if isinstance(stmt, str):
        stmt = (stmt,)
    if isinstance(setup, str):
        setup = (setup,)

    stmt = strip_statements(stmt)
    setup = strip_statements(setup)

    metadata = {}
    if func_metadata:
        metadata.update(func_metadata)
    metadata['timeit_setup'] = format_statements(setup)
    metadata['timeit_stmt'] = format_statements(stmt)

    # args must not be modified, it's passed to the worker process,
    # so use local variables.
    if duplicate and duplicate > 1:
        stmt = stmt * duplicate
        if inner_loops:
            inner_loops *= duplicate
        else:
            inner_loops = duplicate
        metadata['timeit_duplicate'] = duplicate

    kwargs = {'metadata': metadata}
    if inner_loops:
        kwargs['inner_loops'] = inner_loops

    try:
        timer = create_timer(stmt, setup)
        runner.bench_sample_func(name, sample_func,
                                 timer, **kwargs)
    except SystemExit:
        raise
    except:
        print("Error when running timeit benchmark:")
        print()
        print("Statement:")
        print(format_statements(setup))
        print()
        print("Setup:")
        print(format_statements(stmt))
        print()
        timer.print_exc()
        sys.exit(1)
