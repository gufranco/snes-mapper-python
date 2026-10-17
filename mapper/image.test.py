import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mapper

BANK = 0x10000
HALF = 0x8000
WINDOW = 0xC0


def a_logical(banks: int) -> bytes:
    blob = bytearray(banks * BANK)
    for bank in range(banks):
        blob[bank * BANK] = 0xA0 | bank
        blob[bank * BANK + HALF] = 0xB0 | bank
    return bytes(blob)


class BankCountTest(unittest.TestCase):
    def test_a_whole_number_of_banks_is_counted(self) -> None:
        # Arrange
        size = 4 * BANK

        # Act
        found = mapper.bank_count(size)

        # Assert
        self.assertEqual(found, 4)

    def test_a_size_that_is_not_whole_banks_is_refused(self) -> None:
        # Arrange
        size = BANK + 1

        # Act
        with self.assertRaises(mapper.NotWholeBanks) as raised:
            mapper.bank_count(size)

        # Assert
        self.assertEqual(str(raised.exception), "65537 is not a whole number of 65536 byte banks")

    def test_the_refusal_names_the_size(self) -> None:
        # Arrange
        size = 0x1234

        # Act
        with self.assertRaises(mapper.NotWholeBanks) as raised:
            mapper.bank_count(size)

        # Assert
        self.assertIn("4660", str(raised.exception))

    def test_an_empty_image_holds_no_banks(self) -> None:
        # Arrange
        size = 0

        # Act
        found = mapper.bank_count(size)

        # Assert
        self.assertEqual(found, 0)

    def test_the_published_sizes_are_the_ones_the_readme_gives(self) -> None:
        # Arrange
        expected = (0x10000, 0x8000, 0xC0)

        # Act
        found = (mapper.BANK, mapper.HALF, mapper.WINDOW_FIRST_BANK)

        # Assert
        self.assertEqual(found, expected)


class InterleaveTest(unittest.TestCase):
    def test_interleaving_keeps_the_size(self) -> None:
        # Arrange
        logical = a_logical(4)

        # Act
        built = mapper.interleave(logical)

        # Assert
        self.assertEqual(len(built), len(logical))

    def test_interleaving_then_undoing_it_gives_the_original_back(self) -> None:
        # Arrange
        logicals = [a_logical(banks) for banks in (1, 2, 4, 8, 16)]

        # Act
        found = [mapper.deinterleave(mapper.interleave(one)) for one in logicals]

        # Assert
        self.assertEqual(found, logicals)

    def test_undoing_then_interleaving_gives_the_original_back(self) -> None:
        # Arrange
        swapped = [a_logical(banks) for banks in (1, 2, 4, 8)]

        # Act
        found = [mapper.interleave(mapper.deinterleave(one)) for one in swapped]

        # Assert
        self.assertEqual(found, swapped)

    def test_the_upper_half_of_a_bank_moves_to_the_front(self) -> None:
        # Arrange
        logical = a_logical(2)

        # Act
        swapped = mapper.interleave(logical)

        # Assert
        self.assertEqual((swapped[0], swapped[HALF]), (0xB0, 0xB1))

    def test_the_lower_half_of_a_bank_moves_behind_every_upper_half(self) -> None:
        # Arrange
        logical = a_logical(2)

        # Act
        swapped = mapper.interleave(logical)

        # Assert
        self.assertEqual((swapped[2 * HALF], swapped[3 * HALF]), (0xA0, 0xA1))

    def test_an_image_that_is_not_whole_banks_is_refused(self) -> None:
        # Arrange
        logical = bytes(BANK + 3)

        # Act
        with self.assertRaises(mapper.NotWholeBanks) as raised:
            mapper.interleave(logical)

        # Assert
        self.assertIn("65539", str(raised.exception))

    def test_and_so_is_undoing_one(self) -> None:
        # Arrange
        built = bytes(BANK + 3)

        # Act
        with self.assertRaises(mapper.NotWholeBanks) as raised:
            mapper.deinterleave(built)

        # Assert
        self.assertIn("65539", str(raised.exception))


