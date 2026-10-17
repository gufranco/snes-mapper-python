import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mapper

LOW = 0x7FC0
HIGH = 0xFFC0
FAR = 0x40FFC0
STUB = 0x200


def a_cartridge(
    at: int = LOW,
    title: str = "TEST CARTRIDGE      ",
    mapping: int = 0x20,
    chipset: int = 0x00,
    rom_size: int = 0x0A,
    ram_size: int = 0x00,
    country: int = 0x01,
    size: int = 0x80000,
) -> bytes:
    rom = bytearray(size)
    rom[at : at + 21] = title.encode("ascii")[:21].ljust(21, b" ")
    rom[at + 21] = mapping
    rom[at + 22] = chipset
    rom[at + 23] = rom_size
    rom[at + 24] = ram_size
    rom[at + 25] = country
    checksum = 0x1234
    rom[at + 28] = (checksum ^ 0xFFFF) & 0xFF
    rom[at + 29] = (checksum ^ 0xFFFF) >> 8
    rom[at + 30] = checksum & 0xFF
    rom[at + 31] = checksum >> 8
    return bytes(rom)


class LocationTest(unittest.TestCase):
    def test_the_candidate_places_are_the_ones_the_readme_gives(self) -> None:
        # Arrange
        expected = (0x7FC0, 0xFFC0, 0x200)

        # Act
        found = (mapper.LOROM_HEADER, mapper.HIROM_HEADER, mapper.COPIER_BYTES)

        # Assert
        self.assertEqual(found, expected)

    def test_a_low_rom_header_sits_where_low_rom_puts_it(self) -> None:
        # Arrange
        rom = a_cartridge()

        # Act
        found = mapper.read(rom)

        # Assert
        self.assertEqual(found.at, LOW)

    def test_a_high_rom_header_sits_where_high_rom_puts_it(self) -> None:
        # Arrange
        rom = a_cartridge(at=HIGH, mapping=0x21, size=0x100000)

        # Act
        found = mapper.read(rom)

        # Assert
        self.assertEqual(found.at, HIGH)

    def test_an_extended_header_is_found_four_megabytes_in(self) -> None:
        # Arrange
        rom = a_cartridge(at=FAR, mapping=0x35, size=0x500000)

        # Act
        found = mapper.read(rom)

        # Assert
        self.assertEqual((found.at, found.layout), (FAR, "exhirom"))

    def test_a_copier_stub_is_stepped_over(self) -> None:
        # Arrange
        rom = bytes(STUB) + a_cartridge()

        # Act
        found = mapper.read(rom)

        # Assert
        self.assertEqual((found.at, found.shift), (LOW + STUB, STUB))

    def test_a_rom_too_small_to_hold_a_header_is_refused(self) -> None:
        # Arrange
        rom = bytes(64)

        # Act
        with self.assertRaises(mapper.NoHeader) as raised:
            mapper.read(rom)

        # Assert
        self.assertEqual(str(raised.exception), "no header found in 64 bytes")

    def test_a_rom_with_no_plausible_header_is_refused(self) -> None:
        # Arrange
        rom = bytes(0x80000)

        # Act
        with self.assertRaises(mapper.NoHeader) as raised:
            mapper.read(rom)

        # Assert
        self.assertEqual(str(raised.exception), "no header found in 524288 bytes")


