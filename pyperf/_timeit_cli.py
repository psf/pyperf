"""
"pyperf timeit" microbenchmark command based on the Python timeit module.
"""
from __future__ import annotations
from typing import TYPE_CHECKING
from pyperf._runner import Runner
from pyperf._timeit import bench_timeit, TimeitArgs

if TYPE_CHECKING:
    from argparse import ArgumentParser
    from pyperf._metadata import MetadataType
    from collections.abc import Sequence, Callable
    from typing_extensions import override
    from importlib.metadata import EntryPoints

else:
    def override(func):
        return func

DEFAULT_NAME = 'timeit'



def add_cmdline_args_default(cmd: list[str], args: TimeitArgs) -> None:
    cmd.extend(('--name', args.name))
    if args.inner_loops:
        cmd.extend(('--inner-loops', str(args.inner_loops)))
    for setup in args.setup:
        cmd.extend(("--setup", setup))
    for teardown in args.teardown:
        cmd.extend(('--teardown', teardown))
    if args.duplicate:
        cmd.extend(('--duplicate', str(args.duplicate)))
    cmd.extend(args.stmt)


class TimeitRunner(Runner[TimeitArgs]):
    def __init__(
        self,
        values: int | None = None,
        processes: int | None = None,
        loops: int = 0,
        min_time: float = 0.1,
        metadata: MetadataType | None = None,
        show_name: bool = True,
        program_args: Sequence[str] | None = None,
        add_cmdline_args: Callable[[list[str], TimeitArgs], None] | None = None,
        _argparser: ArgumentParser | None = None,
        warmups: int = 1,
        hooks: EntryPoints | None = None,
        ) -> None:

        if program_args is None:
            program_args = ('-m', 'pyperf', 'timeit')
        if add_cmdline_args is None:
            add_cmdline_args = add_cmdline_args_default

        super().__init__(
            values=values,
            processes=processes,
            loops=loops,
            min_time=min_time,
            metadata=metadata,
            show_name=show_name,
            program_args=program_args,
            add_cmdline_args=add_cmdline_args,
            namespace_type=TimeitArgs,
            _argparser=_argparser,
            warmups=warmups,
            hooks=hooks,
        )

        def parse_name(name: str) -> str:
            return name.strip()

        cmd = self.argparser
        cmd.add_argument('--name', type=parse_name,
                         help='Benchmark name (default: %r)' % DEFAULT_NAME)
        cmd.add_argument('-s', '--setup', action='append', default=[],
                         help='setup statements')
        cmd.add_argument('--teardown', action='append', default=[],
                         help='teardown statements')
        cmd.add_argument('--inner-loops',
                         type=int,
                         help='Number of inner loops per value. For example, '
                              'the number of times that the code is copied '
                              'manually multiple times to reduce the overhead '
                              'of the outer loop.')
        cmd.add_argument('--duplicate', type=int,
                         help='duplicate statements to reduce the overhead of '
                              'the outer loop and multiply inner_loops '
                              'by DUPLICATE')
        cmd.add_argument('stmt', nargs='+', help='executed statements')

    @override
    def _process_args(self) -> None:
        Runner._process_args(self)
        args = self.args

        self._show_name = bool(args.name)
        if not args.name:
            args.name = DEFAULT_NAME


def main(runner: TimeitRunner) -> None:
    args = runner.args
    bench_timeit(runner, args.name, args.stmt, args.setup, args.teardown,
                 args.inner_loops, args.duplicate)
