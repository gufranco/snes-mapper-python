import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mapper


class WorkRamOffsetTest(unittest.TestCase):
    def test_the_low_eight_kilobytes_of_every_low_bank_are_the_same_cells(self) -> None:
        # Arrange
        addresses = [0x001000, 0x201000, 0x3F1000, 0x801000, 0xBF1000, 0x7E1000]

        # Act
        cells = [mapper.work_ram_offset(one) for one in addresses]

        # Assert
        self.assertEqual(cells, [0x1000] * 6)

    def test_banks_7e_and_7f_hold_the_whole_128_kilobytes_in_order(self) -> None:
        # Arrange
        addresses = [0x7E0000, 0x7EFFFF, 0x7F0000, 0x7FFFFF]

        # Act
        cells = [mapper.work_ram_offset(one) for one in addresses]

        # Assert
        self.assertEqual(cells, [0x00000, 0x0FFFF, 0x10000, 0x1FFFF])

    def test_an_address_that_is_not_work_ram_has_no_cell(self) -> None:
        # Arrange
        addresses = [0x002000, 0x008000, 0x401000, 0xC01000, 0x7D1000, 0x800000 | 0x2100]

        # Act
        cells = [mapper.work_ram_offset(one) for one in addresses]

        # Assert
        self.assertEqual(cells, [None] * 6)

    def test_an_address_past_24_bits_is_masked_first(self) -> None:
        # Arrange
        address = 0x1_201000

        # Act
        cell = mapper.work_ram_offset(address)

        # Assert
        self.assertEqual(cell, 0x1000)

    def test_a_cell_is_given_exactly_where_resolve_names_work_ram(self) -> None:
        # Arrange
        addresses = [
            (bank << 16) | page for bank in range(0x100) for page in (0x0000, 0x1FFF, 0x2000)
        ]

        # Act
        disagreeing = [
            one
            for one in addresses
            if (mapper.work_ram_offset(one) is not None)
            != (mapper.resolve(mapper.LOROM, one).region == mapper.WORK_RAM)
        ]

        # Assert
        self.assertEqual(disagreeing, [])

    def test_every_one_of_the_131072_cells_is_reachable(self) -> None:
        # Arrange
        addresses = [(bank << 16) | page for bank in (0x7E, 0x7F) for page in range(0x10000)]

        # Act
        cells = {mapper.work_ram_offset(one) for one in addresses}

        # Assert
        self.assertEqual(len(cells), 0x20000)


if __name__ == "__main__":
    unittest.main()
