#!/usr/bin/env python3
import sys
import pyperf

runner = pyperf.Runner()
runner.bench_command('python_startup', [sys.executable, '-c', 'pass'])
