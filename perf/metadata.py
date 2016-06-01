import os
import platform
import sys

PY3 = (sys.version_info >= (3,))


def collect_python_metadata(metadata):
    ver = sys.version_info
    metadata['python_version'] = '%s.%s.%s' % (ver.major, ver.minor, ver.micro)
    if os.environ.get('PYTHONHASHSEED', ''):
        metadata['python_hashseed'] = os.environ['PYTHONHASHSEED']


def _collect_linux_metadata(metadata):
    # CPU model
    try:
        cpu_model_name = ''
        if PY3:
            fp = open("/proc/cpuinfo", encoding="utf-8")
        else:
            fp = open("/proc/cpuinfo")
        with fp:
            for line in fp:
                if line.startswith('model name'):
                    cpu_model_name = line.split(':', 1)[1].strip()
                    break
        if cpu_model_name:
            metadata['cpu_model_name'] = cpu_model_name
    except (OSError, IOError):
        pass


def collect_system_metadata(metadata):
    metadata['platform'] = platform.platform(True, False)
    if sys.platform.startswith('linux'):
        _collect_linux_metadata(metadata)

    # CPU count
    cpu_count = None
    if hasattr(os, 'cpu_count'):
        # Python 3.4
        cpu_count = os.cpu_count()
    else:
        try:
            import multiprocessing
        except ImportError:
            pass
        else:
            try:
                cpu_count = multiprocessing.cpu_count()
            except NotImplementedError:
                pass
    if cpu_count is not None and cpu_count >= 1:
        metadata['cpu_count'] = str(cpu_count)
