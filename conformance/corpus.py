"""Replay every header combination a real ROM library contains.

There is no published suite for a cartridge memory map, and there does not need
to be one: the evidence is the cartridges themselves. A header is thirty two
bytes of a cartridge describing how it is built, and which layout it declares,
which coprocessor is fitted and how much memory it carries are facts about a
physical object rather than anything authored. Facts sit outside what copyright
reaches, per 17 U.S.C. 102(b) and Feist, so a census of them travels freely while
not one byte of any game does.

**What was measured.** A library of real cartridges, parsed for their header
fields. Every distinct combination of mapping byte, chipset byte, ROM size, save
memory size, country and header placement became one case here, and the cases
between them account for every cartridge the census read.

**What each case checks.** The header those fields produce, and then what a set
of probe addresses resolve to under the layout it declares: work RAM, the
register window, save memory, cartridge, and what reaching each one costs.

**What is not here.** No title, no content, no cartridge bytes. Each case is a
tuple of numbers and the answers they should produce.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapper import header, layout

EXAMPLE_LIMIT = 5

DEFAULT_CORPUS = Path(__file__).resolve().parent / "corpus.json"

TITLE = b"CORPUS CARTRIDGE     "
CHECKSUM = 0x5A5A

SIZE_FOR_OFFSET = {
    header.LOROM_HEADER: 0x100000,
    header.HIROM_HEADER: 0x200000,
    header.EXHIROM_HEADER: 0x600000,
}
"""How large a stand-in has to be for each offset to exist inside it."""

PROBES = (
    0x000100,
    0x002100,
    0x004200,
    0x00420B,
    0x004300,
    0x008000,
    0x018000,
    0x400000,
    0x700000,
    0x7E0000,
    0x7F0000,
    0x808000,
    0xC00000,
    0xFFFFFF,
)
"""The addresses each case is asked about: one per region a layout can reach."""


def load(path=None):
    """The corpus, from where it was asked for or from the one that ships."""
    with Path(path or DEFAULT_CORPUS).open() as handle:
        return json.load(handle)


def cartridge_for(case):
    """A cartridge carrying this case's real header fields and nothing else.

    The fields are measured from real hardware. Everything around them is filler,
    because a header is all this package reads and a cartridge's contents are not
    ours to carry.
    """
    at = case["expect"]["at"]
    if at not in SIZE_FOR_OFFSET:
        at = at - header.COPIER_BYTES if at - header.COPIER_BYTES in SIZE_FOR_OFFSET else at
    if at not in SIZE_FOR_OFFSET:
        at = header.LOROM_HEADER if at & 0xFFFF == header.LOROM_HEADER else header.HIROM_HEADER
    rom = bytearray(SIZE_FOR_OFFSET[at])
    rom[at : at + 21] = TITLE
    rom[at + 21] = case["mapping"]
    rom[at + 22] = case["chipset"]
    rom[at + 23] = case["rom_size"]
    rom[at + 24] = case["ram_size"]
    rom[at + 25] = case["country"]
    rom[at + 28] = (CHECKSUM ^ 0xFFFF) & 0xFF
    rom[at + 29] = (CHECKSUM ^ 0xFFFF) >> 8
    rom[at + 30] = CHECKSUM & 0xFF
    rom[at + 31] = CHECKSUM >> 8
    return bytes(rom)


def check(case):
    """What went wrong with one case, or nothing when it agreed."""
    try:
        found = header.read(cartridge_for(case))
    except Exception as error:  # noqa: BLE001
        return f"mapping {case.get('mapping')}: {type(error).__name__}"

    expect = case["expect"]
    for name, got in (
        ("at", found.at),
        ("layout", found.layout),
        ("fast", found.fast),
        ("coprocessor", found.coprocessor),
        ("battery", found.battery),
        ("rom_bytes", found.rom_bytes),
        ("ram_bytes", found.ram_bytes),
    ):
        if expect[name] != got:
            return f"mapping {case['mapping']:#04x}: {name} want {expect[name]} got {got}"

    for address, region, offset, cycles in case["resolutions"]:
        resolved = layout.resolve(found.layout, address, fast=found.fast)
        if (resolved.region, resolved.offset, resolved.cycles) != (region, offset, cycles):
            return (
                f"mapping {case['mapping']:#04x} at {address:06X}: "
                f"want {region}/{offset}/{cycles} "
                f"got {resolved.region}/{resolved.offset}/{resolved.cycles}"
            )

    return None


def run(cases):
    """How many cases agreed, how many did not, and a few that did not."""
    passed = failed = 0
    examples = []
    for case in cases:
        wrong = check(case)
        if wrong is None:
            passed += 1
        else:
            failed += 1
            if len(examples) < EXAMPLE_LIMIT:
                examples.append(wrong)
    return passed, failed, examples


def main(argv):
    path = Path(argv[0]) if argv else DEFAULT_CORPUS
    if not path.is_file():
        print(f"  no corpus at {path}")
        return 2

    found = load(path)
    passed, failed, examples = run(found["cases"])
    print(f"  {passed + failed} header combinations from {path}")
    print(f"  measured across {found['measured_from']} cartridges")
    print(f"  {passed} agreed, {failed} did not")
    for line in examples:
        print(f"    {line}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
