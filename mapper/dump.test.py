import random
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapper import dump


def _image(banks=2, seed=1):
    generator = random.Random(seed)
    return bytes(generator.randrange(256) for _ in range(banks * 0x10000))


class CopierStubTest(unittest.TestCase):
    def test_a_whole_number_of_half_banks_carries_no_stub(self):
        self.assertFalse(dump.has_copier_stub(_image()))

    def test_the_same_image_with_five_hundred_and_twelve_more_bytes_does(self):
        self.assertTrue(dump.has_copier_stub(bytes(dump.COPIER_BYTES) + _image()))

    def test_a_file_shorter_than_the_stub_cannot_be_one(self):
        self.assertFalse(dump.has_copier_stub(bytes(dump.COPIER_BYTES)))

    def test_a_file_of_no_recognised_length_is_left_alone(self):
        self.assertFalse(dump.has_copier_stub(bytes(1234)))

    def test_stripping_removes_exactly_the_stub(self):
        image = _image()

        self.assertEqual(dump.strip_copier_stub(bytes(dump.COPIER_BYTES) + image), image)

    def test_stripping_an_image_that_never_had_one_changes_nothing(self):
        image = _image()

        self.assertEqual(dump.strip_copier_stub(image), image)


class GameDoctorTest(unittest.TestCase):
    def test_the_parts_join_in_name_order_with_one_stub_removed(self):
        first, second = _image(banks=1, seed=2), _image(banks=1, seed=3)

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "SF6A.078").write_bytes(bytes(dump.COPIER_BYTES) + first)
            (root / "SF6B.078").write_bytes(second)

            self.assertEqual(dump.join_game_doctor(root), first + second)

    def test_the_order_ignores_case(self):
        first, second = _image(banks=1, seed=4), _image(banks=1, seed=5)

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "sf6a.078").write_bytes(first)
            (root / "SF6B.078").write_bytes(second)

            self.assertEqual(dump.join_game_doctor(root), first + second)

    def test_a_folder_with_no_parts_gives_nothing_rather_than_failing(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "notes.txt").write_bytes(b"nothing here")

            self.assertEqual(dump.join_game_doctor(folder), b"")


class ReadTest(unittest.TestCase):
    def test_a_dump_comes_back_as_the_console_would_have_seen_it(self):
        image = _image()

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "game.smc"
            path.write_bytes(bytes(dump.COPIER_BYTES) + image)

            self.assertEqual(dump.read(path), image)


class RatioTest(unittest.TestCase):
    def test_an_empty_block_has_no_ratio_rather_than_a_division(self):
        self.assertEqual(dump.deflate_ratio(b""), 0.0)

    def test_a_block_of_one_repeated_byte_compresses_far_below_one(self):
        self.assertLess(dump.deflate_ratio(bytes(0x10000)), 0.1)

    def test_a_block_of_random_bytes_does_not(self):
        self.assertGreater(dump.deflate_ratio(_image(banks=1)), 0.9)

    def test_the_ratio_is_the_compressed_size_over_the_original(self):
        block = _image(banks=1, seed=6)

        self.assertEqual(
            dump.deflate_ratio(block),
            len(zlib.compress(block, dump.DEFLATE_LEVEL)) / len(block),
        )

    def test_one_ratio_per_whole_block_and_none_for_the_remainder(self):
        found = dump.block_ratios(bytes(0x10000 * 3 + 5), block=0x10000)

        self.assertEqual(len(found), 3)

    def test_an_image_shorter_than_one_block_gives_no_ratios(self):
        self.assertEqual(dump.block_ratios(bytes(0x100), block=0x10000), [])


class ReuseTest(unittest.TestCase):
    def test_a_chunk_is_indexed_at_the_first_place_it_appears(self):
        data = b"AB" * 8

        index = dump.chunk_index(data, chunk=4, stride=2)

        self.assertEqual(index[b"ABAB"], 0)

    def test_an_image_shorter_than_the_chunk_indexes_nothing(self):
        self.assertEqual(dump.chunk_index(b"AB", chunk=4, stride=2), {})

    def test_an_image_compared_with_itself_reuses_everything(self):
        image = _image(banks=1, seed=7)

        found, total = dump.measure_reuse(image, image)

        self.assertEqual(found, total)
        self.assertGreater(total, 0)

    def test_two_unrelated_images_reuse_nothing(self):
        found, _ = dump.measure_reuse(_image(banks=1, seed=8), _image(banks=1, seed=9))

        self.assertEqual(found, 0)

    def test_a_run_that_moved_by_less_than_a_chunk_is_still_found(self):
        run = _image(banks=1, seed=10)[:4096]
        source = run + bytes(4096)
        target = bytes(dump.CHUNK_STRIDE) + run + bytes(4096)

        found, _ = dump.measure_reuse(source, target)

        self.assertGreater(found, 0)


if __name__ == "__main__":
    unittest.main()