class FieldTest(unittest.TestCase):
    def test_the_title_comes_back_without_its_padding(self) -> None:
        # Arrange
        rom = a_cartridge()

        # Act
        found = mapper.read(rom)

        # Assert
        self.assertEqual(found.title, "TEST CARTRIDGE")

    def test_the_mapping_byte_is_kept(self) -> None:
        # Arrange
        rom = a_cartridge(mapping=0x21)

        # Act
        found = mapper.read(rom)

        # Assert
        self.assertEqual(found.mapping, 0x21)

    def test_the_chipset_byte_is_kept(self) -> None:
        # Arrange
        rom = a_cartridge(chipset=0x03)

        # Act
        found = mapper.read(rom)

        # Assert
        self.assertEqual(found.chipset, 0x03)

    def test_the_rom_size_is_read_as_a_power_of_two(self) -> None:
        # Arrange
        rom = a_cartridge(rom_size=0x0A)

        # Act
        found = mapper.read(rom)

        # Assert
        self.assertEqual(found.rom_bytes, 1024 * 1024)

    def test_a_ram_size_of_zero_means_no_save_memory(self) -> None:
        # Arrange
        rom = a_cartridge(ram_size=0x00)

        # Act
        found = mapper.read(rom)

        # Assert
        self.assertEqual(found.ram_bytes, 0)

    def test_a_ram_size_reads_as_a_power_of_two(self) -> None:
        # Arrange
        rom = a_cartridge(ram_size=0x03)

        # Act
        found = mapper.read(rom)

        # Assert
        self.assertEqual(found.ram_bytes, 8 * 1024)

    def test_the_country_byte_is_kept(self) -> None:
        # Arrange
        rom = a_cartridge(country=0x02)

        # Act
        found = mapper.read(rom)

        # Assert
        self.assertEqual(found.country, 0x02)

    def test_the_checksum_and_its_complement_are_read(self) -> None:
        # Arrange
        rom = a_cartridge()

        # Act
        found = mapper.read(rom)

        # Assert
        self.assertEqual((found.checksum, found.complement), (0x1234, 0xEDCB))

    def test_a_header_whose_checksum_pair_agrees_says_so(self) -> None:
        # Arrange
        rom = a_cartridge()

        # Act
        found = mapper.read(rom)

        # Assert
        self.assertTrue(found.checksum_agrees)

    def test_a_header_whose_pair_does_not_sum_to_ffff_says_so(self) -> None:
        # Arrange
        raw = bytes(28) + bytes([0x00, 0x00, 0x34, 0x12])

        # Act
        found = mapper.Header(LOW, raw)

        # Assert
        self.assertFalse(found.checksum_agrees)

    def test_a_header_keeps_the_bytes_it_was_built_from(self) -> None:
        # Arrange
        raw = bytearray(range(32))

        # Act
        found = mapper.Header(LOW, raw)

        # Assert
        self.assertEqual((found.at, found.raw), (LOW, bytes(range(32))))


class KindTest(unittest.TestCase):
    def test_the_low_bits_of_the_mapping_byte_name_the_layout(self) -> None:
        # Arrange
        roms = (a_cartridge(mapping=0x20), a_cartridge(at=HIGH, mapping=0x21, size=0x100000))

        # Act
        found = [mapper.read(rom).layout for rom in roms]

        # Assert
        self.assertEqual(found, ["lorom", "hirom"])

    def test_the_fast_bit_of_the_mapping_byte_is_read(self) -> None:
        # Arrange
        roms = (a_cartridge(mapping=0x20), a_cartridge(mapping=0x30))

        # Act
        found = [mapper.read(rom).fast for rom in roms]

        # Assert
        self.assertEqual(found, [False, True])

    def test_a_chipset_byte_names_whether_a_coprocessor_is_present(self) -> None:
        # Arrange
        roms = (a_cartridge(chipset=0x02), a_cartridge(chipset=0x03))

        # Act
        found = [mapper.read(rom).coprocessor for rom in roms]

        # Assert
        self.assertEqual(found, [False, True])

    def test_a_chipset_byte_names_whether_save_memory_is_present(self) -> None:
        # Arrange
        roms = (a_cartridge(chipset=0x02), a_cartridge(chipset=0x00))

        # Act
        found = [mapper.read(rom).battery for rom in roms]

        # Assert
        self.assertEqual(found, [True, False])

    def test_a_header_prints_as_its_title_and_layout(self) -> None:
        # Arrange
        found = mapper.read(a_cartridge())

        # Act
        printed = repr(found)

        # Assert
        self.assertEqual(printed, "<Header 'TEST CARTRIDGE' lorom at 0x007fc0>")


