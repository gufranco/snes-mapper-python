import copy
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import against_cartridges

from mapper import header


def a_cartridge(at=header.LOROM_HEADER, mapping=0x20, size=0x100000):
    rom = bytearray(size)
    rom[at : at + 21] = b"SWEPT CARTRIDGE      "
    rom[at + 21] = mapping
    rom[at + 23] = 0x0A
    rom[at + 25] = 0x01
    rom[at + 28] = 0xA5
    rom[at + 29] = 0xA5
    rom[at + 30] = 0x5A
    rom[at + 31] = 0x5A
    return bytes(rom)


class SweepTest(unittest.TestCase):
    def setUp(self):
        self.where = Path(tempfile.mkdtemp())
        (self.where / "region").mkdir()
        (self.where / "region" / "one.sfc").write_bytes(a_cartridge())

    def test_a_cartridge_the_corpus_covers_agrees(self):
        read, agreed, wrong = against_cartridges.sweep(self.where)

        self.assertEqual((read, agreed, wrong), (1, 1, []))

    def test_a_cartridge_with_no_header_is_counted_as_refused(self):
        (self.where / "region" / "blank.sfc").write_bytes(bytes(0x100000))

        self.assertEqual(against_cartridges.sweep(self.where)[0], 1)

    def test_a_combination_the_corpus_never_saw_is_reported(self):
        read, agreed, wrong = against_cartridges.sweep(self.where, cases=[])

        self.assertEqual((read, agreed), (1, 0))
        self.assertIn("no case", wrong[0])

    def test_a_case_the_model_now_disagrees_with_is_reported(self):
        cases = copy.deepcopy(against_cartridges.cases_by_key())
        keyed = cases[against_cartridges.key_of(header.read(a_cartridge()))]
        keyed["expect"]["layout"] = "nonsense"

        _, agreed, wrong = against_cartridges.sweep(self.where, cases=list(cases.values()))

        self.assertEqual(agreed, 0)
        self.assertIn("layout", wrong[0])

    def test_a_directory_that_is_not_there_reads_nothing(self):
        self.assertEqual(against_cartridges.sweep(Path("/nowhere/at/all"))[0], 0)

    def test_the_file_that_disagreed_is_named_so_it_can_be_found(self):
        _, _, wrong = against_cartridges.sweep(self.where, cases=[])

        self.assertIn("one.sfc", wrong[0])

    def test_a_file_that_is_not_a_cartridge_is_passed_over(self):
        (self.where / "region" / "notes.txt").write_bytes(b"nothing here")

        self.assertEqual(against_cartridges.sweep(self.where)[0], 1)

    def test_a_directory_named_like_a_cartridge_is_passed_over(self):
        (self.where / "region" / "folder.sfc").mkdir()

        self.assertEqual(against_cartridges.sweep(self.where)[0], 1)

    def test_only_the_first_few_disagreements_are_reported(self):
        for index in range(against_cartridges.EXAMPLE_LIMIT + 3):
            (self.where / "region" / f"copy{index}.sfc").write_bytes(
                a_cartridge(size=0x100000 + index * 0x8000)
            )

        _, _, wrong = against_cartridges.sweep(self.where, cases=[])

        self.assertEqual(len(wrong), against_cartridges.EXAMPLE_LIMIT)

    def test_only_the_first_few_that_disagree_with_their_case_are_reported(self):
        cases = copy.deepcopy(against_cartridges.cases_by_key())
        keyed = cases[against_cartridges.key_of(header.read(a_cartridge()))]
        keyed["expect"]["layout"] = "nonsense"
        for index in range(against_cartridges.EXAMPLE_LIMIT + 3):
            (self.where / "region" / f"copy{index}.sfc").write_bytes(a_cartridge())

        read, agreed, wrong = against_cartridges.sweep(self.where, cases=list(cases.values()))

        self.assertEqual(agreed, 0)
        self.assertEqual(len(wrong), against_cartridges.EXAMPLE_LIMIT)
        self.assertGreater(read, against_cartridges.EXAMPLE_LIMIT)

    def test_a_headerless_file_does_not_stop_the_ones_after_it(self):
        (self.where / "region" / "aaa-blank.sfc").write_bytes(bytes(0x100000))

        read, agreed, _ = against_cartridges.sweep(self.where)

        self.assertEqual((read, agreed), (1, 1))


class KeyTest(unittest.TestCase):
    def test_every_case_in_the_corpus_has_a_key(self):
        self.assertEqual(len(against_cartridges.cases_by_key()), len(against_cartridges.CASES))

    def test_a_header_keys_to_the_case_that_recorded_it(self):
        found = header.read(a_cartridge())

        self.assertIn(against_cartridges.key_of(found), against_cartridges.cases_by_key())

    def test_a_stubbed_dump_keys_to_the_same_case_as_a_bare_one(self):
        bare = header.read(a_cartridge())
        stubbed = header.read(b"\x00" * header.COPIER_BYTES + a_cartridge())

        self.assertEqual(against_cartridges.key_of(bare), against_cartridges.key_of(stubbed))


class MainTest(unittest.TestCase):
    def test_a_library_that_agrees_reports_success(self):
        where = Path(tempfile.mkdtemp())
        (where / "one.sfc").write_bytes(a_cartridge())

        self.assertEqual(against_cartridges.main([str(where)]), 0)

    def test_a_library_that_disagrees_reports_failure(self):
        where = Path(tempfile.mkdtemp())
        (where / "one.sfc").write_bytes(a_cartridge(mapping=0x21))

        self.assertEqual(against_cartridges.main([str(where)]), 1)

    def test_an_empty_library_is_skipped_rather_than_passed(self):
        self.assertEqual(against_cartridges.main([str(Path(tempfile.mkdtemp()))]), 2)


if __name__ == "__main__":
    unittest.main()
