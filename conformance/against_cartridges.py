"""Read every cartridge on disk and hold the model to what the corpus recorded.

The corpus replays 289 header combinations against a stand-in built from numbers.
That proves the model still answers what it answered when the recording was taken.
It cannot prove the recording covers the library, because a combination nobody
measured leaves no gap behind: it simply is not there to fail.

So this walks the real files instead. Every cartridge present is read, keyed by the
combination it carries, and looked up. A cartridge whose combination has no case is
a hole in the corpus and is reported as one. A cartridge whose case disagrees with
what the model now says is a regression. Neither is visible from the corpus alone.

The library is the authority and the corpus is a cache of it, so this is the test
that decides and the corpus is what runs when the library is absent.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import corpus

import cartridges
from mapper import header

EXAMPLE_LIMIT = 10

CASES = corpus.load()["cases"]

CHECKED = ("layout", "fast", "coprocessor", "battery", "rom_bytes", "ram_bytes")


def key_of(found):
    """What identifies the combination a header carries.

    The offset is the one in the address space rather than the one in the file, so
    a dump carrying a copier stub keys to the same case as a bare one.
    """
    return (
        found.mapping,
        found.chipset,
        found.raw[23],
        found.raw[24],
        found.country,
        found.at - found.shift,
    )


def key_of_case(case):
    return (
        case["mapping"],
        case["chipset"],
        case["rom_size"],
        case["ram_size"],
        case["country"],
        case["expect"]["at"],
    )


def cases_by_key(cases=None):
    return {key_of_case(case): case for case in (CASES if cases is None else cases)}


def _disagreement(found, case, path):
    for name in CHECKED:
        got = getattr(found, name)
        if case["expect"][name] != got:
            return f"{path.name}: {name} want {case['expect'][name]} got {got}"
    return None


def sweep(where=None, cases=None):
    """How many cartridges were read, how many agreed, and which did not."""
    where = Path(where) if where is not None else cartridges.directory()
    if not where.is_dir():
        return 0, 0, []

    known = cases_by_key(cases)
    read = agreed = 0
    wrong = []

    for path in sorted(where.rglob("*")):
        if path.suffix.lower() not in cartridges.READABLE_SUFFIXES or not path.is_file():
            continue
        try:
            found = header.read(path.read_bytes())
        except header.NoHeader:
            continue

        read += 1
        case = known.get(key_of(found))
        if case is None:
            if len(wrong) < EXAMPLE_LIMIT:
                wrong.append(
                    f"{path.name}: no case for mapping {found.mapping:#04x} at {found.at:#08x}"
                )
            continue

        told = _disagreement(found, case, path)
        if told is None:
            agreed += 1
        elif len(wrong) < EXAMPLE_LIMIT:
            wrong.append(told)

    return read, agreed, wrong


def main(argv):
    where = Path(argv[0]) if argv else cartridges.directory()
    read, agreed, wrong = sweep(where)

    if not read:
        print(f"  no cartridge found under {where}")
        print(f"  {cartridges.WHY_NOT}")
        return 2

    print(f"  {read} cartridges read from {where}")
    print(f"  {agreed} agreed, {read - agreed} did not")
    for line in wrong:
        print(f"    {line}")
    return 1 if read != agreed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
