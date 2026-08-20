import json
import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapper import layout

HARDWARE = Path(__file__).resolve().parent / "hardware.json"

CARRIER = 3579545.4545454545
"""The NTSC colour carrier the console's master clock is six times."""


def declared() -> dict[str, Any]:
    held = json.loads(HARDWARE.read_text())
    assert isinstance(held, dict), f"{HARDWARE} does not hold an object"
    return held


def fact(name: str) -> dict[str, Any]:
    found = declared()["facts"][name]
    assert isinstance(found, dict), f"{name} is not recorded as a fact"
    return found


class DocumentTest(unittest.TestCase):
    """That the file names its source well enough for somebody to go and check."""

    def test_it_names_the_document_and_when_it_was_read(self) -> None:
        held = declared()["document"]

        for named in ("publisher", "title", "readOn", "readVia"):
            self.assertIn(named, held)

    def test_and_says_what_the_document_does_not_contain(self) -> None:
        self.assertIn("neither", declared()["document"]["note"])

    def test_the_authority_order_is_written_down(self) -> None:
        self.assertGreaterEqual(len(declared()["authority"]["order"]), 2)


class DerivationTest(unittest.TestCase):
    """That the two verified counts really do follow from the printed speeds.

    This is the point of recording a derivation rather than a number: the
    arithmetic is checkable, so a figure cannot quietly become folklore.
    """

    def test_the_master_clock_is_six_times_the_colour_carrier(self) -> None:
        self.assertEqual(round(CARRIER * 6), fact("masterClockHz")["value"])

    def test_a_fast_access_is_the_master_clock_over_the_high_bus_speed(self) -> None:
        master = fact("masterClockHz")["value"]

        self.assertEqual(round(master / 3.58e6), fact("fastAccessMasterCycles")["value"])

    def test_and_back_the_other_way_gives_the_speed_the_manual_prints(self) -> None:
        master = fact("masterClockHz")["value"]
        cycles = fact("fastAccessMasterCycles")["value"]

        self.assertEqual(round(master / cycles / 1e6, 2), 3.58)

    def test_a_slow_access_is_the_master_clock_over_the_normal_bus_speed(self) -> None:
        master = fact("masterClockHz")["value"]

        self.assertEqual(round(master / 2.68e6), fact("slowAccessMasterCycles")["value"])

    def test_and_back_the_other_way_gives_that_speed_too(self) -> None:
        master = fact("masterClockHz")["value"]
        cycles = fact("slowAccessMasterCycles")["value"]

        self.assertEqual(round(master / cycles / 1e6, 2), 2.68)


class ModelTest(unittest.TestCase):
    """That the module counts in the numbers this file records."""

    def test_the_fast_count_matches_the_documented_derivation(self) -> None:
        self.assertEqual(layout.FAST, fact("fastAccessMasterCycles")["value"])

    def test_the_slow_count_matches_it_too(self) -> None:
        self.assertEqual(layout.SLOW, fact("slowAccessMasterCycles")["value"])

    def test_the_extra_slow_count_matches_what_is_recorded_unverified(self) -> None:
        self.assertEqual(layout.XSLOW, fact("extraSlowAccessMasterCycles")["value"])

    def test_a_slow_access_costs_more_than_a_fast_one(self) -> None:
        self.assertGreater(layout.SLOW, layout.FAST)

    def test_and_an_extra_slow_one_costs_more_still(self) -> None:
        self.assertGreater(layout.XSLOW, layout.SLOW)


class HonestyTest(unittest.TestCase):
    """That the one figure with no document behind it says so."""

    def test_the_two_derived_counts_are_marked_verified(self) -> None:
        for name in ("fastAccessMasterCycles", "slowAccessMasterCycles"):
            self.assertTrue(fact(name)["verified"], name)

    def test_the_third_is_not(self) -> None:
        self.assertFalse(fact("extraSlowAccessMasterCycles")["verified"])

    def test_and_says_what_would_settle_it(self) -> None:
        self.assertIn("howToSettleIt", fact("extraSlowAccessMasterCycles"))

    def test_the_file_says_what_it_does_not_model(self) -> None:
        self.assertGreaterEqual(len(declared()["notCycleAccurate"]["doesNot"]), 2)


class ResolutionTest(unittest.TestCase):
    """That a resolved address is charged the count its region calls for."""

    def test_a_high_bank_rom_access_costs_the_fast_count_when_fast_is_asked_for(self) -> None:
        found = layout.resolve(layout.LOROM, 0x808000, fast=True)

        self.assertEqual(found.cycles, layout.FAST)

    def test_and_the_slow_count_when_it_is_not(self) -> None:
        found = layout.resolve(layout.LOROM, 0x808000, fast=False)

        self.assertEqual(found.cycles, layout.SLOW)

    def test_a_low_bank_rom_access_is_slow_whatever_was_asked_for(self) -> None:
        found = layout.resolve(layout.LOROM, 0x008000, fast=True)

        self.assertEqual(found.cycles, layout.SLOW)


if __name__ == "__main__":
    unittest.main()
