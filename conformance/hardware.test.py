import json
import sys
import unittest
from pathlib import Path
from typing import Any, override

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

    def source(self) -> Any:
        return declared()["documents"]["developmentManual"]

    def test_it_names_the_document_and_when_it_was_read(self) -> None:
        held = self.source()

        for named in ("publisher", "title", "readOn", "readVia", "file"):
            self.assertIn(named, held)

    def test_and_says_what_the_document_does_not_contain(self) -> None:
        self.assertIn("neither", self.source()["note"])

    def test_every_figure_taken_from_it_says_so(self) -> None:
        """A figure the manual printed, and one derived from those, cite the key.

        The extra-slow count does not, and must not: no document supports it.
        """
        facts = declared()["facts"]
        citing = sorted(name for name, one in facts.items() if one.get("document"))

        self.assertEqual(
            citing,
            ["busSpeeds", "fastAccessMasterCycles", "slowAccessMasterCycles"],
        )

    def test_and_the_one_no_document_supports_does_not(self) -> None:
        held = declared()["facts"]["extraSlowAccessMasterCycles"]

        self.assertNotIn("document", held)
        self.assertFalse(held["verified"])

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


class DivergenceTest(unittest.TestCase):
    """The standing of each fact, kept in the file the family reads for that.

    `hardware.json` already marks the unverified figure. This checks that the
    same thing is said in the place a reader of any sibling repository will look
    for it, so the two cannot part company.
    """

    @override
    def setUp(self) -> None:
        here = Path(__file__).resolve().parent
        self.entries: list[dict[str, Any]] = json.loads((here / "divergences.json").read_text())[
            "divergences"
        ]

    def test_each_entry_says_which_source_the_package_follows(self) -> None:
        allowed = {"document", "reference", "neither"}

        self.assertEqual({entry["packageFollows"] for entry in self.entries} - allowed, set())

    def test_each_entry_says_what_would_settle_it(self) -> None:
        missing = [entry["id"] for entry in self.entries if not entry.get("wouldSettleIt")]

        self.assertEqual(missing, [])

    def test_the_unverified_access_count_is_named_here_too(self) -> None:
        named = {entry["id"] for entry in self.entries}

        self.assertIn("extra-slow-access-is-unverified", named)

    def test_and_it_agrees_with_the_mark_on_the_fact_itself(self) -> None:
        entry = next(
            item for item in self.entries if item["id"] == "extra-slow-access-is-unverified"
        )

        self.assertEqual(
            (
                entry["packageFollows"],
                declared()["facts"]["extraSlowAccessMasterCycles"]["verified"],
            ),
            ("reference", False),
        )

    def test_the_master_clock_not_coming_from_the_manual_is_named(self) -> None:
        named = {entry["id"] for entry in self.entries}

        self.assertIn("the-master-clock-is-not-from-the-manual", named)


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
