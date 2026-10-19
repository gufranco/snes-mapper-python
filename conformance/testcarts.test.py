import contextlib
import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from conformance import testcarts  # noqa: E402

READINGS: dict[str, Any] = testcarts.load(testcarts.READINGS)

HEADER = 0x7FC0

RESET = 0x7FFC


def a_cartridge(reset: int = 0x8000, size: int = 0x80000) -> bytes:
    image = bytearray(size)
    image[HEADER : HEADER + 21] = b"WORKED EXAMPLE       "
    image[HEADER + 0x15] = 0x20
    image[HEADER + 0x17] = 0x09
    image[HEADER + 0x1C : HEADER + 0x20] = b"\x00\x00\xff\xff"
    image[RESET : RESET + 2] = bytes((reset & 0xFF, reset >> 8))
    return bytes(image)


def a_folder_holding(files: dict[str, bytes]) -> Path:
    where = Path(tempfile.mkdtemp())
    for name, blob in files.items():
        (where / name).write_bytes(blob)
    return where


def a_record_naming(blob: bytes, name: str = "worked") -> Path:
    where = Path(tempfile.mkdtemp()) / "testroms.json"
    entry = {"id": name, "sha256": hashlib.sha256(blob).hexdigest()}
    where.write_text(json.dumps({"cartridges": [entry]}))
    return where


def readings_holding(found: dict[str, Any]) -> Path:
    where = Path(tempfile.mkdtemp()) / "testcarts.json"
    where.write_text(json.dumps(found))
    return where


def holding(image: bytes) -> dict[str, str]:
    return {"SNES_TEST_CARTRIDGE_DIR": str(a_folder_holding({"a.sfc": image}))}


def quietly(*arguments: Any, **options: Any) -> tuple[int, str]:
    said = io.StringIO()
    with contextlib.redirect_stdout(said), contextlib.redirect_stderr(said):
        status = testcarts.main(*arguments, **options)
    return status, said.getvalue()


