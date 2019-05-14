#!/usr/bin/env python3
import pyperf
import time


def func():
    time.sleep(0.001)


runner = pyperf.Runner()
runner.bench_func('sleep', func)
