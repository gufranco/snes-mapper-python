import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import mapper  # noqa: E402

VERSION_FILE = ROOT / "mapper" / "version.py"


def stamped() -> str:
    line = next(
        one for one in VERSION_FILE.read_text().splitlines() if one.startswith("VERSION = ")
    )
    return line.split('"')[1]


class VersionTest(unittest.TestCase):
    def test_the_version_is_three_numbers(self) -> None:
        # Arrange
        held = mapper.__version__

        # Act
        parts = held.split(".")

        # Assert
        self.assertEqual(len(parts), 3)
        self.assertTrue(all(part.isdigit() for part in parts))

    def test_the_package_reports_the_same_version(self) -> None:
        # Arrange
        held = stamped()

        # Act
        reported = mapper.__version__

        # Assert
        self.assertEqual(reported, held)


if __name__ == "__main__":
    unittest.main()
