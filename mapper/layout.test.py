import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapper import layout


class RegionTest(unittest.TestCase):
    def test_work_ram_banks_are_named_as_work_ram(self):
        for bank in (0x7E, 0x7F):
            self.assertEqual(layout.resolve(layout.LOROM, bank << 16).region, layout.WORK_RAM)

    def test_the_bottom_of_a_low_bank_is_the_mirror_of_work_ram(self):
        found = layout.resolve(layout.LOROM, 0x000100)

        self.assertEqual(found.region, layout.WORK_RAM)

    def test_the_register_window_is_named_as_registers(self):
        for address in (0x002100, 0x004200, 0x004300, 0x00420B):
            self.assertEqual(layout.resolve(layout.LOROM, address).region, layout.REGISTERS)

    def test_the_upper_half_of_a_low_bank_is_cartridge(self):
        self.assertEqual(layout.resolve(layout.LOROM, 0x008000).region, layout.ROM)

    def test_a_high_bank_is_cartridge_throughout_in_high_rom(self):
        self.assertEqual(layout.resolve(layout.HIROM, 0xC00000).region, layout.ROM)

    def test_save_memory_has_its_own_window_in_low_rom(self):
        self.assertEqual(layout.resolve(layout.LOROM, 0x700000).region, layout.SAVE_RAM)


class SpeedTest(unittest.TestCase):
    def test_the_low_half_of_the_space_is_always_slow(self):
        self.assertEqual(layout.resolve(layout.LOROM, 0x008000, fast=True).cycles, layout.SLOW)

    def test_the_upper_half_runs_fast_when_the_cartridge_asks(self):
        self.assertEqual(layout.resolve(layout.LOROM, 0x808000, fast=True).cycles, layout.FAST)

    def test_the_upper_half_stays_slow_when_it_does_not(self):
        self.assertEqual(layout.resolve(layout.LOROM, 0x808000, fast=False).cycles, layout.SLOW)

    def test_work_ram_never_runs_fast(self):
        self.assertEqual(layout.resolve(layout.LOROM, 0x7E0000, fast=True).cycles, layout.SLOW)

    def test_the_register_window_runs_at_its_own_speed(self):
        self.assertEqual(layout.resolve(layout.LOROM, 0x004200, fast=True).cycles, layout.XSLOW)


class OffsetTest(unittest.TestCase):
    def test_a_low_rom_bank_maps_its_upper_half_to_a_thirty_two_kilobyte_page(self):
        self.assertEqual(layout.resolve(layout.LOROM, 0x018000).offset, 0x008000)

    def test_a_low_rom_offset_grows_by_a_page_per_bank(self):
        first = layout.resolve(layout.LOROM, 0x008000).offset
        second = layout.resolve(layout.LOROM, 0x028000).offset

        self.assertEqual(second - first, 0x010000)

    def test_a_high_rom_bank_maps_a_whole_bank(self):
        self.assertEqual(layout.resolve(layout.HIROM, 0xC10000).offset, 0x010000)

    def test_a_mirror_bank_reaches_the_same_place(self):
        self.assertEqual(
            layout.resolve(layout.LOROM, 0x808000).offset,
            layout.resolve(layout.LOROM, 0x008000).offset,
        )

    def test_a_region_that_is_not_cartridge_has_no_offset(self):
        self.assertIsNone(layout.resolve(layout.LOROM, 0x7E0000).offset)


class ReachTest(unittest.TestCase):
    def test_a_cartridge_address_is_reported_as_reachable(self):
        self.assertTrue(layout.resolve(layout.LOROM, 0x008000).is_rom)

    def test_work_ram_is_not_cartridge(self):
        self.assertFalse(layout.resolve(layout.LOROM, 0x7E0000).is_rom)

    def test_a_resolution_prints_as_its_region_and_address(self):
        printed = repr(layout.resolve(layout.LOROM, 0x008000))

        self.assertIn("rom", printed)
        self.assertIn("008000", printed)

    def test_an_address_wraps_into_the_space(self):
        self.assertEqual(
            layout.resolve(layout.LOROM, 0x1008000).address,
            layout.resolve(layout.LOROM, 0x008000).address,
        )

    def test_every_address_in_the_space_resolves_to_something(self):
        for bank in range(0, 0x100, 7):
            for page in range(0, 0x10000, 0x1000):
                found = layout.resolve(layout.LOROM, (bank << 16) | page)

                self.assertIn(found.region, layout.REGIONS)


if __name__ == "__main__":
    unittest.main()
