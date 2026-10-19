import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mapper

REGIONS = {"rom", "work-ram", "save-ram", "registers", "open-bus"}
COPROCESSOR_KINDS = (mapper.SA1, mapper.SPC7110)
SWEEP = [(bank << 16) | page for bank in range(0, 0x100, 7) for page in range(0, 0x10000, 0x1000)]


def offsets(kind: str, addresses: list[int]) -> list[int | None]:
    return [mapper.resolve(kind, address).offset for address in addresses]


class RegionTest(unittest.TestCase):
    def test_the_published_names_are_the_ones_the_readme_gives(self) -> None:
        # Arrange
        expected = ("rom", "work-ram", "save-ram", "registers", "open-bus", "coprocessor", 6, 8, 12)

        # Act
        found = (
            mapper.ROM,
            mapper.WORK_RAM,
            mapper.SAVE_RAM,
            mapper.REGISTERS,
            mapper.OPEN_BUS,
            mapper.COPROCESSOR,
        )

        # Assert
        self.assertEqual((*found, mapper.FAST, mapper.SLOW, mapper.XSLOW), expected)

    def test_work_ram_banks_are_named_as_work_ram(self) -> None:
        # Arrange
        addresses = (0x7E0000, 0x7F0000)

        # Act
        found = [mapper.resolve(mapper.LOROM, address).region for address in addresses]

        # Assert
        self.assertEqual(found, ["work-ram", "work-ram"])

    def test_the_bottom_of_a_low_bank_is_the_mirror_of_work_ram(self) -> None:
        # Arrange
        addresses = (0x000100, 0x3F1FFF, 0x801000)

        # Act
        found = [mapper.resolve(mapper.LOROM, address).region for address in addresses]

        # Assert
        self.assertEqual(found, ["work-ram"] * 3)

    def test_the_register_window_is_named_as_registers(self) -> None:
        # Arrange
        addresses = (0x002100, 0x004200, 0x004300, 0x00420B, 0x005FFF)

        # Act
        found = [mapper.resolve(mapper.LOROM, address).region for address in addresses]

        # Assert
        self.assertEqual(found, ["registers"] * len(addresses))

    def test_the_lower_half_of_a_low_bank_above_the_registers_is_open_bus(self) -> None:
        # Arrange
        address = 0x006000

        # Act
        found = mapper.resolve(mapper.LOROM, address)

        # Assert
        self.assertEqual((found.region, found.offset), ("open-bus", None))

    def test_the_upper_half_of_a_low_bank_is_cartridge(self) -> None:
        # Arrange
        address = 0x008000

        # Act
        found = mapper.resolve(mapper.LOROM, address)

        # Assert
        self.assertEqual(found.region, "rom")

    def test_a_high_bank_is_cartridge_throughout_in_high_rom(self) -> None:
        # Arrange
        addresses = (0xC00000, 0xC07FFF, 0xFFFFFF)

        # Act
        found = [mapper.resolve(mapper.HIROM, address).region for address in addresses]

        # Assert
        self.assertEqual(found, ["rom"] * 3)

    def test_save_memory_has_its_own_window_in_low_rom(self) -> None:
        # Arrange
        addresses = (0x700000, 0x7D7FFF, 0xF00000, 0x6F0000)

        # Act
        found = [mapper.resolve(mapper.LOROM, address).region for address in addresses]

        # Assert
        self.assertEqual(found, ["save-ram", "save-ram", "save-ram", "open-bus"])

    def test_the_high_layout_puts_save_memory_in_the_middle_of_its_low_banks(self) -> None:
        # Arrange
        addresses = (0x206000, 0x3F7FFF, 0xA06000, 0x208000, 0x106000)

        # Act
        found = [mapper.resolve(mapper.HIROM, address).region for address in addresses]

        # Assert
        self.assertEqual(found, ["save-ram", "save-ram", "save-ram", "rom", "rom"])


