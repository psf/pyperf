#!/usr/bin/env python3
import asyncio
import pyperf


def loop_factory():
    return asyncio.new_event_loop()


async def func():
    await asyncio.sleep(0.001)


runner = pyperf.Runner()
runner.bench_async_func('async_sleep', func, loop_factory=loop_factory)
