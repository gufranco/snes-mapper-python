import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapper import header


def a_cartridge(
    at: int = header.LOROM_HEADER,
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
    def test_a_low_rom_header_sits_where_low_rom_puts_it(self) -> None:
        self.assertEqual(header.read(a_cartridge()).at, header.LOROM_HEADER)

    def test_a_high_rom_header_sits_where_high_rom_puts_it(self) -> None:
        rom = a_cartridge(at=header.HIROM_HEADER, mapping=0x21, size=0x100000)

        self.assertEqual(header.read(rom).at, header.HIROM_HEADER)

    def test_a_copier_stub_is_stepped_over(self) -> None:
        rom = b"\x00" * header.COPIER_BYTES + a_cartridge()

        self.assertEqual(header.read(rom).at, header.LOROM_HEADER + header.COPIER_BYTES)

    def test_a_rom_too_small_to_hold_a_header_is_refused(self) -> None:
        with self.assertRaises(header.NoHeader):
            header.read(b"\x00" * 64)

    def test_a_rom_with_no_plausible_header_is_refused(self) -> None:
        with self.assertRaises(header.NoHeader):
            header.read(bytes(0x80000))


class FieldTest(unittest.TestCase):
    def test_the_title_comes_back_without_its_padding(self) -> None:
        self.assertEqual(header.read(a_cartridge()).title, "TEST CARTRIDGE")

    def test_the_mapping_byte_is_kept(self) -> None:
        self.assertEqual(header.read(a_cartridge(mapping=0x21)).mapping, 0x21)

    def test_the_chipset_byte_is_kept(self) -> None:
        self.assertEqual(header.read(a_cartridge(chipset=0x03)).chipset, 0x03)

    def test_the_rom_size_is_read_as_a_power_of_two(self) -> None:
        self.assertEqual(header.read(a_cartridge(rom_size=0x0A)).rom_bytes, 1024 * 1024)

    def test_a_ram_size_of_zero_means_no_save_memory(self) -> None:
        self.assertEqual(header.read(a_cartridge(ram_size=0x00)).ram_bytes, 0)

    def test_a_ram_size_reads_as_a_power_of_two(self) -> None:
        self.assertEqual(header.read(a_cartridge(ram_size=0x03)).ram_bytes, 8 * 1024)

    def test_the_country_byte_is_kept(self) -> None:
        self.assertEqual(header.read(a_cartridge(country=0x02)).country, 0x02)

    def test_the_checksum_and_its_complement_are_read(self) -> None:
        found = header.read(a_cartridge())

        self.assertEqual(found.checksum, 0x1234)
        self.assertEqual(found.complement, 0x1234 ^ 0xFFFF)

    def test_a_header_whose_checksum_pair_agrees_says_so(self) -> None:
        self.assertTrue(header.read(a_cartridge()).checksum_agrees)


class KindTest(unittest.TestCase):
    def test_the_low_bits_of_the_mapping_byte_name_the_layout(self) -> None:
        self.assertEqual(header.read(a_cartridge(mapping=0x20)).layout, header.LOROM)
        self.assertEqual(
            header.read(a_cartridge(at=header.HIROM_HEADER, mapping=0x21, size=0x100000)).layout,
            header.HIROM,
        )

    def test_the_fast_bit_of_the_mapping_byte_is_read(self) -> None:
        self.assertFalse(header.read(a_cartridge(mapping=0x20)).fast)
        self.assertTrue(header.read(a_cartridge(mapping=0x30)).fast)

    def test_a_chipset_byte_names_whether_a_coprocessor_is_present(self) -> None:
        self.assertFalse(header.read(a_cartridge(chipset=0x02)).coprocessor)
        self.assertTrue(header.read(a_cartridge(chipset=0x03)).coprocessor)

    def test_a_chipset_byte_names_whether_save_memory_is_present(self) -> None:
        self.assertTrue(header.read(a_cartridge(chipset=0x02)).battery)
        self.assertFalse(header.read(a_cartridge(chipset=0x00)).battery)

    def test_a_header_prints_as_its_title_and_layout(self) -> None:
        printed = repr(header.read(a_cartridge()))

        self.assertIn("TEST CARTRIDGE", printed)
        self.assertIn("lorom", printed)


class WholeBankTest(unittest.TestCase):
    """A header alone cannot say which of two low maps a cartridge uses.

    Both declare the same byte, because the wider map is what the narrower one grew
    into and nobody changed the field. Length is what separates them, and the wider
    map has exactly one length.
    """

    def test_an_ordinary_low_cartridge_stays_on_the_low_map(self) -> None:
        found = header.read(a_cartridge(mapping=0x20))

        self.assertEqual(header.board(found, 0x100000), header.LOROM)

    def test_a_cartridge_of_the_one_length_that_map_has_is_on_it(self) -> None:
        found = header.read(a_cartridge(mapping=0x30))

        self.assertEqual(header.board(found, header.WHOLEBANK_BYTES), header.WHOLEBANK)

    def test_a_cartridge_past_the_low_map_but_short_of_that_length_is_not(self) -> None:
        found = header.read(a_cartridge(mapping=0x32, chipset=0x45))

        self.assertEqual(header.board(found, 0x600000), header.LOROM)

    def test_a_cartridge_exactly_at_the_low_map_reach_stays_on_it(self) -> None:
        found = header.read(a_cartridge(mapping=0x30))

        self.assertEqual(header.board(found, header.LOROM_REACH), header.LOROM)

    def test_the_chipset_byte_is_never_consulted(self) -> None:
        for chipset in (0x00, 0x02, 0x43, 0x45):
            found = header.read(a_cartridge(mapping=0x32, chipset=chipset))

            self.assertEqual(header.board(found, header.WHOLEBANK_BYTES), header.WHOLEBANK)
            self.assertEqual(header.board(found, 0x400000), header.LOROM)

    def test_an_expansion_still_claiming_a_part_it_no_longer_has_reads_the_same(self) -> None:
        stale = header.read(a_cartridge(mapping=0x32, chipset=0x45))
        corrected = header.read(a_cartridge(mapping=0x32, chipset=0x00))

        self.assertEqual(header.board(stale, header.WHOLEBANK_BYTES), header.WHOLEBANK)
        self.assertEqual(header.board(corrected, header.WHOLEBANK_BYTES), header.WHOLEBANK)

    def test_a_high_cartridge_is_left_where_its_header_put_it(self) -> None:
        found = header.read(a_cartridge(at=header.HIROM_HEADER, mapping=0x21, size=0x200000))

        self.assertEqual(header.board(found, 0x200000), header.HIROM)

    def test_and_so_is_an_extended_one_at_that_very_length(self) -> None:
        found = header.read(a_cartridge(at=header.HIROM_HEADER, mapping=0x35, size=0x200000))

        self.assertEqual(header.board(found, header.WHOLEBANK_BYTES), header.EXHIROM)

    def test_a_declared_coprocessor_layout_is_left_alone_too(self) -> None:
        found = header.read(a_cartridge(mapping=0x23))

        self.assertEqual(header.board(found, header.WHOLEBANK_BYTES), header.SA1)


class OverflowedTitleTest(unittest.TestCase):
    """A title of twenty two characters writes its last one over the mapping byte.

    Real retail cartridges do this, and the byte that lands there is a letter
    rather than a mapping. Every value below is one a cartridge in the measured
    library actually carries.
    """

    def test_a_mapping_byte_in_the_declared_range_is_a_mapping_byte(self) -> None:
        self.assertTrue(header.read(a_cartridge(mapping=0x20)).declared)
        self.assertTrue(header.read(a_cartridge(mapping=0x3A)).declared)

    def test_a_byte_outside_that_range_is_not_one(self) -> None:
        self.assertFalse(header.read(a_cartridge(mapping=0x53)).declared)

    def test_a_letter_left_by_an_overflowed_title_does_not_name_a_layout(self) -> None:
        overflowed = header.read(a_cartridge(mapping=0x53))

        self.assertEqual(overflowed.layout, header.LOROM)

    def test_the_place_the_header_was_found_names_it_instead(self) -> None:
        rom = a_cartridge(at=header.HIROM_HEADER, mapping=0x45, size=0x100000)

        self.assertEqual(header.read(rom).layout, header.HIROM)

    def test_and_that_holds_past_a_copier_stub(self) -> None:
        rom = b"\x00" * header.COPIER_BYTES + a_cartridge(mapping=0x53)

        self.assertEqual(header.read(rom).layout, header.LOROM)

    def test_a_letter_is_never_read_as_the_fast_bit(self) -> None:
        self.assertFalse(header.read(a_cartridge(mapping=0x50)).fast)

    def test_a_declared_mapping_is_still_believed_over_where_it_was_found(self) -> None:
        rom = a_cartridge(at=header.HIROM_HEADER, mapping=0x35, size=0x100000)

        self.assertEqual(header.read(rom).layout, header.EXHIROM)

    def test_a_header_at_no_known_offset_falls_back_to_the_low_layout(self) -> None:
        self.assertEqual(header.Header(0x1234, bytes(32)).layout, header.LOROM)


class ScoreTest(unittest.TestCase):
    def test_the_better_placed_header_is_the_one_chosen(self) -> None:
        rom = bytearray(a_cartridge(size=0x100000))
        rom[header.HIROM_HEADER : header.HIROM_HEADER + 21] = b"\xff" * 21

        self.assertEqual(header.read(bytes(rom)).at, header.LOROM_HEADER)

    def test_a_readable_title_counts_towards_a_header(self) -> None:
        self.assertGreater(header.score(a_cartridge(), header.LOROM_HEADER), 0)

    def test_a_header_of_noise_scores_nothing(self) -> None:
        self.assertLessEqual(header.score(b"\xff" * 0x10000, header.LOROM_HEADER), 0)

    def test_every_size_a_real_cartridge_declares_counts_towards_a_header(self) -> None:
        for declared in range(header.SMALLEST_PLAUSIBLE_SIZE, header.LARGEST_PLAUSIBLE_SIZE + 1):
            scored = header.score(a_cartridge(rom_size=declared), header.LOROM_HEADER)

            self.assertGreaterEqual(scored, 3, declared)

    def test_a_size_larger_than_any_cartridge_ever_made_does_not(self) -> None:
        larger = header.LARGEST_PLAUSIBLE_SIZE + 1
        inside = header.score(
            a_cartridge(rom_size=header.LARGEST_PLAUSIBLE_SIZE), header.LOROM_HEADER
        )

        self.assertEqual(
            header.score(a_cartridge(rom_size=larger), header.LOROM_HEADER), inside - 1
        )

    def test_and_neither_does_one_smaller_than_the_band(self) -> None:
        smaller = header.SMALLEST_PLAUSIBLE_SIZE - 1
        inside = header.score(
            a_cartridge(rom_size=header.SMALLEST_PLAUSIBLE_SIZE), header.LOROM_HEADER
        )

        self.assertEqual(
            header.score(a_cartridge(rom_size=smaller), header.LOROM_HEADER), inside - 1
        )


class CopierStubTest(unittest.TestCase):
    def test_a_whole_number_of_half_banks_carries_no_stub(self) -> None:
        self.assertFalse(header.has_copier_stub(bytes(0x20000)))

    def test_the_same_length_plus_the_stub_does(self) -> None:
        self.assertTrue(header.has_copier_stub(bytes(0x20000 + header.COPIER_BYTES)))

    def test_a_file_no_longer_than_the_stub_cannot_be_one(self) -> None:
        self.assertFalse(header.has_copier_stub(bytes(header.COPIER_BYTES)))

    def test_a_length_of_no_recognised_shape_is_left_alone(self) -> None:
        self.assertFalse(header.has_copier_stub(bytes(1234)))

    def test_the_length_form_answers_the_same_question(self) -> None:
        for size in (0, 0x200, 0x8000, 0x8200, 0x20000, 0x20200, 1234):
            self.assertEqual(header.stub_by_length(size), header.has_copier_stub(bytes(size)), size)


if __name__ == "__main__":
    unittest.main()