class SpeedTest(unittest.TestCase):
    def test_the_low_half_of_the_space_is_always_slow(self) -> None:
        # Arrange
        address = 0x008000

        # Act
        found = mapper.resolve(mapper.LOROM, address, fast=True)

        # Assert
        self.assertEqual(found.cycles, 8)

    def test_the_upper_half_runs_fast_when_the_cartridge_asks(self) -> None:
        # Arrange
        address = 0x808000

        # Act
        found = mapper.resolve(mapper.LOROM, address, fast=True)

        # Assert
        self.assertEqual(found.cycles, 6)

    def test_the_upper_half_stays_slow_when_it_does_not(self) -> None:
        # Arrange
        address = 0x808000

        # Act
        found = mapper.resolve(mapper.LOROM, address, fast=False)

        # Assert
        self.assertEqual(found.cycles, 8)

    def test_work_ram_never_runs_fast(self) -> None:
        # Arrange
        address = 0x7E0000

        # Act
        found = mapper.resolve(mapper.LOROM, address, fast=True)

        # Assert
        self.assertEqual(found.cycles, 8)

    def test_only_the_controller_ports_run_at_the_slowest_speed(self) -> None:
        # Arrange
        addresses = (0x004016, 0x0041FF, 0x004200, 0x804200, 0x805FFF)

        # Act
        found = [mapper.resolve(mapper.LOROM, one, fast=True).cycles for one in addresses]

        # Assert
        self.assertEqual(found, [12, 12, 6, 6, 6])

    def test_the_display_and_audio_registers_run_fast_in_every_bank(self) -> None:
        # Arrange
        addresses = (0x002100, 0x802100, 0x3F2140)

        # Act
        found = [mapper.resolve(mapper.LOROM, one, fast=False).cycles for one in addresses]

        # Assert
        self.assertEqual(found, [6, 6, 6])

    def test_the_expansion_pages_stay_slow_in_the_upper_banks(self) -> None:
        # Arrange
        addresses = (0x806000, 0xB07FFF, 0x006000)

        # Act
        found = [mapper.resolve(mapper.HIROM, one, fast=True).cycles for one in addresses]

        # Assert
        self.assertEqual(found, [8, 8, 8])


class OffsetTest(unittest.TestCase):
    def test_a_low_rom_bank_maps_its_upper_half_to_a_thirty_two_kilobyte_page(self) -> None:
        # Arrange
        address = 0x018000

        # Act
        found = mapper.resolve(mapper.LOROM, address)

        # Assert
        self.assertEqual(found.offset, 0x008000)

    def test_a_low_rom_offset_grows_by_a_page_per_bank(self) -> None:
        # Arrange
        addresses = [0x008000, 0x018000, 0x028000]

        # Act
        found = offsets(mapper.LOROM, addresses)

        # Assert
        self.assertEqual(found, [0x000000, 0x008000, 0x010000])

    def test_a_high_rom_bank_maps_a_whole_bank(self) -> None:
        # Arrange
        address = 0xC10000

        # Act
        found = mapper.resolve(mapper.HIROM, address)

        # Assert
        self.assertEqual(found.offset, 0x010000)

    def test_a_mirror_bank_reaches_the_same_place(self) -> None:
        # Arrange
        addresses = [0x808000, 0x008000]

        # Act
        found = offsets(mapper.LOROM, addresses)

        # Assert
        self.assertEqual(found, [0, 0])

    def test_a_region_that_is_not_cartridge_has_no_offset(self) -> None:
        # Arrange
        address = 0x7E0000

        # Act
        found = mapper.resolve(mapper.LOROM, address)

        # Assert
        self.assertIsNone(found.offset)

    def test_a_name_that_is_no_layout_reads_cartridge_the_way_the_high_one_does(self) -> None:
        # Arrange
        addresses = [0xC10000, 0x206000]

        # Act
        found = [mapper.resolve("superfx", one) for one in addresses]

        # Assert
        self.assertEqual(
            [(one.region, one.offset) for one in found], [("rom", 0x10000), ("rom", 0x206000)]
        )


class ReachTest(unittest.TestCase):
    def test_a_cartridge_address_is_reported_as_reachable(self) -> None:
        # Arrange
        address = 0x008000

        # Act
        found = mapper.resolve(mapper.LOROM, address)

        # Assert
        self.assertTrue(found.is_rom)

    def test_work_ram_is_not_cartridge(self) -> None:
        # Arrange
        address = 0x7E0000

        # Act
        found = mapper.resolve(mapper.LOROM, address)

        # Assert
        self.assertFalse(found.is_rom)

    def test_a_resolution_prints_as_its_region_and_address(self) -> None:
        # Arrange
        found = mapper.resolve(mapper.LOROM, 0x008000)

        # Act
        printed = repr(found)

        # Assert
        self.assertEqual(printed, "<rom at 008000, 8 clocks>")

    def test_an_address_wraps_into_the_space(self) -> None:
        # Arrange
        address = 0x1008000

        # Act
        found = mapper.resolve(mapper.LOROM, address)

        # Assert
        self.assertEqual((found.address, found.offset), (0x008000, 0))

    def test_every_address_in_the_space_resolves_to_something(self) -> None:
        # Arrange
        kinds = (mapper.LOROM, mapper.HIROM)

        # Act
        found = {mapper.resolve(kind, address).region for kind in kinds for address in SWEEP}

        # Assert
        self.assertEqual(found, REGIONS)


