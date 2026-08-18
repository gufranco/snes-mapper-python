"""What arrives on disk, before any of it is a cartridge.

A dump is not a cartridge image. It is a cartridge image plus whatever the device
that read it decided to add, minus whatever it decided to split off, and the
first job of anything reading one is to get back to the bytes the console would
have seen.

Two devices account for nearly all of it. A copier writes a 512-byte stub in
front of the image describing what it just read, which shifts every offset in the
file by a number that appears nowhere in the file. A Game Doctor splits the image
across numbered files, of which only the first carries that stub. Neither is part
of the cartridge, and a tool that forgets either reads the right bytes from the
wrong place and reports something plausible.

The stub is detected by size rather than by content, because its content is not
standardised: a file whose length is a whole number of half-banks plus 512 has
one, and a file whose length is a whole number of half-banks does not. That test
is the same one `header` uses to decide where to look, and it lives here because
stripping the stub is the more basic operation.

The rest of this module is measurement rather than format. Deflate ratio per
block finds the regions of a cartridge that are already compressed, since data a
general-purpose compressor cannot shrink further is usually data something else
already shrank. Chunk indexing answers how much of one image was reused in
another, which is what tells you whether a rebuild changed what it meant to.
"""

import re
import zlib
from pathlib import Path

COPIER_BYTES = 0x200
HALF_BANK = 0x8000

GAME_DOCTOR_PART = re.compile(r"\.078$", re.IGNORECASE)

BLOCK_BYTES = 0x10000
DEFLATE_LEVEL = 6

CHUNK_BYTES = 1024
CHUNK_STRIDE = 512


def has_copier_stub(data):
    """Whether a dump carries the 512 bytes a copier wrote in front of it."""
    if len(data) <= COPIER_BYTES:
        return False
    return (len(data) - COPIER_BYTES) % HALF_BANK == 0 or len(data) % HALF_BANK == COPIER_BYTES


def strip_copier_stub(data):
    """The dump without the stub, or unchanged when it never had one."""
    return data[COPIER_BYTES:] if has_copier_stub(data) else data


def join_game_doctor(folder):
    """One image from a split set, with the stub taken off only the first part.

    The parts sort by name, and the sort is case-insensitive because the device
    wrote them in upper case and half the world has renamed them since.
    """
    parts = sorted(
        (p for p in Path(folder).iterdir() if GAME_DOCTOR_PART.search(p.name)),
        key=lambda p: p.name.upper(),
    )
    if not parts:
        return b""
    chunks = [strip_copier_stub(parts[0].read_bytes())]
    chunks += [p.read_bytes() for p in parts[1:]]
    return b"".join(chunks)


def read(path):
    """A dump from disk, as the console would have seen it."""
    return strip_copier_stub(Path(path).read_bytes())


def deflate_ratio(block):
    """How much a general-purpose compressor can still take off a block."""
    if not block:
        return 0.0
    return len(zlib.compress(block, DEFLATE_LEVEL)) / len(block)


def block_ratios(data, block=BLOCK_BYTES):
    """That ratio across the whole image, which is where its structure shows."""
    return [deflate_ratio(data[i : i + block]) for i in range(0, len(data) - block + 1, block)]


def chunk_index(data, chunk=CHUNK_BYTES, stride=CHUNK_STRIDE):
    """Where each distinct chunk first appears, at a stride finer than the chunk.

    The stride is deliberately shorter than the chunk, so a run that moved by an
    amount that is not a whole chunk is still found.
    """
    index = {}
    for i in range(0, len(data) - chunk + 1, stride):
        index.setdefault(data[i : i + chunk], i)
    return index


def measure_reuse(source, target, chunk=CHUNK_BYTES, stride=CHUNK_STRIDE):
    """How many of one image's chunks appear anywhere in another."""
    index = chunk_index(target, chunk=chunk, stride=stride)
    found = total = 0
    for i in range(0, len(source) - chunk + 1, chunk):
        total += 1
        if source[i : i + chunk] in index:
            found += 1
    return found, total
