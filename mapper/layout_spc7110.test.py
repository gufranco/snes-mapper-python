import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mapper


def landed(addresses: list[int]) -> list[tuple[str, int | None]]:
    return [
        (found.region, found.offset)
        for found in (mapper.resolve(mapper.SPC7110, one) for one in addresses)
    ]


class Spc7110Test(unittest.TestCase):
    def test_the_program_rom_is_the_first_megabyte(self) -> None:
        # Arrange
        addresses = [0xC00000, 0xCFFFFF, 0x008000, 0x8F8000]

        # Act
        found = landed(addresses)

        # Assert
        self.assertEqual(
            found, [("rom", 0x000000), ("rom", 0x0FFFFF), ("rom", 0x008000), ("rom", 0x0F8000)]
        )

    def test_every_data_bank_reads_the_first_data_megabyte_before_the_game_selects_one(
        self,
    ) -> None:
        # Arrange
        addresses = [0xD00000, 0x108000, 0xE00000, 0xF0FFFF, 0xBFFFFF]

        # Act
        found = landed(addresses)

        # Assert
        self.assertEqual(
            found,
            [
                ("rom", 0x100000),
                ("rom", 0x108000),
                ("rom", 0x100000),
                ("rom", 0x10FFFF),
                ("rom", 0x1FFFFF),
            ],
        )

    def test_the_registers_and_the_port_banks_are_the_chip_s(self) -> None:
        # Arrange
        addresses = [0x004800, 0x80483F, 0x500000, 0x58FFFF, 0x004840]

        # Act
        found = [region for region, _ in landed(addresses)]

        # Assert
        self.assertEqual(found, ["coprocessor"] * 4 + ["registers"])

    def test_backup_ram_sits_in_the_system_banks_alone(self) -> None:
        # Arrange
        addresses = [0x006000, 0xBF7FFF, 0x406000, 0x700000]

        # Act
        found = [region for region, _ in landed(addresses)]

        # Assert
        self.assertEqual(found, ["save-ram", "save-ram", "open-bus", "open-bus"])

    def test_the_header_is_where_the_console_reads_it(self) -> None:
        # Arrange
        model = mapper.layout_named(mapper.SPC7110)

        # Act
        found = model.resolve(0x00FFC0)

        # Assert
        self.assertEqual(found.offset, model.header_at)


if __name__ == "__main__":
    unittest.main()
