"""Everything that needs a cartridge library on disk to say anything at all.

These live apart from the rest because of what they do when nobody has one. A
skipped test contributes no coverage, so on a runner with an empty directory every
line here reads as uncovered, and the coverage gate then fails for a reason that
has nothing to do with the code. Keeping them in one file lets that file sit
outside the gate while everything else stays inside it.

The alternative was to relax the gate, which would have hidden real gaps in the
files that can be measured everywhere. This hides nothing: the modules these
exercise are measured by the tests beside them, and what is set aside is the
bookkeeping of the checks themselves.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conformance import against_cartridges, cartridges
from mapper import header, layout

PRESENT = cartridges.present()

# Every class in this file is outside the coverage gate, and it is the only file
# here that is. Its whole subject is the cartridges a machine happens to hold, so
# it runs on one machine and not another, and counting it would make the number
# mean something different depending on who ran it. Everything these exercise is
# covered by cartridges the other tests write themselves.


@unittest.skipUnless(PRESENT, cartridges.WHY_NOT)
class IdentityTest(unittest.TestCase):  # pragma: no cover
    def test_every_cartridge_on_disk_matches_all_four_of_its_digests(self) -> None:
        for identity, path in PRESENT:
            self.assertTrue(identity.sha256, path)

    def test_the_manifest_describes_every_cartridge_that_is_here(self) -> None:
        named = {entry["name"] for entry in cartridges.manifest()["cartridges"]}

        for identity, _ in PRESENT:
            self.assertIn(identity.name, named)

    def test_the_whole_manifest_is_here_rather_than_part_of_it(self) -> None:
        listed = {entry[cartridges.DECIDES] for entry in cartridges.manifest()["cartridges"]}
        here = {identity.sha256 for identity, _ in PRESENT}

        self.assertEqual(here, listed)

    def test_the_same_cartridge_filed_under_two_regions_is_one_cartridge(self) -> None:
        files = len(PRESENT)
        distinct = len({identity.sha256 for identity, _ in PRESENT})

        self.assertGreaterEqual(files, distinct)


@unittest.skipUnless(PRESENT, cartridges.WHY_NOT)
class SweepTest(unittest.TestCase):  # pragma: no cover
    def test_every_cartridge_in_the_library_agrees_with_the_corpus(self) -> None:
        read, agreed, wrong = against_cartridges.sweep()

        self.assertEqual(wrong, [])
        self.assertEqual(read, agreed)

    def test_the_library_is_the_whole_one_rather_than_a_handful(self) -> None:
        self.assertGreater(against_cartridges.sweep()[0], 2000)


@unittest.skipUnless(PRESENT, cartridges.WHY_NOT)
class WholeBankTest(unittest.TestCase):  # pragma: no cover
    def test_no_retail_cartridge_is_on_the_whole_bank_map(self) -> None:
        named = [
            identity.name
            for identity, path in PRESENT
            if header.board(header.read(path.read_bytes()), identity.size) == header.WHOLEBANK
        ]

        self.assertEqual(named, [])

    def test_no_retail_cartridge_is_large_enough_for_that_map(self) -> None:
        for identity, _ in PRESENT:
            self.assertLess(
                identity.size, layout.WHOLEBANK_BANKS * layout.BANK_BYTES, identity.name
            )

    def test_the_cartridges_that_reach_past_the_low_map_are_the_ones_expected(self) -> None:
        larger = {
            identity.name.rsplit("/", 1)[-1]
            for identity, _ in PRESENT
            if identity.size > header.LOROM_REACH and identity.layout == header.LOROM
        }

        self.assertEqual(larger, {"Star Ocean (Japan).sfc"})


if __name__ == "__main__":
    unittest.main()