class OverflowedTitleTest(unittest.TestCase):
    def test_a_mapping_byte_in_the_declared_range_is_a_mapping_byte(self) -> None:
        # Arrange
        roms = (a_cartridge(mapping=0x20), a_cartridge(mapping=0x3A))

        # Act
        found = [mapper.read(rom).declared for rom in roms]

        # Assert
        self.assertEqual(found, [True, True])

    def test_a_byte_outside_that_range_is_not_one(self) -> None:
        # Arrange
        rom = a_cartridge(mapping=0x53)

        # Act
        found = mapper.read(rom)

        # Assert
        self.assertFalse(found.declared)

    def test_a_letter_left_by_an_overflowed_title_does_not_name_a_layout(self) -> None:
        # Arrange
        rom = a_cartridge(mapping=0x53)

        # Act
        overflowed = mapper.read(rom)

        # Assert
        self.assertEqual(overflowed.layout, "lorom")

    def test_the_place_the_header_was_found_names_it_instead(self) -> None:
        # Arrange
        rom = a_cartridge(at=HIGH, mapping=0x45, size=0x100000)

        # Act
        found = mapper.read(rom)

        # Assert
        self.assertEqual(found.layout, "hirom")

    def test_and_that_holds_past_a_copier_stub(self) -> None:
        # Arrange
        rom = bytes(STUB) + a_cartridge(at=HIGH, mapping=0x45, size=0x100000)

        # Act
        found = mapper.read(rom)

        # Assert
        self.assertEqual(found.layout, "hirom")

    def test_a_letter_is_never_read_as_the_fast_bit(self) -> None:
        # Arrange
        rom = a_cartridge(mapping=0x50)

        # Act
        found = mapper.read(rom)

        # Assert
        self.assertFalse(found.fast)

    def test_a_declared_mapping_is_still_believed_over_where_it_was_found(self) -> None:
        # Arrange
        rom = a_cartridge(at=HIGH, mapping=0x35, size=0x100000)

        # Act
        found = mapper.read(rom)

        # Assert
        self.assertEqual(found.layout, "exhirom")

    def test_a_header_at_no_known_offset_falls_back_to_the_low_layout(self) -> None:
        # Arrange
        raw = bytes(32)

        # Act
        found = mapper.Header(0x1234, raw)

        # Assert
        self.assertEqual((found.layout, found.shift), ("lorom", 0))

    def test_the_readme_example_of_an_overflowed_title_reads_as_it_says(self) -> None:
        # Arrange
        raw = b"CONTRA3 THE ALIEN WARS" + bytes(10)

        # Act
        found = mapper.Header(LOW, raw)

        # Assert
        self.assertEqual((found.mapping, found.declared, found.layout), (0x53, False, "lorom"))


class ScoreTest(unittest.TestCase):
    def test_the_better_placed_header_is_the_one_chosen(self) -> None:
        # Arrange
        rom = bytearray(a_cartridge(size=0x100000))
        rom[HIGH : HIGH + 21] = b"\xff" * 21

        # Act
        found = mapper.read(bytes(rom))

        # Assert
        self.assertEqual(found.at, LOW)

    def test_a_well_formed_header_earns_every_point(self) -> None:
        # Arrange
        rom = a_cartridge()

        # Act
        scored = mapper.score(rom, LOW)

        # Assert
        self.assertEqual(scored, 4)

    def test_a_header_of_noise_scores_nothing(self) -> None:
        # Arrange
        rom = b"\xff" * 0x10000

        # Act
        scored = mapper.score(rom, LOW)

        # Assert
        self.assertEqual(scored, 0)

    def test_a_place_too_near_the_end_for_thirty_two_bytes_scores_below_nothing(self) -> None:
        # Arrange
        rom = bytes(LOW + 31)

        # Act
        scored = mapper.score(rom, LOW)

        # Assert
        self.assertEqual(scored, -1)

    def test_each_signal_earns_its_own_point(self) -> None:
        # Arrange
        roms = (
            a_cartridge(title="\x00" * 21),
            a_cartridge(mapping=0x21),
            a_cartridge(rom_size=0x00),
        )

        # Act
        scored = [mapper.score(rom, LOW) for rom in roms]

        # Assert
        self.assertEqual(scored, [3, 3, 3])

    def test_a_checksum_of_zero_earns_no_point_even_when_its_pair_agrees(self) -> None:
        # Arrange
        rom = bytearray(a_cartridge())
        rom[LOW + 28 : LOW + 32] = bytes([0xFF, 0xFF, 0x00, 0x00])

        # Act
        scored = mapper.score(bytes(rom), LOW)

        # Assert
        self.assertEqual(scored, 3)

    def test_every_size_a_real_cartridge_declares_counts_towards_a_header(self) -> None:
        # Arrange
        band = range(8, 14)

        # Act
        scored = [mapper.score(a_cartridge(rom_size=declared), LOW) for declared in band]

        # Assert
        self.assertEqual(scored, [4] * len(band))

    def test_a_size_larger_than_any_cartridge_ever_made_does_not(self) -> None:
        # Arrange
        rom = a_cartridge(rom_size=14)

        # Act
        scored = mapper.score(rom, LOW)

        # Assert
        self.assertEqual(scored, 3)

    def test_and_neither_does_one_smaller_than_the_band(self) -> None:
        # Arrange
        rom = a_cartridge(rom_size=7)

        # Act
        scored = mapper.score(rom, LOW)

        # Assert
        self.assertEqual(scored, 3)


if __name__ == "__main__":
    unittest.main()
