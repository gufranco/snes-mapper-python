"""Build the corpus from a cartridge library you own.

The corpus beside this is replayed on every run, and a recording nothing can
reproduce is a recording nobody can check. This is the other half: point it at a
library and it writes that file out again, so anyone holding the same cartridges
can confirm the one that ships is what those cartridges say.

Nothing of any cartridge survives the trip. Each contributes the thirty two bytes
of its header, of which the twenty one byte title is dropped on the way in, and
what comes out is a tuple of numbers per distinct combination with a count of how
many cartridges carried it. That count is the only trace a cartridge leaves.

Two cartridges with identical header fields at different offsets are two cases
rather than one, because where a header sits is what names the layout whenever the
byte that should name it is a letter left behind by an overflowing title.
"""

import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import census
import corpus

from mapper import header, layout

COMMENT = (
    "Every distinct combination of cartridge header fields found across a real ROM"
    " library, with the layout and address resolutions each one produces. Header"
    " fields are facts about a cartridge and carry none of its content. Rebuild"
    " with record.py against a library you own."
)

NUMBERS = ("mapping", "chipset", "rom_size", "ram_size", "country")


def fields_of(found):
    """The numbers that make one case, with the title left behind."""
    return {
        "mapping": found.mapping,
        "chipset": found.chipset,
        "rom_size": found.raw[23],
        "ram_size": found.raw[24],
        "country": found.country,
        "at": found.at - found.shift,
    }


def expectation(found):
    """What the model makes of this header.

    The offset is the one the header occupies in the address space rather than the
    one it occupies in the file. A copier stub moves the second without moving the
    first, and it is a property of somebody's dump rather than of the cartridge.
    """
    return {
        "at": found.at - found.shift,
        "layout": found.layout,
        "fast": found.fast,
        "coprocessor": found.coprocessor,
        "battery": found.battery,
        "rom_bytes": found.rom_bytes,
        "ram_bytes": found.ram_bytes,
    }


def resolutions(found, probes):
    """What each probe address reaches under the layout this header declares."""
    return [
        [address, reached.region, reached.offset, reached.cycles]
        for address, reached in (
            (address, layout.resolve(found.layout, address, fast=found.fast)) for address in probes
        )
    ]


def gather(images, probes):
    """One case per distinct header combination, counted, in a fixed order."""
    seen = {}
    counts = collections.Counter()
    read = refused = 0

    for blob in images:
        try:
            found = header.read(blob)
        except header.NoHeader:
            refused += 1
            continue

        read += 1
        fields = fields_of(found)
        key = (*(fields[name] for name in NUMBERS), fields["at"])
        counts[key] += 1
        if key not in seen:
            seen[key] = dict(
                {name: fields[name] for name in NUMBERS},
                expect=expectation(found),
                resolutions=resolutions(found, probes),
            )

    cases = []
    for key in sorted(seen, key=lambda held: (held[-1], *held[:-1])):
        case = seen[key]
        cases.append(
            {
                **{name: case[name] for name in NUMBERS},
                "cartridges": counts[key],
                "expect": case["expect"],
                "resolutions": case["resolutions"],
            }
        )
    return cases, read, refused


def main(argv):
    if not argv:
        print("usage: record.py <library directory> [corpus out] [limit]")
        return 2

    root = Path(argv[0])
    if not root.is_dir():
        print(f"  nothing at {root}")
        return 2

    out = Path(argv[1]) if len(argv) > 1 else corpus.DEFAULT_CORPUS
    limit = int(argv[2]) if len(argv) > 2 else None

    paths = census.cartridges(root, limit)
    if not paths:
        print(f"  no cartridges under {root}")
        return 1

    probes = list(corpus.load(out)["probes"]) if out.is_file() else list(corpus.PROBES)
    counted = census.tally(path.read_bytes() for path in paths)
    cases, read, refused = gather((path.read_bytes() for path in paths), probes)

    out.write_text(
        json.dumps(
            {
                "comment": COMMENT,
                "measured_from": read,
                "census": counted,
                "probes": probes,
                "cases": cases,
            },
            indent=2,
        )
        + "\n"
    )

    print(f"  {read} cartridges read, {refused} refused, from {root}")
    print(f"  {len(cases)} distinct header combinations")
    print(f"  written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
