import importlib
import re
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapper import doctor, header


class Complaint(Exception):
    pass


def a_directory(names: tuple[str, ...] = ()) -> Path:
    where = Path(tempfile.mkdtemp())
    for name in names:
        (where / name).write_bytes(b"\x00" * 16)
    return where


def a_file(body: str) -> Path:
    where = Path(tempfile.mkdtemp()) / "held.json"
    where.write_text(body)
    return where


class FindingTest(unittest.TestCase):
    def test_a_finding_says_what_was_checked(self) -> None:
        one = doctor.Finding("python", True, "3.14")

        self.assertEqual(one.name, "python")

    def test_a_healthy_finding_prints_with_a_mark_that_says_so(self) -> None:
        one = doctor.Finding("python", True, "3.14")

        self.assertIn("ok", one.line)

    def test_and_an_unhealthy_one_prints_differently(self) -> None:
        one = doctor.Finding("python", False, "3.9")

        self.assertNotIn("ok", one.line)

    def test_an_unhealthy_finding_says_what_to_do_about_it(self) -> None:
        one = doctor.Finding("python", False, "3.9", "upgrade")

        self.assertIn("upgrade", one.report)

    def test_a_healthy_one_keeps_its_advice_to_itself(self) -> None:
        one = doctor.Finding("python", True, "3.14", "upgrade")

        self.assertNotIn("upgrade", one.report)

    def test_and_so_does_an_unhealthy_one_with_none_to_give(self) -> None:
        one = doctor.Finding("python", False, "3.9")

        self.assertEqual(one.report, one.line)

    def test_a_finding_prints_as_itself(self) -> None:
        one = doctor.Finding("python", False, "3.9")

        self.assertEqual(repr(one), "<Finding python not ok>")

    def test_and_says_so_when_it_is_well(self) -> None:
        one = doctor.Finding("python", True, "3.14")

        self.assertEqual(repr(one), "<Finding python ok>")


class PythonTest(unittest.TestCase):
    def test_it_reports_the_python_it_is_running_on(self) -> None:
        one = doctor._python()

        self.assertTrue(one.ok, one.detail)

    def test_and_names_the_package(self) -> None:
        one = doctor._package()

        self.assertEqual(one.name, "mapper")


class ModelTest(unittest.TestCase):
    def test_every_published_layout_resolves_its_probe(self) -> None:
        unwell = [name for name in doctor.PROBE if not doctor._model(name).ok]

        self.assertEqual(unwell, [])

    def test_a_layout_that_refuses_reports_what_it_said(self) -> None:
        one = doctor._model("no such layout")

        self.assertIn("UnknownModel", one.detail)

    def test_and_is_not_reported_as_well(self) -> None:
        one = doctor._model("no such layout")

        self.assertFalse(one.ok)

    def test_a_probe_landing_outside_rom_is_reported(self) -> None:
        held: dict[str, tuple[int, int | None]] = dict(doctor.PROBE, lorom=(0x7E0000, None))
        with unittest.mock.patch.object(doctor, "PROBE", held):
            one = doctor._model("lorom")

        self.assertFalse(one.ok, one.detail)


class ReadingTest(unittest.TestCase):
    def test_a_header_is_read_out_of_bytes_built_here(self) -> None:
        one = doctor._reading()

        self.assertTrue(one.ok, one.detail)

    def test_the_title_it_writes_is_the_width_the_reader_publishes(self) -> None:
        self.assertEqual(len(doctor.TITLE), header.TITLE_BYTES)

    def test_an_image_the_reader_refuses_is_reported_as_what_it_said(self) -> None:
        one = doctor._reading(lambda: b"")

        self.assertFalse(one.ok, one.detail)

    def test_and_a_title_that_comes_back_wrong_is_reported(self) -> None:
        def wrong() -> bytes:
            rom = bytearray(doctor._synthetic())
            rom[0x7FC0] = ord("X")
            return bytes(rom)

        one = doctor._reading(wrong)

        self.assertFalse(one.ok, one.detail)


