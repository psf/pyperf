#!/usr/bin/env bash
# Integration test: run pyperf --in-process inside Pyodide + Node.js.
#
# This script sets up a Pyodide virtual environment, installs pyperf into it,
# and runs a simple benchmark using --in-process mode to verify that pyperf
# works in environments without subprocess support.
#
# Usage:
#   pip install pyodide-build
#   pyodide xbuildenv install 0.29.3
#   ./test_pyodide.sh
#
# Prerequisites
#   - Python 3.13
#   - Node.js 24+
set -euo pipefail

VENV_DIR=".venv-pyodide-test"
RESULT_FILE="$(mktemp)"
rm -rf "$RESULT_FILE" "$VENV_DIR"
trap 'rm -rf "$RESULT_FILE" "$VENV_DIR"' EXIT

# --- Setup ---

echo "==> Creating Pyodide virtual environment"
pyodide venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

echo "==> Installing pyperf into Pyodide venv"
pip install .

# --- Test 1: bench_time_func with --in-process ---

echo "==> Running bench_time_func benchmark (--in-process)"
python -c "
import pyperf

import time, math

def bench_nqueens(loops, n=8):
    t0 = time.perf_counter()
    for _ in range(loops):
        solutions = []
        def solve(queens, row):
            if row == n:
                solutions.append(queens[:])
                return
            for col in range(n):
                if col not in queens:
                    diag1 = set(q + i for i, q in enumerate(queens))
                    diag2 = set(q - i for i, q in enumerate(queens))
                    if col + row not in diag1 and col - row not in diag2:
                        queens.append(col)
                        solve(queens, row + 1)
                        queens.pop()
        solve([], 0)
    return time.perf_counter() - t0

runner = pyperf.Runner()
runner.parse_args(['--in-process', '-w1', '-n3', '-l1', '--output', '$RESULT_FILE'])
runner.bench_time_func('nqueens', bench_nqueens)
"

# --- Verify output ---

echo "==> Verifying JSON output"
python -c "
import json, sys

with open('$RESULT_FILE') as f:
    data = json.load(f)

name = data['metadata']['name']
runs = data['benchmarks'][0]['runs']
n_values = len([r for r in runs if 'values' in r])

print(f'Benchmark: {name}')
print(f'Value runs: {n_values}')

assert name == 'nqueens', f'Expected name nqueens, got {name}'
assert n_values > 0, f'Expected at least 1 value run, got {n_values}'
print('OK: JSON output is valid')
"

# --- Test 2: bench_func with --in-process ---

echo "==> Running bench_func benchmark (--in-process)"
python -c "
import pyperf

def pidigits(n):
    k, a, b, a1, b1 = 2, 4, 1, 12, 4
    digits = []
    while len(digits) < n:
        p, q, k = k * k, 2 * k + 1, k + 1
        a, b, a1, b1 = a1, b1, p * a + q * a1, p * b + q * b1
        d, d1 = a // b, a1 // b1
        while d == d1 and len(digits) < n:
            digits.append(d)
            a, a1 = 10 * (a % b), 10 * (a1 % b1)
            d, d1 = a // b, a1 // b1
    return digits

runner = pyperf.Runner()
runner.parse_args(['--in-process', '-p1', '-w0', '-n2', '-l1', '--quiet'])
bench = runner.bench_func('pidigits', pidigits, 100)
assert bench is not None, 'bench_func returned None'
assert bench.get_nvalue() == 2, f'Expected 2 values, got {bench.get_nvalue()}'
print('OK: bench_func works')
"

# --- Test 3: python -m pyperf timeit --in-process ---

echo "==> Running python -m pyperf timeit --in-process"
python -m pyperf timeit --in-process -p1 -n3 -l1 -w1 \
    -s "import math" \
    "sum(math.sqrt(i) for i in range(1000))"

# --- Test 4: python -m pyperf subcommands ---

echo "==> Running python -m pyperf show"
python -m pyperf show "$RESULT_FILE"

echo "==> Running python -m pyperf stats"
python -m pyperf stats "$RESULT_FILE"

echo "==> Running python -m pyperf dump --quiet"
python -m pyperf dump --quiet "$RESULT_FILE"

echo "OK: all tests passed"
