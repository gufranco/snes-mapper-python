import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mapper

LOW = 0x7FC0
HIGH = 0xFFC0
TWELVE_MEGABYTES = 0xC00000
FOUR_MEGABYTES = 0x400000


def a_header(mapping: int, chipset: int = 0x00, at: int = LOW) -> mapper.Header:
    raw = bytearray(32)
    raw[:21] = b"TEST CARTRIDGE".ljust(21)
    raw[21] = mapping
    raw[22] = chipset
    return mapper.Header(at, bytes(raw))


class BoardTest(unittest.TestCase):
    def test_an_ordinary_low_cartridge_stays_on_the_low_map(self) -> None:
        # Arrange
        found = a_header(mapping=0x20)

        # Act
        named = mapper.board(found, 0x100000)

        # Assert
        self.assertEqual(named, "lorom")

    def test_a_cartridge_of_the_one_length_that_map_has_is_on_it(self) -> None:
        # Arrange
        found = a_header(mapping=0x30)

        # Act
        named = mapper.board(found, TWELVE_MEGABYTES)

        # Assert
        self.assertEqual(named, "wholebank")

    def test_a_cartridge_past_the_low_map_but_short_of_that_length_is_not(self) -> None:
        # Arrange
        found = a_header(mapping=0x32, chipset=0x45)

        # Act
        named = mapper.board(found, 0x600000)

        # Assert
        self.assertEqual(named, "lorom")

    def test_a_cartridge_exactly_at_the_low_map_reach_stays_on_it(self) -> None:
        # Arrange
        found = a_header(mapping=0x30)

        # Act
        named = mapper.board(found, FOUR_MEGABYTES)

        # Assert
        self.assertEqual(named, "lorom")

    def test_the_chipset_byte_is_never_consulted(self) -> None:
        # Arrange
        chipsets = (0x00, 0x02, 0x43, 0x45)
        found = [a_header(mapping=0x32, chipset=one) for one in chipsets]

        # Act
        named = [
            (mapper.board(one, TWELVE_MEGABYTES), mapper.board(one, FOUR_MEGABYTES))
            for one in found
        ]

        # Assert
        self.assertEqual(named, [("wholebank", "lorom")] * len(chipsets))

    def test_an_expansion_still_claiming_a_part_it_no_longer_has_reads_the_same(self) -> None:
        # Arrange
        stale = a_header(mapping=0x32, chipset=0x45)
        corrected = a_header(mapping=0x32, chipset=0x00)

        # Act
        named = [mapper.board(one, TWELVE_MEGABYTES) for one in (stale, corrected)]

        # Assert
        self.assertEqual(named, ["wholebank", "wholebank"])

    def test_a_high_cartridge_is_left_where_its_header_put_it(self) -> None:
        # Arrange
        found = a_header(at=HIGH, mapping=0x21)

        # Act
        named = mapper.board(found, 0x200000)

        # Assert
        self.assertEqual(named, "hirom")

    def test_and_so_is_an_extended_one_at_that_very_length(self) -> None:
        # Arrange
        found = a_header(at=HIGH, mapping=0x35)

        # Act
        named = mapper.board(found, TWELVE_MEGABYTES)

        # Assert
        self.assertEqual(named, "exhirom")

    def test_a_declared_coprocessor_layout_is_left_alone_too(self) -> None:
        # Arrange
        found = a_header(mapping=0x23)

        # Act
        named = mapper.board(found, TWELVE_MEGABYTES)

        # Assert
        self.assertEqual(named, "sa1")


if __name__ == "__main__":
    unittest.main()