class EachTestCartridgeMapsAsRecordedTest(unittest.TestCase):
    def test_240p_test_suite_ntsc(self) -> None:
        # Arrange
        recorded = READINGS["240p-test-suite-ntsc"]

        # Act
        landed = testcarts.landing(recorded)

        # Assert
        self.assertEqual(
            (recorded["layout"], recorded["reset"], landed.region, landed.offset),
            ("lorom", 0x80B7, "rom", 0x00B7),
        )

    def test_240p_test_suite_pal(self) -> None:
        # Arrange
        recorded = READINGS["240p-test-suite-pal"]

        # Act
        landed = testcarts.landing(recorded)

        # Assert
        self.assertEqual(
            (recorded["layout"], recorded["reset"], landed.region, landed.offset),
            ("lorom", 0x80B7, "rom", 0x00B7),
        )

    def test_burn_in_rev_d(self) -> None:
        # Arrange
        recorded = READINGS["burn-in-rev-d"]

        # Act
        account = testcarts.account(recorded)

        # Assert
        self.assertEqual((account, recorded["layout"]), ("no header", None))

    def test_campus_challenge_92_menu(self) -> None:
        # Arrange
        recorded = READINGS["campus-challenge-92-menu"]

        # Act
        account = testcarts.account(recorded)

        # Assert
        self.assertEqual((account, recorded["layout"]), ("no header", None))

    def test_controller_test_cassette(self) -> None:
        # Arrange
        recorded = READINGS["controller-test-cassette"]

        # Act
        account = testcarts.account(recorded)

        # Assert
        self.assertEqual((account, recorded["layout"]), ("no header", None))

    def test_dsp1_tech_demo(self) -> None:
        # Arrange
        recorded = READINGS["dsp1-tech-demo"]

        # Act
        account = testcarts.account(recorded)

        # Assert
        self.assertEqual((account, recorded["layout"]), ("no header", None))

    def test_emudetect_v21(self) -> None:
        # Arrange
        recorded = READINGS["emudetect-v21"]

        # Act
        landed = testcarts.landing(recorded)

        # Assert
        self.assertEqual(
            (recorded["layout"], recorded["reset"], landed.region, landed.offset),
            ("lorom", 0xF000, "rom", 0x7000),
        )

    def test_evoke_2010_logo_zoomer(self) -> None:
        # Arrange
        recorded = READINGS["evoke-2010-logo-zoomer"]

        # Act
        landed = testcarts.landing(recorded)

        # Assert
        self.assertEqual(
            (recorded["layout"], recorded["reset"], landed.region, landed.offset),
            ("sa1", 0x801F, "rom", 0x001F),
        )

    def test_hd_retrovision_1_4(self) -> None:
        # Arrange
        recorded = READINGS["hd-retrovision-1-4"]

        # Act
        landed = testcarts.landing(recorded)

        # Assert
        self.assertEqual(
            (recorded["layout"], recorded["reset"], landed.region, landed.offset),
            ("lorom", 0x810B, "rom", 0x010B),
        )

    def test_ntf_2_5_rev_a(self) -> None:
        # Arrange
        recorded = READINGS["ntf-2-5-rev-a"]

        # Act
        account = testcarts.account(recorded)

        # Assert
        self.assertEqual((account, recorded["layout"]), ("no header", None))

    def test_sa1_3d_demo(self) -> None:
        # Arrange
        recorded = READINGS["sa1-3d-demo"]

        # Act
        landed = testcarts.landing(recorded)

        # Assert
        self.assertEqual(
            (recorded["layout"], recorded["reset"], landed.region, landed.offset),
            ("sa1", 0x801F, "rom", 0x001F),
        )

    def test_sa1_speed_test_5_1(self) -> None:
        # Arrange
        recorded = READINGS["sa1-speed-test-5-1"]

        # Act
        landed = testcarts.landing(recorded)

        # Assert
        self.assertEqual(
            (recorded["layout"], recorded["reset"], landed.region, landed.offset),
            ("sa1", 0x8000, "rom", 0x0000),
        )

    def test_sa1_demonstration(self) -> None:
        # Arrange
        recorded = READINGS["sa1-demonstration"]

        # Act
        account = testcarts.account(recorded)

        # Assert
        self.assertEqual((account, recorded["layout"]), ("no header", None))

    def test_sa1_demonstration_header_fix(self) -> None:
        # Arrange
        recorded = READINGS["sa1-demonstration-header-fix"]

        # Act
        landed = testcarts.landing(recorded)

        # Assert
        self.assertEqual(
            (recorded["layout"], recorded["reset"], landed.region, landed.offset),
            ("sa1", 0xFF00, "rom", 0x7F00),
        )

    def test_test_program(self) -> None:
        # Arrange
        recorded = READINGS["test-program"]

        # Act
        account = testcarts.account(recorded)

        # Assert
        self.assertEqual((account, recorded["layout"]), ("no header", None))

    def test_snsp_aging_1_02(self) -> None:
        # Arrange
        recorded = READINGS["snsp-aging-1-02"]

        # Act
        account = testcarts.account(recorded)

        # Assert
        self.assertEqual((account, recorded["layout"]), ("no header", None))

    def test_aging_1_00(self) -> None:
        # Arrange
        recorded = READINGS["aging-1-00"]

        # Act
        account = testcarts.account(recorded)

        # Assert
        self.assertEqual((account, recorded["layout"]), ("no header", None))

    def test_control_deck_tester_rev_1(self) -> None:
        # Arrange
        recorded = READINGS["control-deck-tester-rev-1"]

        # Act
        account = testcarts.account(recorded)

        # Assert
        self.assertEqual((account, recorded["layout"]), ("no header", None))


class TheRecordTest(unittest.TestCase):
    def test_every_listed_cartridge_has_a_reading(self) -> None:
        # Arrange
        listed = testcarts.wanted(testcarts.load(testcarts.RECORD))

        # Act
        read = sorted(READINGS)

        # Assert
        self.assertEqual(read, sorted(listed.values()))

    def test_the_readings_carry_no_title(self) -> None:
        # Arrange
        text = testcarts.READINGS.read_text()

        # Act
        titled = "title" in text

        # Assert
        self.assertIs(titled, False)


class TheReaderTest(unittest.TestCase):
    def test_a_reset_vector_into_the_program_is_mapped(self) -> None:
        # Arrange
        image = a_cartridge(reset=0x8123)

        # Act
        found = testcarts.reading(image)

        # Assert
        self.assertEqual(
            found,
            {
                "size": 0x80000,
                "layout": "lorom",
                "fast": False,
                "banks": None,
                "shift": 0,
                "reset": 0x8123,
                "account": "mapped",
            },
        )

    def test_a_reset_vector_into_the_registers_is_named(self) -> None:
        # Arrange
        image = a_cartridge(reset=0x2100)

        # Act
        found = testcarts.reading(image)

        # Assert
        self.assertEqual(found["account"], "reset outside the program")

    def test_an_image_with_no_header_is_named(self) -> None:
        # Arrange
        image = bytes(0x20000)

        # Act
        found = testcarts.reading(image)

        # Assert
        self.assertEqual(found, {"size": 0x20000, "layout": None, "account": "no header"})

    def test_a_copier_stub_moves_the_vector_with_the_header(self) -> None:
        # Arrange
        image = bytes(0x200) + a_cartridge(reset=0x8040)

        # Act
        found = testcarts.reading(image)

        # Assert
        self.assertEqual((found["shift"], found["reset"]), (0x200, 0x8040))

    def test_the_whole_bank_map_carries_its_bank_count(self) -> None:
        # Arrange
        image = a_cartridge(reset=0x8000, size=0xC00000)

        # Act
        found = testcarts.reading(image)

        # Assert
        self.assertEqual(
            (found["layout"], found["banks"], found["account"]), ("wholebank", 0xC0, "mapped")
        )


