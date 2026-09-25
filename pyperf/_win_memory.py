from typing import Literal
from _winapi import GetCurrentProcess # type: ignore[import-not-found, unused-ignore, attr-defined]

try:
    import ctypes
    from ctypes import wintypes
except ImportError:
    GetProcessMemoryInfo = None
else:
    SIZE_T = ctypes.c_size_t

    class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
        _fields_ = [
            ('cb', wintypes.DWORD),
            ('PageFaultCount', wintypes.DWORD),
            ('PeakWorkingSetSize', SIZE_T),
            ('WorkingSetSize', SIZE_T),
            ('QuotaPeakPagedPoolUsage', SIZE_T),
            ('QuotaPagedPoolUsage', SIZE_T),
            ('QuotaPeakNonPagedPoolUsage', SIZE_T),
            ('QuotaNonPagedPoolUsage', SIZE_T),
            ('PagefileUsage', SIZE_T),
            ('PeakPagefileUsage', SIZE_T),
            ('PrivateUsage', SIZE_T),
        ]

        cb: int
        PageFaultCount: int
        PeakWorkingSetSize: int
        WorkingSetSize: int
        QuotaPeakPagedPoolUsage: int
        QuotaPagedPoolUsage: int
        QuotaPeakNonPagedPoolUsage: int
        QuotaNonPagedPoolUsage: int
        PagefileUsage: int
        PeakPagefileUsage: int
        PrivateUsage: int

    GetProcessMemoryInfo = ctypes.windll.psapi.GetProcessMemoryInfo  # type: ignore[attr-defined, unused-ignore]
    GetProcessMemoryInfo.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX),
        wintypes.DWORD,
    ]
    GetProcessMemoryInfo.restype = wintypes.BOOL


def get_peak_pagefile_usage() -> int:
    process = GetCurrentProcess()
    counters = PROCESS_MEMORY_COUNTERS_EX()
    ret = GetProcessMemoryInfo(process, # type: ignore[misc, unused-ignore]
                               ctypes.byref(counters),
                               ctypes.sizeof(counters))
    if not ret:
        raise ctypes.WinError() # type: ignore[attr-defined, unused-ignore]

    return counters.PeakPagefileUsage


def check_tracking_memory() -> Literal['memory usage is zero', 'missing ctypes module, unable to get GetProcessMemoryInfo()'] | None:
    if GetProcessMemoryInfo is None:
        return ("missing ctypes module, "
                "unable to get GetProcessMemoryInfo()")

    usage = get_peak_pagefile_usage()
    if not usage:
        return "memory usage is zero"

    # it seems to work
    return None
