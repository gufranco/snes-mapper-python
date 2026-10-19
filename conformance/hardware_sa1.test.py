import json
import re
import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mapper

HARDWARE = Path(__file__).resolve().parent / "hardware.json"

BANK_RANGE = re.compile(r"\b([0-9A-F]{2})H-([0-9A-F]{2})H\b")

PAGE_RANGE = re.compile(r"\b([0-9A-F]{4})H-([0-9A-F]{4})H\b")

FAR_RANGE = re.compile(r"([0-9A-F]{2}):([0-9A-F]{4})H~([0-9A-F]{2}):([0-9A-F]{4})H")

INITIAL = re.compile(r"Initial value: ([0-9A-F]{2})H")

BLOCK = 0x100000

PROBE_PAGES = (0x0000, 0x7FFF, 0x8000, 0xFFFF)


def fact(name: str) -> dict[str, Any]:
    found = json.loads(HARDWARE.read_text())["facts"][name]
    assert isinstance(found, dict), f"{name} is not recorded as a fact"
    return found


def bank_ranges(quote: str) -> list[range]:
    return [range(int(low, 16), int(high, 16) + 1) for low, high in BANK_RANGE.findall(quote)]


def page_range(quote: str) -> range:
    low, high = PAGE_RANGE.findall(quote)[0]
    return range(int(low, 16), int(high, 16) + 1)


def far(text: str) -> list[tuple[int, int]]:
    return [
        ((int(bank, 16) << 16) | int(low, 16), (int(end, 16) << 16) | int(high, 16))
        for bank, low, end, high in FAR_RANGE.findall(text)
    ]


def landed(address: int) -> tuple[str, int | None]:
    found = mapper.resolve(mapper.SA1, address)
    return found.region, found.offset


def block_of(address: int) -> int:
    offset = landed(address)[1]
    assert offset is not None, f"{address:06X} reaches no ROM"
    return offset // BLOCK


class DirectBankTest(unittest.TestCase):
    def test_each_sixteen_banks_from_c0_carry_one_eight_megabit_block(self) -> None:
        # Arrange
        areas = bank_ranges(fact("sa1BankSwitching")["quote"])

        # Act
        found = [
            {block_of((bank << 16) | page) for bank in area for page in PROBE_PAGES}
            for area in areas
        ]

        # Assert
        self.assertEqual(found, [{0}, {1}, {2}, {3}])


class ProjectionTest(unittest.TestCase):
    def test_each_thirty_two_banks_below_the_window_carry_one_block(self) -> None:
        # Arrange
        areas = bank_ranges(fact("sa1RomProjection")["quote"])
        pages = page_range(fact("sa1RomProjection")["quote"])

        # Act
        found = [
            {block_of((bank << 16) | page) for bank in area for page in pages[::0x1000]}
            for area in areas
        ]

        # Assert
        self.assertEqual(found, [{0}, {1}, {2}, {3}])

    def test_the_projection_runs_in_successive_order(self) -> None:
        # Arrange
        pairs = far(fact("sa1RomOrder")["quote"])
        sources, targets = pairs[0::2], pairs[1::2]

        # Act
        found = [(landed(low)[1], landed(high)[1]) for low, high in targets]

        # Assert
        self.assertEqual(found, [(landed(low)[1], landed(high)[1]) for low, high in sources])

    def test_the_fixed_projection_puts_the_blocks_in_order(self) -> None:
        # Arrange
        quote = fact("sa1FirstBlocks")["quote"]
        blocks = [low for low, _high in far(quote)]
        areas = bank_ranges(quote)

        # Act
        found = [landed((area[0] << 16) | 0x8000)[1] for area in areas]

        # Assert
        self.assertEqual(found, blocks)

    def test_the_vectors_reach_the_registration_data(self) -> None:
        # Arrange
        quote = fact("sa1Vectors")["quote"]
        held = far(quote)[0]
        pages = page_range(quote)

        # Act
        found = [landed(page)[1] for page in (pages[0], pages[-1])]

        # Assert
        self.assertEqual(found, [held[0] & 0xFFFF, held[1] & 0xFFFF])


