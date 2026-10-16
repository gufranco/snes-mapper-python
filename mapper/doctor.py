from __future__ import annotations

import json
import os
import platform
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, override

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable, Mapping, Sequence


def _version(where: Path | None = None) -> str:
    found = re.search(
        r"""VERSION\s*[:=][^"']*["']([^"']+)["']""",
        (where or Path(__file__).resolve().parent / "version.py").read_text(),
    )
    return found.group(1) if found else "unknown"


ROOT = Path(__file__).resolve().parent.parent


def _reachable(root: Path = ROOT, path: list[str] | None = None) -> bool:
    where = sys.path if path is None else path
    if str(root) in where:
        return False
    where.insert(0, str(root))
    return True


_reachable()

from mapper import environment, header, models  # noqa: E402

VERSION = _version()

MANIFEST = ROOT / "cartridges.manifest.json"

CORPUS = ROOT / "conformance" / "corpus.json"

DIRECTORY_VARIABLE = "SNES_CARTRIDGE_DIR"

DEFAULT_DIRECTORY = ROOT / "cartridges"

ALONGSIDE = ROOT.parent / "cartridges"

READABLE_SUFFIXES = (".sfc", ".smc")

OLDEST_PYTHON = (3, 12)

TITLE = b"DOCTOR SYNTHETIC IMAGE"[: header.TITLE_BYTES]


class Finding:
    __slots__ = ("advice", "detail", "name", "ok")

    def __init__(self, name: str, ok: bool, detail: str, advice: str | None = None) -> None:
        self.name = name
        self.ok = ok
        self.detail = detail
        self.advice = advice

    @property
    def line(self) -> str:
        return f"  {'ok  ' if self.ok else '   !'}  {self.name}: {self.detail}"

    @property
    def report(self) -> str:
        if self.ok or not self.advice:
            return self.line
        return f"{self.line}\n         {self.advice}"

    @override
    def __repr__(self) -> str:
        return f"<Finding {self.name} {'ok' if self.ok else 'not ok'}>"


def _python() -> Finding:
    return Finding(
        "python",
        sys.version_info[:2] >= OLDEST_PYTHON,
        f"{platform.python_version()} on {platform.system()} {platform.machine()}",
        f"this package needs {OLDEST_PYTHON[0]}.{OLDEST_PYTHON[1]} or newer",
    )


def _package() -> Finding:
    return Finding("mapper", True, f"version {VERSION}")


PROBE: dict[str, tuple[int, int | None]] = {
    "lorom": (0x808000, None),
    "hirom": (0xC00000, None),
    "exhirom": (0xC00000, None),
    "wholebank": (0xC00000, 192),
}


def _model(name: str) -> Finding:
    address, banks = PROBE.get(name, (0x808000, None))
    try:
        one = models.layout_named(name)
        landed = one.resolve(address, banks=banks)
    except Exception as trouble:
        return Finding(
            name,
            False,
            f"{type(trouble).__name__}: {trouble}",
            f"resolving {address:#08x} through this layout failed, which is the finding",
        )
    where = f"{landed.offset:#08x} in {landed.region}" if landed.is_rom else landed.region
    return Finding(
        name,
        landed.is_rom,
        f"header at {one.header_at:#06x}, {address:#08x} lands at {where}, {landed.cycles} clocks",
        f"{address:#08x} should have landed in ROM and landed in {landed.region},"
        " which carries no offset into the image",
    )


def _synthetic() -> bytes:
    rom = bytearray(b"\x00" * 0x10000)
    rom[0x7FC0 : 0x7FC0 + len(TITLE)] = TITLE
    rom[0x7FD5] = 0x20
    rom[0x7FD7] = 0x08
    rom[0x7FDC] = 0xFF
    rom[0x7FDD] = 0xFF
    return bytes(rom)


def _reading(build: Callable[[], bytes] = _synthetic) -> Finding:
    try:
        found = header.read(build())
    except Exception as trouble:
        return Finding(
            "reading a header",
            False,
            f"{type(trouble).__name__}: {trouble}",
            "the reader failed on an image built here, so nothing about a real"
            " cartridge can be trusted from this machine",
        )
    return Finding(
        "reading a header",
        found.title.strip() == TITLE.decode().strip(),
        f"title {found.title.strip()!r}, {found.layout}, at {found.at:#06x}",
        f"the title should have read {TITLE.decode().strip()!r}",
    )


