# Hooks are installable context managers defined as entry points so that
# arbitrary code can by run right before and after the actual internal
# benchmarking code is run.


import abc
import importlib.metadata
import sys


def get_hooks():
    hook_prefix = "pyperf.hook"
    entry_points = importlib.metadata.entry_points()
    if sys.version_info[:2] < (3, 10):
        group = entry_points[hook_prefix]
    else:
        group = entry_points.select(hook_prefix)
    return (x.load() for x in group)


def get_hook_names():
    return (x.__name__ for x in get_hooks())


def get_selected_hooks(hook_names):
    if hook_names is None:
        return

    hook_mapping = {hook.__name__: hook for hook in get_hooks()}
    for hook_name in hook_names:
        yield hook_mapping[hook_name]


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
        if not hasattr(sys, "_pystats_on"):
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
