import sys

import perf


if sys.stdin.isatty():
    print("Warning: JSON is expected on stdin")

stdout = sys.stdin.read()
runs = []
for line in stdout.splitlines():
    line = line.strip()
    if not line:
        # ignore empty lines
        continue
    run = perf.RunResult.from_json(line)
    runs.append(run)
if not runs:
    print("ERROR: no run result JSON read from stdin")
    sys.exit(1)

result = perf.Results(runs=runs)
print("Average: %s" % result)