def _manifest(path: Path | str = MANIFEST) -> Finding:
    try:
        held = json.loads(Path(path).read_text())
    except OSError as trouble:
        return Finding(
            "manifest",
            False,
            f"could not be read: {trouble}",
            "the manifest names every cartridge the library check identifies;"
            " without it that check cannot run at all",
        )
    except ValueError as trouble:
        return Finding(
            "manifest",
            False,
            f"is not readable as JSON: {trouble}",
            "the file is here and damaged, which is worse than absent",
        )
    named = held.get("cartridges") or []
    bad = held.get("badDumps") or []
    return Finding(
        "manifest",
        bool(named),
        f"{len(named)} cartridges and {len(bad)} bad dumps named",
        "a manifest naming nothing identifies nothing",
    )


def _corpus(path: Path | str = CORPUS) -> Finding:
    try:
        held = json.loads(Path(path).read_text())
    except OSError as trouble:
        return Finding("corpus", False, f"could not be read: {trouble}")
    except ValueError as trouble:
        return Finding("corpus", False, f"is not readable as JSON: {trouble}")
    cases = held.get("cases") or []
    return Finding(
        "corpus",
        bool(cases),
        f"{len(cases)} recorded cases, measured from {held.get('measured_from', 'not stated')}",
        "a corpus with no cases proves nothing",
    )


def _looking(environment: Mapping[str, str] | None = None) -> list[Finding]:
    held = environment if environment is not None else os.environ
    named = held.get(DIRECTORY_VARIABLE)
    places = [*([Path(named)] if named else []), ALONGSIDE, DEFAULT_DIRECTORY]
    chosen = (
        Path(named) if named else next((one for one in places if one.is_dir()), DEFAULT_DIRECTORY)
    )
    return [
        Finding(
            DIRECTORY_VARIABLE,
            True,
            f"set to {named}" if named else "not set, so the places below are tried in order",
        ),
        Finding("looking in", True, ", ".join(str(one) for one in places)),
        Finding("chosen", True, str(chosen)),
    ]


def _library(where: Path | str, shipped: Path = DEFAULT_DIRECTORY) -> Finding:
    place = Path(where)
    if not place.is_dir():
        return Finding(
            "library",
            True,
            f"none at {place}, so the check against real cartridges will skip rather than run",
        )
    try:
        present = [
            one
            for one in place.rglob("*")
            if one.suffix.lower() in READABLE_SUFFIXES and one.is_file()
        ]
    except OSError as trouble:
        return Finding("library", False, f"could not be read: {trouble}")
    if not present and place == shipped:
        return Finding(
            "library",
            True,
            f"{place} holds no images yet, so the check against real cartridges will skip"
            " rather than run",
        )
    return Finding(
        "library",
        bool(present),
        f"{len(present)} images at {place}"
        if present
        else f"{place} is here and holds nothing this package reads",
        "a directory that is present and empty reads as a library to anything that"
        " only checks the path; either fill it or unset the variable",
    )


def examine(
    environment: Mapping[str, str] | None = None,
    manifest: Path | str = MANIFEST,
    corpus: Path | str = CORPUS,
) -> list[Finding]:
    found = [_python(), _package()]
    found.extend(_model(name) for name in sorted(models.MODELS))
    found.append(_reading())
    found.append(_manifest(manifest))
    found.append(_corpus(corpus))
    where = _looking(environment)
    found.extend(where)
    found.append(_library(where[-1].detail))
    return found


def report(found: Sequence[Finding]) -> list[str]:
    unwell = [one for one in found if not one.ok]
    lines = [f"mapper {VERSION} on {platform.python_version()}, {platform.system()}", ""]
    lines.append("  the machine")
    lines.extend(environment.lines(ROOT))
    lines.append("")
    lines.append("  this package")
    lines.extend(one.report for one in found)
    lines.append("")
    if unwell:
        lines.append(f"  {len(unwell)} of {len(found)} checks did not pass")
    else:
        lines.append(f"  {len(found)} checks, nothing to report")
    return lines


def main(
    argv: Sequence[str] = (),
    examine: Callable[..., list[Finding]] = examine,
    say: Callable[[str], None] = print,
) -> int:
    found = examine()
    for line in report(found):
        say(line)
    return 1 if any(not one.ok for one in found) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
