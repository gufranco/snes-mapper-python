import hashlib
import json
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cartridges


def an_image(filler=0xAB, size=64):
    return bytes([filler]) * size


def a_catalogue(image, name="made-up.sfc", **overrides):
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
    def test_the_manifest_describes_cartridges(self):
        self.assertTrue(cartridges.manifest()["cartridges"])

    def test_every_cartridge_carries_all_four_digests(self):
        for entry in cartridges.manifest()["cartridges"]:
            for name in cartridges.DIGESTS:
                self.assertIn(name, entry, (entry["name"], name))

    def test_each_digest_is_the_length_that_kind_of_digest_has(self):
        for entry in cartridges.manifest()["cartridges"]:
            for name, width in cartridges.DIGEST_WIDTHS.items():
                self.assertEqual(len(entry[name]), width, (entry["name"], name))

    def test_every_cartridge_names_a_file_and_a_length(self):
        for entry in cartridges.manifest()["cartridges"]:
            self.assertTrue(entry["name"])
            self.assertGreater(entry["bytes"], 0)

    def test_no_two_cartridges_share_a_deciding_digest(self):
        seen = [entry[cartridges.DECIDES] for entry in cartridges.manifest()["cartridges"]]

        self.assertEqual(len(seen), len(set(seen)))

    def test_every_layout_the_package_models_is_represented(self):
        named = {entry["layout"] for entry in cartridges.manifest()["cartridges"]}

        for layout in ("lorom", "hirom", "exhirom", "sa1", "spc7110"):
            self.assertIn(layout, named)

    def test_both_sides_of_the_overflowed_mapping_byte_are_represented(self):
        declared = {entry["declared"] for entry in cartridges.manifest()["cartridges"]}

        self.assertEqual(declared, {True, False})

    def test_a_manifest_can_be_read_from_somewhere_else(self):
        where = Path(tempfile.mkdtemp()) / "other.json"
        where.write_text(json.dumps({"cartridges": []}))

        self.assertEqual(cartridges.manifest(where)["cartridges"], [])


class IdentifyTest(unittest.TestCase):
    def test_a_cartridge_the_manifest_knows_is_named(self):
        image = an_image()

        self.assertEqual(cartridges.identify(image, a_catalogue(image)).name, "made-up.sfc")

    def test_and_carries_the_layout_the_manifest_recorded(self):
        image = an_image()

        self.assertEqual(cartridges.identify(image, a_catalogue(image)).layout, "lorom")

    def test_a_cartridge_of_the_right_length_and_wrong_content_says_so(self):
        image = an_image()

        with self.assertRaises(cartridges.Unrecognised) as raised:
            cartridges.identify(image, a_catalogue(image, sha256="0" * 64))

        self.assertIn("altered", str(raised.exception))

    def test_a_cartridge_of_no_length_the_manifest_knows_says_that(self):
        with self.assertRaises(cartridges.Unrecognised) as raised:
            cartridges.identify(b"\x00" * 7, {"cartridges": []})

        self.assertIn("7", str(raised.exception))

    def test_the_report_always_carries_the_digest_that_was_computed(self):
        with self.assertRaises(cartridges.Unrecognised) as raised:
            cartridges.identify(b"\x00" * 7, {"cartridges": []})

        self.assertIn(hashlib.sha256(b"\x00" * 7).hexdigest(), str(raised.exception))


class CrossCheckTest(unittest.TestCase):
    def test_a_cartridge_whose_other_digests_disagree_is_refused(self):
        image = an_image()

        with self.assertRaises(cartridges.Corrupt) as raised:
            cartridges.identify(image, a_catalogue(image, crc32="00000000"))

        self.assertIn("crc32", str(raised.exception))

    def test_every_kind_of_disagreement_is_caught(self):
        image = an_image()
        for name, wrong in (("md5", "0" * 32), ("sha1", "0" * 40), ("crc32", "0" * 8)):
            with self.assertRaises(cartridges.Corrupt):
                cartridges.identify(image, a_catalogue(image, **{name: wrong}))

    def test_a_manifest_that_only_names_the_deciding_digest_is_still_accepted(self):
        image = an_image()
        catalogue = a_catalogue(image)
        for name in ("crc32", "md5", "sha1"):
            del catalogue["cartridges"][0][name]

        self.assertEqual(cartridges.identify(image, catalogue).name, "made-up.sfc")


class PrintingTest(unittest.TestCase):
    def test_a_cartridge_prints_as_the_file_and_the_title_it_carries(self):
        printed = repr(cartridges.Identity("a.sfc", "A GAME", 512, "lorom", "0" * 64))

        self.assertIn("a.sfc", printed)
        self.assertIn("A GAME", printed)


class DirectoryTest(unittest.TestCase):
    def test_the_directory_comes_from_the_environment_when_one_is_named(self):
        self.assertEqual(cartridges.directory({cartridges.DIRECTORY_VARIABLE: "/x"}), Path("/x"))

    def test_and_from_the_repository_when_none_is(self):
        self.assertEqual(cartridges.directory({}).name, "cartridges")

    def test_a_directory_that_is_not_there_yields_nothing(self):
        self.assertEqual(list(cartridges.found(Path("/nowhere/at/all"))), [])

    def test_a_file_the_manifest_does_not_know_is_passed_over(self):
        where = Path(tempfile.mkdtemp())
        (where / "nonsense.sfc").write_bytes(b"\x00" * 99)

        self.assertEqual(list(cartridges.found(where, {"cartridges": []})), [])

    def test_a_file_that_is_not_a_cartridge_is_passed_over(self):
        where = Path(tempfile.mkdtemp())
        (where / "notes.txt").write_bytes(b"nothing here")

        self.assertEqual(list(cartridges.found(where, {"cartridges": []})), [])

    def test_a_cartridge_in_a_subdirectory_is_still_found(self):
        where = Path(tempfile.mkdtemp())
        (where / "region").mkdir()
        image = an_image()
        (where / "region" / "made-up.sfc").write_bytes(image)

        self.assertEqual(len(list(cartridges.found(where, a_catalogue(image)))), 1)

    def test_a_directory_beside_a_parent_project_is_searched_as_well(self):
        places = cartridges.directories({})

        self.assertIn(cartridges.ALONGSIDE, places)

    def test_the_named_directory_is_searched_before_any_other(self):
        places = cartridges.directories({cartridges.DIRECTORY_VARIABLE: "/x"})

        self.assertEqual(places[0], Path("/x"))

    def test_the_first_place_that_is_actually_there_is_the_one_used(self):
        here = Path(tempfile.mkdtemp())

        self.assertEqual(cartridges.directory({}, places=[Path("/nowhere"), here]), here)

    def test_when_no_place_is_there_the_one_in_this_repository_is_named(self):
        chosen = cartridges.directory({}, places=[Path("/nowhere"), Path("/nor/here")])

        self.assertEqual(chosen, cartridges.DEFAULT_DIRECTORY)


if __name__ == "__main__":
    unittest.main()
