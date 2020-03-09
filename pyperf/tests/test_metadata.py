import io
import sys
import textwrap
import unittest
from unittest import mock

from pyperf import _collect_metadata as perf_metadata
from pyperf._metadata import METADATA_VALUE_TYPES


MANDATORY_METADATA = [
    'date',
    'python_implementation', 'python_version',
    'platform']
if sys.platform.startswith('linux'):
    MANDATORY_METADATA.append('aslr')


class TestMetadata(unittest.TestCase):
    def test_collect_metadata(self):
        metadata = perf_metadata.collect_metadata()

        for key in MANDATORY_METADATA:
            self.assertIn(key, metadata)

        for key, value in metadata.items():
            # test key
            self.assertIsInstance(key, str)
            self.assertRegex(key, '^[a-z][a-z0-9_]+$')

            # test value
            self.assertIsInstance(value, METADATA_VALUE_TYPES)
            self.assertNotEqual(value, '')
            if isinstance(value, str):
                self.assertEqual(value.strip(), value)
                self.assertNotIn('\n', value)

    def test_collect_cpu_affinity(self):
        metadata = {}
        perf_metadata.collect_cpu_affinity(metadata, {2, 3}, 4)
        self.assertEqual(metadata['cpu_affinity'], '2-3')

        metadata = {}
        perf_metadata.collect_cpu_affinity(metadata, {0, 1, 2, 3}, 4)
        self.assertNotIn('cpu_affinity', metadata)


