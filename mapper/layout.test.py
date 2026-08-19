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


class ExtendedHighTest(unittest.TestCase):
    """The extended layout reaches past four megabytes; the plain high one cannot.

    Its two halves are swapped relative to where a reader expects them. The banks
    the console boots from carry the second half of the image, which is the whole
    reason an extended cartridge keeps its header at 0x40FFC0.
    """

    def test_a_low_bank_reaches_the_far_half_of_the_image(self):
        found = layout.resolve(layout.EXHIROM, 0x00FFC0)

        self.assertEqual(found.offset, 0x40FFC0)

    def test_a_high_bank_reaches_the_near_half(self):
        found = layout.resolve(layout.EXHIROM, 0xC0FFC0)

        self.assertEqual(found.offset, 0x00FFC0)

    def test_the_far_half_runs_to_the_top_of_the_low_banks(self):
        found = layout.resolve(layout.EXHIROM, 0x7DFFFF)

        self.assertEqual(found.offset, 0x7DFFFF)

    def test_the_near_half_runs_to_the_top_of_the_space(self):
        found = layout.resolve(layout.EXHIROM, 0xFFFFFF)

        self.assertEqual(found.offset, 0x3FFFFF)

    def test_the_plain_high_layout_never_reaches_past_four_megabytes(self):
        for address in (0x00FFC0, 0x7DFFFF, 0xC0FFC0, 0xFFFFFF):
            self.assertLess(layout.resolve(layout.HIROM, address).offset, 0x400000)

    def test_the_two_layouts_disagree_wherever_the_extended_one_is_the_point(self):
        plain = layout.resolve(layout.HIROM, 0x00FFC0).offset
        extended = layout.resolve(layout.EXHIROM, 0x00FFC0).offset

        self.assertNotEqual(plain, extended)

    def test_a_mirrored_low_bank_reaches_the_far_half_as_well(self):
        found = layout.resolve(layout.EXHIROM, 0x30FFC0)

        self.assertEqual(found.offset, 0x70FFC0)

    def test_the_extended_layout_keeps_the_save_window_the_high_one_has(self):
        found = layout.resolve(layout.EXHIROM, 0x206000)

        self.assertEqual(found.region, layout.SAVE_RAM)

    def test_work_ram_is_still_decided_before_any_cartridge_half(self):
        found = layout.resolve(layout.EXHIROM, 0x7E0000)

        self.assertEqual(found.region, layout.WORK_RAM)

    def test_every_address_in_the_space_resolves_under_the_extended_layout(self):
        for bank in range(0, 0x100, 7):
            for page in range(0, 0x10000, 0x1000):
                found = layout.resolve(layout.EXHIROM, (bank << 16) | page)

                self.assertIn(found.region, layout.REGIONS)

    def test_no_cartridge_offset_it_produces_falls_outside_the_largest_image(self):
        for bank in range(0, 0x100):
            found = layout.resolve(layout.EXHIROM, (bank << 16) | 0xFFFF)

            if found.is_rom:
                self.assertLess(found.offset, layout.EXHIROM_BYTES)


