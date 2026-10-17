import importlib
import os
import re
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mapper
from mapper import doctor

SOURCE = Path(__file__).resolve().parent / "doctor.py"

VERDICT = re.compile(r"^  (\d+ checks, nothing to report|\d+ of \d+ checks did not pass)$")


class FindingTest(unittest.TestCase):
    def test_a_finding_says_what_was_checked(self) -> None:
        # Arrange
        name = "python"

        # Act
        one = doctor.Finding(name, True, "3.14")

        # Assert
        self.assertEqual(one.name, "python")

    def test_a_healthy_finding_prints_with_a_mark_that_says_so(self) -> None:
        # Arrange
        one = doctor.Finding("python", True, "3.14")

        # Act
        line = one.line

        # Assert
        self.assertIn("ok", line)

    def test_and_an_unhealthy_one_prints_differently(self) -> None:
        # Arrange
        one = doctor.Finding("python", False, "3.9")

        # Act
        line = one.line

        # Assert
        self.assertNotIn("ok", line)

    def test_an_unhealthy_finding_says_what_to_do_about_it(self) -> None:
        # Arrange
        one = doctor.Finding("python", False, "3.9", "upgrade")

        # Act
        report = one.report

        # Assert
        self.assertIn("upgrade", report)

    def test_a_healthy_one_keeps_its_advice_to_itself(self) -> None:
        # Arrange
        one = doctor.Finding("python", True, "3.14", "upgrade")

        # Act
        report = one.report

        # Assert
        self.assertNotIn("upgrade", report)

    def test_and_so_does_an_unhealthy_one_with_none_to_give(self) -> None:
        # Arrange
        one = doctor.Finding("python", False, "3.9")

        # Act
        report = one.report

        # Assert
        self.assertEqual(report, one.line)

    def test_a_finding_prints_as_itself(self) -> None:
        # Arrange
        one = doctor.Finding("python", False, "3.9")

        # Act
        printed = repr(one)

        # Assert
        self.assertEqual(printed, "<Finding python not ok>")

    def test_and_says_so_when_it_is_well(self) -> None:
        # Arrange
        one = doctor.Finding("python", True, "3.14")

        # Act
        printed = repr(one)

        # Assert
        self.assertEqual(printed, "<Finding python ok>")


class PythonTest(unittest.TestCase):
    def test_it_reports_the_python_it_is_running_on(self) -> None:
        # Arrange
        check = doctor.check_python

        # Act
        one = check()

        # Assert
        self.assertTrue(one.ok, one.detail)

    def test_and_names_the_package(self) -> None:
        # Arrange
        check = doctor.check_package

        # Act
        one = check()

        # Assert
        self.assertEqual(one.name, "mapper")


class ModelTest(unittest.TestCase):
    def test_every_published_layout_resolves_its_probe(self) -> None:
        # Arrange
        names = sorted(doctor.PROBE)

        # Act
        unwell = [name for name in names if not doctor.check_model(name).ok]

        # Assert
        self.assertEqual(unwell, [])

    def test_a_layout_that_refuses_reports_what_it_said(self) -> None:
        # Arrange
        name = "no such layout"

        # Act
        one = doctor.check_model(name)

        # Assert
        self.assertIn("UnknownModel", one.detail)

    def test_and_is_not_reported_as_well(self) -> None:
        # Arrange
        name = "no such layout"

        # Act
        one = doctor.check_model(name)

        # Assert
        self.assertFalse(one.ok)

    def test_a_probe_landing_outside_rom_is_reported(self) -> None:
        # Arrange
        held: dict[str, tuple[int, int | None]] = dict(doctor.PROBE, lorom=(0x7E0000, None))

        # Act
        with unittest.mock.patch.object(doctor, "PROBE", held):
            one = doctor.check_model("lorom")

        # Assert
        self.assertFalse(one.ok, one.detail)


class ReadingTest(unittest.TestCase):
    def test_a_header_is_read_out_of_bytes_built_here(self) -> None:
        # Arrange
        check = doctor.check_reading

        # Act
        one = check()

        # Assert
        self.assertTrue(one.ok, one.detail)

    def test_the_title_it_writes_is_the_width_the_reader_publishes(self) -> None:
        # Arrange
        image = doctor.synthetic_image()

        # Act
        found = mapper.read(image)

        # Assert
        self.assertEqual((len(doctor.TITLE), found.title), (21, doctor.TITLE.decode()))

    def test_an_image_the_reader_refuses_is_reported_as_what_it_said(self) -> None:
        # Arrange
        def empty() -> bytes:
            return b""

        # Act
        one = doctor.check_reading(empty)

        # Assert
        self.assertEqual((one.ok, one.detail), (False, "NoHeader: no header found in 0 bytes"))

    def test_and_a_title_that_comes_back_wrong_is_reported(self) -> None:
        # Arrange
        def wrong() -> bytes:
            rom = bytearray(doctor.synthetic_image())
            rom[0x7FC0] = ord("X")
            return bytes(rom)

        # Act
        one = doctor.check_reading(wrong)

        # Assert
        self.assertFalse(one.ok, one.detail)


