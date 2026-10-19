import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conformance import selftest_code
from conformance.selftest_code import Event, Unreadable, Walk

MIRROR = bytes.fromhex("a955aa8d0010a220daabad0010c955aad047a200daaba2ff")

TRANSFER = bytes.fromhex(
    "a255"
    "8640"
    "a209"
    "8e0043"
    "a91000"
    "8d0543"
    "a201"
    "8e0b42"
    "a200"
    "bf00007f"
    "c95555"
    "e8e8"
    "e010"
    "ca"
    "f000"
    "8000"
    "4c0000"
    "209988"
    "e220"
    "a5ff"
    "8543"
    "640e"
    "9c0010"
    "a0"
    "07"
    "c8"
    "88"
)

STORE_WALK = bytes.fromhex("a20043a00b009d0000e8e07b43f00e88d0f4e8e8e8e8e8a00b004c0000")

LOAD_WALK = bytes.fromhex("a20043a543a00b00bd0000c543d019e8e07b43f00e88d0f0e8e8e8e8e8a00b004c0000")


class TheReaderTest(unittest.TestCase):
    def test_a_word_store_is_two_byte_stores_through_the_data_bank(self) -> None:
        # Arrange
        code = MIRROR

        # Act
        events = selftest_code.read_code(code, 0, 6, m16=True, x16=False)

        # Assert
        self.assertEqual(
            events, [Event("store", 0x001000, 0x55, 1), Event("store", 0x001001, 0xAA, 1)]
        )

    def test_a_bank_pulled_from_the_stack_moves_the_next_load(self) -> None:
        # Arrange
        code = MIRROR

        # Act
        events = selftest_code.read_code(code, 0, len(code) - 2, m16=True, x16=False)

        # Assert
        self.assertEqual(
            events[2:], [Event("load", 0x201000, 0, 2), Event("compare", 0, 0xAA55, 2)]
        )

    def test_every_instruction_a_transfer_test_uses_is_read(self) -> None:
        # Arrange
        code = TRANSFER

        # Act
        events = selftest_code.read_code(code, 0, len(code), m16=True, x16=False)

        # Assert
        self.assertEqual(
            events,
            [
                Event("store", 0x000040, 0x55, 1),
                Event("store", 0x004300, 0x09, 1),
                Event("store", 0x004305, 0x10, 1),
                Event("store", 0x004306, 0x00, 1),
                Event("store", 0x00420B, 0x01, 1),
                Event("load", 0x7F0000, 0, 2),
                Event("compare", 0, 0x5555, 2),
                Event("bound", 0, 0x10, 1),
                Event("call", 0x008899, 0, 0),
                Event("load", 0x0000FF, 0, 1),
                Event("store", 0x000043, 0x10, 1),
                Event("store", 0x00000E, 0x00, 1),
                Event("store", 0x001000, 0x00, 1),
            ],
        )

    def test_rep_widens_the_accumulator_and_the_index(self) -> None:
        # Arrange
        code = bytes.fromhex("c230a91234a2abcd8e0010")

        # Act
        events = selftest_code.read_code(code, 0, len(code), m16=False, x16=False)

        # Assert
        self.assertEqual(
            events, [Event("store", 0x001000, 0xAB, 1), Event("store", 0x001001, 0xCD, 1)]
        )

    def test_an_indexed_long_load_carries_the_index_it_was_taken_at(self) -> None:
        # Arrange
        code = bytes.fromhex("a204e8bf10007f")

        # Act
        events = selftest_code.read_code(code, 0, len(code), m16=False, x16=False)

        # Assert
        self.assertEqual(events, [Event("load", 0x7F0015, 5, 1)])

    def test_a_decrement_wraps_inside_the_index_width(self) -> None:
        # Arrange
        code = bytes.fromhex("a200cabf00007f")

        # Act
        events = selftest_code.read_code(code, 0, len(code), m16=False, x16=False)

        # Assert
        self.assertEqual(events, [Event("load", 0x7F00FF, 0xFF, 1)])

    def test_an_opcode_it_does_not_know_is_refused_by_offset(self) -> None:
        # Arrange
        code = bytes.fromhex("a9ff02")

        # Act
        attempt = lambda: selftest_code.read_code(code, 0, 3, m16=False, x16=False)  # noqa: E731

        # Assert
        self.assertRaisesRegex(Unreadable, "opcode 02 at 0x2", attempt)

    def test_an_instruction_cut_off_by_the_image_is_refused(self) -> None:
        # Arrange
        code = bytes.fromhex("a9")

        # Act
        attempt = lambda: selftest_code.read_code(code, 0, 1, m16=True, x16=False)  # noqa: E731

        # Assert
        self.assertRaisesRegex(Unreadable, "runs past the image", attempt)

    def test_a_bank_pulled_from_an_empty_stack_is_refused(self) -> None:
        # Arrange
        code = bytes.fromhex("ab")

        # Act
        attempt = lambda: selftest_code.read_code(code, 0, 1, m16=True, x16=False)  # noqa: E731

        # Assert
        self.assertRaisesRegex(Unreadable, "pulls a bank nothing pushed", attempt)


