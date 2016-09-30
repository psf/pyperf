"""
"perf timeit" microbenchmark command based on the Python timeit module.
"""
from __future__ import division, print_function, absolute_import

import itertools
import sys
import timeit

import perf
from perf._cli import display_title
from perf.text_runner import TextRunner


class TimeitRunner(TextRunner):
    def __init__(self, *args, **kw):
        if 'name' not in kw:
            kw['name'] = 'timeit'
        TextRunner.__init__(self, *args, **kw)

        cmd = self.argparser
        cmd.add_argument('--name',
                         help='Benchmark name (default: %r)' % self.name)
        cmd.add_argument('-s', '--setup', action='append', default=[],
                         help='setup statements')
        cmd.add_argument('--inner-loops',
                         type=int,
                         help='Number of inner loops per sample. For example, '
                              'the number of times that the code is copied '
                              'manually multiple times to reduce the overhead '
                              'of the outer loop.')
        cmd.add_argument("--compare-to", metavar="PYTHON2",
                         help='Run benchmark on the Python executable PYTHON, '
                              'run benchmark on Python executable PYTHON2, '
                              'and then compare results')
        cmd.add_argument('stmt', nargs='+', help='executed statements')

    def bench_compare(self, python):
        self.args.python = python
        self.args.compare = None
        self.args.output = None
        self.args.append = None
        bench = perf.Benchmark()
        self._spawn_workers(bench)
        return bench


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


def sample_func(loops, timer):
    if perf.python_implementation() == 'pypy':
        inner = timer.make_inner()
        return inner(loops, timer.timer)
    else:
        it = itertools.repeat(None, loops)
        return timer.inner(it, timer.timer)


def prepare_args(runner, cmd):
    args = runner.args
    cmd.extend(('--name', runner.name))
    if args.inner_loops:
        cmd.extend(('--inner-loops', str(args.inner_loops)))
    for setup in args.setup:
        cmd.extend(("--setup", setup))
    cmd.extend(args.stmt)


def cmd_compare(runner, timer):
    from perf._compare import timeit_compare_benchs

    # need a local copy, because bench_compare() modifies args
    python1 = runner.args.python
    python2 = runner.args.compare_to

    display_title('Benchmark %s' % python1)
    bench1 = runner.bench_compare(python1)
    print()

    display_title('Benchmark %s' % python2)
    bench2 = runner.bench_compare(python2)
    print()

    display_title('Compare')
    timeit_compare_benchs(bench1, bench2, runner.args)


def main(runner):
    args = runner.args

    args.setup = _format_stmt(args.setup)
    args.stmt = _format_stmt(args.stmt)

    if args.name:
        runner.name = args.name
    if args.inner_loops:
        runner.inner_loops = args.inner_loops
    runner.metadata['timeit_setup'] = _stmt_metadata(args.setup)
    runner.metadata['timeit_stmt'] = _stmt_metadata(args.stmt)

    runner.program_args = (sys.executable, '-m', 'perf', 'timeit')
    runner.prepare_subprocess_args = prepare_args

    timer = create_timer(runner)

    # FIXME: abs path for compare

    if args.compare_to:
        cmd_compare(runner, timer)
    else:
        try:
            runner.bench_sample_func(sample_func, timer)
        except SystemExit:
            raise
        except:
            timer.print_exc()
            sys.exit(1)
