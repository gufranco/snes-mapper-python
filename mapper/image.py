"""Where a byte sits in a file, as opposed to where the console sees it.

`layout` answers what an address is. This answers where it lives on disk, and the
two are not the same question, because a cartridge image is not always stored in
the order the console reads it.

**Interleaved images.** Some dumps store every bank's upper half first and every
lower half afterwards, rather than storing each bank whole. The console never
sees this: it is an artefact of how the dump was taken. Anything that patches a
byte at a known address has to undo it first, and a patch applied to an
interleaved image without undoing it lands half a bank away from where it was
meant to, in another bank's data, silently.

**Windowed banks.** A cartridge larger than the ordinary layout can address
reaches the rest of itself through a window in the high banks, where the two
halves of one bank come from two different runs of the file. The arithmetic is
not hard, and getting it subtly wrong produces an image that boots and then
corrupts one region, which is worse than one that does not boot at all.

Both conversions are exact inverses of themselves, which is what makes them
checkable without a corpus: an address converted to an offset and back must be
the address it started as, for every address in the image.
"""

BANK = 0x10000
HALF = 0x8000

WINDOW_FIRST_BANK = 0xC0
WINDOW_LOW_BASE = 0x80
WINDOW_HIGH_BASE = 0x00


class NotWholeBanks(Exception):
    pass


def bank_count(size):
    """How many banks an image holds, or a refusal if it holds part of one."""
    if size % BANK:
        raise NotWholeBanks(f"{size} is not a whole number of {BANK} byte banks")
    return size // BANK


def snes_to_file(bank, addr, banks):
    """Where an address sits in an interleaved image of that many banks."""
    if addr < HALF:
        return (bank + banks) * HALF + addr
    return bank * HALF + (addr - HALF)


def file_to_snes(offset, banks):
    """Which bank and address an offset in an interleaved image belongs to."""
    block, rest = divmod(offset, HALF)
    if block < banks:
        return block, HALF + rest
    return block - banks, rest


def window_to_file(bank, addr, banks):
    """Where a windowed bank's byte sits, whose halves come from two runs."""
    offset = bank - WINDOW_FIRST_BANK
    base = WINDOW_LOW_BASE if addr < HALF else WINDOW_HIGH_BASE
    return (base + offset + banks) * HALF + (addr & (HALF - 1))


def address_to_file(bank, addr, banks):
    """Where a byte sits, whichever of the two routes its bank takes."""
    if bank >= WINDOW_FIRST_BANK:
        return window_to_file(bank, addr, banks)
    return snes_to_file(bank, addr, banks)


def interleave(logical):
    """Rearrange an image into the order an interleaved dump stores it in."""
    banks = bank_count(len(logical))
    built = bytearray(len(logical))
    for bank in range(banks):
        base = bank * BANK
        built[bank * HALF : (bank + 1) * HALF] = logical[base + HALF : base + BANK]
        built[(bank + banks) * HALF : (bank + banks + 1) * HALF] = logical[base : base + HALF]
    return bytes(built)


def deinterleave(built):
    """Put an interleaved image back into the order the console reads it."""
    banks = bank_count(len(built))
    logical = bytearray(len(built))
    for bank in range(banks):
        base = bank * BANK
        logical[base : base + HALF] = built[(bank + banks) * HALF : (bank + banks + 1) * HALF]
        logical[base + HALF : base + BANK] = built[bank * HALF : (bank + 1) * HALF]
    return bytes(logical)
