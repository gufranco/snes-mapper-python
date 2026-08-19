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
test, because the stub itself is not standardised: a file whose length is a whole
number of half-banks plus 512 has one, and a file whose length is a whole number
of half-banks does not.
"""

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
"""The band the declared size has to land in to count towards a header.

Both ends are measured rather than reasoned. Across 7,314 cartridges the byte at
the right offset lands in 8 to 13 in 98.85% of them, and at a wrong offset in 3.18%
of them, which is what makes it worth a point at all.

The upper end used to be 14. Not one cartridge declares 14, and fifteen wrong
offsets do, so raising the ceiling only ever awarded points to data pretending to be
a header. Lowering the floor was measured too and is not worth it: going down to 7
picks up seven more real cartridges and twelve more wrong offsets, and going to 6
picks up one more of each. Fifty five cartridges declare nothing at all, and the
other three signals are what find those.
"""

DECLARED_HIGH_NIBBLES = (0x2, 0x3)
"""The two high nibbles every real mapping byte carries.

Ten mapping bytes exist and all of them are 0x2x or 0x3x. A byte outside that
range is not a mapping byte at all, and the usual reason is a title of twenty two
characters overflowing its twenty one byte field and writing its last letter here.
Contra III leaves an S, Krusty's Super Fun House and Space Football leave an E,
and the low nibble of a letter names a layout the cartridge does not have.

Across 7,314 cartridges 98.47% carry a byte in this range. Of the 112 that do not,
51 were being given the wrong layout, the wrong bus speed, or both.
"""

FAMILY_OF_OFFSET = {
    LOROM_HEADER: LOROM,
    HIROM_HEADER: HIROM,
    EXHIROM_HEADER: EXHIROM,
}
"""What the place a header sits says, for when the byte that should say is junk.

Only consulted for an undeclared mapping byte. A declared one is believed even
where it disagrees with the offset, because ExHiROM puts its header where HiROM
does whenever the image is small enough that the far copy would sit past the end.
"""

FAST_BIT = 0x10

BATTERY_CHIPSETS = frozenset({0x02, 0x05, 0x06, 0x09, 0x0A})
COPROCESSOR_FROM = 0x03

LOROM_REACH = 0x400000
"""How far the ordinary low map gets: 128 banks of a thirty two kilobyte page."""

WHOLEBANK_BYTES = 0xC00000
"""The one size the whole-bank map has: 192 banks, twelve megabytes.

Size is the whole test, and it is an equality rather than a threshold. The window
those 192 banks open is only inside the file at 192 banks or more, and 192 is also
all the address space leaves below it, so the map has exactly one shape.

The chipset byte was tried here first and is wrong twice over. A cartridge that had
its coprocessor removed declares no chipset at all, so the byte misses every
expansion, which is the case this exists for. And every cartridge that does declare
S-DD1 is smaller than this: those reach past the low map by having the chip switch
banks, which is a different mechanism that this package does not model. Reading the
byte as the signal would have put Star Ocean's retail six megabyte cartridge on a
map whose window addresses a megabyte past the end of it.

The byte being stale is then somebody else's problem rather than one to guard
against here. An expansion built from a cartridge that had one often still claims
it, because clearing the field is a separate act from removing the part, and this
never reads the field.
"""

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
    def declared(self):
        """Whether the byte at the mapping position is a mapping byte at all."""
        return (self.mapping >> 4) in DECLARED_HIGH_NIBBLES

    @property
    def layout(self):
        if self.declared:
            return LAYOUTS.get(self.mapping & 0x0F, LOROM)
        return FAMILY_OF_OFFSET.get(self.at - self.shift, LOROM)

    @property
    def shift(self):
        """How far a copier stub pushed this header past the offset it belongs at."""
        return COPIER_BYTES if self.at - COPIER_BYTES in FAMILY_OF_OFFSET else 0

    @property
    def fast(self):
        """Whether the cartridge asks for the faster of the two bus speeds."""
        return self.declared and bool(self.mapping & FAST_BIT)

    @property
    def coprocessor(self):
        return self.chipset >= COPROCESSOR_FROM

    @property
    def battery(self):
        return self.chipset in BATTERY_CHIPSETS

    def __repr__(self):
        return f"<Header {self.title!r} {self.layout} at {self.at:#08x}>"


def stub_by_length(size):
    """Whether a file of that length carries a copier stub.

    The test is only ever a length test, so it is written as one. Anything
    deciding how a file is packaged can then answer without reading it, which on
    a library that runs to gigabytes is the whole cost of the question.
    """
    if size <= COPIER_BYTES:
        return False
    return (size - COPIER_BYTES) % HALF_BANK == 0 or size % HALF_BANK == COPIER_BYTES


def has_copier_stub(rom):
    """Whether a dump carries the 512 bytes a copier wrote in front of it."""
    return stub_by_length(len(rom))


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
    if SMALLEST_PLAUSIBLE_SIZE <= raw[23] <= LARGEST_PLAUSIBLE_SIZE:
        points += 1
    if (found.mapping & 0x0F) in LAYOUTS and _sits_where_it_says(found, at):
        points += 1

    return points


def offsets(rom):
    """Every place a header could be, including past a copier stub."""
    shift = COPIER_BYTES if has_copier_stub(rom) else 0
    return [candidate + shift for candidate in CANDIDATES]


def board(found, size):
    """Which map a cartridge actually uses, given its header and how large it is.

    The header alone cannot say. The whole-bank map and the ordinary low map declare
    the same byte, because the second is what the first grew out of and nobody
    changed the field. What separates them is length: the wider map has exactly one
    shape, twelve megabytes, so an image of that length on a low declaration is on
    it and any other length is not.

    A cartridge declaring anything other than a low layout is left alone. This
    answers one question, and a high or extended or coprocessor declaration already
    answered it.
    """
    if found.layout != LOROM:
        return found.layout
    return WHOLEBANK if size == WHOLEBANK_BYTES else LOROM


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
