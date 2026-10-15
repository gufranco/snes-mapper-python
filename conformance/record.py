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

from conformance import census, corpus
from mapper import errors, header, layout

COMMENT = (
    "Every distinct combination of cartridge header fields found across a real ROM"
    " library, with the layout and address resolutions each one produces. Header"
    " fields are facts about a cartridge and carry none of its content. Rebuild"
    " with record.py against a library you own."
)

NUMBERS = ("mapping", "chipset", "rom_size", "ram_size", "country")


def fields_of(found: Any) -> dict[str, Any]:
    return {
        "mapping": found.mapping,
        "chipset": found.chipset,
        "rom_size": found.raw[23],
        "ram_size": found.raw[24],
        "country": found.country,
        "at": found.at - found.shift,
    }


def expectation(found: Any) -> dict[str, Any]:
    return {
        "at": found.at - found.shift,
        "layout": found.layout,
        "fast": found.fast,
        "coprocessor": found.coprocessor,
        "battery": found.battery,
        "rom_bytes": found.rom_bytes,
        "ram_bytes": found.ram_bytes,
    }


def resolutions(found: Any, probes: Iterable[Any]) -> list[list[Any]]:
    return [
        [address, reached.region, reached.offset, reached.cycles]
        for address, reached in (
            (address, layout.resolve(found.layout, address, fast=found.fast)) for address in probes
        )
    ]


def gather(images: Iterable[bytes], probes: Iterable[Any]) -> tuple[list[dict[str, Any]], int, int]:
    seen: dict[Any, dict[str, Any]] = {}
    counts: collections.Counter[Any] = collections.Counter()
    read = refused = 0

    for blob in images:
        try:
            found = header.read(blob)
        except errors.NoHeader:
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


def main(argv: Sequence[str]) -> int:
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
