from __future__ import division, print_function, absolute_import

import errno
import os
import subprocess
import sys

from perf._utils import (read_first_line, sysfs_path,
                         format_cpu_list, get_logical_cpu_count)

MSR_IA32_MISC_ENABLE = 0x1a0
MSR_IA32_MISC_ENABLE_TURBO_DISABLE_BIT = 38


def is_root():
    return (os.getuid() == 0)


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

    stdout = proc.communicate()[0]
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

    def show(self):
        pass

    def read(self):
        pass

    def tune(self):
        pass

    def reset(self):
        pass


class TurboBoostMSR(Operation):
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
            print("%s: %s" % (self.name, ', '.join(text)))

    def read_msr(self, cpu, reg_num, bitfield=None):
        # -x for hexadecimal output
        cmd = ['rdmsr', '-p%s' % cpu, '-x']
        if bitfield:
            cmd.extend(('-f', bitfield))
        cmd.append('%#x' % reg_num)

        exitcode, stdout = get_output(cmd)
        stdout = stdout.rstrip()

        if exitcode or not stdout:
            msg = ('Failed to read MSR %#x of CPU %s '
                  '(exit code %s). '
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

    def write(self, enabled):
        cpus = self.system.get_cpus()
        for cpu in cpus:
            self.write_cpu(cpu, enabled)

    def tune(self):
        self.write(False)

    def reset(self):
        self.write(True)


class TurboBoostIntelPstate(Operation):
    def __init__(self, system):
        Operation.__init__(self, 'Turbo Boost (intel_pstate driver)', system)
        self.enabled = None

    def show(self):
        if self.enabled is None:
            return

        enabled = 'enabled' if self.enabled else 'disabled'
        print("%s: %s" % (self.name, enabled))

    def read(self):
        path = sysfs_path("devices/system/cpu/intel_pstate/no_turbo")
        no_turbo = read_first_line(path)

        if no_turbo == '1':
            self.enabled = False
        elif no_turbo == '0':
            self.enabled = True
        else:
            self.error("Invalid no_turbo value: %r" % no_turbo)

    def write(self, enabled):
        if self.enabled is None:
            self.read()
            if self.enabled == enabled:
                # no_turbo already set to the expected value
                return

        path = sysfs_path("devices/system/cpu/intel_pstate/no_turbo")
        content = '0' if enabled else '1'

        try:
            with open(path, 'w') as fp:
                fp.write(content)

            msg = "%r written into %s" % (content, path)
            if enabled:
                self.info("Turbo Boost enabled: %s" % msg)
            else:
                self.info("Turbo Boost disabled: %s" % msg)
        except IOError as exc:
            msg = "Failed to write into %s" % path
            if exc.errno in (errno.EPERM, errno.EACCES) and not is_root():
                msg += " (retry as root?)"
            self.error("%s: %s" % (msg, exc))

    def tune(self):
        self.write(False)

    def reset(self):
        self.write(True)


def use_intel_pstate(cpu):
    path = sysfs_path("devices/system/cpu/cpu%s/cpufreq/scaling_driver" % cpu)
    scaling_driver = read_first_line(path)
    return (scaling_driver == 'intel_pstate')


class System:
    def __init__(self):
        self.operations = []
        self.errors = []
        self.has_messages = False

        if use_intel_pstate(0):
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
        tune = (action == 'tune')
        reset = (action == 'reset')

        for operation in self.operations:
            if tune:
                operation.tune()
            elif reset:
                operation.reset()
            operation.read()

        if self.has_messages:
            print()

        for operation in self.operations:
            operation.show()

        if self.errors:
            print()
            for msg in self.errors:
                print("ERROR: %s" % msg)
