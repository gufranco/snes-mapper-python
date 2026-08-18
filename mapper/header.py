"""The cartridge header, and working out which of the candidate places it is in.

A SNES cartridge carries thirty two bytes describing itself: a title, how the
ROM is mapped into the address space, which coprocessor is fitted, how much ROM
and save memory there is, and a checksum with its complement. Everything the rest
of this package does starts here, because the mapping byte decides where every
address lands.

The awkward part is that the header has no fixed home. It sits at a different
offset depending on the layout it describes, which is circular: you cannot know
where to look without knowing the answer you are looking for. So every candidate
is scored on how much it looks like a header, and the best one wins. That is what
every emulator does, and it is why two of them occasionally disagree about an
unusual cartridge.

Some dumps also carry a copier stub in front of the image, which shifts every
offset by a fixed amount. Detecting it is a length test rather than a content
test, because the stub itself is not standardised.
"""

LOROM_HEADER = 0x7FC0
HIROM_HEADER = 0xFFC0
EXHIROM_HEADER = 0x40FFC0

CANDIDATES = (LOROM_HEADER, HIROM_HEADER, EXHIROM_HEADER)

COPIER_BYTES = 0x200

HEADER_BYTES = 32
TITLE_BYTES = 21

LOROM = "lorom"
HIROM = "hirom"
EXHIROM = "exhirom"
SA1 = "sa1"
SPC7110 = "spc7110"

LAYOUTS = {
    0x00: LOROM,
    0x01: HIROM,
    0x02: LOROM,
    0x03: SA1,
    0x05: EXHIROM,
    0x0A: SPC7110,
}

FAST_BIT = 0x10

BATTERY_CHIPSETS = frozenset({0x02, 0x05, 0x06, 0x09, 0x0A})
COPROCESSOR_FROM = 0x03

MINIMUM_SCORE = 2


class NoHeader(Exception):
    pass


class Header:
    """What a cartridge says about itself, and where it said it."""

    def __init__(self, at, raw):
        self.at = at
        self.raw = bytes(raw)

    @property
    def title(self):
        held = self.raw[:TITLE_BYTES]
        return held.decode("ascii", "replace").rstrip(" \x00")

    @property
    def mapping(self):
        return self.raw[21]

    @property
    def chipset(self):
        return self.raw[22]

    @property
    def rom_bytes(self):
        """The declared size. The byte is a power of two in kilobytes, not bytes."""
        return (1 << self.raw[23]) * 1024 if self.raw[23] else 0

    @property
    def ram_bytes(self):
        return (1 << self.raw[24]) * 1024 if self.raw[24] else 0

    @property
    def country(self):
        return self.raw[25]

    @property
    def complement(self):
        return self.raw[28] | (self.raw[29] << 8)

    @property
    def checksum(self):
        return self.raw[30] | (self.raw[31] << 8)

    @property
    def checksum_agrees(self):
        """Whether the checksum and its complement are consistent with each other."""
        return self.checksum ^ self.complement == 0xFFFF

    @property
    def layout(self):
        return LAYOUTS.get(self.mapping & 0x0F, LOROM)

    @property
    def fast(self):
        """Whether the cartridge asks for the faster of the two bus speeds."""
        return bool(self.mapping & FAST_BIT)

    @property
    def coprocessor(self):
        return self.chipset >= COPROCESSOR_FROM

    @property
    def battery(self):
        return self.chipset in BATTERY_CHIPSETS

    def __repr__(self):
        return f"<Header {self.title!r} {self.layout} at {self.at:#08x}>"


def _sits_where_it_says(found, at):
    """Whether the layout this header claims would put it at this offset."""
    if found.layout in (LOROM, SA1):
        return (at & 0xFFFF) == LOROM_HEADER
    return (at & 0xFFFF) == (HIROM_HEADER & 0xFFFF)


def _printable(held):
    return sum(1 for byte in held if 0x20 <= byte < 0x7F)


def score(rom, at):
    """How much the bytes at that offset look like a header rather than data.

    Four signals, each worth a point. A title that reads as text, a checksum
    consistent with its complement, a declared ROM size that is plausible, and a
    mapping byte naming a layout that would put the header where it was found. No
    single one is decisive, which is why they are counted rather than tested.
    """
    if at + HEADER_BYTES > len(rom):
        return -1

    raw = rom[at : at + HEADER_BYTES]
    found = Header(at, raw)
    points = 0

    if _printable(raw[:TITLE_BYTES]) >= TITLE_BYTES - 2:
        points += 1
    if found.checksum_agrees and found.checksum:
        points += 1
    if 8 <= raw[23] <= 14:
        points += 1
    if (found.mapping & 0x0F) in LAYOUTS and _sits_where_it_says(found, at):
        points += 1

    return points


def offsets(rom):
    """Every place a header could be, including past a copier stub."""
    shift = COPIER_BYTES if len(rom) % 0x8000 == COPIER_BYTES else 0
    return [candidate + shift for candidate in CANDIDATES]


def read(rom):
    """The header this cartridge carries, chosen from the candidate places."""
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
