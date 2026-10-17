import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapper import doctor


def a_directory(names: tuple[str, ...] = ()) -> Path:
    where = Path(tempfile.mkdtemp())
    for name in names:
        (where / name).write_bytes(b"\x00" * 16)
    return where


def a_file(body: str) -> Path:
    where = Path(tempfile.mkdtemp()) / "held.json"
    where.write_text(body)
    return where


def refuse(*_: Any, **__: Any) -> Any:
    raise OSError("permission denied")


def absent() -> Path:
    return Path(tempfile.mkdtemp()) / "absent.json"


class ManifestTest(unittest.TestCase):
    def test_the_manifest_beside_the_package_names_cartridges(self) -> None:
        # Arrange
        check = doctor.check_manifest

        # Act
        one = check()

        # Assert
        self.assertTrue(one.ok, one.detail)

    def test_a_manifest_that_is_not_there_is_reported(self) -> None:
        # Arrange
        where = absent()

        # Act
        one = doctor.check_manifest(where)

        # Assert
        self.assertEqual((one.ok, one.detail.startswith("could not be read")), (False, True))

    def test_a_manifest_that_is_not_json_is_reported_differently(self) -> None:
        # Arrange
        where = a_file("{")

        # Act
        one = doctor.check_manifest(where)

        # Assert
        self.assertIn("not readable as JSON", one.detail)

    def test_a_manifest_naming_nothing_is_not_well(self) -> None:
        # Arrange
        where = a_file('{"cartridges": []}')

        # Act
        one = doctor.check_manifest(where)

        # Assert
        self.assertEqual((one.ok, one.detail), (False, "0 cartridges and 0 bad dumps named"))


class CorpusTest(unittest.TestCase):
    def test_the_corpus_beside_the_package_holds_cases(self) -> None:
        # Arrange
        check = doctor.check_corpus

        # Act
        one = check()

        # Assert
        self.assertTrue(one.ok, one.detail)

    def test_a_corpus_that_is_not_there_is_reported(self) -> None:
        # Arrange
        where = absent()

        # Act
        one = doctor.check_corpus(where)

        # Assert
        self.assertEqual((one.ok, one.detail.startswith("could not be read")), (False, True))

    def test_a_corpus_that_is_not_json_is_reported(self) -> None:
        # Arrange
        where = a_file("{")

        # Act
        one = doctor.check_corpus(where)

        # Assert
        self.assertIn("not readable as JSON", one.detail)

    def test_a_corpus_with_no_cases_is_not_well(self) -> None:
        # Arrange
        where = a_file('{"cases": []}')

        # Act
        one = doctor.check_corpus(where)

        # Assert
        self.assertEqual(
            (one.ok, one.detail), (False, "0 recorded cases, measured from not stated")
        )


class LookingTest(unittest.TestCase):
    def test_a_named_directory_is_reported_as_named(self) -> None:
        # Arrange
        environment = {doctor.DIRECTORY_VARIABLE: "/somewhere"}

        # Act
        found = doctor.check_looking(environment)

        # Assert
        self.assertEqual(found[0].detail, "set to /somewhere")

    def test_and_it_is_the_one_chosen_even_when_it_is_not_there(self) -> None:
        # Arrange
        environment = {doctor.DIRECTORY_VARIABLE: "/somewhere"}

        # Act
        found = doctor.check_looking(environment)

        # Assert
        self.assertEqual(found[-1].detail, "/somewhere")

    def test_an_unset_variable_says_the_places_are_tried_in_order(self) -> None:
        # Arrange
        environment: dict[str, str] = {}

        # Act
        found = doctor.check_looking(environment)

        # Assert
        self.assertIn("tried in order", found[0].detail)

    def test_and_the_chosen_place_is_one_of_the_places_looked_in(self) -> None:
        # Arrange
        environment: dict[str, str] = {}

        # Act
        found = doctor.check_looking(environment)

        # Assert
        self.assertIn(found[-1].detail, found[1].detail)

    def test_the_real_environment_is_read_when_none_is_given(self) -> None:
        # Arrange
        check = doctor.check_looking

        # Act
        found = check()

        # Assert
        self.assertEqual(len(found), 3)

    def test_the_places_are_tried_in_the_order_the_sweep_tries_them(self) -> None:
        # Arrange
        expected = f"{doctor.ALONGSIDE}, {doctor.DEFAULT_DIRECTORY}"

        # Act
        found = doctor.check_looking({})

        # Assert
        self.assertEqual(found[1].detail, expected)

    def test_the_default_is_chosen_when_no_place_exists(self) -> None:
        # Arrange
        held = Path(tempfile.mkdtemp()) / "absent"

        # Act
        with (
            unittest.mock.patch.object(doctor, "DEFAULT_DIRECTORY", held),
            unittest.mock.patch.object(doctor, "ALONGSIDE", held),
        ):
            found = doctor.check_looking({})

        # Assert
        self.assertEqual(found[-1].detail, str(held))


class LibraryTest(unittest.TestCase):
    def test_a_library_that_is_not_there_is_reported_as_absent_not_broken(self) -> None:
        # Arrange
        where = Path(tempfile.mkdtemp()) / "absent"

        # Act
        one = doctor.check_library(where)

        # Assert
        self.assertTrue(one.ok, one.detail)

    def test_and_says_the_check_against_cartridges_will_skip(self) -> None:
        # Arrange
        where = Path(tempfile.mkdtemp()) / "absent"

        # Act
        one = doctor.check_library(where)

        # Assert
        self.assertIn("skip rather than run", one.detail)

    def test_a_library_holding_images_counts_them(self) -> None:
        # Arrange
        where = a_directory(("a.sfc", "b.smc"))

        # Act
        one = doctor.check_library(where)

        # Assert
        self.assertEqual(one.detail, f"2 images at {where}")

    def test_and_is_well(self) -> None:
        # Arrange
        where = a_directory(("a.sfc",))

        # Act
        one = doctor.check_library(where)

        # Assert
        self.assertTrue(one.ok, one.detail)

    def test_a_directory_that_is_there_and_empty_is_not_well(self) -> None:
        # Arrange
        where = a_directory()

        # Act
        one = doctor.check_library(where)

        # Assert
        self.assertFalse(one.ok, one.detail)

    def test_the_directory_a_fresh_checkout_ships_empty_is_the_normal_state(self) -> None:
        # Arrange
        where = a_directory(("README.md",))

        # Act
        one = doctor.check_library(where, shipped=where)

        # Assert
        self.assertEqual((one.ok, "skip rather than run" in one.detail), (True, True))

    def test_because_that_is_what_a_run_over_nothing_looks_like(self) -> None:
        # Arrange
        where = a_directory(("notes.txt",))

        # Act
        one = doctor.check_library(where)

        # Assert
        self.assertIn("holds nothing", one.detail)

    def test_a_library_that_cannot_be_read_is_reported_as_what_it_said(self) -> None:
        # Arrange
        where = a_directory()

        # Act
        with unittest.mock.patch.object(Path, "rglob", refuse):
            one = doctor.check_library(where)

        # Assert
        self.assertEqual((one.ok, one.detail), (False, "could not be read: permission denied"))


if __name__ == "__main__":
    unittest.main()