class ManifestTest(unittest.TestCase):
    def test_the_manifest_beside_the_package_names_cartridges(self) -> None:
        one = doctor._manifest()

        self.assertTrue(one.ok, one.detail)

    def test_a_manifest_that_is_not_there_is_reported(self) -> None:
        one = doctor._manifest(Path(tempfile.mkdtemp()) / "absent.json")

        self.assertFalse(one.ok)

    def test_a_manifest_that_is_not_json_is_reported_differently(self) -> None:
        one = doctor._manifest(a_file("{"))

        self.assertIn("not readable as JSON", one.detail)

    def test_a_manifest_naming_nothing_is_not_well(self) -> None:
        one = doctor._manifest(a_file('{"cartridges": []}'))

        self.assertFalse(one.ok)


class CorpusTest(unittest.TestCase):
    def test_the_corpus_beside_the_package_holds_cases(self) -> None:
        one = doctor._corpus()

        self.assertTrue(one.ok, one.detail)

    def test_a_corpus_that_is_not_there_is_reported(self) -> None:
        one = doctor._corpus(Path(tempfile.mkdtemp()) / "absent.json")

        self.assertFalse(one.ok)

    def test_a_corpus_that_is_not_json_is_reported(self) -> None:
        one = doctor._corpus(a_file("{"))

        self.assertIn("not readable as JSON", one.detail)

    def test_a_corpus_with_no_cases_is_not_well(self) -> None:
        one = doctor._corpus(a_file('{"cases": []}'))

        self.assertFalse(one.ok)


class LookingTest(unittest.TestCase):
    def test_a_named_directory_is_reported_as_named(self) -> None:
        found = doctor._looking({doctor.DIRECTORY_VARIABLE: "/somewhere"})

        self.assertIn("set to /somewhere", found[0].detail)

    def test_and_it_is_the_one_chosen_even_when_it_is_not_there(self) -> None:
        found = doctor._looking({doctor.DIRECTORY_VARIABLE: "/somewhere"})

        self.assertEqual(found[-1].detail, "/somewhere")

    def test_an_unset_variable_says_the_places_are_tried_in_order(self) -> None:
        found = doctor._looking({})

        self.assertIn("tried in order", found[0].detail)

    def test_and_the_chosen_place_is_one_of_the_places_looked_in(self) -> None:
        found = doctor._looking({})

        self.assertIn(found[-1].detail, found[1].detail)

    def test_the_real_environment_is_read_when_none_is_given(self) -> None:
        found = doctor._looking()

        self.assertEqual(len(found), 3)

    def test_the_default_is_chosen_when_no_place_exists(self) -> None:
        held = Path(tempfile.mkdtemp()) / "absent"
        with (
            unittest.mock.patch.object(doctor, "DEFAULT_DIRECTORY", held),
            unittest.mock.patch.object(doctor, "ALONGSIDE", held),
        ):
            found = doctor._looking({})

        self.assertEqual(found[-1].detail, str(held))


class LibraryTest(unittest.TestCase):
    def test_a_library_that_is_not_there_is_reported_as_absent_not_broken(self) -> None:
        one = doctor._library(Path(tempfile.mkdtemp()) / "absent")

        self.assertTrue(one.ok, one.detail)

    def test_and_says_the_check_against_cartridges_will_skip(self) -> None:
        one = doctor._library(Path(tempfile.mkdtemp()) / "absent")

        self.assertIn("skip rather than run", one.detail)

    def test_a_library_holding_images_counts_them(self) -> None:
        one = doctor._library(a_directory(("a.sfc", "b.smc")))

        self.assertIn("2 images", one.detail)

    def test_and_is_well(self) -> None:
        one = doctor._library(a_directory(("a.sfc",)))

        self.assertTrue(one.ok, one.detail)

    def test_a_directory_that_is_there_and_empty_is_not_well(self) -> None:
        one = doctor._library(a_directory())

        self.assertFalse(one.ok, one.detail)

    def test_because_that_is_what_a_run_over_nothing_looks_like(self) -> None:
        one = doctor._library(a_directory(("notes.txt",)))

        self.assertIn("holds nothing", one.detail)

    def test_a_library_that_cannot_be_read_is_reported_as_what_it_said(self) -> None:
        where = a_directory()

        def refuse(*_: Any, **__: Any) -> Any:
            raise OSError("permission denied")

        with unittest.mock.patch.object(Path, "rglob", refuse):
            one = doctor._library(where)

        self.assertIn("permission denied", one.detail)


