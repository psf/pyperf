import json
import sys

import perf


if sys.stdin.isatty():
    print("Warning: JSON is expected on stdin")

stdout = sys.stdin.read()
runs = []
results = []
for line in stdout.splitlines():
    line = line.strip()
    if not line:
        # ignore empty lines
        continue

    data = json.loads(line)
    if 'run_result' in data:
        run = perf.RunResult._from_json(data['run_result'])
        runs.append(run)
    elif 'results' in data:
        result = perf.Results._from_json(data['results'])
        results.append(result)
    else:
        print("ERROR: invalid JSON")
        sys.exit(1)

if runs:
    result = perf.Results(runs=runs)
    results.append(result)

if not results:
    print("ERROR: no result JSON read from stdin")
    sys.exit(1)

for result in results:
    if result.metadata:
        print("Metadata:")
        for key, value in sorted(result.metadata.items()):
            print("- %s: %s" % (key, value))
    print("Average: %s" % result)
