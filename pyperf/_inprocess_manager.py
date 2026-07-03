import pyperf
from pyperf._manager import Manager
from pyperf._worker import WorkerProcessTask


class InProcessManager(Manager):
    def __init__(self, runner, task):
        super().__init__(runner)
        self._task_func = task.task_func
        self._task_name = task.name
        self._func_metadata = {
            k: v for k, v in task.metadata.items() if k not in ("name",)
        }
        self._inner_loops = task.inner_loops

    def spawn_worker(self, calibrate_loops, calibrate_warmups):
        args = self.args
        args.calibrate_loops = int(calibrate_loops == 1)
        args.recalibrate_loops = int(calibrate_loops > 1)
        args.calibrate_warmups = int(calibrate_warmups == 1)
        args.recalibrate_warmups = int(calibrate_warmups > 1)

        task = WorkerProcessTask(
            self.runner,
            self._task_name,
            self._task_func,
            self._func_metadata,
        )
        task.inner_loops = self._inner_loops
        run = task.create_run()

        bench = pyperf.Benchmark((run,))
        return pyperf.BenchmarkSuite([bench])