class TheFolderTest(unittest.TestCase):
    def test_the_variable_names_the_folder(self) -> None:
        # Arrange
        environment = {"SNES_TEST_CARTRIDGE_DIR": "/somewhere"}

        # Act
        where = testcarts.directory(environment)

        # Assert
        self.assertEqual(where, Path("/somewhere"))

    def test_with_no_variable_the_library_alongside_is_read(self) -> None:
        # Arrange
        environment = {"SNES_TEST_CARTRIDGE_DIR": " "}

        # Act
        where = testcarts.directory(environment)

        # Assert
        self.assertEqual(where, ROOT.parent / "snes-roms" / "5 Tools & Service Test Carts")

    def test_the_process_environment_is_read_when_none_is_given(self) -> None:
        # Arrange
        expected = testcarts.directory(dict(os.environ))

        # Act
        where = testcarts.directory()

        # Assert
        self.assertEqual(where, expected)

    def test_only_listed_images_are_yielded(self) -> None:
        # Arrange
        image = a_cartridge()
        where = a_folder_holding({"a.sfc": image, "b.sfc": bytes(16), "c.txt": image})

        # Act
        found = list(testcarts.present(where, {hashlib.sha256(image).hexdigest(): "worked"}))

        # Assert
        self.assertEqual(found, [("worked", image)])

    def test_a_missing_folder_yields_nothing(self) -> None:
        # Arrange
        where = Path(tempfile.mkdtemp()) / "gone"

        # Act
        found = list(testcarts.present(where, {}))

        # Assert
        self.assertEqual(found, [])


class TheRunnerTest(unittest.TestCase):
    def test_with_no_image_it_says_so_and_exits_two(self) -> None:
        # Arrange
        environment = {"SNES_TEST_CARTRIDGE_DIR": str(Path(tempfile.mkdtemp()))}

        # Act
        status, said = quietly(["testcarts.py"], environment)

        # Assert
        self.assertEqual(
            (status, said),
            (
                2,
                "  no test cartridge present: set SNES_TEST_CARTRIDGE_DIR to a folder holding one\n",
            ),
        )

    def test_a_reading_that_matches_the_record_passes(self) -> None:
        # Arrange
        image = a_cartridge()
        readings = readings_holding({"worked": testcarts.reading(image)})

        # Act
        status, said = quietly(["testcarts.py"], holding(image), a_record_naming(image), readings)

        # Assert
        self.assertEqual(
            (status, said), (0, "  1 of 1 test cartridges present\n  worked: mapped\n")
        )

    def test_a_reading_that_moved_fails(self) -> None:
        # Arrange
        image = a_cartridge()

        # Act
        status, said = quietly(
            ["testcarts.py"], holding(image), a_record_naming(image), readings_holding({})
        )

        # Assert
        self.assertEqual(
            (status, said.splitlines()[-1]),
            (1, "  FAILED worked: read differently from the record"),
        )

    def test_a_reading_nobody_accounts_for_fails(self) -> None:
        # Arrange
        image = a_cartridge(reset=0x2100)
        readings = readings_holding({"worked": testcarts.reading(image)})

        # Act
        status, said = quietly(["testcarts.py"], holding(image), a_record_naming(image), readings)

        # Assert
        self.assertEqual(
            (status, said.splitlines()[-1]),
            (1, "  FAILED worked: reset outside the program, not accounted for"),
        )

    def test_record_writes_what_it_read(self) -> None:
        # Arrange
        image = a_cartridge()
        out = Path(tempfile.mkdtemp()) / "out.json"

        # Act
        status, _ = quietly(
            ["testcarts.py", "--record", str(out)], holding(image), a_record_naming(image)
        )

        # Assert
        self.assertEqual(
            (status, json.loads(out.read_text())), (0, {"worked": testcarts.reading(image)})
        )

    def test_a_wrong_argument_is_refused(self) -> None:
        # Arrange
        argv = ["testcarts.py", "--keep", "out.json"]

        # Act
        status, said = quietly(argv)

        # Assert
        self.assertEqual((status, said), (2, "usage: testcarts.py [--record out.json]\n"))

    def test_a_lone_argument_is_refused(self) -> None:
        # Arrange
        argv = ["testcarts.py", "--record"]

        # Act
        status, _ = quietly(argv)

        # Assert
        self.assertEqual(status, 2)


if __name__ == "__main__":
    unittest.main()