class ExamineTest(unittest.TestCase):
    def test_the_examination_produces_findings(self) -> None:
        found = doctor.examine()

        self.assertTrue(all(isinstance(one, doctor.Finding) for one in found))

    def test_it_looks_at_every_published_layout(self) -> None:
        named = {one.name for one in doctor.examine()}

        self.assertTrue(set(doctor.PROBE) <= named, named)

    def test_and_at_the_library_last_because_that_is_the_answer(self) -> None:
        found = doctor.examine()

        self.assertEqual(found[-1].name, "library")


class ReportTest(unittest.TestCase):
    def test_a_clean_examination_says_there_is_nothing_to_report(self) -> None:
        lines = doctor.report([doctor.Finding("one", True, "fine")])

        self.assertIn("nothing to report", lines[-1])

    def test_and_a_dirty_one_counts_what_did_not_pass(self) -> None:
        lines = doctor.report(
            [doctor.Finding("one", True, "fine"), doctor.Finding("two", False, "not")]
        )

        self.assertIn("1 of 2", lines[-1])


class MainTest(unittest.TestCase):
    def test_a_clean_machine_exits_zero(self) -> None:
        code = doctor.main((), lambda: [doctor.Finding("one", True, "fine")], lambda _: None)

        self.assertEqual(code, 0)

    def test_and_a_machine_with_a_finding_exits_one(self) -> None:
        code = doctor.main((), lambda: [doctor.Finding("one", False, "not")], lambda _: None)

        self.assertEqual(code, 1)

    def test_the_report_is_said_rather_than_returned(self) -> None:
        said: list[str] = []

        doctor.main((), lambda: [doctor.Finding("one", True, "fine")], said.append)

        self.assertTrue(any("nothing to report" in one for one in said))

    def test_it_runs_end_to_end_whatever_this_machine_holds(self) -> None:
        """A report, not a verdict that the machine is well.

        Asserting a clean exit here would make the suite require exactly the
        machine the doctor exists to report on. CI has no cartridges, and a
        doctor that says so is working. What has to hold on every machine is
        that it examines everything and prints a line for each finding.
        """
        said: list[str] = []

        code = doctor.main((), doctor.examine, said.append)

        self.assertIn(code, (0, 1))
        self.assertGreaterEqual(len(said), len(doctor.examine()))


class PathTest(unittest.TestCase):
    """That the doctor puts the repository on the path when nothing else has.

    Run as a file it has no package to be relative to, so it inserts the
    repository itself. Under the test suite the path is already set, so the line
    never runs and nothing would report it broken.
    """

    def test_the_repository_is_put_on_the_path_when_it_is_not_already_there(self) -> None:
        held = [one for one in sys.path if one != str(doctor.ROOT)]

        with unittest.mock.patch.object(sys, "path", held):
            importlib.reload(doctor)

            self.assertIn(str(doctor.ROOT), held)

    def test_the_version_is_read_out_of_the_file_rather_than_imported(self) -> None:
        found = re.search(
            r'VERSION[^"\']*"([^"]+)"', (doctor.ROOT / "mapper" / "version.py").read_text()
        )
        assert found is not None

        self.assertEqual(doctor.VERSION, found.group(1))

    def test_a_version_file_naming_nothing_reads_as_unknown(self) -> None:
        where = Path(tempfile.mkdtemp()) / "version.py"
        where.write_text("NOTHING = 1\n")

        self.assertEqual(doctor._version(where), "unknown")


if __name__ == "__main__":
    unittest.main()
