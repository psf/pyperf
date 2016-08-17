import threading
import time

try:
    import win32api
    import win32process
except ImportError:
    win32api = None


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
        if win32api is not None:
            self._handle = win32api.GetCurrentProcess()

    def get(self):
        if win32api is not None:
            # FIXME: do we really need a thread since the kernel already
            # computes the maximum for us?
            pmi = win32process.GetProcessMemoryInfo(self._handle)
            usage = pmi["PeakPagefileUsage"]
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
    if win32api is not None:
        mem_thread.get()
    else:
        try:
            mem_thread.get()
        except IOError as exc:
            return "unable to read /proc/self/smaps: %s" % exc

    if not mem_thread.peak_usage:
        return "memory usage is zero"

    # it seems to work
    return None
