import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, override

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from conformance import corpus  # noqa: E402
from mapper import header  # noqa: E402


def a_case(at: int, mapping: int) -> dict[str, Any]:
    return {
        "expect": {"at": at},
        "mapping": mapping,
        "chipset": 0x00,
        "rom_size": 0x0A,
        "ram_size": 0x00,
        "country": 0x01,
    }


def said(found: str | None) -> str:
    """What a failing case said, insisting that it said something.

    check() returns nothing when a case agreed, so the type is optional. Every use
    below is about a case that was meant to disagree, and asserting that here means
    a case that unexpectedly passes fails on that rather than on a None.
    """
    assert found is not None, "the case agreed when it was meant to disagree"
    return found


class StandInTest(unittest.TestCase):
    def test_a_case_at_a_known_offset_is_built_there(self) -> None:
        built = corpus.cartridge_for(a_case(header.HIROM_HEADER, 0x21))

        self.assertEqual(len(built), corpus.SIZE_FOR_OFFSET[header.HIROM_HEADER])

    def test_a_stubbed_high_offset_is_built_at_the_high_one(self) -> None:
        built = corpus.cartridge_for(a_case(header.HIROM_HEADER + header.COPIER_BYTES, 0x21))

        self.assertEqual(len(built), corpus.SIZE_FOR_OFFSET[header.HIROM_HEADER])

    def test_and_a_stubbed_low_offset_at_the_low_one(self) -> None:
        built = corpus.cartridge_for(a_case(header.LOROM_HEADER + header.COPIER_BYTES, 0x20))

        self.assertEqual(len(built), corpus.SIZE_FOR_OFFSET[header.LOROM_HEADER])

    def test_an_offset_that_is_neither_falls_back_by_where_it_sits_in_its_bank(self) -> None:
        built = corpus.cartridge_for(a_case(0x123456, 0x21))

        self.assertEqual(len(built), corpus.SIZE_FOR_OFFSET[header.HIROM_HEADER])

    def test_the_extended_offset_gets_an_image_large_enough_to_hold_it(self) -> None:
        built = corpus.cartridge_for(a_case(header.EXHIROM_HEADER, 0x35))

        self.assertGreater(len(built), header.EXHIROM_HEADER)


class DefinitionTest(unittest.TestCase):
    def test_the_repository_ships_a_corpus(self) -> None:
        self.assertTrue(corpus.load()["cases"])

    def test_the_corpus_says_how_many_cartridges_it_was_measured_from(self) -> None:
        self.assertGreater(corpus.load()["measured_from"], 1000)

    def test_the_corpus_carries_the_census_beside_the_cases(self) -> None:
        found = corpus.load()["census"]

        self.assertTrue(found["layout"])
        self.assertTrue(found["offsets"])

    def test_a_corpus_is_read_from_where_it_is_asked_for(self) -> None:
        with tempfile.TemporaryDirectory() as where:
            path = Path(where) / "c.json"
            path.write_text(json.dumps({"cases": [], "measured_from": 1, "probes": []}))

            self.assertEqual(corpus.load(path)["measured_from"], 1)