class BackupRamTest(unittest.TestCase):
    def test_backup_ram_starts_at_bank_40(self) -> None:
        # Arrange
        quote = fact("sa1BackupRamBanks")["quote"]
        bank = int(re.findall(r"bank ([0-9A-F]{2})H", quote)[0], 16)
        page = int(re.findall(r"justified to ([0-9A-F]{4})H", quote)[0], 16)

        # Act
        found = landed((bank << 16) | page)

        # Assert
        self.assertEqual(found, (mapper.SAVE_RAM, None))

    def test_and_is_projected_into_every_system_bank(self) -> None:
        # Arrange
        quote = fact("sa1BackupRamImage")["quote"]
        mapping = INITIAL.findall(fact("sa1Bmaps")["quote"])
        pages = page_range(quote)

        # Act
        found = {
            landed((bank << 16) | page)[0]
            for area in bank_ranges(quote)
            for bank in area
            for page in (pages[0], pages[-1])
        }

        # Assert
        self.assertEqual((found, mapping), ({mapper.SAVE_RAM}, ["00"]))


class WindowTest(unittest.TestCase):
    def test_the_sa1_registers_are_the_coprocessor_s(self) -> None:
        # Arrange
        quote = fact("sa1Registers")["quote"]
        pages = page_range(quote)

        # Act
        found = {
            landed((bank << 16) | page)[0]
            for area in bank_ranges(quote)
            for bank in area
            for page in (pages[0], pages[-1])
        }

        # Assert
        self.assertEqual(found, {mapper.COPROCESSOR})

    def test_and_so_is_its_internal_ram(self) -> None:
        # Arrange
        quote = fact("sa1Iram")["quote"]
        pages = page_range(quote)

        # Act
        found = {
            landed((bank << 16) | page)[0]
            for area in bank_ranges(quote)
            for bank in area
            for page in (pages[0], pages[-1])
        }

        # Assert
        self.assertEqual(found, {mapper.COPROCESSOR})


class InitialValueTest(unittest.TestCase):
    def test_the_map_is_the_one_the_initial_bank_values_select(self) -> None:
        # Arrange
        names = ("sa1Cxb", "sa1Dxb", "sa1Exb", "sa1Fxb")
        values = [int(INITIAL.findall(fact(name)["quote"])[0], 16) for name in names]
        fixed = "area 1 is copied" in fact("sa1CxbFixed")["quote"]

        # Act
        found = [block_of(bank << 16) for bank in (0xC0, 0xD0, 0xE0, 0xF0)]

        # Assert
        self.assertEqual((found, fixed), (values, True))


class MapTest(unittest.TestCase):
    def test_every_row_of_the_figure_lands_where_it_is_drawn(self) -> None:
        # Arrange
        rows = fact("sa1Map")["rows"]
        expected = {
            "SUPER NES WRAM": mapper.WORK_RAM,
            "SA-1 Register": mapper.COPROCESSOR,
            "SA-1 I-RAM": mapper.COPROCESSOR,
            "BW-RAM": mapper.SAVE_RAM,
            "Select Game Pak ROM": mapper.ROM,
            "GAME PAK ROM": mapper.ROM,
            "cross-hatched": mapper.OPEN_BUS,
        }

        # Act
        found = [
            {
                landed((bank << 16) | page)[0]
                for low, high in (part.split("-") for part in row["banks"].split(", "))
                for bank in (int(low, 16), int(high, 16))
                for page in (int(row["pages"][:4], 16), int(row["pages"][5:], 16))
            }
            for row in rows
        ]

        # Assert
        self.assertEqual(
            found,
            [
                {
                    next(
                        region
                        for label, region in expected.items()
                        if row["label"].startswith(label)
                    )
                }
                for row in rows
            ],
        )


if __name__ == "__main__":
    unittest.main()
