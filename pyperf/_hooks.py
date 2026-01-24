# Hooks are installable context managers defined as entry points so that
# arbitrary code can by run right before and after the actual internal
# benchmarking code is run.


import abc
import importlib.metadata
import os
import os.path
import shlex
import signal
import subprocess
import sys
import tempfile
import uuid


def get_hooks():
    hook_prefix = "pyperf.hook"
    entry_points = importlib.metadata.entry_points()
    if sys.version_info[:2] < (3, 10):
        group = entry_points[hook_prefix]
    else:
        group = entry_points.select(group=hook_prefix)
    return group


def get_hook_names():
    return (x.name for x in get_hooks())


def get_selected_hooks(hook_names):
    if hook_names is None:
        return

    hook_mapping = {hook.name: hook for hook in get_hooks()}
    for hook_name in hook_names:
        yield hook_mapping[hook_name]


def instantiate_selected_hooks(hook_names):
    hook_managers = {}
    for hook in get_selected_hooks(hook_names):
        try:
            hook_managers[hook.name] = hook.load()()
        except HookError as e:
            print(f"ERROR setting up hook '{hook.name}':", file=sys.stderr)
            print(str(e), file=sys.stderr)
            sys.exit(1)

    return hook_managers


class HookError(Exception):
    pass


class HookBase(abc.ABC):
    def __init__(self):
        """
        Create a new instance of the hook.
        """
        pass

    def teardown(self, _metadata):
        """
        Called when the hook is completed for a process. May add any information
        collected to the passed-in `metadata` dictionary.
        """
        pass

    def __enter__(self):
        """
        Called immediately before running benchmark code.

        May be called multiple times per instance.
        """
        pass

    def __exit__(self, _exc_type, _exc_value, _traceback):
        """
        Called immediately after running benchmark code.
        """
        pass


class _test_hook(HookBase):
    def __init__(self):
        self._count = 0

    def teardown(self, metadata):
        metadata["_test_hook"] = self._count

    def __enter__(self):
        self._count += 1

    def __exit__(self, _exc_type, _exc_value, _traceback):
        pass


class pystats(HookBase):
    def __init__(self):
        if not hasattr(sys, "_stats_on"):
            raise HookError(
                "Can not collect pystats because python was not built with --enable-pystats"
            )
        sys._stats_off()
        sys._stats_clear()

    def teardown(self, metadata):
        metadata["pystats"] = "enabled"

    def __enter__(self):
        sys._stats_on()

    def __exit__(self, _exc_type, _exc_value, _traceback):
        sys._stats_off()


