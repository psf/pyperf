import time

import perf.text_runner

def func():
    time.sleep(0.001)

runner = perf.text_runner.TextRunner()
runner.bench_func(func)
