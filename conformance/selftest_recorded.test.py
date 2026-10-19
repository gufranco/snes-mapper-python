import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conformance import selftest, testcarts
from conformance.selftest_replay import failures

MEASURED: dict[str, Any] = testcarts.load(selftest.MEASURED)


def summary(measured: dict[str, Any]) -> tuple[Any, ...]:
    return (
        failures(measured),
        measured["registers"]["agreed"],
        measured["mirror"]["agreed"],
        measured["transfers"]["agreed"],
        measured["transfers"]["channels"][7]["countLanded"],
    )


class EachSelfTestReplaysAsRecordedTest(unittest.TestCase):
    def test_burn_in_rev_d(self) -> None:
        # Arrange
        measured = MEASURED["burn-in-rev-d"]

        # Act
        found = summary(measured)

        # Assert
        self.assertEqual(found, ([], 704, 6, 8, ["$4355"]))

    def test_snsp_aging_1_02(self) -> None:
        # Arrange
        measured = MEASURED["snsp-aging-1-02"]

        # Act
        found = summary(measured)

        # Assert
        self.assertEqual(found, ([], 704, 6, 8, ["$4355"]))

    def test_aging_1_00(self) -> None:
        # Arrange
        measured = MEASURED["aging-1-00"]

        # Act
        found = summary(measured)

        # Assert
        self.assertEqual(found, ([], 704, 6, 8, ["$4355"]))

    def test_control_deck_tester_rev_1(self) -> None:
        # Arrange
        measured = MEASURED["control-deck-tester-rev-1"]

        # Act
        found = summary(measured)

        # Assert
        self.assertEqual(found, ([], 704, 6, 8, ["$4355"]))

    def test_ntf_2_5_rev_a(self) -> None:
        # Arrange
        measured = MEASURED["ntf-2-5-rev-a"]

        # Act
        found = summary(measured)

        # Assert
        self.assertEqual(found, ([], 704, 6, 8, ["$4355"]))

    def test_test_program(self) -> None:
        # Arrange
        measured = MEASURED["test-program"]

        # Act
        found = summary(measured)

        # Assert
        self.assertEqual(found, ([], 704, 6, 8, ["$4355"]))


if __name__ == "__main__":
    unittest.main()
