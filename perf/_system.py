from __future__ import division, print_function, absolute_import

import errno
import os
import re
import subprocess
import sys

from perf._cpu_utils import (parse_cpu_list,
                             get_logical_cpu_count, get_isolated_cpus,
                             format_cpu_list, format_cpu_infos)
from perf._utils import (read_first_line, sysfs_path, proc_path, open_text,
                         popen_communicate)


MSR_IA32_MISC_ENABLE = 0x1a0
MSR_IA32_MISC_ENABLE_TURBO_DISABLE_BIT = 38


def is_root():
    return (os.getuid() == 0)


def write_text(filename, content):
    with open_text(filename, write=True) as fp:
        fp.write(content)
        fp.flush()


def run_cmd(cmd):
    try:
        proc = subprocess.Popen(cmd)
    except OSError as exc:
        if exc.errno == errno.ENOENT:
            return 127
        else:
            raise

    proc.wait()
    return proc.returncode


def get_output(cmd):
    try:
        proc = subprocess.Popen(cmd,
                                stdout=subprocess.PIPE,
                                universal_newlines=True)
    except OSError as exc:
        if exc.errno == errno.ENOENT:
            return (127, '')
        else:
            raise

    stdout = popen_communicate(proc)[0]
    exitcode = proc.returncode
    return (exitcode, stdout)


class Operation(object):
    def __init__(self, name, system):
        self.name = name
        self.system = system

    def info(self, msg):
        self.system.info('%s: %s' % (self.name, msg))

    def error(self, msg):
        self.system.error('%s: %s' % (self.name, msg))

    def read(self):
        pass

    def show(self):
        pass

    def write(self, tune):
        pass


class TurboBoostMSR(Operation):
    """
    Get/Set Turbo Boost mode of Intel CPUs using rdmsr/wrmsr.
    """

    def __init__(self, system):
        Operation.__init__(self, 'Turbo Boost (MSR)', system)
        self.cpu_states = {}

    def show(self):
        enabled = set()
        disabled = set()
        for cpu, state in self.cpu_states.items():
            if state:
                enabled.add(cpu)
            else:
                disabled.add(cpu)

        text = []
        if enabled:
            text.append('CPU %s: enabled' % format_cpu_list(enabled))
        if disabled:
            text.append('CPU %s: disabled' % format_cpu_list(disabled))
        if text:
            self.info(', '.join(text))

    def read_msr(self, cpu, reg_num, bitfield=None):
        # -x for hexadecimal output
        cmd = ['rdmsr', '-p%s' % cpu, '-x']
        if bitfield:
            cmd.extend(('-f', bitfield))
        cmd.append('%#x' % reg_num)

        exitcode, stdout = get_output(cmd)
        stdout = stdout.rstrip()

        if exitcode or not stdout:
            msg = ('Failed to read MSR %#x of CPU %s (exit code %s). '
                   'Is rdmsr tool installed?'
                   % (reg_num, cpu, exitcode))
            if not is_root():
                msg += ' Retry as root?'
            self.error(msg)
            return None

        return int(stdout, 16)

    def read_cpu(self, cpu):
        bit = MSR_IA32_MISC_ENABLE_TURBO_DISABLE_BIT
        msr = self.read_msr(cpu, MSR_IA32_MISC_ENABLE, '%s:%s' % (bit, bit))
        if msr is None:
            return

        if msr == 0:
            self.cpu_states[cpu] = True
        elif msr == 1:
            self.cpu_states[cpu] = False
        else:
            self.error('invalid MSR bit: %#x' % msr)

    def read(self):
        cpus = self.system.get_cpus()
        for cpu in cpus:
            self.read_cpu(cpu)

    def write_msr(self, cpu, reg_num, value):
        cmd = ['wrmsr', '-p%s' % cpu, "%#x" % reg_num, '%#x' % value]
        exitcode = run_cmd(cmd)
        if exitcode:
            self.error("Failed to write %#x into MSR %#x of CPU %s" % (value, reg_num, cpu))
            return False

        return True

    def write_cpu(self, cpu, enabled):
        value = self.read_msr(cpu, MSR_IA32_MISC_ENABLE)
        if value is None:
            return

        mask = (1 << MSR_IA32_MISC_ENABLE_TURBO_DISABLE_BIT)
        if not enabled:
            new_value = value | mask
        else:
            new_value = value & ~mask

        if new_value != value:
            if self.write_msr(cpu, MSR_IA32_MISC_ENABLE, new_value):
                state = "enabled" if enabled else "disabled"
                self.info("Turbo Boost %s on CPU %s: MSR %#x set to %#x"
                          % (state, cpu, MSR_IA32_MISC_ENABLE, new_value))

    def write(self, tune):
        enabled = (not tune)
        cpus = self.system.get_cpus()
        for cpu in cpus:
            self.write_cpu(cpu, enabled)


