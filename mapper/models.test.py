import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mapper


class CatalogueTest(unittest.TestCase):
    def test_the_package_names_every_layout_it_covers(self) -> None:
        # Arrange
        expected = ["exhirom", "hirom", "lorom", "wholebank"]

        # Act
        found = sorted(mapper.MODELS)

        # Assert
        self.assertEqual(found, expected)

    def test_a_layout_says_what_it_is_and_where_its_header_sits(self) -> None:
        # Arrange
        name = "lorom"

        # Act
        found = mapper.layout_named(name)

        # Assert
        self.assertGreater(len(found.summary), 0)
        self.assertEqual(found.header_at, 0x7FC0)

    def test_a_layout_name_is_matched_however_it_is_written(self) -> None:
        # Arrange
        written = ("LOROM", "lo", "mode20", "LO_ROM", "Mode-20")

        # Act
        found = [mapper.layout_named(one).name for one in written]

        # Assert
        self.assertEqual(found, ["lorom"] * len(written))

    def test_every_alias_the_readme_lists_names_its_layout(self) -> None:
        # Arrange
        listed = {
            "lorom": ("lo", "mode20", "20"),
            "hirom": ("hi", "mode21", "21"),
            "exhirom": ("exhi", "mode25", "25"),
            "wholebank": ("whole", "wholebanks", "interleaved"),
        }

        # Act
        found = {name: mapper.layout_named(name).aliases for name in listed}

        # Assert
        self.assertEqual(found, listed)

    def test_a_layout_the_package_does_not_have_is_refused_by_name(self) -> None:
        # Arrange
        name = "sa1"

        # Act
        with self.assertRaises(mapper.UnknownModelError) as raised:
            mapper.layout_named(name)

        # Assert
        self.assertTrue(str(raised.exception).startswith("sa1 is not a layout"))

    def test_the_refusal_lists_what_is_available(self) -> None:
        # Arrange
        name = "nonsense"

        # Act
        with self.assertRaises(mapper.UnknownModelError) as raised:
            mapper.layout_named(name)

        # Assert
        self.assertEqual(
            str(raised.exception),
            "nonsense is not a layout this package covers; it has exhirom, hirom, lorom, wholebank",
        )

    def test_a_layout_prints_as_its_name_and_header(self) -> None:
        # Arrange
        found = mapper.layout_named("hirom")

        # Act
        printed = repr(found)

        # Assert
        self.assertEqual(printed, "<Model hirom, header at 0xffc0>")


class ResolveTest(unittest.TestCase):
    def test_a_layout_resolves_an_address_the_way_the_space_does(self) -> None:
        # Arrange
        found = mapper.layout_named("lorom")

        # Act
        landed = found.resolve(0x008000)

        # Assert
        self.assertEqual((landed.region, landed.offset), ("rom", 0))

    def test_a_layout_carries_the_speed_it_was_asked_about(self) -> None:
        # Arrange
        found = mapper.layout_named("lorom")

        # Act
        landed = found.resolve(0x808000, fast=True)

        # Assert
        self.assertEqual(landed.cycles, 6)

    def test_the_high_layout_reaches_cartridge_where_the_low_one_does_not(self) -> None:
        # Arrange
        found = mapper.layout_named("hirom")

        # Act
        landed = found.resolve(0xC00000)

        # Assert
        self.assertEqual(landed.region, "rom")

    def test_a_layout_passes_the_bank_count_and_save_window_through(self) -> None:
        # Arrange
        found = mapper.layout_named("wholebank")

        # Act
        landed = found.resolve(0x700000, banks=192, save=True)

        # Assert
        self.assertEqual(landed.region, "save-ram")


if __name__ == "__main__":
    unittest.main()
