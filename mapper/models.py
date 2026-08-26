"""Which cartridge layouts this package covers, and what each one is.

A layout is not a chip. It is how a cartridge wires its ROM into the console's
address space, and the console has no idea which one it is talking to: the
cartridge asserts it through the header and the mapping either works or the game
does not boot. So the catalogue here lists layouts rather than parts, and each
entry is backed by a count of how many real cartridges declare it.

A layout with no cartridges behind it does not belong in this table, because then
its presence would be a guess rather than a measurement.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from .errors import UnknownModelError

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterable

from . import layout as spaces


class Model:
    """One layout: what it is, where its header sits, and how to resolve it."""

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
    """The model of that name, however it happens to be written.

    MODELS is the catalogue and holds one key per model. This is what
    resolves the names people actually write, which include aliases MODELS
    does not carry as keys, and it refuses a name nothing answers to.

    Named for what it hands back rather than for the act of looking, because
    this package has no constructor to fold it into: a model is what
    a caller comes here for.
    """
    found = _BY_ALIAS.get(_normalise(name))
    if found is None:
        raise UnknownModelError(
            f"{name} is not a layout this package covers; it has {', '.join(sorted(MODELS))}"
        )
    return found
