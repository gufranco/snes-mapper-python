"""Where an address lands, and how long the console takes to get there.

This is the layer that decides whether `$7E:0900` is cartridge or work RAM,
whether `$420B` is a graphics register or a transfer register, and whether a
patch written at one offset will be read back at the address it was meant for.

Every one of those questions has a wrong answer that looks right. Banks `$7E`
and `$7F` are work RAM and belong to no cartridge, but they sit in the middle of
the bank numbering and read like ordinary addresses. The bottom eight kilobytes
of every low bank mirror the start of that work RAM. The transfer registers live
in the CPU's own window rather than beside the graphics registers they feed. Each
of those has cost real debugging time, which is why they are a table here instead
of a rule someone has to remember.

Speed is part of the answer rather than a separate question. The same cartridge
byte takes six master clocks through the upper half of the space and eight
through the lower half, and only when the cartridge asked for it in its header.
Anything that counts cycles has to resolve the address first.
"""

from __future__ import annotations

from typing import override

from mapper import image

from .errors import NeedsBankCount

LOROM = "lorom"
HIROM = "hirom"
EXHIROM = "exhirom"
WHOLEBANK = "wholebank"

ROM = "rom"
WORK_RAM = "work-ram"
SAVE_RAM = "save-ram"
REGISTERS = "registers"
OPEN_BUS = "open-bus"

REGIONS = frozenset({ROM, WORK_RAM, SAVE_RAM, REGISTERS, OPEN_BUS})

FAST = 6
SLOW = 8
XSLOW = 12

WORK_RAM_BANKS = (0x7E, 0x7F)
WORK_RAM_MIRROR = 0x2000

REGISTER_WINDOW = (0x2000, 0x6000)

LOROM_PAGE = 0x8000
BANK_BYTES = 0x10000

SAVE_RAM_BANKS = range(0x70, 0x7E)
HIROM_SAVE_BANKS = range(0x20, 0x40)
HIROM_SAVE_WINDOW = (0x6000, 0x8000)

FAST_HALF = 0x80

EXHIROM_HALF = 0x400000
"""How far into the image the banks the console boots from actually point.

The extended layout is the plain high one with its two halves swapped. Banks
`$80-$FF` carry the first four megabytes, and banks `$00-$7D`, which include the
ones holding the reset vector, carry everything past them. That swap is why an
extended cartridge keeps its header at `0x40FFC0`: `$00:FFC0` is what the console
reads, and under this layout that address lands four megabytes into the file.

Treating the two layouts as one caps every image at four megabytes and sends every
address in the lower banks to the wrong half of anything larger.
"""

WHOLEBANK_WINDOW_FIRST_BANK = 0xC0
"""Where the map stops taking banks straight through and opens its window."""

WHOLEBANK_BANKS = 0xC0
"""How many banks this map needs, which is the same 192 the window starts at.

Not a convention. The window's lower halves are read from the run belonging to
bank `$80` onwards, so the topmost byte it names sits at `(191 + banks)` half-banks
into the file while the file itself is `2 * banks` half-banks long. Those meet at
exactly 192, and below it the window addresses bytes past the end of the image.

So this is a twelve megabyte shape rather than a family of sizes. A smaller
cartridge that reaches past the ordinary low map does it with a coprocessor
switching banks, which is a different mechanism and is not this.
"""

WHOLEBANK_BYTES = 0xC00000
"""Twelve megabytes, ninety six megabit, which is what this map reaches.

Neither extended layout gets past eight, because both spend a bank's lower half on
the system area or on a mirror. This one spends nothing below the window: every
bank there carries a whole sixty four kilobytes, so 192 banks of cartridge fit in
the address space and the file holds all of them.

It is named for its shape rather than for a chip, because the shape is all there
is to it. The S-DD1 boards were the first to need it and are where it was first
measured, but nothing in the arithmetic mentions a coprocessor and nothing about
it is reserved to one. Any cartridge that needs more room than the extended
layouts reach can be built this way.

That matters most in the direction the traffic actually runs. Taking a coprocessor
out of a cartridge, by baking what it answered into a table, makes the image larger
and leaves the map alone: the expansion ends up here, and it declares no chipset at
all because there is no longer a chip to declare. So a cartridge on this map may
carry a coprocessor, may have carried one until somebody removed it, or may never
have had one. The map does not say, and it does not need to.
"""


EXHIROM_BYTES = 0x800000
"""The most an extended cartridge can reach: eight megabytes, sixty four megabit.

Four through `$80-$FF` and four through `$00-$7D`, and the very top of the far half
is reachable only through banks `$3E` and `$3F`, because `$7E` and `$7F` are work
RAM and never leave the console.

An image larger than this is not addressable by this layout however it is declared.
Anything past eight megabytes is built on the whole-bank map instead, which reaches
twelve by spending no part of a bank on anything but cartridge.
"""


