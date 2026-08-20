import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import override

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from conformance import corpus, record
from mapper import header


def a_cartridge(
    at: int = header.LOROM_HEADER,
    mapping: int = 0x20,
    chipset: int = 0x00,
    size: int = 0x100000,
    title: bytes = b"RECORDED CARTRIDGE   ",
) -> bytes:
    rom = bytearray(size)
    rom[at : at + 21] = title
    rom[at + 21] = mapping
    rom[at + 22] = chipset
    rom[at + 23] = 0x0A
    rom[at + 25] = 0x01
    rom[at + 28] = 0xA5
    rom[at + 29] = 0xA5
    rom[at + 30] = 0x5A
    rom[at + 31] = 0x5A
    return bytes(rom)


PROBES = [0x8000, 0x7E0000]


class FieldsTest(unittest.TestCase):
    def test_a_case_carries_the_numbers_and_not_the_title(self) -> None:
        found = header.read(a_cartridge())

        fields = record.fields_of(found)

        self.assertEqual(fields["mapping"], 0x20)
        self.assertNotIn("title", fields)

    def test_a_case_carries_the_offset_the_header_sat_at(self) -> None:
        found = header.read(a_cartridge())

        self.assertEqual(record.fields_of(found)["at"], header.LOROM_HEADER)

    def test_a_copier_stub_does_not_change_the_offset_a_case_carries(self) -> None:
        found = header.read(b"\x00" * header.COPIER_BYTES + a_cartridge())

        self.assertEqual(record.fields_of(found)["at"], header.LOROM_HEADER)


class GatherTest(unittest.TestCase):
    def test_one_cartridge_makes_one_case(self) -> None:
        cases, read, refused = record.gather([a_cartridge()], PROBES)

        self.assertEqual(len(cases), 1)
        self.assertEqual((read, refused), (1, 0))

    def test_two_identical_cartridges_make_one_case_counted_twice(self) -> None:
        cases, _, _ = record.gather([a_cartridge(), a_cartridge()], PROBES)

        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0]["cartridges"], 2)

    def test_a_title_that_differs_does_not_make_a_second_case(self) -> None:
        pair = [a_cartridge(), a_cartridge(title=b"ANOTHER CARTRIDGE    ")]

        self.assertEqual(len(record.gather(pair, PROBES)[0]), 1)

    def test_the_same_fields_at_two_offsets_make_two_cases(self) -> None:
        pair = [
            a_cartridge(mapping=0x45),
            a_cartridge(at=header.HIROM_HEADER, mapping=0x45, size=0x200000),
        ]

        self.assertEqual(len(record.gather(pair, PROBES)[0]), 2)

    def test_a_cartridge_with_no_header_is_refused_rather_than_guessed_at(self) -> None:
        cases, read, refused = record.gather([bytes(0x100000)], PROBES)

        self.assertEqual((len(cases), read, refused), (0, 0, 1))

    def test_every_case_answers_every_probe(self) -> None:
        cases, _, _ = record.gather([a_cartridge()], PROBES)

        self.assertEqual(len(cases[0]["resolutions"]), len(PROBES))

    def test_a_case_records_what_the_model_says_the_header_is(self) -> None:
        cases, _, _ = record.gather([a_cartridge()], PROBES)

        self.assertEqual(cases[0]["expect"]["layout"], header.LOROM)

    def test_cases_come_out_in_the_same_order_every_time(self) -> None:
        images = [a_cartridge(mapping=0x30), a_cartridge(), a_cartridge(chipset=0x02)]

        first = record.gather(images, PROBES)[0]
        again = record.gather(list(reversed(images)), PROBES)[0]

        self.assertEqual([case["mapping"] for case in first], [case["mapping"] for case in again])


class StubTest(unittest.TestCase):
    def test_a_stubbed_dump_records_the_offset_the_cartridge_has(self) -> None:
        cases, _, _ = record.gather([b"\x00" * header.COPIER_BYTES + a_cartridge()], PROBES)

        self.assertEqual(cases[0]["expect"]["at"], header.LOROM_HEADER)

    def test_a_stubbed_dump_and_a_bare_one_are_the_same_case(self) -> None:
        pair = [a_cartridge(), b"\x00" * header.COPIER_BYTES + a_cartridge()]

        self.assertEqual(len(record.gather(pair, PROBES)[0]), 1)

    def test_what_a_stubbed_dump_records_replays_clean(self) -> None:
        cases, _, _ = record.gather([b"\x00" * header.COPIER_BYTES + a_cartridge()], corpus.PROBES)

        self.assertEqual(corpus.run(cases)[1], 0)


class ReplayTest(unittest.TestCase):
    def test_what_was_recorded_replays_without_disagreeing(self) -> None:
        images = [a_cartridge(mapping=value) for value in (0x20, 0x30, 0x21, 0x45, 0x53)]

        cases, _, _ = record.gather(images, corpus.PROBES)

        self.assertEqual(corpus.run(cases)[1], 0)


class MainTest(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.where = Path(tempfile.mkdtemp())
        (self.where / "one.sfc").write_bytes(a_cartridge())
        (self.where / "two.sfc").write_bytes(a_cartridge(mapping=0x30))
        self.out = self.where / "corpus.json"

    def test_a_library_is_written_out_as_a_corpus(self) -> None:
        self.assertEqual(record.main([str(self.where), str(self.out)]), 0)
        self.assertEqual(len(json.loads(self.out.read_text())["cases"]), 2)

    def test_the_corpus_it_writes_replays_clean(self) -> None:
        record.main([str(self.where), str(self.out)])

        self.assertEqual(corpus.main([str(self.out)]), 0)

    def test_recording_twice_writes_the_same_file(self) -> None:
        record.main([str(self.where), str(self.out)])
        once = self.out.read_text()
        record.main([str(self.where), str(self.out)])

        self.assertEqual(self.out.read_text(), once)

    def test_a_limit_stops_after_that_many_cartridges(self) -> None:
        record.main([str(self.where), str(self.out), "1"])

        self.assertEqual(json.loads(self.out.read_text())["measured_from"], 1)

    def test_the_probes_of_an_existing_corpus_are_kept(self) -> None:
        self.out.write_text(json.dumps({"probes": [0x8000], "cases": []}))
        record.main([str(self.where), str(self.out)])

        self.assertEqual(json.loads(self.out.read_text())["probes"], [0x8000])

    def test_no_arguments_explains_itself(self) -> None:
        self.assertEqual(record.main([]), 2)

    def test_a_directory_that_is_not_there_is_refused(self) -> None:
        self.assertEqual(record.main(["/nowhere/at/all", str(self.out)]), 2)

    def test_a_directory_with_no_cartridges_is_refused(self) -> None:
        self.assertEqual(record.main([str(Path(tempfile.mkdtemp())), str(self.out)]), 1)


if __name__ == "__main__":
    unittest.main()