class CpuFunctionsTests(unittest.TestCase):
    INTEL_CPU_INFO = textwrap.dedent("""
        processor : 0
        vendor_id\t: GenuineIntel
        cpu family\t: 6
        model\t\t: 58
        model name\t: Intel(R) Core(TM) i7-3520M CPU @ 2.90GHz
        stepping\t: 9
        microcode\t: 0x1c
        cpu MHz\t\t: 1287.554
        cache size\t: 4096 KB
        physical id\t: 0
        siblings\t: 4
        core id\t\t: 0
        cpu cores\t: 2
        apicid\t\t: 0
        initial apicid\t: 0
        fpu\t\t: yes
        fpu_exception\t: yes
        cpuid level\t: 13
        wp\t\t: yes
        flags\t\t: fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush dts acpi mmx fxsr sse sse2 ss ht tm pbe syscall nx rdtscp lm constant_tsc arch_perfmon pebs bts rep_good nopl xtopology nonstop_tsc aperfmperf eagerfpu pni pclmulqdq dtes64 monitor ds_cpl vmx smx est tm2 ssse3 cx16 xtpr pdcm pcid sse4_1 sse4_2 x2apic popcnt tsc_deadline_timer aes xsave avx f16c rdrand lahf_lm epb tpr_shadow vnmi flexpriority ept vpid fsgsbase smep erms xsaveopt dtherm ida arat pln pts
        bugs\t\t:
        bogomips\t: 5786.64
        clflush size\t: 64
        cache_alignment\t: 64
        address sizes\t: 36 bits physical, 48 bits virtual
        power management:

        processor\t: 1
        vendor_id\t: GenuineIntel
        cpu family\t: 6
        model\t\t: 58
        model name\t: Intel(R) Core(TM) i7-3520M CPU @ 2.90GHz
        stepping\t: 9
        microcode\t: 0x1c
        cpu MHz\t\t: 1225.363
        cache size\t: 4096 KB
        physical id\t: 0
        siblings\t: 4
        core id\t\t: 0
        cpu cores\t: 2
        apicid\t\t: 1
        initial apicid\t: 1
        fpu\t\t: yes
        fpu_exception\t: yes
        cpuid level\t: 13
        wp\t\t: yes
        flags\t\t: fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush dts acpi mmx fxsr sse sse2 ss ht tm pbe syscall nx rdtscp lm constant_tsc arch_perfmon pebs bts rep_good nopl xtopology nonstop_tsc aperfmperf eagerfpu pni pclmulqdq dtes64 monitor ds_cpl vmx smx est tm2 ssse3 cx16 xtpr pdcm pcid sse4_1 sse4_2 x2apic popcnt tsc_deadline_timer aes xsave avx f16c rdrand lahf_lm epb tpr_shadow vnmi flexpriority ept vpid fsgsbase smep erms xsaveopt dtherm ida arat pln pts
        bugs\t\t:
        bogomips\t: 5791.91
        clflush size\t: 64
        cache_alignment\t: 64
        address sizes\t: 36 bits physical, 48 bits virtual
        power management:

        processor\t: 2
        vendor_id\t: GenuineIntel
        cpu family\t: 6
        model\t\t: 58
        model name\t: Intel(R) Core(TM) i7-3520M CPU @ 2.90GHz
        stepping\t: 9
        microcode\t: 0x1c
        cpu MHz\t\t: 1200.101
        cache size\t: 4096 KB
        physical id\t: 0
        siblings\t: 4
        core id\t\t: 1
        cpu cores\t: 2
        apicid\t\t: 2
        initial apicid\t: 2
        fpu\t\t: yes
        fpu_exception\t: yes
        cpuid level\t: 13
        wp\t\t: yes
        flags\t\t: fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush dts acpi mmx fxsr sse sse2 ss ht tm pbe syscall nx rdtscp lm constant_tsc arch_perfmon pebs bts rep_good nopl xtopology nonstop_tsc aperfmperf eagerfpu pni pclmulqdq dtes64 monitor ds_cpl vmx smx est tm2 ssse3 cx16 xtpr pdcm pcid sse4_1 sse4_2 x2apic popcnt tsc_deadline_timer aes xsave avx f16c rdrand lahf_lm epb tpr_shadow vnmi flexpriority ept vpid fsgsbase smep erms xsaveopt dtherm ida arat pln pts
        bugs\t\t:
        bogomips\t: 5790.60
        clflush size\t: 64
        cache_alignment\t: 64
        address sizes\t: 36 bits physical, 48 bits virtual
        power management:
    """)

    POWER8_CPUINFO = textwrap.dedent("""
        processor       : 0
        cpu             : POWER8E (raw), altivec supported
        clock           : 3425.000000MHz
        revision        : 2.1 (pvr 004b 0201)

        processor       : 159
        cpu             : POWER8E (raw), altivec supported
        clock           : 3425.000000MHz
        revision        : 2.1 (pvr 004b 0201)

        timebase        : 512000000
        platform        : PowerNV
        model           : 8247-22L
        machine         : PowerNV 8247-22L
        firmware        : OPAL v3
    """)

    def test_cpu_config(self):
        nohz_full = '2-3\n'

        def mock_open(filename, *args, **kw):
            filename = filename.replace('\\', '/')
            if filename == '/sys/devices/system/cpu/cpu0/cpufreq/scaling_driver':
                data = 'DRIVER\n'
            elif filename == '/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor':
                data = 'GOVERNOR\n'
            elif filename.startswith('/sys/devices/system/cpu/nohz_full'):
                data = nohz_full
            elif filename.startswith('/sys/devices/system/cpu/cpu2'):
                raise IOError
            elif filename == '/sys/devices/system/cpu/cpuidle/current_driver':
                data = 'IDLE_DRV\n'
            else:
                raise ValueError("unexpect open: %r" % filename)
            return io.StringIO(data)

        with mock.patch('pyperf._collect_metadata.get_isolated_cpus', return_value=[2]):
            with mock.patch('pyperf._utils.open', create=True, side_effect=mock_open):
                metadata = {}
                perf_metadata.collect_cpu_config(metadata, [0, 2])
        self.assertEqual(metadata['cpu_config'],
                         '0=driver:DRIVER, governor:GOVERNOR; '
                         '2=nohz_full, isolated; '
                         'idle:IDLE_DRV')

        nohz_full = '  (null)\n'
        with mock.patch('pyperf._collect_metadata.get_isolated_cpus'):
            with mock.patch('pyperf._utils.open', create=True, side_effect=mock_open):
                metadata = {}
                perf_metadata.collect_cpu_config(metadata, [0, 2])
        self.assertEqual(metadata['cpu_config'],
                         '0=driver:DRIVER, governor:GOVERNOR; '
                         'idle:IDLE_DRV')

    def test_intel_cpu_frequencies(self):
        def mock_open(filename, *args, **kw):
            filename = filename.replace('\\', '/')
            if filename == '/proc/cpuinfo':
                data = self.INTEL_CPU_INFO
            elif filename == '/sys/devices/system/cpu/cpu0/cpufreq/scaling_driver':
                data = 'DRIVER\n'
            elif filename == '/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor':
                data = 'GOVERNOR\n'
            elif filename.startswith('/sys/devices/system/cpu/cpu2'):
                raise IOError
            else:
                raise ValueError("unexpect open: %r" % filename)
            return io.StringIO(data)

        with mock.patch('pyperf._utils.open', create=True, side_effect=mock_open):
            metadata = {}
            perf_metadata.collect_cpu_freq(metadata, [0, 2])
            perf_metadata.collect_cpu_model(metadata)
            self.assertEqual(metadata['cpu_freq'],
                             '0=1288 MHz; 2=1200 MHz')
            self.assertEqual(metadata['cpu_model_name'],
                             'Intel(R) Core(TM) i7-3520M CPU @ 2.90GHz')

    def test_power8_cpu_frequencies(self):
        def mock_open(filename, *args, **kw):
            filename = filename.replace('\\', '/')
            if filename == '/proc/cpuinfo':
                data = self.POWER8_CPUINFO
            else:
                raise ValueError("unexpect open: %r" % filename)
            return io.StringIO(data)

        with mock.patch('pyperf._utils.open', create=True, side_effect=mock_open):
            metadata = {}
            perf_metadata.collect_cpu_freq(metadata, [0, 159])
            perf_metadata.collect_cpu_model(metadata)
            self.assertEqual(metadata['cpu_freq'],
                             '0,159=3425 MHz')
            self.assertEqual(metadata['cpu_machine'],
                             'PowerNV 8247-22L')


if __name__ == "__main__":
    unittest.main()