class Resolution:
    """What one address turned out to be."""

    __slots__ = ("address", "cycles", "offset", "region")

    def __init__(self, address: int, region: str, offset: int | None, cycles: int) -> None:
        self.address = address
        self.region = region
        self.offset = offset
        self.cycles = cycles

    @property
    def is_rom(self) -> bool:
        return self.region == ROM

    @override
    def __repr__(self) -> str:
        return f"<{self.region} at {self.address:06X}, {self.cycles} clocks>"


def _speed(bank: int, page: int, region: str, fast: bool) -> int:
    if region == REGISTERS and REGISTER_WINDOW[0] <= page < 0x4000:
        return FAST if fast and bank >= FAST_HALF else SLOW
    if region == REGISTERS:
        return XSLOW
    if region == WORK_RAM:
        return SLOW
    return FAST if fast and bank >= FAST_HALF else SLOW


def _lorom_offset(bank: int, page: int) -> int:
    return ((bank & 0x7F) * LOROM_PAGE) + (page - LOROM_PAGE)


def _hirom_offset(bank: int, page: int) -> int:
    return ((bank & 0x3F) * BANK_BYTES) + page


def _exhirom_offset(bank: int, page: int) -> int:
    """The high offset, moved into the far half for every bank below `$80`."""
    return _hirom_offset(bank, page) + (0 if bank & FAST_HALF else EXHIROM_HALF)


def _wholebank_offset(bank: int, page: int, banks: int) -> int:
    """Where a whole-bank byte sits, which depends on how large the image is.

    The bank count is not optional here even though it is optional in resolve():
    resolve refuses this layout without one, so by the time this is reached the
    count exists. Saying so in the signature puts the invariant where a reader
    trips over it rather than in a comment three functions away.

    The arithmetic is the file placement in `image`, because it is the same
    question asked from the other end: that module answers where a byte goes when
    an image is written, and this answers what the console finds when it reads.
    Two copies of one rule drift, so there is one.
    """
    return image.address_to_file(bank, page, banks)


def resolve(
    kind: str,
    address: int,
    fast: bool = False,
    banks: int | None = None,
    save: bool = False,
) -> Resolution:
    """What sits at that address under that layout, and what reaching it costs.

    The order of the tests is the point. Work RAM is decided before anything
    else, because its banks look like cartridge banks and are not. The register
    window is decided next, because it overlaps the part of a low bank that would
    otherwise be a mirror. Only what survives both is cartridge.

    `banks` is how many whole banks the image holds, and the whole-bank map needs it
    because its two runs sit one image apart. `save` says the cartridge carries
    battery-backed memory, which takes a window that map would otherwise fill with
    cartridge; an expansion built to drop a coprocessor usually carries none.
    """
    if kind == WHOLEBANK:
        if banks is None:
            raise NeedsBankCount(
                f"{WHOLEBANK} maps an address by how large the image is, so resolving one"
                " needs the bank count: image.bank_count(len(rom))"
            )
        if banks < WHOLEBANK_BANKS:
            raise NeedsBankCount(
                f"{WHOLEBANK} needs {WHOLEBANK_BANKS} banks and this image has {banks}."
                " Below that the window reads past the end of the file, so a smaller"
                " cartridge reaching past the low map is switching banks with a"
                " coprocessor rather than using this map"
            )

    address &= 0xFFFFFF
    bank = address >> 16
    page = address & 0xFFFF

    if bank in WORK_RAM_BANKS or ((bank & 0x7F) < 0x40 and page < WORK_RAM_MIRROR):
        region, offset = WORK_RAM, None
    elif (bank & 0x7F) < 0x40 and REGISTER_WINDOW[0] <= page < REGISTER_WINDOW[1]:
        region, offset = REGISTERS, None
    elif (
        kind in (LOROM, WHOLEBANK)
        and (bank & 0x7F) in SAVE_RAM_BANKS
        and (kind != WHOLEBANK or save)
    ) or (
        kind in (HIROM, EXHIROM)
        and (bank & 0x7F) in HIROM_SAVE_BANKS
        and (HIROM_SAVE_WINDOW[0] <= page < HIROM_SAVE_WINDOW[1])
    ):
        region, offset = SAVE_RAM, None
    elif kind == WHOLEBANK:
        assert banks is not None, "the guard above refuses this layout without a bank count"
        region, offset = ROM, _wholebank_offset(bank, page, banks)
    elif kind == LOROM:
        if page < LOROM_PAGE:
            region, offset = OPEN_BUS, None
        else:
            region, offset = ROM, _lorom_offset(bank, page)
    elif kind == EXHIROM:
        region, offset = ROM, _exhirom_offset(bank, page)
    else:
        region, offset = ROM, _hirom_offset(bank, page)

    return Resolution(address, region, offset, _speed(bank, page, region, fast))
