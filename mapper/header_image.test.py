import os
import sys
import unittest
from pathlib import Path
from typing import override

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mapper

LOW = 0x7FC0
STUB = 0x200


class CopierStubTest(unittest.TestCase):
    def test_a_whole_number_of_half_banks_carries_no_stub(self) -> None:
        # Arrange
        rom = bytes(0x20000)

        # Act
        found = mapper.has_copier_stub(rom)

        # Assert
        self.assertFalse(found)

    def test_the_same_length_plus_the_stub_does(self) -> None:
        # Arrange
        rom = bytes(0x20000 + STUB)

        # Act
        found = mapper.has_copier_stub(rom)

        # Assert
        self.assertTrue(found)

    def test_a_file_no_longer_than_the_stub_cannot_be_one(self) -> None:
        # Arrange
        rom = bytes(STUB)

        # Act
        found = mapper.has_copier_stub(rom)

        # Assert
        self.assertFalse(found)

    def test_a_length_of_no_recognised_shape_is_left_alone(self) -> None:
        # Arrange
        rom = bytes(1234)

        # Act
        found = mapper.has_copier_stub(rom)

        # Assert
        self.assertFalse(found)

    def test_the_length_form_answers_the_same_question(self) -> None:
        # Arrange
        sizes = (0, 0x200, 0x8000, 0x8200, 0x20000, 0x20200, 0x100200, 0x100000, 1234)

        # Act
        found = [mapper.stub_by_length(size) for size in sizes]

        # Assert
        self.assertEqual(found, [False, False, False, True, False, True, True, False, False])


class HandedInTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        held = os.environ.get("SNES_CARTRIDGE_DIR")
        self.addCleanup(os.environ.__setitem__, "SNES_CARTRIDGE_DIR", held or "")
        os.environ["SNES_CARTRIDGE_DIR"] = "/nowhere-at-all"

    def built(self) -> bytes:
        made = bytearray(0x80000)
        made[0x7FC0 : 0x7FC0 + len(b"HANDED IN DIRECTLY")] = b"HANDED IN DIRECTLY"
        made[0x7FD5], made[0x7FD6], made[0x7FD7] = 0x20, 0x00, 0x09
        return bytes(made)

    def test_a_header_is_read_out_of_bytes_alone(self) -> None:
        # Arrange
        rom = self.built()

        # Act
        found = mapper.read(rom)

        # Assert
        self.assertEqual(found.title, "HANDED IN DIRECTLY")

    def test_a_candidate_place_is_scored_on_bytes_alone(self) -> None:
        # Arrange
        rom = self.built()

        # Act
        found = mapper.score(rom, LOW)

        # Assert
        self.assertEqual(found, 2)

    def test_only_the_doctor_names_that_variable_beside_the_reader(self) -> None:
        # Arrange
        package = Path(__file__).resolve().parent

        # Act
        naming = sorted(
            one.name for one in package.glob("*.py") if "SNES_CARTRIDGE_DIR" in one.read_text()
        )

        # Assert
        self.assertEqual(naming, sorted(["doctor.py", Path(__file__).name]))


if __name__ == "__main__":
    unittest.main()
