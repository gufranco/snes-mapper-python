"""Take a census of a cartridge library you own.

A header is thirty two bytes in which a cartridge describes how it is built:
which layout it declares, which coprocessor is fitted, how much ROM and save
memory it carries, and where in the address space it expects to be found. Those
are facts about a physical object. They are not authored, they carry none of the
game, and a count of how many cartridges share a combination is a measurement.

So this walks a library, reads only those thirty two bytes from each cartridge,
and writes down what it found. It never records a title, because a title is the
one field in the header that is a name rather than a measurement, and it never
reads a byte outside the header at all.

What comes out is the corpus this repository is tested against: every distinct
combination of header fields the library contains, with a count of how many
cartridges each one accounts for. A model that gets a rare mapping byte wrong
fails against the combination that names it.

A cartridge whose header cannot be found is counted as refused rather than
guessed at. Prototypes and unfinished dumps often carry a blank one, and
inventing a layout for them would put fiction into a corpus of facts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterable, Sequence
    from pathlib import Path

import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapper import errors, header

SUFFIXES = (".sfc", ".smc")


def cartridges(root: Path, limit: int | None = None) -> list[Path]:
    """Every cartridge image under a directory, in a fixed order."""
    found = sorted(
        path for path in Path(root).rglob("*") if path.is_file() and path.suffix.lower() in SUFFIXES
    )
    return found[:limit] if limit else found


def tally(images: Iterable[bytes]) -> dict[str, Any]:
    """What the library is made of, with none of what the cartridges hold."""
    mapping: collections.Counter[Any] = collections.Counter()
    chipset: collections.Counter[Any] = collections.Counter()
    layouts: collections.Counter[Any] = collections.Counter()
    rom_size: collections.Counter[Any] = collections.Counter()
    ram_size: collections.Counter[Any] = collections.Counter()
    country: collections.Counter[Any] = collections.Counter()
    offsets: collections.Counter[Any] = collections.Counter()
    combinations: collections.Counter[Any] = collections.Counter()
    fast = battery = agrees = 0
    read = refused = 0

    for blob in images:
        try:
            found = header.read(blob)
        except errors.NoHeader:
            refused += 1
            continue

        read += 1
        mapping[found.mapping] += 1
        chipset[found.chipset] += 1
        layouts[found.layout] += 1
        rom_size[found.raw[23]] += 1
        ram_size[found.raw[24]] += 1
        country[found.country] += 1
        offsets[found.at] += 1
        fast += found.fast
        battery += found.battery
        agrees += found.checksum_agrees
        combinations[
            (found.mapping, found.chipset, found.raw[23], found.raw[24], found.country)
        ] += 1

    return {
        "comment": (
            "A census of a cartridge library: declared layouts, coprocessors, sizes and "
            "placements. Header fields are facts about a physical object. No title and "
            "no cartridge content is recorded."
        ),
        "roms": read,
        "refused": refused,
        "layout": dict(sorted(layouts.items())),
        "mapping": {str(value): count for value, count in sorted(mapping.items())},
        "chipset": {str(value): count for value, count in sorted(chipset.items())},
        "rom_size": {str(value): count for value, count in sorted(rom_size.items())},
        "ram_size": {str(value): count for value, count in sorted(ram_size.items())},
        "country": {str(value): count for value, count in sorted(country.items())},
        "offsets": {str(value): count for value, count in sorted(offsets.items())},
        "fast": fast,
        "battery": battery,
        "checksum_agrees": agrees,
        "combinations": [
            {
                "mapping": combination[0],
                "chipset": combination[1],
                "rom_size": combination[2],
                "ram_size": combination[3],
                "country": combination[4],
                "cartridges": count,
            }
            for combination, count in sorted(combinations.items())
        ],
    }


def main(argv: Sequence[str]) -> int:
    if len(argv) < 2:
        print("usage: census.py <library directory> <census out> [limit]")
        return 2

    root = Path(argv[0])
    if not root.is_dir():
        print(f"  nothing at {root}")
        return 2

    limit = int(argv[2]) if len(argv) > 2 else None
    images = cartridges(root, limit)
    if not images:
        print(f"  no cartridges under {root}")
        return 1

    found = tally(path.read_bytes() for path in images)
    Path(argv[1]).write_text(json.dumps(found, indent=2) + "\n")

    print(f"  {found['roms']} cartridges read, {found['refused']} refused, from {root}")
    print(f"  {len(found['combinations'])} distinct header combinations")
    print(f"  written to {argv[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
