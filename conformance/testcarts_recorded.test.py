import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from conformance import testcarts  # noqa: E402

READINGS: dict[str, Any] = testcarts.load(testcarts.READINGS)


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


if __name__ == "__main__":
    unittest.main()