class perf_record(HookBase):
    """Profile the benchmark using perf-record.

    Profile data is written to the current directory directory by default, or
    to the value of the `PYPERF_PERF_RECORD_DATA_DIR` environment variable, if
    it is provided.

    Profile data files have a basename of the form `perf.data.<uuid>`

    The value of the `PYPERF_PERF_RECORD_EXTRA_OPTS` environment variable is
    appended to the command line of perf-record, if provided.
    """

    def __init__(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.ctl_fifo = self.mkfifo(self.tempdir.name, "ctl_fifo")
        self.ack_fifo = self.mkfifo(self.tempdir.name, "ack_fifo")
        perf_data_dir = os.environ.get("PYPERF_PERF_RECORD_DATA_DIR", "")
        perf_data_basename = f"perf.data.{uuid.uuid4()}"
        cmd = ["perf", "record",
               "--pid", str(os.getpid()),
               "--output", os.path.join(perf_data_dir, perf_data_basename),
               "--control", f"fifo:{self.ctl_fifo},{self.ack_fifo}"]
        extra_opts = os.environ.get("PYPERF_PERF_RECORD_EXTRA_OPTS", "")
        cmd += shlex.split(extra_opts)
        self.perf = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.ctl_fd = open(self.ctl_fifo, "w")
        self.ack_fd = open(self.ack_fifo, "r")

    def __enter__(self):
        self.exec_perf_cmd("enable")

    def __exit__(self, _exc_type, _exc_value, _traceback):
        self.exec_perf_cmd("disable")

    def teardown(self, metadata):
        try:
            self.exec_perf_cmd("stop")
            self.perf.wait(timeout=120)
        finally:
            self.ctl_fd.close()
            self.ack_fd.close()

    def mkfifo(self, tmpdir, basename):
        path = os.path.join(tmpdir, basename)
        os.mkfifo(path)
        return path

    def exec_perf_cmd(self, cmd):
        self.ctl_fd.write(f"{cmd}\n")
        self.ctl_fd.flush()
        self.ack_fd.readline()


class tachyon(HookBase):
    """Profile the benchmark using sampling profiler (Tachyon).

    Profile data is written to the current directory by default, or
    to the value of the `PYPERF_TACHYON_DATA_DIR` environment variable.

    Profile data files have a basename `tachyon.<uuid>.<ext>`.

    Configuration environment variables:
        PYPERF_TACHYON_DATA_DIR: Output directory (default: current)
        PYPERF_TACHYON_FORMAT: Output format - pstats, collapsed, flamegraph,
                               gecko, heatmap, binary (default: pstats)
        PYPERF_TACHYON_MODE: Profiling mode - wall, cpu, gil, exception
                             (default: cpu)
        PYPERF_TACHYON_INTERVAL: Sampling interval in microseconds (default: 1000)
        PYPERF_TACHYON_ALL_THREADS: Set to "1" to profile all threads
        PYPERF_TACHYON_NATIVE: Set to "1" to include the native frames
        PYPERF_TACHYON_ASYNC_AWARE: Set to "1" for async-aware profiling
    """

    FORMAT_EXTENSIONS = {
        "pstats": "pstats",
        "collapsed": "txt",
        "flamegraph": "html",
        "gecko": "json",
        "heatmap": "",
        "binary": "bin",
    }
    VALID_MODES = {"wall", "cpu", "gil", "exception"}

    def __init__(self):
        if sys.platform == "win32":
            raise HookError("tachyon hook is not supported on Windows")

        if sys.version_info < (3, 15):
            raise HookError(
                "tachyon hook requires Python 3.15+, "
                "current version: %s.%s"
                % (sys.version_info.major, sys.version_info.minor)
            )

        try:
            import profiling.sampling  # noqa: F401
        except ImportError:
            raise HookError("profiling.sampling module not available")

        self.format = os.environ.get("PYPERF_TACHYON_FORMAT", "pstats")
        self.mode = os.environ.get("PYPERF_TACHYON_MODE", "cpu")
        self.interval = int(os.environ.get("PYPERF_TACHYON_INTERVAL", "1000"))
        self.data_dir = os.environ.get("PYPERF_TACHYON_DATA_DIR", "")
        self.all_threads = os.environ.get("PYPERF_TACHYON_ALL_THREADS", "") == "1"
        self.native = os.environ.get("PYPERF_TACHYON_NATIVE", "") == "1"
        self.async_aware = os.environ.get("PYPERF_TACHYON_ASYNC_AWARE", "") == "1"

        if self.format not in self.FORMAT_EXTENSIONS:
            raise HookError(
                "Invalid PYPERF_TACHYON_FORMAT: %s (valid: %s)"
                % (self.format, ", ".join(sorted(self.FORMAT_EXTENSIONS)))
            )

        if self.mode not in self.VALID_MODES:
            raise HookError(
                "Invalid PYPERF_TACHYON_MODE: %s (valid: %s)"
                % (self.mode, ", ".join(sorted(self.VALID_MODES)))
            )

        if self.format == "gecko" and "PYPERF_TACHYON_MODE" in os.environ:
            raise HookError("--mode is not compatible with gecko output")

        if self.async_aware:
            if self.native:
                raise HookError("--async-aware is incompatible with --native")
            if self.all_threads:
                raise HookError("--async-aware is incompatible with --all-threads")
            if self.mode in ("cpu", "gil"):
                raise HookError("--async-aware is incompatible with --mode=cpu or --mode=gil")

        self._proc = None
        self.output_paths = []

    def __enter__(self):
        if self._proc is not None:
            self._stop_profiler()

        if self.data_dir:
            os.makedirs(self.data_dir, exist_ok=True)

        ext = self.FORMAT_EXTENSIONS[self.format]
        basename = f"tachyon.{uuid.uuid4()}"
        if ext:
            basename = f"{basename}.{ext}"
        output_path = os.path.join(self.data_dir, basename)

        cmd = [
            sys.executable,
            "-m", "profiling.sampling",
            "attach",
            str(os.getpid()),
            "-i", str(self.interval),
        ]

        if self.format == "gecko":
            cmd.append("--gecko")
        else:
            cmd.append(f"--{self.format}")
            cmd.extend(["--mode", self.mode])

        cmd.extend(["-o", output_path])

        if self.all_threads:
            cmd.append("-a")
        if self.native:
            cmd.append("--native")
        if self.async_aware:
            cmd.append("--async-aware")

        self._proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.output_paths.append(output_path)

    def __exit__(self, _exc_type, _exc_value, _traceback):
        self._stop_profiler()

    def _stop_profiler(self):
        if not self._proc:
            return

        if self._proc.poll() is None:
            self._proc.send_signal(signal.SIGINT)
            try:
                self._proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
                    self._proc.wait()

        self._proc = None

    def teardown(self, metadata):
        self._stop_profiler()
        if self.output_paths:
            metadata["tachyon_profiles"] = os.pathsep.join(self.output_paths)
            metadata["tachyon_output_dir"] = self.data_dir or "."
            metadata["tachyon_format"] = self.format
            if self.format != "gecko":
                metadata["tachyon_mode"] = self.mode
            metadata["tachyon_interval"] = self.interval
            metadata["tachyon_async_aware"] = int(self.async_aware)
