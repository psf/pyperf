#!/usr/bin/env python3
import asyncio
import pyperf
import time


async def func():
    await asyncio.sleep(0.001)


runner = pyperf.Runner()
runner.bench_async_func('async_sleep', func)