class ExamineTest(unittest.TestCase):
    def test_the_examination_produces_findings(self) -> None:
        # Arrange
        examine = doctor.examine

        # Act
        found = examine()

        # Assert
        self.assertTrue(all(isinstance(one, doctor.Finding) for one in found))

    def test_it_looks_at_every_published_layout(self) -> None:
        # Arrange
        expected = set(doctor.PROBE)

        # Act
        named = {one.name for one in doctor.examine()}

        # Assert
        self.assertTrue(expected <= named, named)

    def test_and_at_the_library_last_because_that_is_the_answer(self) -> None:
        # Arrange
        examine = doctor.examine

        # Act
        found = examine()

        # Assert
        self.assertEqual(found[-1].name, "library")


class ReportTest(unittest.TestCase):
    def test_a_clean_examination_says_there_is_nothing_to_report(self) -> None:
        # Arrange
        found = [doctor.Finding("one", True, "fine")]

        # Act
        lines = doctor.report(found)

        # Assert
        self.assertEqual(lines[-1], "  1 checks, nothing to report")

    def test_and_a_dirty_one_counts_what_did_not_pass(self) -> None:
        # Arrange
        found = [doctor.Finding("one", True, "fine"), doctor.Finding("two", False, "not")]

        # Act
        lines = doctor.report(found)

        # Assert
        self.assertEqual(lines[-1], "  1 of 2 checks did not pass")


class MainTest(unittest.TestCase):
    def test_a_clean_machine_exits_zero(self) -> None:
        # Arrange
        found = [doctor.Finding("one", True, "fine")]

        # Act
        code = doctor.main((), lambda: found, lambda _: None)

        # Assert
        self.assertEqual(code, 0)

    def test_and_a_machine_with_a_finding_exits_one(self) -> None:
        # Arrange
        found = [doctor.Finding("one", False, "not")]

        # Act
        code = doctor.main((), lambda: found, lambda _: None)

        # Assert
        self.assertEqual(code, 1)

    def test_the_report_is_said_rather_than_returned(self) -> None:
        # Arrange
        said: list[str] = []

        # Act
        doctor.main((), lambda: [doctor.Finding("one", True, "fine")], said.append)

        # Assert
        self.assertTrue(any("nothing to report" in one for one in said))

    def test_it_runs_end_to_end_whatever_this_machine_holds(self) -> None:
        # Arrange
        said: list[str] = []

        # Act
        code = doctor.main((), doctor.examine, said.append)

        # Assert
        self.assertIn(code, (0, 1))
        self.assertGreaterEqual(len(said), len(doctor.examine()))


class PathTest(unittest.TestCase):
    def test_the_repository_is_put_on_the_path_when_it_is_not_already_there(self) -> None:
        # Arrange
        held = [one for one in sys.path if one != str(doctor.ROOT)]

        # Act
        with unittest.mock.patch.object(sys, "path", held):
            importlib.reload(doctor)

        # Assert
        self.assertIn(str(doctor.ROOT), held)

    def test_the_version_is_read_out_of_the_file_rather_than_imported(self) -> None:
        # Arrange
        text = (doctor.ROOT / "mapper" / "version.py").read_text()

        # Act
        found = re.search(r'VERSION[^"\']*"([^"]+)"', text)

        # Assert
        self.assertEqual(doctor.VERSION, found.group(1) if found else None)

    def test_a_version_file_naming_nothing_reads_as_unknown(self) -> None:
        # Arrange
        where = Path(tempfile.mkdtemp()) / "version.py"
        where.write_text("NOTHING = 1\n")

        # Act
        found = doctor.installed_version(where)

        # Assert
        self.assertEqual(found, "unknown")


class TheDoctorRunsWhereThePackageMightNotImportTest(unittest.TestCase):
    def test_a_root_that_is_not_on_the_path_is_put_there(self) -> None:
        # Arrange
        path: list[str] = []

        # Act
        added = doctor.reachable(Path("/somewhere"), path)

        # Assert
        self.assertEqual((added, path), (True, ["/somewhere"]))

    def test_a_root_already_on_the_path_is_left_alone(self) -> None:
        # Arrange
        path = ["/somewhere"]

        # Act
        added = doctor.reachable(Path("/somewhere"), path)

        # Assert
        self.assertEqual((added, path), (False, ["/somewhere"]))


class TheDoctorRunsAsTheReadmeSaysTest(unittest.TestCase):
    def test_running_it_as_a_file_from_elsewhere_prints_a_report_rather_than_a_traceback(
        self,
    ) -> None:
        # Arrange
        elsewhere = tempfile.mkdtemp()
        bare = {name: value for name, value in os.environ.items() if name != "PYTHONPATH"}

        # Act
        finished = subprocess.run(
            [sys.executable, str(SOURCE)],
            capture_output=True,
            text=True,
            cwd=elsewhere,
            env=bare,
            check=False,
        )

        # Assert
        self.assertIn(finished.returncode, (0, 1))
        self.assertNotIn("Traceback", finished.stderr)
        self.assertRegex(finished.stdout.splitlines()[-1], VERDICT)

    def test_the_readme_names_the_invocation_that_works(self) -> None:
        # Arrange
        readme = doctor.ROOT / "README.md"

        # Act
        said = readme.read_text()

        # Assert
        self.assertIn("python3 mapper/doctor.py", said)


if __name__ == "__main__":
    unittest.main()
