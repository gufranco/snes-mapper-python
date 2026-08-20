import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapper import image


def a_logical(banks: int) -> bytes:
    blob = bytearray(banks * image.BANK)
    for bank in range(banks):
        blob[bank * image.BANK] = 0xA0 | bank
        blob[bank * image.BANK + image.HALF] = 0xB0 | bank
    return bytes(blob)


class BankCountTest(unittest.TestCase):
    def test_a_whole_number_of_banks_is_counted(self) -> None:
        self.assertEqual(image.bank_count(4 * image.BANK), 4)

    def test_a_size_that_is_not_whole_banks_is_refused(self) -> None:
        with self.assertRaises(image.NotWholeBanks):
            image.bank_count(image.BANK + 1)

    def test_the_refusal_names_the_size(self) -> None:
        with self.assertRaises(image.NotWholeBanks) as raised:
            image.bank_count(0x1234)

        self.assertIn("4660", str(raised.exception))

    def test_an_empty_image_holds_no_banks(self) -> None:
        self.assertEqual(image.bank_count(0), 0)


class InterleaveTest(unittest.TestCase):
    def test_interleaving_keeps_the_size(self) -> None:
        logical = a_logical(4)

        self.assertEqual(len(image.interleave(logical)), len(logical))

    def test_interleaving_then_undoing_it_gives_the_original_back(self) -> None:
        for banks in (1, 2, 4, 8, 16):
            logical = a_logical(banks)

            self.assertEqual(image.deinterleave(image.interleave(logical)), logical)

    def test_undoing_then_interleaving_gives_the_original_back(self) -> None:
        for banks in (1, 2, 4, 8):
            swapped = a_logical(banks)

            self.assertEqual(image.interleave(image.deinterleave(swapped)), swapped)

    def test_the_upper_half_of_a_bank_moves_to_the_front(self) -> None:
        logical = a_logical(2)

        swapped = image.interleave(logical)

        self.assertEqual(swapped[0], 0xB0)

    def test_the_lower_half_of_a_bank_moves_behind_every_upper_half(self) -> None:
        logical = a_logical(2)

        swapped = image.interleave(logical)

        self.assertEqual(swapped[2 * image.HALF], 0xA0)

    def test_an_image_that_is_not_whole_banks_is_refused(self) -> None:
        with self.assertRaises(image.NotWholeBanks):
            image.interleave(bytes(image.BANK + 3))


class AddressTest(unittest.TestCase):
    def test_the_upper_half_of_a_bank_sits_in_the_first_run(self) -> None:
        self.assertEqual(image.snes_to_file(0, image.HALF, 4), 0)

    def test_the_lower_half_of_a_bank_sits_behind_every_upper_half(self) -> None:
        self.assertEqual(image.snes_to_file(0, 0, 4), 4 * image.HALF)

    def test_each_bank_advances_by_half_a_bank(self) -> None:
        first = image.snes_to_file(0, image.HALF, 4)
        second = image.snes_to_file(1, image.HALF, 4)

        self.assertEqual(second - first, image.HALF)

    def test_an_address_and_its_offset_agree_in_both_directions(self) -> None:
        banks = 8
        for bank in range(banks):
            for addr in (0x0000, 0x1234, image.HALF, image.HALF + 0x1234, 0xFFFF):
                offset = image.snes_to_file(bank, addr, banks)

                self.assertEqual(image.file_to_snes(offset, banks), (bank, addr))

    def test_every_offset_in_an_image_maps_back_to_an_address(self) -> None:
        banks = 4
        for offset in range(0, banks * image.BANK, 0x400):
            bank, addr = image.file_to_snes(offset, banks)

            self.assertEqual(image.snes_to_file(bank, addr, banks), offset)


class WindowTest(unittest.TestCase):
    def test_the_window_starts_where_the_mapper_puts_it(self) -> None:
        self.assertEqual(image.WINDOW_FIRST_BANK, 0xC0)

    def test_a_windowed_bank_reaches_the_image(self) -> None:
        found = image.window_to_file(image.WINDOW_FIRST_BANK, image.HALF, 8)

        self.assertGreaterEqual(found, 0)

    def test_the_two_halves_of_a_windowed_bank_come_from_different_runs(self) -> None:
        low = image.window_to_file(image.WINDOW_FIRST_BANK, 0x0000, 8)
        high = image.window_to_file(image.WINDOW_FIRST_BANK, image.HALF, 8)

        self.assertNotEqual(low, high)

    def test_a_windowed_bank_advances_by_half_a_bank(self) -> None:
        first = image.window_to_file(image.WINDOW_FIRST_BANK, image.HALF, 8)
        second = image.window_to_file(image.WINDOW_FIRST_BANK + 1, image.HALF, 8)

        self.assertEqual(second - first, image.HALF)

    def test_an_address_below_the_window_takes_the_ordinary_route(self) -> None:
        self.assertEqual(
            image.address_to_file(0, image.HALF, 8), image.snes_to_file(0, image.HALF, 8)
        )

    def test_an_address_inside_the_window_takes_the_windowed_route(self) -> None:
        bank = image.WINDOW_FIRST_BANK

        self.assertEqual(
            image.address_to_file(bank, image.HALF, 8), image.window_to_file(bank, image.HALF, 8)
        )

    def test_every_windowed_bank_lands_inside_an_image_that_holds_it(self) -> None:
        banks = 0x40
        for bank in range(image.WINDOW_FIRST_BANK, 0x100):
            for addr in (0x0000, image.HALF):
                found = image.window_to_file(bank, addr, banks)

                self.assertGreaterEqual(found, 0)
                self.assertLess(found, banks * image.BANK * 2)


if __name__ == "__main__":
    unittest.main()
