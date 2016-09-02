from __future__ import division, print_function, absolute_import

import sys
import threading
import time


MS_WINDOWS = (sys.platform == 'win32')
if MS_WINDOWS:
    try:
        # Use Python 3.3 _winapi module if available
        from _winapi import GetCurrentProcess
    except ImportError:
        GetCurrentProcess = None

    try:
        import ctypes
        from ctypes import wintypes
    except ImportError:
        GetProcessMemoryInfo = None
    else:
        if GetCurrentProcess is None:
            GetCurrentProcess = ctypes.windll.kernel32.GetCurrentProcess
            GetCurrentProcess.argtypes = []
            GetCurrentProcess.restype = wintypes.HANDLE

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

        GetProcessMemoryInfo = ctypes.windll.psapi.GetProcessMemoryInfo
        GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX),
            wintypes.DWORD,
        ]
        GetProcessMemoryInfo.restype = wintypes.BOOL


# Code to parse Linux /proc/%d/smaps files.
#
# See http://bmaurer.blogspot.com/2006/03/memory-usage-with-smaps.html for
# a quick introduction to smaps.
#
# Need Linux 2.6.16 or newer.
def read_smap_file():
    total = 0
    fp = open("/proc/self/smaps", "rb")
    with fp:
        for line in fp:
            # Include both Private_Clean and Private_Dirty sections.
            line = line.rstrip()
            if line.startswith(b"Private_") and line.endswith(b'kB'):
                parts = line.split()
                total += int(parts[1]) * 1024
    return total


class PeakMemoryUsageThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.peak_usage = 0
        self._done = threading.Event()
        self.sleep = 0.001   # 1 ms
        self._quit = False
        if MS_WINDOWS:
            self._handle = GetCurrentProcess()

    def get(self):
        if MS_WINDOWS:
            # FIXME: do we really need a thread since the kernel already
            # computes the maximum for us?
            counters = PROCESS_MEMORY_COUNTERS_EX()
            ret = GetProcessMemoryInfo(self._handle,
                                       ctypes.byref(counters),
                                       ctypes.sizeof(counters))
            if not ret:
                raise ctypes.WinError()

            usage = counters.PeakPagefileUsage
        else:
            usage = read_smap_file()

        self.peak_usage = max(self.peak_usage, usage)

    def run(self):
        try:
            while not self._quit:
                self.get()
                time.sleep(self.sleep)
        finally:
            self._done.set()

    def stop(self):
        self._quit = True
        self._done.wait()
        return self.peak_usage


def check_tracking_memory():
    mem_thread = PeakMemoryUsageThread()
    # FIXME: better error message if win32api is not available on Windows
    # FIXME: better error message on platforms != Linux and != Windows
    # FIXME: better error message on platforms on Linux < 2.6.16
    if MS_WINDOWS:
        if GetProcessMemoryInfo is None:
            return ("missing ctypes module, "
                    "unable to get GetProcessMemoryInfo()")
    else:
        try:
            mem_thread.get()
        except IOError as exc:
            return "unable to read /proc/self/smaps: %s" % exc

    if not mem_thread.peak_usage:
        return "memory usage is zero"

    # it seems to work
    return None
