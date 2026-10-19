import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conformance import selftest_replay
from conformance.selftest_code import Unreadable

PATTERNS = ("00", "ff", "0f", "f0", "33", "cc", "aa", "55")

REGISTERS = "".join(f"a9{one}8543200082204082a566d0034c0000" for one in PATTERNS)

STORE_WALK = "a20043a00b009d0000e8e07b43f00e88d0f4e8e8e8e8e8a00b004c0000"

LOAD_WALK = "a20043a543a00b00bd0000c543d019e8e07b43f00e88d0f0e8e8e8e8e8a00b004c0000"

MIRROR = (
    "a955aa8d0010a95a558d0210a9aa5a8d0410"
    "a220daab"
    "ad0010c955aad047ad0210c95a55d03fad0410c9aa5ad037"
    "a9aa558d0010a9a5aa8d0210a955a58d0410"
    "a200daab"
    "ad0010c9aa55d01fad0210c9a5aad017ad0410c955a5d00f"
)

TO_VRAM = "a2558640a2098e0043a2188e0143a940008d0243a2008e0443a910008d0543a2018e0b42"

TO_RAM = (
    "a2818e4043a2398e4143a900008d4243a27f8e4443a910008d4543a2108e0b42a200bf00007fc95555d009e8e8e010"
)

STALE = (
    "a2818e7043a2398e7143a930008d7243a27f8e7443a910008d5543a2808e0b42a230bf00007fc90000d021e8e8e040"
)

AT = {"registers": 0x100, "store": 0x200, "load": 0x240, "mirror": 0x300, "transfers": 0x400}


def an_image(**pieces: str) -> bytes:
    image = bytearray(0x10000)
    chosen = {
        "registers": REGISTERS,
        "store": STORE_WALK,
        "load": LOAD_WALK,
        "mirror": MIRROR,
        "transfers": TO_VRAM + TO_RAM + STALE,
        **pieces,
    }
    for name, code in chosen.items():
        held = bytes.fromhex(code)
        image[AT[name] : AT[name] + len(held)] = held
    return bytes(image)


def part(name: str, code: str) -> dict[str, str]:
    return {"start": f"{AT[name]:#06x}", "stop": f"{AT[name] + len(bytes.fromhex(code)):#06x}"}


class TheRegisterTestTest(unittest.TestCase):
    def test_eight_patterns_through_eighty_eight_registers_all_read_back(self) -> None:
        # Arrange
        image = an_image()

        # Act
        found = selftest_replay.registers(image, part("registers", REGISTERS))

        # Assert
        self.assertEqual(
            found,
            {
                "patterns": 8,
                "registers": 88,
                "reads": 704,
                "agreed": 704,
                "first": "$4300",
                "last": "$437A",
            },
        )

    def test_a_read_walk_that_visits_other_registers_is_refused(self) -> None:
        # Arrange
        image = an_image(load=LOAD_WALK.replace("e07b43", "e07a43"))

        # Act
        attempt = lambda: selftest_replay.registers(image, part("registers", REGISTERS))  # noqa: E731

        # Assert
        self.assertRaisesRegex(Unreadable, "do not visit the same registers", attempt)

    def test_a_routine_that_is_not_in_the_program_is_refused(self) -> None:
        # Arrange
        code = REGISTERS.replace("200082", "200001")
        image = an_image(registers=code)

        # Act
        attempt = lambda: selftest_replay.registers(image, part("registers", code))  # noqa: E731

        # Assert
        self.assertRaisesRegex(Unreadable, "is not in the program", attempt)


