import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from conformance import testcarts  # noqa: E402
from conformance.selftest_code import Unreadable  # noqa: E402
from conformance.selftest_replay import failures, replay  # noqa: E402

RECORD = testcarts.RECORD

SPEC = ROOT / "conformance" / "selftest.json"

MEASURED = ROOT / "conformance" / "selftest_measured.json"

UNREADABLE = "unreadable"


def replayed(rom: bytes, spec: Mapping[str, Mapping[str, str]]) -> dict[str, Any]:
    try:
        return replay(rom, spec)
    except Unreadable as refused:
        return {UNREADABLE: str(refused)}


def present(
    environment: Mapping[str, str] | None, record: Path, tests: Mapping[str, Any]
) -> dict[str, Any]:
    digests = testcarts.wanted(testcarts.load(record))
    found = testcarts.present(testcarts.directory(environment), digests)
    return {name: replayed(rom, tests[name]) for name, rom in found if name in tests}


def problems_with(name: str, found: Mapping[str, Any], held: Mapping[str, Any]) -> list[str]:
    if UNREADABLE in found:
        return [f"{name}: {found[UNREADABLE]}"]
    moved = ["replayed differently from the record"] if held.get(name) != found else []
    return [
        f"{name}: {why}" for why in (*moved, *(f"{part} disagrees" for part in failures(found)))
    ]


def problems(found: Mapping[str, Any], held: Mapping[str, Any]) -> list[str]:
    return [line for name, one in sorted(found.items()) for line in problems_with(name, one, held)]


def report(found: Mapping[str, Any], listed: int, wrong: Sequence[str]) -> None:
    print(f"  {len(found)} of {listed} self-test cartridges present")
    for name, one in sorted(found.items()):
        print(f"  {name}: {'disagrees' if UNREADABLE in one or failures(one) else 'agrees'}")
    for line in wrong:
        print(f"  FAILED {line}")


def main(
    argv: Sequence[str],
    environment: Mapping[str, str] | None = None,
    record: Path = RECORD,
    spec: Path = SPEC,
    measured: Path = MEASURED,
) -> int:
    if not testcarts.understood(argv):
        print("usage: selftest.py [--record out.json]", file=sys.stderr)
        return 2
    tests = testcarts.load(spec)["tests"]
    found = present(environment, record, tests)
    if not found:
        print(
            "  no self-test cartridge present:"
            f" set {testcarts.DIRECTORY_VARIABLE} to a folder holding one"
        )
        return testcarts.NOT_PRESENT
    if len(argv) == 3:
        Path(argv[2]).write_text(json.dumps(found, indent=2, sort_keys=True) + "\n")
    wrong = problems(found, testcarts.load(measured) if len(argv) == 1 else found)
    report(found, len(tests), wrong)
    return 1 if wrong else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