class TurboBoostIntelPstate(Operation):
    """
    Get/Set Turbo Boost mode of Intel CPUs by reading from/writing into
    /sys/devices/system/cpu/intel_pstate/no_turbo of the intel_pstate driver.
    """

    def __init__(self, system):
        Operation.__init__(self, 'Turbo Boost (intel_pstate driver)', system)
        self.path = sysfs_path("devices/system/cpu/intel_pstate/no_turbo")
        self.enabled = None

    def read(self):
        no_turbo = read_first_line(self.path)
        if no_turbo == '1':
            self.enabled = False
        elif no_turbo == '0':
            self.enabled = True
        else:
            self.error("Invalid no_turbo value: %r" % no_turbo)
            self.enabled = None

    def show(self):
        if self.enabled is not None:
            state = 'enabled' if self.enabled else 'disabled'
            self.info("Turbo Boost %s" % state)

    def write(self, tune):
        enabled = (not tune)

        self.read()
        if self.enabled == enabled:
            # no_turbo already set to the expected value
            return

        content = '0' if enabled else '1'

        try:
            write_text(self.path, content)
        except IOError as exc:
            msg = "Failed to write into %s" % self.path
            if exc.errno in (errno.EPERM, errno.EACCES) and not is_root():
                msg += " (retry as root?)"
            self.error("%s: %s" % (msg, exc))
            return

        msg = "%r written into %s" % (content, self.path)
        if enabled:
            self.info("Turbo Boost enabled: %s" % msg)
        else:
            self.info("Turbo Boost disabled: %s" % msg)


class CPUGovernorIntelPstate(Operation):
    """
    Get/Set CPU scaling governor of the intel_pstate driver.
    """

    def __init__(self, system):
        Operation.__init__(self, 'CPU scaling governor (intel_pstate driver)',
                           system)
        self.path = sysfs_path("devices/system/cpu/cpu0/cpufreq/scaling_governor")
        self.governor = None

    def read(self):
        governor = read_first_line(self.path)
        if governor:
            self.governor = governor
        else:
            self.error("Unable to read CPU scaling governor from %s" % self.path)

    def show(self):
        if self.governor:
            self.info(self.governor)

    def write(self, tune):
        new_governor = 'performance' if tune else 'powersave'
        self.read()
        if not self.governor:
            return

        if new_governor == self.governor:
            return
        try:
            write_text(self.path, new_governor)
        except IOError as exc:
            self.error("Failed to to set the CPU scaling governor: %s" % exc)
        else:
            self.info("CPU scaling governor set to %s" % new_governor)


