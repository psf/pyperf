import json
import os
import subprocess
import sys
import tempfile
import pyperf


def create_temp_benchmark(tmpdir, data):
    import uuid
    """
    Create a valid pyperf JSON benchmark file.

    pyperf requires the structure:
    {
        "version": "1.0",
        "benchmarks": [
            {
                "metadata": {...},
                "runs": [...]
            }
        ]
    }
    """

    # pyperf requires a benchmark name + unit
    metadata = {
        "name": "test_bench",
        "unit": "second"
    }
    metadata.update(data.get("metadata", {}))

    benchmark = {
        "metadata": metadata,
        "runs": data.get("runs", [])
    }

    suite = {
        "version": "1.0",
        "benchmarks": [benchmark]
    }

    path = os.path.join(tmpdir, f"bench_{uuid.uuid4().hex}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(suite, f)

    return path


def run_command(cmd):
    proc = subprocess.Popen(
        [sys.executable, "-m", "pyperf"] + cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, stderr = proc.communicate()
    return stdout, stderr


def test_compare_to_with_extra_metadata(tmpdir):
    # 1. Create benchmark files with metadata
    bench1 = create_temp_benchmark(tmpdir, {
        "metadata": {"os": "linux", "cpu": "amd"},
        "runs": [{"values": [1.0]}]
    })

    bench2 = create_temp_benchmark(tmpdir, {
        "metadata": {"os": "linux", "cpu": "intel"},
        "runs": [{"values": [1.0]}]
    })

    # 2. Run compare_to
    cmd = [
        "compare_to",
        "--extra-metadata=os,cpu",
        bench1,
        bench2,
    ]

    stdout, stderr = run_command(cmd)

    # 3. Assertions
    assert stderr == ""
    assert "os" in stdout
    assert "cpu" in stdout
    assert "linux" in stdout
    assert "amd" in stdout
    assert "intel" in stdout
    assert "Benchmark" in stdout