class CoprocessorLayoutTest(unittest.TestCase):
    def test_every_address_resolves_under_the_two_coprocessor_layouts(self) -> None:
        # Arrange
        kinds = COPROCESSOR_KINDS

        # Act
        found = {mapper.resolve(kind, address).region for kind in kinds for address in SWEEP}

        # Assert
        self.assertEqual(found, REGIONS | {"coprocessor"})

    def test_the_console_still_decides_what_an_access_costs(self) -> None:
        # Arrange
        addresses = (0x002200, 0x003000, 0x004016, 0x004800, 0x006000, 0x808000, 0xC00000)

        # Act
        found = [
            [mapper.resolve(kind, one, fast=True).cycles for one in addresses]
            for kind in COPROCESSOR_KINDS
        ]

        # Assert
        self.assertEqual(found, [[6, 6, 12, 6, 8, 6, 6]] * 2)

    def test_an_sa1_bank_below_the_window_is_not_the_low_layout_s(self) -> None:
        # Arrange
        addresses = [0x808000, 0x208000]

        # Act
        found = offsets(mapper.SA1, addresses) + offsets(mapper.LOROM, addresses)

        # Assert
        self.assertEqual(found, [0x200000, 0x100000, 0x000000, 0x100000])


class ExtendedHighTest(unittest.TestCase):
    def test_a_low_bank_reaches_the_far_half_of_the_image(self) -> None:
        # Arrange
        address = 0x00FFC0

        # Act
        found = mapper.resolve(mapper.EXHIROM, address)

        # Assert
        self.assertEqual(found.offset, 0x40FFC0)

    def test_a_high_bank_reaches_the_near_half(self) -> None:
        # Arrange
        address = 0xC0FFC0

        # Act
        found = mapper.resolve(mapper.EXHIROM, address)

        # Assert
        self.assertEqual(found.offset, 0x00FFC0)

    def test_the_far_half_runs_to_the_top_of_the_low_banks(self) -> None:
        # Arrange
        address = 0x7DFFFF

        # Act
        found = mapper.resolve(mapper.EXHIROM, address)

        # Assert
        self.assertEqual(found.offset, 0x7DFFFF)

    def test_the_near_half_runs_to_the_top_of_the_space(self) -> None:
        # Arrange
        address = 0xFFFFFF

        # Act
        found = mapper.resolve(mapper.EXHIROM, address)

        # Assert
        self.assertEqual(found.offset, 0x3FFFFF)

    def test_the_plain_high_layout_never_reaches_past_four_megabytes(self) -> None:
        # Arrange
        addresses = [0x00FFC0, 0x7DFFFF, 0xC0FFC0, 0xFFFFFF]

        # Act
        found = offsets(mapper.HIROM, addresses)

        # Assert
        self.assertEqual(found, [0x00FFC0, 0x3DFFFF, 0x00FFC0, 0x3FFFFF])

    def test_the_two_layouts_disagree_wherever_the_extended_one_is_the_point(self) -> None:
        # Arrange
        addresses = [0x00FFC0]

        # Act
        found = offsets(mapper.HIROM, addresses) + offsets(mapper.EXHIROM, addresses)

        # Assert
        self.assertEqual(found, [0x00FFC0, 0x40FFC0])

    def test_a_mirrored_low_bank_reaches_the_far_half_as_well(self) -> None:
        # Arrange
        address = 0x30FFC0

        # Act
        found = mapper.resolve(mapper.EXHIROM, address)

        # Assert
        self.assertEqual(found.offset, 0x70FFC0)

    def test_the_extended_layout_keeps_the_save_window_the_high_one_has(self) -> None:
        # Arrange
        address = 0x206000

        # Act
        found = mapper.resolve(mapper.EXHIROM, address)

        # Assert
        self.assertEqual(found.region, "save-ram")

    def test_work_ram_is_still_decided_before_any_cartridge_half(self) -> None:
        # Arrange
        address = 0x7E0000

        # Act
        found = mapper.resolve(mapper.EXHIROM, address)

        # Assert
        self.assertEqual(found.region, "work-ram")

    def test_every_address_in_the_space_resolves_under_the_extended_layout(self) -> None:
        # Arrange
        kind = mapper.EXHIROM

        # Act
        found = {mapper.resolve(kind, address).region for address in SWEEP}

        # Assert
        self.assertEqual(found, REGIONS - {"open-bus"})

    def test_no_cartridge_offset_it_produces_falls_outside_the_largest_image(self) -> None:
        # Arrange
        addresses = [(bank << 16) | 0xFFFF for bank in range(0x100)]

        # Act
        found = [one for one in offsets(mapper.EXHIROM, addresses) if one is not None]

        # Assert
        self.assertEqual((max(found), [one for one in found if one >= 0x800000]), (0x7FFFFF, []))


if __name__ == "__main__":
    unittest.main()