class WholeBankTest(unittest.TestCase):
    """The map that gives every bank below the window a whole sixty four kilobytes.

    Named for its shape, not for a chip. The S-DD1 boards were where it was first
    measured, and a cartridge that had its coprocessor removed lands here too,
    declaring no chipset at all. Every offset asserted below is one a reference
    implementation asserts, and that reference was validated against a cartridge
    that boots on hardware.
    """

    BANKS = 192

    def test_the_upper_half_of_a_bank_sits_where_plain_low_rom_puts_it(self):
        found = layout.resolve(layout.WHOLEBANK, 0x008000, banks=self.BANKS)

        self.assertEqual((found.region, found.offset), (layout.ROM, 0x000000))

    def test_and_the_next_bank_a_half_bank_further_in(self):
        found = layout.resolve(layout.WHOLEBANK, 0x018000, banks=self.BANKS)

        self.assertEqual(found.offset, 0x008000)

    def test_the_lower_half_of_a_bank_sits_a_whole_image_away(self):
        found = layout.resolve(layout.WHOLEBANK, 0x400000, banks=self.BANKS)

        self.assertEqual((found.region, found.offset), (layout.ROM, 0x800000))

    def test_the_window_banks_take_the_other_route(self):
        low = layout.resolve(layout.WHOLEBANK, 0xC00000, banks=self.BANKS)
        high = layout.resolve(layout.WHOLEBANK, 0xC08000, banks=self.BANKS)

        self.assertEqual(low.offset, 0xA00000)
        self.assertEqual(high.offset, 0x600000)

    def test_the_window_advances_one_half_bank_per_bank(self):
        for step in range(4):
            found = layout.resolve(layout.WHOLEBANK, ((0xC0 + step) << 16), banks=self.BANKS)

            self.assertEqual(found.offset, 0xA00000 + step * 0x8000)

    def test_the_address_the_reference_pins_resolves_where_it_says(self):
        found = layout.resolve(layout.WHOLEBANK, 0xC04D6A, banks=self.BANKS)

        self.assertEqual(found.offset, 0xA04D6A)

    def test_the_system_area_is_still_the_system_area(self):
        self.assertEqual(
            layout.resolve(layout.WHOLEBANK, 0x000100, banks=self.BANKS).region, layout.WORK_RAM
        )
        self.assertEqual(
            layout.resolve(layout.WHOLEBANK, 0x002100, banks=self.BANKS).region, layout.REGISTERS
        )
        self.assertEqual(
            layout.resolve(layout.WHOLEBANK, 0x7E0000, banks=self.BANKS).region, layout.WORK_RAM
        )

    def test_a_cartridge_with_save_memory_keeps_a_window_for_it(self):
        found = layout.resolve(layout.WHOLEBANK, 0x700000, banks=self.BANKS, save=True)

        self.assertEqual(found.region, layout.SAVE_RAM)

    def test_and_one_without_carries_cartridge_there_instead(self):
        found = layout.resolve(layout.WHOLEBANK, 0x700000, banks=self.BANKS)

        self.assertEqual(found.region, layout.ROM)

    def test_no_two_addresses_below_the_window_reach_the_same_byte(self):
        seen = set()
        for bank in range(0x40, 0x7E):
            for page in (0x0000, 0x8000):
                found = layout.resolve(layout.WHOLEBANK, (bank << 16) | page, banks=self.BANKS)
                self.assertNotIn(found.offset, seen)
                seen.add(found.offset)

    def test_and_no_window_bank_collides_with_one_below_it(self):
        below = {
            layout.resolve(layout.WHOLEBANK, (bank << 16) | page, banks=self.BANKS).offset
            for bank in range(0x40, 0x7E)
            for page in (0x0000, 0x8000)
        }

        for bank in range(0xC0, 0x100):
            for page in (0x0000, 0x8000):
                found = layout.resolve(layout.WHOLEBANK, (bank << 16) | page, banks=self.BANKS)

                self.assertNotIn(found.offset, below)

    def test_every_cartridge_byte_it_names_is_inside_the_image(self):
        size = self.BANKS * layout.BANK_BYTES
        for bank in range(0x100):
            for page in (0x0000, 0x8000, 0xFFFF):
                found = layout.resolve(layout.WHOLEBANK, (bank << 16) | page, banks=self.BANKS)

                if found.is_rom:
                    self.assertLess(found.offset, size, hex((bank << 16) | page))

    def test_an_image_too_small_for_the_window_is_refused(self):
        with self.assertRaises(layout.NeedsBankCount) as raised:
            layout.resolve(layout.WHOLEBANK, 0x400000, banks=64)

        self.assertIn("64", str(raised.exception))

    def test_the_refusal_says_how_many_banks_the_map_wants(self):
        with self.assertRaises(layout.NeedsBankCount) as raised:
            layout.resolve(layout.WHOLEBANK, 0x400000, banks=191)

        self.assertIn(str(layout.WHOLEBANK_BANKS), str(raised.exception))

    def test_the_smallest_image_it_accepts_is_the_one_the_window_fits_in(self):
        found = layout.resolve(layout.WHOLEBANK, 0xC00000, banks=layout.WHOLEBANK_BANKS)

        self.assertEqual(found.offset, 0xA00000)

    def test_every_window_byte_lands_inside_an_image_of_that_size(self):
        size = layout.WHOLEBANK_BANKS * layout.BANK_BYTES
        for bank in range(0xC0, 0x100):
            for page in (0x0000, 0x7FFF, 0x8000, 0xFFFF):
                found = layout.resolve(
                    layout.WHOLEBANK, (bank << 16) | page, banks=layout.WHOLEBANK_BANKS
                )

                self.assertLess(found.offset, size, hex((bank << 16) | page))

    def test_resolving_it_without_a_bank_count_is_refused(self):
        with self.assertRaises(layout.NeedsBankCount):
            layout.resolve(layout.WHOLEBANK, 0x008000)

    def test_the_refusal_says_what_is_missing(self):
        with self.assertRaises(layout.NeedsBankCount) as raised:
            layout.resolve(layout.WHOLEBANK, 0x008000)

        self.assertIn("bank count", str(raised.exception))

    def test_every_address_in_the_space_resolves_under_this_board(self):
        for bank in range(0, 0x100, 7):
            for page in range(0, 0x10000, 0x1000):
                found = layout.resolve(layout.WHOLEBANK, (bank << 16) | page, banks=self.BANKS)

                self.assertIn(found.region, layout.REGIONS)


if __name__ == "__main__":
    unittest.main()
