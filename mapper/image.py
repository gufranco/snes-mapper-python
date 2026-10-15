from .errors import NotWholeBanks

BANK = 0x10000
HALF = 0x8000

WINDOW_FIRST_BANK = 0xC0
WINDOW_LOW_BASE = 0x80
WINDOW_HIGH_BASE = 0x00


def bank_count(size: int) -> int:
    if size % BANK:
        raise NotWholeBanks(f"{size} is not a whole number of {BANK} byte banks")
    return size // BANK


def snes_to_file(bank: int, addr: int, banks: int) -> int:
    if addr < HALF:
        return (bank + banks) * HALF + addr
    return bank * HALF + (addr - HALF)


def file_to_snes(offset: int, banks: int) -> tuple[int, int]:
    block, rest = divmod(offset, HALF)
    if block < banks:
        return block, HALF + rest
    return block - banks, rest


def window_to_file(bank: int, addr: int, banks: int) -> int:
    offset = bank - WINDOW_FIRST_BANK
    base = WINDOW_LOW_BASE if addr < HALF else WINDOW_HIGH_BASE
    return (base + offset + banks) * HALF + (addr & (HALF - 1))


def address_to_file(bank: int, addr: int, banks: int) -> int:
    if bank >= WINDOW_FIRST_BANK:
        return window_to_file(bank, addr, banks)
    return snes_to_file(bank, addr, banks)


def interleave(logical: bytes) -> bytes:
    banks = bank_count(len(logical))
    built = bytearray(len(logical))
    for bank in range(banks):
        base = bank * BANK
        built[bank * HALF : (bank + 1) * HALF] = logical[base + HALF : base + BANK]
        built[(bank + banks) * HALF : (bank + banks + 1) * HALF] = logical[base : base + HALF]
    return bytes(built)


def deinterleave(built: bytes) -> bytes:
    banks = bank_count(len(built))
    logical = bytearray(len(built))
    for bank in range(banks):
        base = bank * BANK
        logical[base : base + HALF] = built[(bank + banks) * HALF : (bank + banks + 1) * HALF]
        logical[base + HALF : base + BANK] = built[bank * HALF : (bank + 1) * HALF]
    return bytes(logical)
