import functools
import os.path
import subprocess
import sys

from pyperf._utils import shell_quote, popen_communicate
from pyperf._worker import WorkerTask


def bench_command(command, task, loops):
    path = os.path.dirname(__file__)
    script = os.path.join(path, '_process_time.py')
    run_script = [sys.executable, script]

    args = run_script + [str(loops)] + command
    proc = subprocess.Popen(args,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            universal_newlines=True)
    output = popen_communicate(proc)[0]
    if proc.returncode:
        raise Exception("Command failed with exit code %s"
                        % proc.returncode)

    rss = None
    try:
        lines = output.splitlines()
        timing = float(lines[0])
        if len(lines) >= 2:
            rss = int(lines[1])
    except ValueError:
        raise ValueError("failed to parse script output: %r" % output)

    if rss:
        # store the maximum
        max_rss = task.metadata.get('command_max_rss', 0)
        task.metadata['command_max_rss'] = max(max_rss, rss)
    return timing


class BenchCommandTask(WorkerTask):
    def __init__(self, runner, name, command):
        command_str = ' '.join(map(shell_quote, command))
        metadata = {'command': command_str}
        task_func = functools.partial(bench_command, command)
        WorkerTask.__init__(self, runner, name, task_func, metadata)

    def compute(self):
        WorkerTask.compute(self)
        if self.args.track_memory:
            value = self.metadata.pop('command_max_rss', None)
            if not value:
                raise RuntimeError("failed to get the process RSS")

            self._set_memory_value(value)