class LinuxScheduler(Operation):
    """
    Check isolcpus=cpus and rcu_nocbs=cpus paramaters of the Linux kernel
    command line.
    """

    def __init__(self, system):
        Operation.__init__(self, 'Linux scheduler', system)
        self.ncpu = None
        self.linux_version = None
        self.msgs = []

    def read(self):
        self.ncpu = get_logical_cpu_count()
        if self.ncpu is None:
            self.error("Unable to get the number of CPUs")
            return

        release = os.uname()[2]
        try:
            version_txt = release.split('-', 1)[0]
            self.linux_version = tuple(map(int, version_txt.split('.')))
        except ValueError:
            self.error("Failed to get the Linux version: release=%r" % release)
            return

        # isolcpus= parameter existed prior to 2.6.12-rc2 (2005)
        # which is first commit of the Linux git repository
        self.check_isolcpus()

        # Commit 3fbfbf7a3b66ec424042d909f14ba2ddf4372ea8 added rcu_nocbs
        if self.linux_version >= (3, 8):
            self.check_rcu_nocbs()

    def check_isolcpus(self):
        isolated = get_isolated_cpus()
        if isolated:
            self.msgs.append('Isolated CPUs (%s/%s): %s'
                             % (len(isolated), self.ncpu,
                                format_cpu_list(isolated)))
        elif self.ncpu > 1:
            self.msgs.append('Use isolcpus=<cpu list> kernel parameter '
                             'to isolate CPUs')

    def read_rcu_nocbs(self):
        cmdline = read_first_line(proc_path('cmdline'))
        if not cmdline:
            return

        match = re.search(r'\brcu_nocbs=([^ ]+)', cmdline)
        if not match:
            return

        cpus = match.group(1)
        return parse_cpu_list(cpus)

    def check_rcu_nocbs(self):
        rcu_nocbs = self.read_rcu_nocbs()
        if rcu_nocbs:
            self.msgs.append('RCU disabled on CPUs (%s/%s): %s'
                             % (len(rcu_nocbs), self.ncpu,
                                format_cpu_list(rcu_nocbs)))
        elif self.ncpu > 1:
            self.msgs.append('Use rcu_nocbs=<cpu list> kernel parameter '
                             '(with isolcpus) to not not schedule RCU '
                             'on isolated CPUs (Linux 3.8 and newer)')

    def show(self):
        for msg in self.msgs:
            self.info(msg)


class ASLR(Operation):
    # randomize_va_space procfs existed prior to 2.6.12-rc2 (2005)
    # which is first commit of the Linux git repository

    STATE = {'0': 'No randomization',
             '1': 'Conservative randomization',
             '2': 'Full randomization'}

    def __init__(self, system):
        Operation.__init__(self, 'ASLR', system)
        self.path = proc_path("sys/kernel/randomize_va_space")
        self.aslr = None

    def read(self):
        line = read_first_line(self.path)
        if line in self.STATE:
            self.aslr = line
        else:
            self.error("Failed to read %s" % self.path)

    def show(self):
        if not self.aslr:
            return

        state = self.STATE[self.aslr]
        self.info(state)

    def write(self, tune):
        self.read()
        value = self.aslr
        if not value:
            return

        new_value = '2'
        if new_value == value:
            return

        try:
            with open(self.path, 'w') as fp:
                fp.write(new_value)

            self.info("Full randomization enabled: %r written into %s"
                      % (new_value, self.path))
        except IOError as exc:
            self.error("Failed to write into %s: %s" % (self.path, exc))


