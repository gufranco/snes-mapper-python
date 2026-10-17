import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mapper

BANKS = 192
IMAGE = BANKS * 0x10000
REGIONS = {"rom", "work-ram", "save-ram", "registers", "open-bus"}
SWEEP = [(bank << 16) | page for bank in range(0, 0x100, 7) for page in range(0, 0x10000, 0x1000)]
BELOW_WINDOW = [(bank << 16) | page for bank in range(0x40, 0x7E) for page in (0x0000, 0x8000)]


def offsets(addresses: list[int]) -> list[int | None]:
    return [mapper.resolve(mapper.WHOLEBANK, one, banks=BANKS).offset for one in addresses]


class WholeBankTest(unittest.TestCase):
    def test_the_upper_half_of_a_bank_sits_where_plain_low_rom_puts_it(self) -> None:
        # Arrange
        address = 0x008000

        # Act
        found = mapper.resolve(mapper.WHOLEBANK, address, banks=BANKS)

        # Assert
        self.assertEqual((found.region, found.offset), ("rom", 0x000000))

    def test_and_the_next_bank_a_half_bank_further_in(self) -> None:
        # Arrange
        address = 0x018000

        # Act
        found = mapper.resolve(mapper.WHOLEBANK, address, banks=BANKS)

        # Assert
        self.assertEqual(found.offset, 0x008000)

    def test_the_lower_half_of_a_bank_sits_a_whole_image_away(self) -> None:
        # Arrange
        address = 0x400000

        # Act
        found = mapper.resolve(mapper.WHOLEBANK, address, banks=BANKS)

        # Assert
        self.assertEqual((found.region, found.offset), ("rom", 0x800000))

    def test_the_window_banks_take_the_other_route(self) -> None:
        # Arrange
        addresses = [0xC00000, 0xC08000]

        # Act
        found = offsets(addresses)

        # Assert
        self.assertEqual(found, [0xA00000, 0x600000])

    def test_the_window_advances_one_half_bank_per_bank(self) -> None:
        # Arrange
        addresses = [(0xC0 + step) << 16 for step in range(4)]

        # Act
        found = offsets(addresses)

        # Assert
        self.assertEqual(found, [0xA00000, 0xA08000, 0xA10000, 0xA18000])

    def test_the_address_the_reference_pins_resolves_where_it_says(self) -> None:
        # Arrange
        address = 0xC04D6A

        # Act
        found = mapper.resolve(mapper.WHOLEBANK, address, banks=BANKS)

        # Assert
        self.assertEqual(found.offset, 0xA04D6A)

    def test_the_system_area_is_still_the_system_area(self) -> None:
        # Arrange
        addresses = (0x000100, 0x002100, 0x7E0000)

        # Act
        found = [mapper.resolve(mapper.WHOLEBANK, one, banks=BANKS).region for one in addresses]

        # Assert
        self.assertEqual(found, ["work-ram", "registers", "work-ram"])

    def test_a_cartridge_with_save_memory_keeps_a_window_for_it(self) -> None:
        # Arrange
        address = 0x700000

        # Act
        found = mapper.resolve(mapper.WHOLEBANK, address, banks=BANKS, save=True)

        # Assert
        self.assertEqual(found.region, "save-ram")

    def test_and_one_without_carries_cartridge_there_instead(self) -> None:
        # Arrange
        address = 0x700000

        # Act
        found = mapper.resolve(mapper.WHOLEBANK, address, banks=BANKS)

        # Assert
        self.assertEqual(found.region, "rom")

    def test_no_two_addresses_below_the_window_reach_the_same_byte(self) -> None:
        # Arrange
        addresses = BELOW_WINDOW

        # Act
        found = offsets(addresses)

        # Assert
        self.assertEqual(len(set(found)), len(addresses))

    def test_and_no_window_bank_collides_with_one_below_it(self) -> None:
        # Arrange
        below = set(offsets(BELOW_WINDOW))
        window = [(bank << 16) | page for bank in range(0xC0, 0x100) for page in (0x0000, 0x8000)]

        # Act
        found = offsets(window)

        # Assert
        self.assertEqual(below & set(found), set())

    def test_every_cartridge_byte_it_names_is_inside_the_image(self) -> None:
        # Arrange
        addresses = [(bank << 16) | page for bank in range(0x100) for page in (0, 0x8000, 0xFFFF)]

        # Act
        found = [one for one in offsets(addresses) if one is not None]

        # Assert
        self.assertEqual([one for one in found if one >= IMAGE], [])

    def test_an_image_too_small_for_the_window_is_refused(self) -> None:
        # Arrange
        banks = 64

        # Act
        with self.assertRaises(mapper.NeedsBankCount) as raised:
            mapper.resolve(mapper.WHOLEBANK, 0x400000, banks=banks)

        # Assert
        self.assertTrue(
            str(raised.exception).startswith("wholebank needs 192 banks and this image has 64.")
        )

    def test_the_refusal_says_how_many_banks_the_map_wants(self) -> None:
        # Arrange
        banks = 191

        # Act
        with self.assertRaises(mapper.NeedsBankCount) as raised:
            mapper.resolve(mapper.WHOLEBANK, 0x400000, banks=banks)

        # Assert
        self.assertIn("needs 192 banks", str(raised.exception))

    def test_the_smallest_image_it_accepts_is_the_one_the_window_fits_in(self) -> None:
        # Arrange
        banks = 192

        # Act
        found = mapper.resolve(mapper.WHOLEBANK, 0xC00000, banks=banks)

        # Assert
        self.assertEqual((found.offset, mapper.WHOLEBANK_BANKS), (0xA00000, banks))

    def test_every_window_byte_lands_inside_an_image_of_that_size(self) -> None:
        # Arrange
        pages = (0x0000, 0x7FFF, 0x8000, 0xFFFF)
        addresses = [(bank << 16) | page for bank in range(0xC0, 0x100) for page in pages]

        # Act
        found = offsets(addresses)

        # Assert
        self.assertEqual([one for one in found if one is None or one >= IMAGE], [])

    def test_resolving_it_without_a_bank_count_is_refused(self) -> None:
        # Arrange
        address = 0x008000

        # Act
        with self.assertRaises(mapper.NeedsBankCount) as raised:
            mapper.resolve(mapper.WHOLEBANK, address)

        # Assert
        self.assertIn("image.bank_count(len(rom))", str(raised.exception))

    def test_the_refusal_says_what_is_missing(self) -> None:
        # Arrange
        address = 0x008000

        # Act
        with self.assertRaises(mapper.NeedsBankCount) as raised:
            mapper.resolve(mapper.WHOLEBANK, address)

        # Assert
        self.assertIn("bank count", str(raised.exception))

    def test_every_address_in_the_space_resolves_under_this_board(self) -> None:
        # Arrange
        kind = mapper.WHOLEBANK

        # Act
        found = {mapper.resolve(kind, address, banks=BANKS, save=True).region for address in SWEEP}

        # Assert
        self.assertEqual(found, REGIONS - {"open-bus"})


if __name__ == "__main__":
    unittest.main()
