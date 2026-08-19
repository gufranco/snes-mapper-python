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

LOROM = "lorom"
HIROM = "hirom"
EXHIROM = "exhirom"

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

EXHIROM_BYTES = 0x800000
"""The most an extended cartridge can reach: eight megabytes, sixty four megabit.

Four through `$80-$FF` and four through `$00-$7D`, and the very top of the far half
is reachable only through banks `$3E` and `$3F`, because `$7E` and `$7F` are work
RAM and never leave the console.

An image larger than this is not addressable by this layout however it is declared.
The ninety six megabit files that exist are decompressed rebuilds of an S-DD1
cartridge, which is a low layout with a decompressor rather than a wider map, so
their size says nothing about how far a bank can reach.
"""


class Resolution:
    """What one address turned out to be."""

    def __init__(self, address, region, offset, cycles):
        self.address = address
        self.region = region
        self.offset = offset
        self.cycles = cycles

    @property
    def is_rom(self):
        return self.region == ROM

    def __repr__(self):
        return f"<{self.region} at {self.address:06X}, {self.cycles} clocks>"


def _speed(bank, page, region, fast):
    if region == REGISTERS and REGISTER_WINDOW[0] <= page < 0x4000:
        return FAST if fast and bank >= FAST_HALF else SLOW
    if region == REGISTERS:
        return XSLOW
    if region == WORK_RAM:
        return SLOW
    return FAST if fast and bank >= FAST_HALF else SLOW


def _lorom_offset(bank, page):
    return ((bank & 0x7F) * LOROM_PAGE) + (page - LOROM_PAGE)


def _hirom_offset(bank, page):
    return ((bank & 0x3F) * BANK_BYTES) + page


def _exhirom_offset(bank, page):
    """The high offset, moved into the far half for every bank below `$80`."""
    return _hirom_offset(bank, page) + (0 if bank & FAST_HALF else EXHIROM_HALF)


def resolve(kind, address, fast=False):
    """What sits at that address under that layout, and what reaching it costs.

    The order of the tests is the point. Work RAM is decided before anything
    else, because its banks look like cartridge banks and are not. The register
    window is decided next, because it overlaps the part of a low bank that would
    otherwise be a mirror. Only what survives both is cartridge.
    """
    address &= 0xFFFFFF
    bank = address >> 16
    page = address & 0xFFFF

    if bank in WORK_RAM_BANKS or ((bank & 0x7F) < 0x40 and page < WORK_RAM_MIRROR):
        region, offset = WORK_RAM, None
    elif (bank & 0x7F) < 0x40 and REGISTER_WINDOW[0] <= page < REGISTER_WINDOW[1]:
        region, offset = REGISTERS, None
    elif (kind == LOROM and (bank & 0x7F) in SAVE_RAM_BANKS) or (
        kind in (HIROM, EXHIROM)
        and (bank & 0x7F) in HIROM_SAVE_BANKS
        and (HIROM_SAVE_WINDOW[0] <= page < HIROM_SAVE_WINDOW[1])
    ):
        region, offset = SAVE_RAM, None
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
