import hashlib
import json
import os
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conformance import cartridges


def an_image(filler: int = 0xAB, size: int = 64) -> bytes:
    return bytes([filler]) * size


def a_catalogue(image: bytes, name: str = "made-up.sfc", **overrides: Any) -> dict[str, Any]:
    entry = {
        "name": name,
        "title": "MADE UP",
        "bytes": len(image),
        "layout": "lorom",
        "mapping": "0x20",
        "chipset": "0x00",
        "declared": True,
        "crc32": f"{zlib.crc32(image) & 0xFFFFFFFF:08x}",
        "md5": hashlib.md5(image).hexdigest(),
        "sha1": hashlib.sha1(image).hexdigest(),
        "sha256": hashlib.sha256(image).hexdigest(),
    }
    entry.update(overrides)
    return {"cartridges": [entry]}


class ManifestTest(unittest.TestCase):
    def test_the_manifest_describes_cartridges(self) -> None:
        self.assertTrue(cartridges.manifest()["cartridges"])

    def test_every_cartridge_carries_all_four_digests(self) -> None:
        for entry in cartridges.manifest()["cartridges"]:
            for name in cartridges.DIGESTS:
                self.assertIn(name, entry, (entry["name"], name))

    def test_each_digest_is_the_length_that_kind_of_digest_has(self) -> None:
        for entry in cartridges.manifest()["cartridges"]:
            for name, width in cartridges.DIGEST_WIDTHS.items():
                self.assertEqual(len(entry[name]), width, (entry["name"], name))

    def test_every_cartridge_names_a_file_and_a_length(self) -> None:
        for entry in cartridges.manifest()["cartridges"]:
            self.assertTrue(entry["name"])
            self.assertGreater(entry["bytes"], 0)

    def test_no_two_cartridges_share_a_deciding_digest(self) -> None:
        seen = [entry[cartridges.DECIDES] for entry in cartridges.manifest()["cartridges"]]

        self.assertEqual(len(seen), len(set(seen)))

    def test_every_layout_the_package_models_is_represented(self) -> None:
        named = {entry["layout"] for entry in cartridges.manifest()["cartridges"]}

        for layout in ("lorom", "hirom", "exhirom", "sa1", "spc7110"):
            self.assertIn(layout, named)

    def test_both_sides_of_the_overflowed_mapping_byte_are_represented(self) -> None:
        declared = {entry["declared"] for entry in cartridges.manifest()["cartridges"]}

        self.assertEqual(declared, {True, False})

    def test_a_manifest_can_be_read_from_somewhere_else(self) -> None:
        where = Path(tempfile.mkdtemp()) / "other.json"
        where.write_text(json.dumps({"cartridges": []}))

        self.assertEqual(cartridges.manifest(where)["cartridges"], [])


class IdentifyTest(unittest.TestCase):
    def test_a_cartridge_the_manifest_knows_is_named(self) -> None:
        image = an_image()

        self.assertEqual(cartridges.identify(image, a_catalogue(image)).name, "made-up.sfc")

    def test_and_carries_the_layout_the_manifest_recorded(self) -> None:
        image = an_image()

        self.assertEqual(cartridges.identify(image, a_catalogue(image)).layout, "lorom")

    def test_a_cartridge_of_the_right_length_and_wrong_content_says_so(self) -> None:
        image = an_image()

        with self.assertRaises(cartridges.Unrecognised) as raised:
            cartridges.identify(image, a_catalogue(image, sha256="0" * 64))

        self.assertIn("altered", str(raised.exception))

    def test_a_cartridge_of_no_length_the_manifest_knows_says_that(self) -> None:
        with self.assertRaises(cartridges.Unrecognised) as raised:
            cartridges.identify(b"\x00" * 7, {"cartridges": []})

        self.assertIn("7", str(raised.exception))

    def test_the_report_always_carries_the_digest_that_was_computed(self) -> None:
        with self.assertRaises(cartridges.Unrecognised) as raised:
            cartridges.identify(b"\x00" * 7, {"cartridges": []})

        self.assertIn(hashlib.sha256(b"\x00" * 7).hexdigest(), str(raised.exception))


class CrossCheckTest(unittest.TestCase):
    def test_a_cartridge_whose_other_digests_disagree_is_refused(self) -> None:
        image = an_image()

        with self.assertRaises(cartridges.Corrupt) as raised:
            cartridges.identify(image, a_catalogue(image, crc32="00000000"))

        self.assertIn("crc32", str(raised.exception))

    def test_every_kind_of_disagreement_is_caught(self) -> None:
        image = an_image()
        for name, wrong in (("md5", "0" * 32), ("sha1", "0" * 40), ("crc32", "0" * 8)):
            with self.assertRaises(cartridges.Corrupt):
                cartridges.identify(image, a_catalogue(image, **{name: wrong}))

    def test_a_manifest_that_only_names_the_deciding_digest_is_still_accepted(self) -> None:
        image = an_image()
        catalogue = a_catalogue(image)
        for name in ("crc32", "md5", "sha1"):
            del catalogue["cartridges"][0][name]

        self.assertEqual(cartridges.identify(image, catalogue).name, "made-up.sfc")


