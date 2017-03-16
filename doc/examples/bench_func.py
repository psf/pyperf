import perf
import time


def func():
    time.sleep(0.001)


runner = perf.Runner()
runner.bench_func('sleep', func)
