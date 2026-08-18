import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapper import layout, models


class CatalogueTest(unittest.TestCase):
    def test_the_package_names_every_layout_it_covers(self):
        for name in (layout.LOROM, layout.HIROM, layout.EXHIROM):
            self.assertIn(name, models.MODELS)

    def test_a_layout_says_what_it_is_and_where_its_header_sits(self):
        found = models.describe(layout.LOROM)

        self.assertTrue(found.summary)
        self.assertEqual(found.header_at, 0x7FC0)

    def test_a_layout_name_is_matched_however_it_is_written(self):
        for written in ("LOROM", "lo", "mode20", "LO_ROM"):
            self.assertEqual(models.describe(written).name, layout.LOROM)

    def test_a_layout_the_package_does_not_have_is_refused_by_name(self):
        with self.assertRaises(models.UnknownModelError):
            models.describe("sa1")

    def test_the_refusal_lists_what_is_available(self):
        with self.assertRaises(models.UnknownModelError) as raised:
            models.describe("nonsense")

        self.assertIn("lorom", str(raised.exception))

    def test_a_layout_prints_as_its_name_and_header(self):
        printed = repr(models.describe(layout.HIROM))

        self.assertIn("hirom", printed)
        self.assertIn("ffc0", printed)


class ResolveTest(unittest.TestCase):
    def test_a_layout_resolves_an_address_the_way_the_space_does(self):
        found = models.describe(layout.LOROM).resolve(0x008000)

        self.assertEqual(found.region, layout.ROM)

    def test_a_layout_carries_the_speed_it_was_asked_about(self):
        found = models.describe(layout.LOROM).resolve(0x808000, fast=True)

        self.assertEqual(found.cycles, layout.FAST)

    def test_the_high_layout_reaches_cartridge_where_the_low_one_does_not(self):
        self.assertEqual(models.describe(layout.HIROM).resolve(0xC00000).region, layout.ROM)


if __name__ == "__main__":
    unittest.main()
