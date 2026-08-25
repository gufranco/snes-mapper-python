"""Look at this machine and say what is actually here, so a report can be believed.

What goes wrong with this package is rarely a defect in it. It is a Python too
old to run it, a cartridge library that was never put where the checks look, or
a library that is there and holds files nothing recognises. All three look the
same from outside: the run is green and it proved less than the reader thinks.

That last one is why this exists here at all. Everything this package claims
about a header was recorded from a retail library, and the check that holds the
recording to the library skips silently when the library is absent. A skip and a
pass print the same thing, and a reader with no library gets the reassurance of
the corpus without the evidence underneath it.

Two rules shape it, and they are the whole point.

Nothing is hidden. A check that fails says what it saw, and a check that itself
throws is caught and reported as what it threw, named by its type. A library
that is absent is reported as absent rather than as a failure, because a fresh
checkout has none and that is the normal state, but it is never reported as
nothing at all.

Nothing is inferred. Every line is something looked at on this machine just now,
including a header actually read out of a synthetic image rather than a claim
that the reader imports.
"""

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
    """The package version, read out of the file beside this one.

    Read rather than imported. Importing it would go through the package, and a
    package that will not import is one of the things this exists to report.
    """
    found = re.search(
        r"""VERSION\s*[:=][^"']*["']([^"']+)["']""",
        (where or Path(__file__).resolve().parent / "version.py").read_text(),
    )
    return found.group(1) if found else "unknown"


ROOT = Path(__file__).resolve().parent.parent

VERSION = _version()

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mapper import header, models  # noqa: E402

MANIFEST = ROOT / "cartridges.manifest.json"

CORPUS = ROOT / "conformance" / "corpus.json"

DIRECTORY_VARIABLE = "SNES_CARTRIDGE_DIR"

DEFAULT_DIRECTORY = ROOT / "cartridges"

ALONGSIDE = ROOT.parent / "cartridges"

READABLE_SUFFIXES = (".sfc", ".smc")

OLDEST_PYTHON = (3, 12)

TITLE = b"DOCTOR SYNTHETIC IMAGE"[: header.TITLE_BYTES]
"""Cut to the width the reader publishes, so nothing is read back truncated.

Taken from the reader rather than counted here. A copy of a width is a second
place for it to be wrong, and this one was wrong the first time it was written."""


class Finding:
    """One thing that was looked at, and what was there."""

    __slots__ = ("advice", "detail", "name", "ok")

    def __init__(self, name: str, ok: bool, detail: str, advice: str | None = None) -> None:
        self.name = name
        self.ok = ok
        self.detail = detail
        self.advice = advice

    @property
    def line(self) -> str:
        """The one-line form, which is what a reader scans."""
        return f"  {'ok  ' if self.ok else '   !'}  {self.name}: {self.detail}"

    @property
    def report(self) -> str:
        """The same, with what to do about it when there is something to do."""
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
"""One address per layout that lands in ROM, with what that layout needs to answer.

Wholebank maps by how large the image is, so resolving one address through it
takes a bank count the others do not need, and it refuses a count too small to
reach the address rather than reading past the end of the file. Passing it here rather than skipping
the layout keeps every published model on a line of its own.
"""


def _model(name: str) -> Finding:
    """That a layout resolves an address, which is the package in one line."""
    address, banks = PROBE.get(name, (0x808000, None))
    try:
        one = models.describe(name)
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
    """An image with one LoROM header in it, built here rather than read."""
    rom = bytearray(b"\x00" * 0x10000)
    rom[0x7FC0 : 0x7FC0 + len(TITLE)] = TITLE
    rom[0x7FD5] = 0x20
    rom[0x7FD7] = 0x08
    rom[0x7FDC] = 0xFF
    rom[0x7FDD] = 0xFF
    return bytes(rom)


def _reading(build: Callable[[], bytes] = _synthetic) -> Finding:
    """That a header is read out of bytes, not merely that the reader imports."""
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
    """How many cartridges the manifest names, or why it could not be read."""
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
    """The recording, which is what runs when there is no library."""
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
    """Everywhere a cartridge is looked for, and which of them is chosen.

    Reported as its own line because a named directory wins even when it is
    empty, which is deliberate and surprising: a typo in the variable becomes a
    run that finds nothing and says so, rather than one that silently falls back
    and reports a pass over the wrong library.
    """
    held = environment if environment is not None else os.environ
    named = held.get(DIRECTORY_VARIABLE)
    places = [*([Path(named)] if named else []), DEFAULT_DIRECTORY, ALONGSIDE]
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


def _library(where: Path | str) -> Finding:
    """Whether a library is there, and whether it holds anything readable.

    The count of files is the line that matters. A directory that exists and
    holds nothing reads as a present library to anything that only checks the
    path, and the check against real cartridges then runs over nothing and
    reports a pass.
    """
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
    """Everything worth looking at on this machine, in the order a reader wants it."""
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
    """The lines a person pastes into an issue."""
    unwell = [one for one in found if not one.ok]
    lines = [f"mapper {VERSION} on {platform.python_version()}, {platform.system()}", ""]
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