class TheMirrorTestTest(unittest.TestCase):
    def test_words_written_through_one_low_bank_read_back_through_the_other(self) -> None:
        # Arrange
        image = an_image()

        # Act
        found = selftest_replay.mirror(image, part("mirror", MIRROR))

        # Assert
        self.assertEqual(
            found,
            {"stores": 12, "compares": 6, "agreed": 6, "outside": 0, "banks": ["$00", "$20"]},
        )

    def test_a_read_through_a_bank_with_no_work_ram_does_not_agree(self) -> None:
        # Arrange
        code = MIRROR.replace("a220daab", "a240daab")
        image = an_image(mirror=code)

        # Act
        found = selftest_replay.mirror(image, part("mirror", code))

        # Assert
        self.assertEqual((found["agreed"], found["outside"]), (0, 9))

    def test_a_read_of_a_cell_nothing_wrote_does_not_agree(self) -> None:
        # Arrange
        code = "ad0010c955aae010"
        image = an_image(mirror=code)

        # Act
        found = selftest_replay.mirror(image, part("mirror", code))

        # Assert
        self.assertEqual(
            found, {"stores": 0, "compares": 1, "agreed": 0, "outside": 0, "banks": ["$00"]}
        )


class TheTransferTestTest(unittest.TestCase):
    def test_each_channel_is_planned_as_the_cartridge_reads_it_back(self) -> None:
        # Arrange
        image = an_image()

        # Act
        found = selftest_replay.transfers(image, part("transfers", TO_VRAM + TO_RAM + STALE))

        # Assert
        self.assertEqual(
            found["channels"],
            [
                {
                    "channel": 0,
                    "toCpu": False,
                    "step": 0,
                    "destination": "$2118",
                    "length": 16,
                    "countLanded": [],
                    "agrees": True,
                },
                {
                    "channel": 4,
                    "toCpu": True,
                    "step": 1,
                    "destination": "$2139",
                    "length": 16,
                    "countLanded": [],
                    "agrees": True,
                },
                {
                    "channel": 7,
                    "toCpu": True,
                    "step": 1,
                    "destination": "$2139",
                    "length": None,
                    "countLanded": ["$4355"],
                    "agrees": True,
                },
            ],
        )

    def test_a_fixed_source_nothing_wrote_does_not_agree(self) -> None:
        # Arrange
        code = TO_VRAM.replace("a2558640", "a2558641")
        image = an_image(transfers=code)

        # Act
        found = selftest_replay.transfers(image, part("transfers", code))

        # Assert
        self.assertEqual(found, {"enables": 1, "agreed": 0, "channels": found["channels"]})

    def test_a_transfer_shorter_than_the_read_back_does_not_agree(self) -> None:
        # Arrange
        code = TO_RAM.replace("a910008d4543", "a908008d4543")
        image = an_image(transfers=code)

        # Act
        found = selftest_replay.transfers(image, part("transfers", code))

        # Assert
        self.assertEqual((found["agreed"], found["channels"][0]["length"]), (0, 8))

    def test_a_transfer_the_program_never_reads_back_does_not_agree(self) -> None:
        # Arrange
        code = TO_RAM[: TO_RAM.index("a200bf")]
        image = an_image(transfers=code)

        # Act
        found = selftest_replay.transfers(image, part("transfers", code))

        # Assert
        self.assertEqual((found["enables"], found["agreed"]), (1, 0))


class TheVerdictTest(unittest.TestCase):
    def test_a_test_that_agreed_everywhere_has_no_failure(self) -> None:
        # Arrange
        image = an_image()
        spec = {
            "registers": part("registers", REGISTERS),
            "mirror": part("mirror", MIRROR),
            "transfers": part("transfers", TO_VRAM + TO_RAM + STALE),
        }

        # Act
        failed = selftest_replay.failures(selftest_replay.replay(image, spec))

        # Assert
        self.assertEqual(failed, [])

    def test_each_disagreeing_part_is_named(self) -> None:
        # Arrange
        measured = {
            "registers": {"reads": 704, "agreed": 703},
            "mirror": {"compares": 6, "agreed": 6, "outside": 1},
            "transfers": {"enables": 8, "agreed": 7},
        }

        # Act
        failed = selftest_replay.failures(measured)

        # Assert
        self.assertEqual(failed, ["registers", "mirror", "transfers"])


if __name__ == "__main__":
    unittest.main()