class PrintingTest(unittest.TestCase):
    def test_a_cartridge_prints_as_the_file_and_the_title_it_carries(self) -> None:
        printed = repr(cartridges.Identity("a.sfc", "A GAME", 512, "lorom", "0" * 64))

        self.assertIn("a.sfc", printed)
        self.assertIn("A GAME", printed)


class DirectoryTest(unittest.TestCase):
    def test_the_directory_comes_from_the_environment_when_one_is_named(self) -> None:
        self.assertEqual(cartridges.directory({cartridges.DIRECTORY_VARIABLE: "/x"}), Path("/x"))

    def test_and_from_the_repository_when_none_is(self) -> None:
        self.assertEqual(cartridges.directory({}).name, "cartridges")

    def test_a_directory_that_is_not_there_yields_nothing(self) -> None:
        self.assertEqual(list(cartridges.found(Path("/nowhere/at/all"))), [])

    def test_a_file_the_manifest_does_not_know_is_passed_over(self) -> None:
        where = Path(tempfile.mkdtemp())
        (where / "nonsense.sfc").write_bytes(b"\x00" * 99)

        self.assertEqual(list(cartridges.found(where, {"cartridges": []})), [])

    def test_a_file_that_is_not_a_cartridge_is_passed_over(self) -> None:
        where = Path(tempfile.mkdtemp())
        (where / "notes.txt").write_bytes(b"nothing here")

        self.assertEqual(list(cartridges.found(where, {"cartridges": []})), [])

    def test_a_cartridge_in_a_subdirectory_is_still_found(self) -> None:
        where = Path(tempfile.mkdtemp())
        (where / "region").mkdir()
        image = an_image()
        (where / "region" / "made-up.sfc").write_bytes(image)

        self.assertEqual(len(list(cartridges.found(where, a_catalogue(image)))), 1)

    def test_a_directory_beside_a_parent_project_is_searched_as_well(self) -> None:
        places = cartridges.directories({})

        self.assertIn(cartridges.ALONGSIDE, places)

    def test_the_named_directory_is_searched_before_any_other(self) -> None:
        places = cartridges.directories({cartridges.DIRECTORY_VARIABLE: "/x"})

        self.assertEqual(places[0], Path("/x"))

    def test_the_first_place_that_is_actually_there_is_the_one_used(self) -> None:
        here = Path(tempfile.mkdtemp())

        self.assertEqual(cartridges.directory({}, places=[Path("/nowhere"), here]), here)

    def test_when_no_place_is_there_the_one_in_this_repository_is_named(self) -> None:
        chosen = cartridges.directory({}, places=[Path("/nowhere"), Path("/nor/here")])

        self.assertEqual(chosen, cartridges.DEFAULT_DIRECTORY)


class SharedDirectoryRuleTest(unittest.TestCase):
    """The rule every member of this family uses to find a file it does not carry.

    Byte-identical in all of them, so these check the behaviour that identity is
    supposed to guarantee rather than the text of one copy.
    """

    def test_the_project_above_is_looked_at_before_the_package_itself(self) -> None:
        """Vendored, the parent owns the library, which is what ALONGSIDE is for."""
        found = cartridges.directories({})

        self.assertLess(
            found.index(cartridges.ALONGSIDE), found.index(cartridges.DEFAULT_DIRECTORY)
        )

    def test_a_named_directory_is_looked_at_before_either(self) -> None:
        found = cartridges.directories({cartridges.DIRECTORY_VARIABLE: "/x"})

        self.assertEqual(found[0], Path("/x"))

    def test_more_than_one_can_be_named_at_once(self) -> None:
        found = cartridges.directories({cartridges.DIRECTORY_VARIABLE: f"/x{os.pathsep}/y"})

        self.assertEqual(found[:2], (Path("/x"), Path("/y")))

    def test_an_empty_entry_between_two_names_is_passed_over(self) -> None:
        found = cartridges.directories(
            {cartridges.DIRECTORY_VARIABLE: f"/x{os.pathsep}{os.pathsep}/y"}
        )

        self.assertEqual(found[:2], (Path("/x"), Path("/y")))

    def test_no_directory_appears_twice(self) -> None:
        found = cartridges.directories(
            {cartridges.DIRECTORY_VARIABLE: str(cartridges.DEFAULT_DIRECTORY)}
        )

        self.assertEqual(len(found), len(set(found)))


class DecidingDigestTest(unittest.TestCase):
    """That the manifest tells a reader which of its four digests decides.

    The reader already knows: `DECIDES` names it and nothing else is compared
    against. A person cross-checking a copy reads the manifest rather than the
    module, so the manifest has to say it too, and this is what keeps the two
    from drifting apart.
    """

    def held(self) -> str:
        return str(cartridges.manifest()["decides"])

    def test_the_manifest_names_the_digest_that_decides(self) -> None:
        self.assertIn(cartridges.DECIDES, self.held())

    def test_and_says_the_others_decide_nothing(self) -> None:
        self.assertIn("decides anything on its own", self.held())


if __name__ == "__main__":
    unittest.main()
