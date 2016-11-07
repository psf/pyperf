from __future__ import division, print_function, absolute_import

import errno
import os
import re
import struct
import subprocess
import sys

from perf._cli import display_title
from perf._cpu_utils import (parse_cpu_list,
                             get_logical_cpu_count, get_isolated_cpus,
                             format_cpu_list, format_cpu_infos)
from perf._utils import (read_first_line, sysfs_path, proc_path, open_text,
                         popen_communicate)


MSR_IA32_MISC_ENABLE = 0x1a0
MSR_IA32_MISC_ENABLE_TURBO_DISABLE_BIT = 38


def is_root():
    return (os.getuid() == 0)


def is_permission_error(exc):
    return exc.errno in (errno.EACCES, errno.EPERM)


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


def use_intel_pstate(cpu):
    path = sysfs_path("devices/system/cpu/cpu%s/cpufreq/scaling_driver" % cpu)
    scaling_driver = read_first_line(path)
    return (scaling_driver == 'intel_pstate')


class Operation(object):
    def __init__(self, name, system):
        self.name = name
        self.system = system
        self.permission_error = False

    def advice(self, msg):
        self.system.advice('%s: %s' % (self.name, msg))

    def info(self, msg):
        self.system.info('%s: %s' % (self.name, msg))

    def error(self, msg):
        self.system.error('%s: %s' % (self.name, msg))

    def check_permission_error(self, exc):
        if is_permission_error(exc):
            self.permission_error = True

    def read(self):
        pass

    def show(self):
        pass

    def write(self, tune):
        pass


