import hashlib
import json
import os
import sys
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import mapper  # noqa: E402
from mapper.layout import Resolution  # noqa: E402

RECORD = ROOT / "conformance" / "testroms.json"

READINGS = ROOT / "conformance" / "testcarts.json"

DIRECTORY_VARIABLE = "SNES_TEST_CARTRIDGE_DIR"

KEPT = ROOT / "external" / "tools"

SUFFIXES = (".sfc", ".smc")

NOT_PRESENT = 2

RESET_VECTOR = 0x00FFFC

MAPPED = "mapped"
NO_HEADER = "no header"
OUTSIDE = "reset outside the program"

ACCOUNTED = frozenset({MAPPED, NO_HEADER})


def directory(environment: Mapping[str, str] | None = None) -> Path:
    held = os.environ if environment is None else environment
    named = held.get(DIRECTORY_VARIABLE, "").strip()
    return Path(named) if named else KEPT


def wanted(record: Mapping[str, Any]) -> dict[str, str]:
    return {str(entry["sha256"]): str(entry["id"]) for entry in record["cartridges"]}


def present(where: Path, digests: Mapping[str, str]) -> Iterator[tuple[str, bytes]]:
    if not where.is_dir():
        return
    for path in sorted(where.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUFFIXES:
            blob = path.read_bytes()
            name = digests.get(hashlib.sha256(blob).hexdigest())
            if name is not None:
                yield name, blob


def landing(found: Mapping[str, Any]) -> Resolution:
    return mapper.resolve(found["layout"], found["reset"], found["fast"], found["banks"])


def account(found: Mapping[str, Any]) -> str:
    if found["layout"] is None:
        return NO_HEADER
    return MAPPED if landing(found).is_rom else OUTSIDE


def mapped(rom: bytes, header: mapper.Header) -> dict[str, Any]:
    layout = mapper.board(header, len(rom) - header.shift)
    banks = mapper.bank_count(len(rom) - header.shift) if layout == mapper.WHOLEBANK else None
    vector = mapper.resolve(layout, RESET_VECTOR, header.fast, banks)
    assert vector.offset is not None, "every map puts the vectors in the program"
    at = vector.offset + header.shift
    return {
        "size": len(rom),
        "layout": layout,
        "fast": header.fast,
        "banks": banks,
        "shift": header.shift,
        "reset": rom[at] | (rom[at + 1] << 8),
    }


def reading(rom: bytes) -> dict[str, Any]:
    try:
        header = mapper.read(rom)
    except mapper.NoHeader:
        return {"size": len(rom), "layout": None, "account": NO_HEADER}
    found = mapped(rom, header)
    return {**found, "account": account(found)}


def measured(where: Path, record: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {name: reading(blob) for name, blob in present(where, wanted(record))}


def problems_with(name: str, one: Mapping[str, Any], held: Mapping[str, Any]) -> list[str]:
    moved = ["read differently from the record"] if held.get(name) != one else []
    unaccounted = (
        [f"{one['account']}, not accounted for"] if one["account"] not in ACCOUNTED else []
    )
    return [f"{name}: {why}" for why in (*moved, *unaccounted)]


def problems(found: Mapping[str, Any], held: Mapping[str, Any]) -> list[str]:
    return [line for name, one in sorted(found.items()) for line in problems_with(name, one, held)]


def report(found: Mapping[str, Any], listed: int, wrong: Sequence[str]) -> None:
    print(f"  {len(found)} of {listed} test cartridges present")
    for name, one in sorted(found.items()):
        print(f"  {name}: {one['account']}")
    for line in wrong:
        print(f"  FAILED {line}")


def load(path: Path) -> dict[str, Any]:
    held: dict[str, Any] = json.loads(path.read_text())
    return held


def understood(argv: Sequence[str]) -> bool:
    return len(argv) == 1 or (len(argv) == 3 and argv[1] == "--record")


def main(
    argv: Sequence[str],
    environment: Mapping[str, str] | None = None,
    record: Path = RECORD,
    readings: Path = READINGS,
) -> int:
    if not understood(argv):
        print("usage: testcarts.py [--record out.json]", file=sys.stderr)
        return 2
    listed = load(record)
    found = measured(directory(environment), listed)
    if not found:
        print(f"  no test cartridge present: set {DIRECTORY_VARIABLE} to a folder holding one")
        return NOT_PRESENT
    if len(argv) == 3:
        Path(argv[2]).write_text(json.dumps(found, indent=2, sort_keys=True) + "\n")
    wrong = problems(found, load(readings)) if len(argv) == 1 else []
    report(found, len(listed["cartridges"]), wrong)
    return 1 if wrong else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
