import contextlib
import importlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "conformance"))

census = importlib.import_module("census")

sys.path.insert(0, str(ROOT / "mapper"))
from mapper import header  # noqa: E402


def a_cartridge(mapping=0x20, chipset=0x00, at=header.LOROM_HEADER, size=0x80000):
    rom = bytearray(size)
    rom[at : at + 21] = b"CENSUS CARTRIDGE     "
    rom[at + 21] = mapping
    rom[at + 22] = chipset
    rom[at + 23] = 0x0A
    rom[at + 25] = 0x01
    rom[at + 28] = 0xA5
    rom[at + 29] = 0xA5
    rom[at + 30] = 0x5A
    rom[at + 31] = 0x5A
    return bytes(rom)


class WalkTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="census-")
        self.addCleanup(shutil.rmtree, self.root, True)

    def write(self, name, blob):
        path = Path(self.root) / name
        path.write_bytes(blob)
        return path

    def test_cartridges_are_found_by_their_suffix(self):
        self.write("one.sfc", a_cartridge())
        self.write("two.smc", a_cartridge())
        self.write("notes.txt", b"not a cartridge")

        self.assertEqual(len(census.cartridges(self.root)), 2)

    def test_the_walk_is_in_a_fixed_order(self):
        self.write("b.sfc", a_cartridge())
        self.write("a.sfc", a_cartridge())

        found = [path.name for path in census.cartridges(self.root)]

        self.assertEqual(found, ["a.sfc", "b.sfc"])

    def test_a_limit_takes_only_the_first_few(self):
        for index in range(4):
            self.write(f"{index}.sfc", a_cartridge())

        self.assertEqual(len(census.cartridges(self.root, limit=2)), 2)


class TallyTest(unittest.TestCase):
    def test_a_cartridge_is_counted(self):
        found = census.tally([a_cartridge()])

        self.assertEqual(found["roms"], 1)

    def test_a_layout_is_recorded(self):
        found = census.tally([a_cartridge(mapping=0x20)])

        self.assertEqual(found["layout"]["lorom"], 1)

    def test_a_mapping_byte_is_recorded(self):
        found = census.tally([a_cartridge(mapping=0x30)])

        self.assertEqual(found["mapping"]["48"], 1)

    def test_a_chipset_byte_is_recorded(self):
        found = census.tally([a_cartridge(chipset=0x03)])

        self.assertEqual(found["chipset"]["3"], 1)

    def test_the_fast_bit_is_counted(self):
        found = census.tally([a_cartridge(mapping=0x30)])

        self.assertEqual(found["fast"], 1)

    def test_a_cartridge_with_no_header_is_skipped_rather_than_counted(self):
        found = census.tally([a_cartridge(), bytes(0x80000)])

        self.assertEqual((found["roms"], found["refused"]), (1, 1))

    def test_the_distinct_combinations_are_gathered(self):
        found = census.tally([a_cartridge(mapping=0x20), a_cartridge(mapping=0x21)])

        self.assertEqual(len(found["combinations"]), 2)

    def test_one_combination_counts_every_cartridge_that_shares_it(self):
        found = census.tally([a_cartridge(), a_cartridge()])

        self.assertEqual(found["combinations"][0]["cartridges"], 2)

    def test_the_tally_holds_no_title(self):
        found = census.tally([a_cartridge()])

        self.assertNotIn("CENSUS", json.dumps(found))


class MainTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="census-main-")
        self.addCleanup(shutil.rmtree, self.root, True)
        for index in range(3):
            (Path(self.root) / f"{index}.sfc").write_bytes(a_cartridge(mapping=0x20 + index))

    def run_main(self, argv):
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            code = census.main(argv)
        return code, captured.getvalue()

    def test_no_arguments_explains_how_to_call_it(self):
        code, output = self.run_main([])

        self.assertEqual(code, 2)
        self.assertIn("usage", output)

    def test_a_directory_that_is_not_there_is_reported(self):
        code, output = self.run_main([str(Path(self.root) / "absent"), "out.json"])

        self.assertEqual(code, 2)
        self.assertIn("nothing at", output)

    def test_a_library_becomes_a_census(self):
        out = Path(self.root) / "census.json"

        code, output = self.run_main([str(self.root), str(out)])

        self.assertEqual(code, 0)
        self.assertIn("3 cartridges", output)
        self.assertEqual(json.loads(out.read_text())["roms"], 3)

    def test_a_directory_with_no_cartridges_says_so(self):
        empty = Path(self.root) / "empty"
        empty.mkdir()

        code, output = self.run_main([str(empty), str(Path(self.root) / "c.json")])

        self.assertEqual(code, 1)
        self.assertIn("no cartridges", output)

    def test_a_limit_is_taken_from_the_third_argument(self):
        out = Path(self.root) / "census.json"

        code, _ = self.run_main([str(self.root), str(out), "2"])

        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.read_text())["roms"], 2)


if __name__ == "__main__":
    unittest.main()
