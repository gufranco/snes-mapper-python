from __future__ import annotations

from typing import override

from .errors import NoHeader

LOROM_HEADER = 0x7FC0
HIROM_HEADER = 0xFFC0
EXHIROM_HEADER = 0x40FFC0

CANDIDATES = (LOROM_HEADER, HIROM_HEADER, EXHIROM_HEADER)

COPIER_BYTES = 0x200
HALF_BANK = 0x8000

HEADER_BYTES = 32
TITLE_BYTES = 21

LOROM = "lorom"
HIROM = "hirom"
EXHIROM = "exhirom"
SA1 = "sa1"
SPC7110 = "spc7110"
WHOLEBANK = "wholebank"

LAYOUTS = {
    0x00: LOROM,
    0x01: HIROM,
    0x02: LOROM,
    0x03: SA1,
    0x05: EXHIROM,
    0x0A: SPC7110,
}

SMALLEST_PLAUSIBLE_SIZE = 8
LARGEST_PLAUSIBLE_SIZE = 13

DECLARED_HIGH_NIBBLES = (0x2, 0x3)

FAMILY_OF_OFFSET = {
    LOROM_HEADER: LOROM,
    HIROM_HEADER: HIROM,
    EXHIROM_HEADER: EXHIROM,
}

FAST_BIT = 0x10

BATTERY_CHIPSETS = frozenset({0x02, 0x05, 0x06, 0x09, 0x0A})
COPROCESSOR_FROM = 0x03

LOROM_REACH = 0x400000

WHOLEBANK_BYTES = 0xC00000

MINIMUM_SCORE = 2


class Header:
    __slots__ = ("at", "raw")

    def __init__(self, at: int, raw: bytes) -> None:
        self.at = at
        self.raw = bytes(raw)

    @property
    def title(self) -> str:
        held = self.raw[:TITLE_BYTES]
        return held.decode("ascii", "replace").rstrip(" \x00")

    @property
    def mapping(self) -> int:
        return self.raw[21]

    @property
    def chipset(self) -> int:
        return self.raw[22]

    @property
    def rom_bytes(self) -> int:
        return (1 << self.raw[23]) * 1024 if self.raw[23] else 0

    @property
    def ram_bytes(self) -> int:
        return (1 << self.raw[24]) * 1024 if self.raw[24] else 0

    @property
    def country(self) -> int:
        return self.raw[25]

    @property
    def complement(self) -> int:
        return self.raw[28] | (self.raw[29] << 8)

    @property
    def checksum(self) -> int:
        return self.raw[30] | (self.raw[31] << 8)

    @property
    def checksum_agrees(self) -> bool:
        return self.checksum ^ self.complement == 0xFFFF

    @property
    def declared(self) -> bool:
        return (self.mapping >> 4) in DECLARED_HIGH_NIBBLES

    @property
    def layout(self) -> str:
        if self.declared:
            return LAYOUTS.get(self.mapping & 0x0F, LOROM)
        return FAMILY_OF_OFFSET.get(self.at - self.shift, LOROM)

    @property
    def shift(self) -> int:
        return COPIER_BYTES if self.at - COPIER_BYTES in FAMILY_OF_OFFSET else 0

    @property
    def fast(self) -> bool:
        return self.declared and bool(self.mapping & FAST_BIT)

    @property
    def coprocessor(self) -> bool:
        return self.chipset >= COPROCESSOR_FROM

    @property
    def battery(self) -> bool:
        return self.chipset in BATTERY_CHIPSETS

    @override
    def __repr__(self) -> str:
        return f"<Header {self.title!r} {self.layout} at {self.at:#08x}>"


def stub_by_length(size: int) -> bool:
    if size <= COPIER_BYTES:
        return False
    return (size - COPIER_BYTES) % HALF_BANK == 0 or size % HALF_BANK == COPIER_BYTES


def has_copier_stub(rom: bytes) -> bool:
    return stub_by_length(len(rom))


def _sits_where_it_says(found: Header, at: int) -> bool:
    if found.layout in (LOROM, SA1):
        return (at & 0xFFFF) == LOROM_HEADER
    return (at & 0xFFFF) == (HIROM_HEADER & 0xFFFF)


def _printable(held: bytes) -> int:
    return sum(1 for byte in held if 0x20 <= byte < 0x7F)


def score(rom: bytes, at: int) -> int:
    if at + HEADER_BYTES > len(rom):
        return -1

    raw = rom[at : at + HEADER_BYTES]
    found = Header(at, raw)
    points = 0

    if _printable(raw[:TITLE_BYTES]) >= TITLE_BYTES - 2:
        points += 1
    if found.checksum_agrees and found.checksum:
        points += 1
    if SMALLEST_PLAUSIBLE_SIZE <= raw[23] <= LARGEST_PLAUSIBLE_SIZE:
        points += 1
    if (found.mapping & 0x0F) in LAYOUTS and _sits_where_it_says(found, at):
        points += 1

    return points


def offsets(rom: bytes) -> list[int]:
    shift = COPIER_BYTES if has_copier_stub(rom) else 0
    return [candidate + shift for candidate in CANDIDATES]


def board(found: Header, size: int) -> str:
    if found.layout != LOROM:
        return found.layout
    return WHOLEBANK if size == WHOLEBANK_BYTES else LOROM


def read(rom: bytes) -> Header:
    best = None
    best_score = MINIMUM_SCORE - 1
    for at in offsets(rom):
        points = score(rom, at)
        if points > best_score:
            best = at
            best_score = points

    if best is None or best_score < MINIMUM_SCORE:
        raise NoHeader(f"no header found in {len(rom)} bytes")
    return Header(best, rom[best : best + HEADER_BYTES])