class CoverageTest(unittest.TestCase):
    def test_the_cases_cover_every_cartridge_measured(self) -> None:
        found = corpus.load()

        self.assertEqual(sum(case["cartridges"] for case in found["cases"]), found["measured_from"])

    def test_the_cases_reach_every_layout_the_library_uses(self) -> None:
        layouts = {case["expect"]["layout"] for case in corpus.load()["cases"]}

        self.assertGreaterEqual(len(layouts), 3)

    def test_the_cases_reach_cartridges_with_and_without_a_coprocessor(self) -> None:
        cases = corpus.load()["cases"]

        self.assertTrue(any(c["expect"]["coprocessor"] for c in cases))
        self.assertTrue(any(not c["expect"]["coprocessor"] for c in cases))

    def test_the_cases_reach_both_bus_speeds(self) -> None:
        cases = corpus.load()["cases"]

        self.assertTrue(any(c["expect"]["fast"] for c in cases))
        self.assertTrue(any(not c["expect"]["fast"] for c in cases))

    def test_the_probes_reach_work_ram_registers_and_cartridge(self) -> None:
        regions = {entry[1] for case in corpus.load()["cases"] for entry in case["resolutions"]}

        self.assertTrue({"work-ram", "registers", "rom"} <= regions)

    def test_a_case_carries_no_cartridge_content(self) -> None:
        self.assertEqual(
            sorted(corpus.load()["cases"][0]),
            [
                "cartridges",
                "chipset",
                "country",
                "expect",
                "mapping",
                "ram_size",
                "resolutions",
                "rom_size",
            ],
        )


class CheckTest(unittest.TestCase):
    def test_a_matching_case_reports_nothing(self) -> None:
        found = corpus.load()

        self.assertIsNone(corpus.check(found["cases"][0]))

    def test_a_wrong_layout_is_reported(self) -> None:
        case = corpus.load()["cases"][0]
        wrong = dict(case, expect=dict(case["expect"], layout="nonsense"))

        self.assertIn("layout", said(corpus.check(wrong)))

    def test_a_wrong_resolution_is_reported(self) -> None:
        case = corpus.load()["cases"][0]
        wrong = dict(case, resolutions=[[0x008000, "work-ram", None, 8]])

        self.assertIn("008000", said(corpus.check(wrong)))

    def test_a_case_that_cannot_be_built_is_reported_rather_than_raising(self) -> None:
        self.assertIsNotNone(corpus.check({"mapping": "not a byte"}))


class RunTest(unittest.TestCase):
    def test_the_whole_shipped_corpus_agrees(self) -> None:
        found = corpus.load()

        passed, failed, examples = corpus.run(found["cases"])

        self.assertEqual(failed, 0)
        self.assertEqual(examples, [])
        self.assertEqual(passed, len(found["cases"]))

    def test_a_disagreeing_case_is_counted_and_kept(self) -> None:
        case = corpus.load()["cases"][0]
        wrong = dict(case, expect=dict(case["expect"], layout="nonsense"))

        passed, failed, examples = corpus.run([wrong])

        self.assertEqual((passed, failed), (0, 1))
        self.assertEqual(len(examples), 1)

    def test_only_a_few_examples_are_kept(self) -> None:
        case = corpus.load()["cases"][0]
        wrong = dict(case, expect=dict(case["expect"], layout="nonsense"))

        _, _, examples = corpus.run([wrong] * 40)

        self.assertLessEqual(len(examples), corpus.EXAMPLE_LIMIT)


class MainTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.root = tempfile.mkdtemp(prefix="corpus-")
        self.addCleanup(shutil.rmtree, self.root, True)

    def run_main(self, argv: list[str]) -> Any:
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            code = corpus.main(argv)
        return code, captured.getvalue()

    def test_no_arguments_runs_the_corpus_that_ships(self) -> None:
        code, output = self.run_main([])

        self.assertEqual(code, 0)
        self.assertIn("agreed", output)

    def test_a_corpus_that_is_not_there_is_reported(self) -> None:
        code, output = self.run_main([str(Path(self.root) / "absent.json")])

        self.assertEqual(code, 2)
        self.assertIn("no corpus at", output)

    def test_a_disagreeing_corpus_fails(self) -> None:
        found = corpus.load()
        case = found["cases"][0]
        broken = dict(found, cases=[dict(case, expect=dict(case["expect"], layout="nonsense"))])
        path = Path(self.root) / "broken.json"
        path.write_text(json.dumps(broken))

        code, output = self.run_main([str(path)])

        self.assertEqual(code, 1)
        self.assertIn("1 did not", output)


if __name__ == "__main__":
    unittest.main()
