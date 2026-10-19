from __future__ import annotations

from typing import TYPE_CHECKING, override

from .errors import UnknownModelError

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterable

from . import layout as spaces


class Model:
    __slots__ = ("aliases", "header_at", "name", "summary")

    def __init__(
        self, name: str, summary: str, header_at: int, aliases: Iterable[str] = ()
    ) -> None:
        self.name = name
        self.summary = summary
        self.header_at = header_at
        self.aliases = tuple(aliases)

    def resolve(
        self,
        address: int,
        fast: bool = False,
        banks: int | None = None,
        save: bool = False,
    ) -> spaces.Resolution:
        return spaces.resolve(self.name, address, fast=fast, banks=banks, save=save)

    @override
    def __repr__(self) -> str:
        return f"<Model {self.name}, header at {self.header_at:#06x}>"


_CATALOGUE = (
    Model(
        name=spaces.LOROM,
        summary=(
            "The common layout. Each bank maps a thirty two kilobyte page into the "
            "upper half of its address space, leaving the lower half to work RAM, "
            "registers and save memory."
        ),
        header_at=0x7FC0,
        aliases=("lo", "mode20", "20"),
    ),
    Model(
        name=spaces.HIROM,
        summary=(
            "A whole bank of cartridge per bank in the upper half of the space, with "
            "save memory windowed into the middle of the lower banks."
        ),
        header_at=0xFFC0,
        aliases=("hi", "mode21", "21"),
    ),
    Model(
        name=spaces.EXHIROM,
        summary=(
            "The same as the high layout with a second set of banks reached above it, "
            "used by the handful of cartridges that outgrew four megabytes."
        ),
        header_at=0xFFC0,
        aliases=("exhi", "mode25", "25"),
    ),
    Model(
        name=spaces.WHOLEBANK,
        summary=(
            "Every bank below the window carries a whole sixty four kilobytes, from an "
            "image that stores all the upper halves and then all the lower ones. It is "
            "the only map that reaches twelve megabytes, and it is named for its shape "
            "rather than for any chip, because a cartridge lands here whether it has a "
            "coprocessor, had one removed, or never had one."
        ),
        header_at=0x7FC0,
        aliases=("whole", "wholebanks", "interleaved"),
    ),
    Model(
        name=spaces.SA1,
        summary=(
            "The SA-1's own memory controller, at the bank settings its registers hold "
            "before anything writes them: four eight megabit blocks in order, each a "
            "thirty two kilobyte page per bank below the window and a whole bank above "
            "it, with backup RAM in banks $40 to $4F and its own registers and work RAM "
            "inside the console's register window."
        ),
        header_at=0x7FC0,
        aliases=("mode23", "23"),
    ),
    Model(
        name=spaces.SPC7110,
        summary=(
            "The SPC7110's program ROM in the first megabyte of the image, a whole bank "
            "per bank from $C0 and in the upper half of $00 to $0F, and its data ROM "
            "behind it, as one second implementation reads the board before the game "
            "selects its data banks."
        ),
        header_at=0xFFC0,
    ),
)

MODELS = {model.name: model for model in _CATALOGUE}

_BY_ALIAS = {}
for _model in _CATALOGUE:
    _BY_ALIAS[_model.name] = _model
    for _alias in _model.aliases:
        _BY_ALIAS[_alias] = _model


def _normalise(name: str) -> str:
    return str(name).strip().lower().replace("-", "").replace("_", "")


def layout_named(name: str) -> Model:
    found = _BY_ALIAS.get(_normalise(name))
    if found is None:
        raise UnknownModelError(
            f"{name} is not a layout this package covers; it has {', '.join(sorted(MODELS))}"
        )
    return found