class CPUFrequency(Operation):
    """
    Read/Write /sys/devices/system/cpu/cpuN/cpufreq/scaling_min_freq.
    """

    def __init__(self, system):
        Operation.__init__(self, 'CPU Frequency', system)
        self.path = sysfs_path("devices/system/cpu")
        self.cpus = {}

    def read_cpu(self, cpu):
        path = os.path.join(self.path, 'cpu%s/cpufreq' % cpu)

        scaling_min_freq = read_first_line(os.path.join(path, "scaling_min_freq"))
        scaling_max_freq = read_first_line(os.path.join(path, "scaling_max_freq"))
        if not scaling_min_freq or not scaling_max_freq:
            self.error("Unable to read scaling_min_freq "
                       "or scaling_max_freq of CPU %s" % cpu)
            return

        scaling_min_freq = int(scaling_min_freq)
        scaling_max_freq = int(scaling_max_freq)
        freq = ('min=%s MHz, max=%s MHz'
                % (scaling_min_freq // 1000, scaling_max_freq // 1000))
        self.cpus[cpu] = freq

    def read(self):
        cpus = get_logical_cpu_count()
        if not cpus:
            self.error("Unable to get the number of CPUs")
            return

        for cpu in range(cpus):
            self.read_cpu(cpu)

    def show(self):
        infos = format_cpu_infos(self.cpus)
        if not infos:
            return

        self.info('; '.join(infos))

    def read_freq(self, filename):
        try:
            with open(filename, "rb") as fp:
                return fp.readline()
        except IOError:
            return None

    def write_freq(self, filename, new_freq):
        with open(filename, "rb") as fp:
            freq = fp.readline()

        if new_freq == freq:
            return False

        with open(filename, "wb") as fp:
            fp.write(new_freq)
        return True

    def write_cpu(self, cpu, tune):
        path = os.path.join(self.path, 'cpu%s/cpufreq' % cpu)

        if not tune:
            min_freq = self.read_freq(os.path.join(path, "cpuinfo_min_freq"))
            if not min_freq:
                self.error("Unable to read cpuinfo_min_freq of CPU %s" % cpu)
                return

        max_freq = self.read_freq(os.path.join(path, "cpuinfo_max_freq"))
        if not max_freq:
            self.error("Unable to read cpuinfo_max_freq of CPU %s" % cpu)
            return

        try:
            filename = os.path.join(path, "scaling_min_freq")
            if tune:
                if self.write_freq(filename, max_freq):
                    self.info("Minimum frequency of CPU %s "
                              "set to the maximum frequency" % cpu)
            else:
                if self.write_freq(filename, min_freq):
                    self.info("Minimum frequency of CPU %s "
                              "reset to the minimum frequency" % cpu)
        except IOError:
            self.error("Unable to write scaling_max_freq of CPU %s" % cpu)
            return

    def write(self, tune):
        cpus = get_isolated_cpus()
        if not cpus:
            ncpu = get_logical_cpu_count()
            if not ncpu:
                self.error("Unable to get the number of CPUs")
                return
            cpus = tuple(range(ncpu))

        for cpu in cpus:
            self.write_cpu(cpu, tune)


def use_intel_pstate(cpu):
    path = sysfs_path("devices/system/cpu/cpu%s/cpufreq/scaling_driver" % cpu)
    scaling_driver = read_first_line(path)
    return (scaling_driver == 'intel_pstate')


class System:
    def __init__(self):
        self.operations = []
        self.errors = []
        self.has_messages = False

        self.operations.append(ASLR(self))

        if sys.platform.startswith('linux'):
            self.operations.append(LinuxScheduler(self))

        self.operations.append(CPUFrequency(self))

        if use_intel_pstate(0):
            # Setting the CPU scaling governor resets no_turbo and so must be
            # set before Turbo Boost
            self.operations.append(CPUGovernorIntelPstate(self))
            self.operations.append(TurboBoostIntelPstate(self))
        else:
            self.operations.append(TurboBoostMSR(self))

    def get_cpus(self):
        cpu_count = get_logical_cpu_count()
        if not cpu_count:
            print("ERROR: unable to get the number of logical CPUs")
            sys.exit(1)

        return tuple(range(cpu_count))

    def info(self, msg):
        print(msg)
        self.has_messages = True

    def error(self, msg):
        self.errors.append(msg)

    def main(self, action):
        if action in ('tune', 'reset'):
            tune = (action == 'tune')
            for operation in self.operations:
                operation.write(tune)

        for operation in self.operations:
            operation.read()

        if self.has_messages:
            print()

        for operation in self.operations:
            operation.show()

        if self.errors:
            print()
            for msg in self.errors:
                print("ERROR: %s" % msg)