class TurboBoostMSR(Operation):
    """
    Get/Set Turbo Boost mode of Intel CPUs using /dev/cpu/N/msr.
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

    def read_msr(self, cpu, reg_num, bit=None):
        path = '/dev/cpu/%s/msr' % cpu
        size = struct.calcsize('Q')
        if size != 8:
            # FIXME: always use size=8 but replace unpack() with something else
            raise ValueError("need a 64-bit unsigned integer type")
        try:
            fd = os.open(path, os.O_RDONLY)
            try:
                data = os.pread(fd, size, reg_num)
            finally:
                os.close(fd)
        except IOError as exc:
            self.check_permission_error(exc)
            self.error("Failed to read MSR %#x from %s: %s"
                       % (reg_num, path, exc))
            return None

        reg = struct.unpack('Q', data)[0]
        if bit is not None:
            return bool(reg & (1 << bit))
        else:
            return reg

    def read_cpu(self, cpu):
        msr = self.read_msr(cpu, MSR_IA32_MISC_ENABLE,
                            bit=MSR_IA32_MISC_ENABLE_TURBO_DISABLE_BIT)
        if msr is None:
            return

        self.cpu_states[cpu] = (not msr)

    def read(self):
        for cpu in range(self.system.logical_cpu_count):
            if self.permission_error:
                break
            self.read_cpu(cpu)

    def write_msr(self, cpu, reg_num, value):
        path = '/dev/cpu/%s/msr' % cpu
        size = struct.calcsize('Q')
        if size != 8:
            # FIXME: always use size=8 but replace pack() with something else
            raise ValueError("need a 64-bit unsigned integer type")
        data = struct.pack('Q', value)
        try:
            fd = os.open(path, os.O_WRONLY)
            try:
                data = os.pwrite(fd, data, reg_num)
            finally:
                os.close(fd)
        except IOError as exc:
            self.check_permission_error(exc)
            self.error("Failed to write %#x into MSR %#x using %s: %s"
                       % (value, reg_num, path, exc))
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
        if tune:
            cpus = self.system.cpus
        else:
            cpus = range(self.system.logical_cpu_count)

        for cpu in cpus:
            self.write_cpu(cpu, enabled)
            if self.permission_error:
                break


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
        enable = (not tune)

        self.read()
        if self.enabled == enable:
            # no_turbo already set to the expected value
            return

        content = '0' if enable else '1'
        try:
            write_text(self.path, content)
        except IOError as exc:
            self.check_permission_error(exc)
            action = 'enable' if enable else 'disable'
            msg = "Failed to %s Turbo Boost" % action
            if is_permission_error(exc) and is_root():
                msg += " (Turbo Boost disabled in the BIOS?)"
            msg += ": failed to write into %s" % self.path
            self.error("%s: %s" % (msg, exc))
            return

        msg = "%r written into %s" % (content, self.path)
        action = 'enabled' if enable else 'disabled'
        self.info("Turbo Boost %s: %s" % (action, msg))


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
            self.error("Failed to set the CPU scaling governor: %s" % exc)
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

    def show(self):
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
            self.info('Isolated CPUs (%s/%s): %s'
                      % (len(isolated), self.ncpu,
                         format_cpu_list(isolated)))
        elif self.ncpu > 1:
            self.info('No CPU is isolated')
            self.advice('Use isolcpus=<cpu list> kernel parameter '
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
            self.info('RCU disabled on CPUs (%s/%s): %s'
                      % (len(rcu_nocbs), self.ncpu,
                         format_cpu_list(rcu_nocbs)))
        elif self.ncpu > 1:
            self.advice('Use rcu_nocbs=<cpu list> kernel parameter '
                        '(with isolcpus) to not not schedule RCU '
                        'on isolated CPUs (Linux 3.8 and newer)')


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

        min_mhz = int(scaling_min_freq) // 1000
        max_mhz = int(scaling_max_freq) // 1000
        if min_mhz != max_mhz:
            freq = ('min=%s MHz, max=%s MHz'
                    % (min_mhz, max_mhz))
        else:
            freq = 'min=max=%s MHz' % max_mhz
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
        except IOError as exc:
            self.check_permission_error(exc)
            self.error("Unable to write scaling_max_freq of CPU %s: %s"
                       % (cpu, exc))
            return

    def write(self, tune):
        for cpu in self.system.cpus:
            self.write_cpu(cpu, tune)
            if self.permission_error:
                break


class IRQAffinity(Operation):
    def __init__(self, system):
        Operation.__init__(self, 'IRQ affinity', system)
        self.irq_path = proc_path('irq')
        self.irq_affinity_path = os.path.join(self.irq_path, "%s/smp_affinity")
        self.default_affinity_path = os.path.join(self.irq_path, 'default_smp_affinity')

        self.irqbalance_active = None
        self.systemctl = True
        self.irqs = None
        self.irq_affinity = {}
        self.default_smp_affinity = None

    def read_irqbalance_systemctl(self):
        cmd = ('systemctl', 'status', 'irqbalance')
        exitcode, stdout = get_output(cmd)
        if not stdout:
            # systemctl is not installed? ignore errors
            self.systemctl = False
            return

        match = re.search(r"^ *Loaded: (.*)$", stdout, flags=re.MULTILINE)
        if not match:
            self.error("Failed to parse systemctl loaded state: %r" % stdout)
            return
        self.systemctl = True

        loaded = match.group(1)
        if loaded.startswith('not-found'):
            # irqbalance service is not installed: do nothing
            return

        match = re.search(r"^ *Active: ([^ ]+)", stdout, flags=re.MULTILINE)
        if not match:
            self.error("Failed to parse systemctl active state: %r" % stdout)
            return

        active = match.group(1)
        if active in ('active', 'activating'):
            self.irqbalance_active = True
        elif active in ('inactive', 'deactivating', 'dead'):
            self.irqbalance_active = False
        else:
            self.error("Unknown service state: %r" % active)

    def read_irqbalance_service(self):
        cmd = ('service', 'irqbalance', 'status')
        exitcode, stdout = get_output(cmd)
        if not stdout:
            # failed to the the status: ignore
            return

        stdout = stdout.rstrip()
        state = stdout.split(' ', 1)[-1]
        if state.startswith('stop'):
            self.irqbalance_active = False
        elif state.startswith('start'):
            self.irqbalance_active = True
        else:
            self.error("Unknown service state: %r" % stdout)

    def read_irqbalance_state(self):
        self.read_irqbalance_systemctl()
        if self.systemctl is False:
            self.read_irqbalance_service()

    def parse_affinity(self, mask):
        mask = int(mask, 16)
        cpus = []
        for cpu in range(self.system.logical_cpu_count):
            cpu_mask = 1 << cpu
            if cpu_mask & mask:
                cpus.append(cpu)
        return cpus

    def read_default_affinity(self):
        mask = read_first_line(self.default_affinity_path)
        if not mask:
            return

        self.default_smp_affinity = self.parse_affinity(mask)

    def get_irqs(self):
        if self.irqs is None:
            filenames = os.listdir(self.irq_path)
            self.irqs = [int(name) for name in filenames if name.isdigit()]
            self.irqs.sort()
        return self.irqs

    def read_irq_affinity(self, irq):
        path = self.irq_affinity_path % irq
        try:
            mask = read_first_line(path, error=True)
        except IOError as exc:
            self.check_permission_error(exc)
            self.error("Failed to read %s: %s" % (path, exc))
            return

        cpus = self.parse_affinity(mask)
        self.irq_affinity[irq] = cpus

    def read_irqs_affinity(self):
        for irq in self.get_irqs():
            if self.permission_error:
                break
            self.read_irq_affinity(irq)

    def read(self):
        self.read_irqbalance_state()
        self.read_default_affinity()
        self.read_irqs_affinity()

    def show(self):
        if self.irqbalance_active is not None:
            state = 'active' if self.irqbalance_active else 'inactive'
            self.info("irqbalance service: %s" % state)

        if self.default_smp_affinity:
            self.info("Default IRQ affinity: CPU %s"
                      % format_cpu_list(self.default_smp_affinity))

        if self.irq_affinity:
            infos = {irq: format_cpu_list(cpus)
                     for irq, cpus in self.irq_affinity.items()}
            infos = format_cpu_infos(infos)
            self.info('IRQ affinity: %s' % ', '.join(infos))

    def create_affinity(self, cpus):
        mask = 0
        for cpu in cpus:
            mask |= (1 << cpu)
        return "%x" % mask

    def write_irqbalance_service(self, enable):
        self.read_irqbalance_state()
        if self.irqbalance_active is None:
            # systemd service missing or failed to get its state:
            # don't try to start/stop the irqbalance service
            return

        if self.irqbalance_active == enable:
            # service is already in the expected state: nothing to do
            return

        action = 'start' if enable else 'stop'
        if self.systemctl is False:
            cmd = ('service', 'irqbalance', action)
        else:
            cmd = ('systemctl', action, 'irqbalance')
        exitcode = run_cmd(cmd)
        if exitcode:
            self.error('Failed to %s irqbalance service: '
                       '%s failed with exit code %s'
                       % (action, ' '.join(cmd), exitcode))
            return

        action = 'Start' if enable else 'Stop'
        self.info("%s irqbalance service" % action)

    def write_default(self, new_affinity):
        self.read_default_affinity()
        if new_affinity == self.default_smp_affinity:
            return

        mask = self.create_affinity(new_affinity)
        try:
            write_text(self.default_affinity_path, mask)
        except IOError as exc:
            self.check_permission_error(exc)
            self.error("Failed to write %r into %s: %s"
                       % (mask, self.default_affinity_path, exc))
        else:
            self.info("Set default affinity to CPU %s: write %r into %s"
                      % (format_cpu_list(new_affinity), mask,
                         self.default_affinity_path))

    def write_irq(self, irq, cpus):
        path = self.irq_affinity_path % irq
        mask = self.create_affinity(cpus)
        try:
            write_text(path, mask)
        except IOError as exc:
            self.check_permission_error(exc)
            # EIO means that the IRQ doesn't support SMP affinity:
            # ignore the error
            if exc.errno != errno.EIO:
                self.error("Failed to write %r into %s: %s"
                           % (mask, path, exc))
        else:
            self.info("Set affinity to CPU %s: write %r into %s"
                      % (format_cpu_list(cpus), mask, path))

    def write_irqs(self, new_cpus):
        self.read_irqs_affinity()
        for irq in self.get_irqs():
            if self.permission_error:
                break

            cpus = self.irq_affinity.get(irq)
            if new_cpus != cpus:
                self.write_irq(irq, new_cpus)

    def write(self, tune):
        cpus = range(self.system.logical_cpu_count)
        if tune:
            excluded = set(self.system.cpus)
            # Only compute the subset if excluded is not the full list of cpus
            if excluded != set(cpus):
                cpus = (cpu for cpu in cpus if cpu not in excluded)
        cpus = list(cpus)

        self.write_irqbalance_service(not tune)
        # FIXME: skip on old Linux not supported it?
        self.write_default(cpus)
        self.write_irqs(cpus)


class CheckNOHZFullIntelPstate(Operation):
    def __init__(self, system):
        Operation.__init__(self, 'Check nohz_full', system)

    def show(self):
        nohz_full = read_first_line(sysfs_path('devices/system/cpu/nohz_full'))
        if not nohz_full:
            return

        nohz_full = parse_cpu_list(nohz_full)
        if not nohz_full:
            return

        used = set(self.system.cpus) | set(nohz_full)
        if not used:
            return

        self.advice("WARNING: nohz_full is enabled on CPUs %s which use the "
                    "intel_pstate driver, whereas intel_pstate is incompatible "
                    "with nohz_full"
                    % format_cpu_list(used))
        self.advice("See https://bugzilla.redhat.com/show_bug.cgi?id=1378529")


class System:
    def __init__(self):
        self.operations = []

        self.infos = []
        self.advices = []
        self.errors = []
        self.has_messages = False

        self.logical_cpu_count = None
        # CPUs used for benchmarking: tuple of CPU identifiers
        self.cpus = None

        self.operations.append(ASLR(self))

        if sys.platform.startswith('linux'):
            self.operations.append(LinuxScheduler(self))

        self.operations.append(CPUFrequency(self))

        if use_intel_pstate(0):
            # Setting the CPU scaling governor resets no_turbo and so must be
            # set before Turbo Boost
            self.operations.append(CPUGovernorIntelPstate(self))
            self.operations.append(TurboBoostIntelPstate(self))
            self.operations.append(CheckNOHZFullIntelPstate(self))
        else:
            self.operations.append(TurboBoostMSR(self))

        self.operations.append(IRQAffinity(self))

    def advice(self, msg):
        self.advices.append(msg)

    def info(self, msg):
        self.infos.append(msg)

    def error(self, msg):
        self.errors.append(msg)

    def write_messages(self, title, messages):
        if not messages:
            return

        display_title(title)
        for msg in messages:
            print(msg)
        print()

    def run_operations(self, action):
        if action in ('tune', 'reset'):
            tune = (action == 'tune')
            for operation in self.operations:
                operation.write(tune)

        self.write_messages("Actions", self.infos)
        del self.infos[:]

        for operation in self.operations:
            # FIXME: merge read() and show()?
            operation.read()

        self.write_messages("Info", self.infos)
        del self.infos[:]

        for operation in self.operations:
            operation.show()

    def main(self, action, args):
        self.logical_cpu_count = get_logical_cpu_count()
        if not self.logical_cpu_count:
            sys.exit(1)

        isolated = get_isolated_cpus()
        if isolated:
            self.cpus = tuple(isolated)
        elif args.affinity:
            self.cpus = tuple(args.affinity)
        else:
            self.cpus = tuple(range(self.logical_cpu_count))
        # The list of cpus must be sorted to avoid useless write in operations
        assert sorted(self.cpus) == list(self.cpus)

        self.run_operations(action)

        if any(operation.permission_error for operation in self.operations):
            msg = "ERROR: At least one operation failed with permission error"
            if not is_root():
                msg += ", retry as root"
            self.error(msg)

        self.write_messages("System state", self.infos)
        # Advices are for tuning: hide them for reset
        if action == 'tune':
            self.write_messages("Advices", self.advices)
        self.write_messages("Errors", self.errors)