class TheWalkTest(unittest.TestCase):
    def test_a_store_walk_is_read_for_its_four_numbers(self) -> None:
        # Arrange
        code = STORE_WALK

        # Act
        walk = selftest_code.register_walk(code, 0)

        # Assert
        self.assertEqual(walk, Walk(0x4300, 11, 5, 0x437B, "store"))

    def test_a_load_walk_is_read_the_same_way(self) -> None:
        # Arrange
        code = LOAD_WALK

        # Act
        walk = selftest_code.register_walk(code, 0)

        # Assert
        self.assertEqual(walk, Walk(0x4300, 11, 5, 0x437B, "load"))

    def test_the_absolute_forms_read_like_the_direct_page_forms(self) -> None:
        # Arrange
        code = bytes.fromhex(
            "a20043ad4300a00b00bd0000cd4300d01ae8e07b43f00e88d0efe8e8e8e8e8a00b004c"
        )

        # Act
        walk = selftest_code.register_walk(code, 0)

        # Assert
        self.assertEqual(walk, Walk(0x4300, 11, 5, 0x437B, "load"))

    def test_a_walk_with_an_unknown_instruction_is_refused(self) -> None:
        # Arrange
        code = bytes.fromhex("a2004302")

        # Act
        attempt = lambda: selftest_code.register_walk(code, 0)  # noqa: E731

        # Assert
        self.assertRaisesRegex(Unreadable, "opcode 02 at 0x3", attempt)

    def test_a_walk_missing_a_number_is_refused(self) -> None:
        # Arrange
        code = bytes.fromhex("a200434c")

        # Act
        attempt = lambda: selftest_code.register_walk(code, 0)  # noqa: E731

        # Assert
        self.assertRaisesRegex(Unreadable, "not a register walk", attempt)

    def test_a_walk_that_runs_off_the_image_is_refused(self) -> None:
        # Arrange
        code = bytes.fromhex("a20043e8")

        # Act
        attempt = lambda: selftest_code.register_walk(code, 0)  # noqa: E731

        # Assert
        self.assertRaisesRegex(Unreadable, "runs past the image", attempt)

    def test_the_walk_visits_eleven_registers_of_each_of_eight_channels(self) -> None:
        # Arrange
        walk = Walk(0x4300, 11, 5, 0x437B, "store")

        # Act
        visited = selftest_code.addresses(walk)

        # Assert
        self.assertEqual(
            visited, [0x4300 | (channel << 4) | low for channel in range(8) for low in range(11)]
        )

    def test_a_walk_that_never_reaches_its_end_stops_at_the_bound(self) -> None:
        # Arrange
        walk = Walk(0x4300, 1, 0, 0x4300, "store")

        # Act
        visited = selftest_code.addresses(walk)

        # Assert
        self.assertEqual(len(visited), 0x10000)


if __name__ == "__main__":
    unittest.main()
