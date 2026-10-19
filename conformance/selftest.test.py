import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from conformance import selftest, testcarts  # noqa: E402

MIRROR = bytes.fromhex("a955aa8d0010a220daabad0010c955aad047a9aa558d0010a200daabad0010c9aa55d01f")

AT = 0x100


def an_image(code: bytes = MIRROR) -> bytes:
    image = bytearray(0x1000)
    image[AT : AT + len(code)] = code
    return bytes(image)


def a_folder_holding(image: bytes) -> dict[str, str]:
    where = Path(tempfile.mkdtemp())
    (where / "a.sfc").write_bytes(image)
    return {"SNES_TEST_CARTRIDGE_DIR": str(where)}


def written(document: Any, name: str) -> Path:
    where = Path(tempfile.mkdtemp()) / name
    where.write_text(json.dumps(document))
    return where


def paths_for(image: bytes, measured: Any) -> dict[str, Path]:
    entry = {"id": "worked", "sha256": hashlib.sha256(image).hexdigest()}
    spec = {"tests": {"worked": {"mirror": {"start": f"{AT:#06x}", "stop": f"{AT + 36:#06x}"}}}}
    return {
        "record": written({"cartridges": [entry]}, "testroms.json"),
        "spec": written(spec, "selftest.json"),
        "measured": written(measured, "selftest_measured.json"),
    }


def quietly(*arguments: Any, **options: Any) -> tuple[int, str]:
    said = io.StringIO()
    with contextlib.redirect_stdout(said), contextlib.redirect_stderr(said):
        status = selftest.main(*arguments, **options)
    return status, said.getvalue()


AGREED = {
    "worked": {
        "mirror": {"stores": 4, "compares": 2, "agreed": 2, "outside": 0, "banks": ["$00", "$20"]}
    }
}


class TheRunnerTest(unittest.TestCase):
    def test_a_test_that_replays_as_recorded_passes(self) -> None:
        # Arrange
        image = an_image()

        # Act
        status, said = quietly(["selftest.py"], a_folder_holding(image), **paths_for(image, AGREED))

        # Assert
        self.assertEqual(
            (status, said), (0, "  1 of 1 self-test cartridges present\n  worked: agrees\n")
        )

    def test_a_replay_that_moved_from_the_record_fails(self) -> None:
        # Arrange
        image = an_image()

        # Act
        status, said = quietly(["selftest.py"], a_folder_holding(image), **paths_for(image, {}))

        # Assert
        self.assertEqual(
            (status, said.splitlines()[-1]),
            (1, "  FAILED worked: replayed differently from the record"),
        )

    def test_a_part_that_disagrees_fails_by_name(self) -> None:
        # Arrange
        image = an_image(MIRROR.replace(bytes.fromhex("a220daab"), bytes.fromhex("a240daab")))
        found = selftest.replayed(
            image, {"mirror": {"start": f"{AT:#06x}", "stop": f"{AT + 36:#06x}"}}
        )

        # Act
        status, said = quietly(
            ["selftest.py"], a_folder_holding(image), **paths_for(image, {"worked": found})
        )

        # Assert
        self.assertEqual((status, said.splitlines()[-1]), (1, "  FAILED worked: mirror disagrees"))

    def test_code_the_reader_cannot_follow_fails_with_the_reason(self) -> None:
        # Arrange
        image = an_image(bytes.fromhex("02") + MIRROR[1:])

        # Act
        status, said = quietly(["selftest.py"], a_folder_holding(image), **paths_for(image, AGREED))

        # Assert
        self.assertEqual(
            (status, said.splitlines()[-1]),
            (1, "  FAILED worked: opcode 02 at 0x100 is not one this reader knows"),
        )

    def test_record_writes_what_it_replayed(self) -> None:
        # Arrange
        image = an_image()
        out = Path(tempfile.mkdtemp()) / "out.json"

        # Act
        status, _ = quietly(
            ["selftest.py", "--record", str(out)], a_folder_holding(image), **paths_for(image, {})
        )

        # Assert
        self.assertEqual((status, json.loads(out.read_text())), (0, AGREED))

    def test_with_no_image_it_says_so_and_exits_two(self) -> None:
        # Arrange
        environment = {"SNES_TEST_CARTRIDGE_DIR": str(Path(tempfile.mkdtemp()))}

        # Act
        status, said = quietly(["selftest.py"], environment)

        # Assert
        self.assertEqual(
            (status, said),
            (
                2,
                "  no self-test cartridge present: set SNES_TEST_CARTRIDGE_DIR to a folder holding one\n",
            ),
        )

    def test_a_wrong_argument_is_refused(self) -> None:
        # Arrange
        argv = ["selftest.py", "--keep"]

        # Act
        status, said = quietly(argv)

        # Assert
        self.assertEqual((status, said), (2, "usage: selftest.py [--record out.json]\n"))


class TheShippedRecordTest(unittest.TestCase):
    def test_every_cartridge_the_spec_names_is_in_the_test_cartridge_record(self) -> None:
        # Arrange
        listed = set(testcarts.wanted(testcarts.load(selftest.RECORD)).values())

        # Act
        named = set(testcarts.load(selftest.SPEC)["tests"])

        # Assert
        self.assertEqual(named - listed, set())

    def test_every_cartridge_the_spec_names_was_measured(self) -> None:
        # Arrange
        named = set(testcarts.load(selftest.SPEC)["tests"])

        # Act
        measured = set(testcarts.load(selftest.MEASURED))

        # Assert
        self.assertEqual(measured, named)


if __name__ == "__main__":
    unittest.main()
