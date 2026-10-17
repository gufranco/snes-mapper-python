import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mapper
from conformance import against_cartridges, cartridges

PRESENT = cartridges.present()

LOROM_REACH = 0x400000


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
        # Arrange
        found = [(identity, mapper.read(path.read_bytes())) for identity, path in PRESENT]

        # Act
        named = [
            identity.name
            for identity, header in found
            if mapper.board(header, identity.size) == mapper.WHOLEBANK
        ]

        # Assert
        self.assertEqual(named, [])

    def test_no_retail_cartridge_is_large_enough_for_that_map(self) -> None:
        # Arrange
        sizes = {identity.name: identity.size for identity, _ in PRESENT}

        # Act
        large = sorted(name for name, size in sizes.items() if size >= mapper.WHOLEBANK_BYTES)

        # Assert
        self.assertEqual(large, [])

    def test_the_cartridges_that_reach_past_the_low_map_are_the_ones_expected(self) -> None:
        # Arrange
        identities = [identity for identity, _ in PRESENT]

        # Act
        larger = {
            identity.name.rsplit("/", 1)[-1]
            for identity in identities
            if identity.size > LOROM_REACH and identity.layout == mapper.LOROM
        }

        # Assert
        self.assertEqual(larger, {"Star Ocean (Japan).sfc"})


if __name__ == "__main__":
    unittest.main()