class AddressTest(unittest.TestCase):
    def test_the_upper_half_of_a_bank_sits_in_the_first_run(self) -> None:
        # Arrange
        banks = 4

        # Act
        found = mapper.snes_to_file(0, HALF, banks)

        # Assert
        self.assertEqual(found, 0)

    def test_the_lower_half_of_a_bank_sits_behind_every_upper_half(self) -> None:
        # Arrange
        banks = 4

        # Act
        found = mapper.snes_to_file(0, 0, banks)

        # Assert
        self.assertEqual(found, 0x20000)

    def test_each_bank_advances_by_half_a_bank(self) -> None:
        # Arrange
        banks = 4

        # Act
        found = [mapper.snes_to_file(bank, HALF, banks) for bank in range(banks)]

        # Assert
        self.assertEqual(found, [0x0000, 0x8000, 0x10000, 0x18000])

    def test_an_address_and_its_offset_agree_in_both_directions(self) -> None:
        # Arrange
        banks = 8
        places = [
            (bank, addr)
            for bank in range(banks)
            for addr in (0x0000, 0x1234, HALF, HALF + 0x1234, 0xFFFF)
        ]

        # Act
        found = [
            mapper.file_to_snes(mapper.snes_to_file(bank, addr, banks), banks)
            for bank, addr in places
        ]

        # Assert
        self.assertEqual(found, places)

    def test_every_offset_in_an_image_maps_back_to_an_address(self) -> None:
        # Arrange
        banks = 4
        offsets = list(range(0, banks * BANK, 0x400))

        # Act
        found = [mapper.snes_to_file(*mapper.file_to_snes(one, banks), banks) for one in offsets]

        # Assert
        self.assertEqual(found, offsets)

    def test_the_readme_example_lands_where_it_says(self) -> None:
        # Arrange
        banks = 64

        # Act
        found = (mapper.file_to_snes(0, banks), mapper.file_to_snes(banks * HALF, banks))

        # Assert
        self.assertEqual(found, ((0, 0x8000), (0, 0)))


class WindowTest(unittest.TestCase):
    def test_the_window_starts_where_the_mapper_puts_it(self) -> None:
        # Arrange
        banks = 8

        # Act
        found = (
            mapper.address_to_file(WINDOW - 1, HALF, banks),
            mapper.address_to_file(WINDOW, HALF, banks),
        )

        # Assert
        self.assertEqual(found, (0x5F8000, 0x40000))

    def test_a_windowed_bank_reaches_the_image(self) -> None:
        # Arrange
        banks = 8

        # Act
        found = mapper.window_to_file(WINDOW, HALF, banks)

        # Assert
        self.assertEqual(found, 0x40000)

    def test_the_two_halves_of_a_windowed_bank_come_from_different_runs(self) -> None:
        # Arrange
        banks = 8

        # Act
        found = (
            mapper.window_to_file(WINDOW, 0x0000, banks),
            mapper.window_to_file(WINDOW, HALF, banks),
        )

        # Assert
        self.assertEqual(found, (0x440000, 0x40000))

    def test_a_windowed_bank_advances_by_half_a_bank(self) -> None:
        # Arrange
        banks = 8

        # Act
        found = [mapper.window_to_file(WINDOW + step, HALF, banks) for step in range(3)]

        # Assert
        self.assertEqual(found, [0x40000, 0x48000, 0x50000])

    def test_an_address_below_the_window_takes_the_ordinary_route(self) -> None:
        # Arrange
        banks = 8

        # Act
        found = mapper.address_to_file(0, HALF, banks)

        # Assert
        self.assertEqual(found, mapper.snes_to_file(0, HALF, banks))

    def test_an_address_inside_the_window_takes_the_windowed_route(self) -> None:
        # Arrange
        banks = 8

        # Act
        found = mapper.address_to_file(WINDOW, HALF, banks)

        # Assert
        self.assertEqual(found, mapper.window_to_file(WINDOW, HALF, banks))

    def test_every_windowed_bank_lands_inside_an_image_that_holds_it(self) -> None:
        # Arrange
        banks = 0x40

        # Act
        found = [
            mapper.window_to_file(bank, addr, banks)
            for bank in range(WINDOW, 0x100)
            for addr in (0x0000, HALF)
        ]

        # Assert
        self.assertEqual([one for one in found if not 0 <= one < banks * BANK * 2], [])


if __name__ == "__main__":
    unittest.main()
