import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapper import header


def a_cartridge(
    at=header.LOROM_HEADER,
    title="TEST CARTRIDGE      ",
    mapping=0x20,
    chipset=0x00,
    rom_size=0x0A,
    ram_size=0x00,
    country=0x01,
    size=0x80000,
):
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
    def test_a_low_rom_header_sits_where_low_rom_puts_it(self):
        self.assertEqual(header.read(a_cartridge()).at, header.LOROM_HEADER)

    def test_a_high_rom_header_sits_where_high_rom_puts_it(self):
        rom = a_cartridge(at=header.HIROM_HEADER, mapping=0x21, size=0x100000)

        self.assertEqual(header.read(rom).at, header.HIROM_HEADER)

    def test_a_copier_stub_is_stepped_over(self):
        rom = b"\x00" * header.COPIER_BYTES + a_cartridge()

        self.assertEqual(header.read(rom).at, header.LOROM_HEADER + header.COPIER_BYTES)

    def test_a_rom_too_small_to_hold_a_header_is_refused(self):
        with self.assertRaises(header.NoHeader):
            header.read(b"\x00" * 64)

    def test_a_rom_with_no_plausible_header_is_refused(self):
        with self.assertRaises(header.NoHeader):
            header.read(bytes(0x80000))


class FieldTest(unittest.TestCase):
    def test_the_title_comes_back_without_its_padding(self):
        self.assertEqual(header.read(a_cartridge()).title, "TEST CARTRIDGE")

    def test_the_mapping_byte_is_kept(self):
        self.assertEqual(header.read(a_cartridge(mapping=0x21)).mapping, 0x21)

    def test_the_chipset_byte_is_kept(self):
        self.assertEqual(header.read(a_cartridge(chipset=0x03)).chipset, 0x03)

    def test_the_rom_size_is_read_as_a_power_of_two(self):
        self.assertEqual(header.read(a_cartridge(rom_size=0x0A)).rom_bytes, 1024 * 1024)

    def test_a_ram_size_of_zero_means_no_save_memory(self):
        self.assertEqual(header.read(a_cartridge(ram_size=0x00)).ram_bytes, 0)

    def test_a_ram_size_reads_as_a_power_of_two(self):
        self.assertEqual(header.read(a_cartridge(ram_size=0x03)).ram_bytes, 8 * 1024)

    def test_the_country_byte_is_kept(self):
        self.assertEqual(header.read(a_cartridge(country=0x02)).country, 0x02)

    def test_the_checksum_and_its_complement_are_read(self):
        found = header.read(a_cartridge())

        self.assertEqual(found.checksum, 0x1234)
        self.assertEqual(found.complement, 0x1234 ^ 0xFFFF)

    def test_a_header_whose_checksum_pair_agrees_says_so(self):
        self.assertTrue(header.read(a_cartridge()).checksum_agrees)


class KindTest(unittest.TestCase):
    def test_the_low_bits_of_the_mapping_byte_name_the_layout(self):
        self.assertEqual(header.read(a_cartridge(mapping=0x20)).layout, header.LOROM)
        self.assertEqual(
            header.read(a_cartridge(at=header.HIROM_HEADER, mapping=0x21, size=0x100000)).layout,
            header.HIROM,
        )

    def test_the_fast_bit_of_the_mapping_byte_is_read(self):
        self.assertFalse(header.read(a_cartridge(mapping=0x20)).fast)
        self.assertTrue(header.read(a_cartridge(mapping=0x30)).fast)

    def test_a_chipset_byte_names_whether_a_coprocessor_is_present(self):
        self.assertFalse(header.read(a_cartridge(chipset=0x02)).coprocessor)
        self.assertTrue(header.read(a_cartridge(chipset=0x03)).coprocessor)

    def test_a_chipset_byte_names_whether_save_memory_is_present(self):
        self.assertTrue(header.read(a_cartridge(chipset=0x02)).battery)
        self.assertFalse(header.read(a_cartridge(chipset=0x00)).battery)

    def test_a_header_prints_as_its_title_and_layout(self):
        printed = repr(header.read(a_cartridge()))

        self.assertIn("TEST CARTRIDGE", printed)
        self.assertIn("lorom", printed)


class ScoreTest(unittest.TestCase):
    def test_the_better_placed_header_is_the_one_chosen(self):
        rom = bytearray(a_cartridge(size=0x100000))
        rom[header.HIROM_HEADER : header.HIROM_HEADER + 21] = b"\xff" * 21

        self.assertEqual(header.read(bytes(rom)).at, header.LOROM_HEADER)

    def test_a_readable_title_counts_towards_a_header(self):
        self.assertGreater(header.score(a_cartridge(), header.LOROM_HEADER), 0)

    def test_a_header_of_noise_scores_nothing(self):
        self.assertLessEqual(header.score(b"\xff" * 0x10000, header.LOROM_HEADER), 0)


if __name__ == "__main__":
    unittest.main()
