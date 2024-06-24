# Hooks are installable context managers defined as entry points so that
# arbitrary code can by run right before and after the actual internal
# benchmarking code is run.


import sys


import pkg_resources


def get_hooks():
    return (x.load() for x in pkg_resources.iter_entry_points(group="pyperf.hook", name=None))


def get_hook_names():
    return (x.__name__ for x in get_hooks())


def get_selected_hooks(hook_names):
    if hook_names is None:
        return

    for hook in get_hooks():
        if hook.__name__ in hook_names:
            yield hook


def collect_hook_metadata(metadata, hook_names):
    for hook in get_selected_hooks(hook_names):
        hook.collect_metadata(metadata)


class HookError(Exception):
    pass


class pystats:
    def __init__(self):
        if not hasattr(sys, "_pystats_on"):
            raise HookError(
                "Can not collect pystats because python was not built with --enable-pystats"
            )
        sys._stats_off()
        sys._stats_clear()

    @staticmethod
    def collect_hook_metadata(metadata):
        metadata["pystats"] = "enabled"

    def __enter__(self):
        sys._stats_on()

    def __exit__(self, _exc_type, _exc_value, _traceback):
        sys._stats_off()
