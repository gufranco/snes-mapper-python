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

SYSTEM_PAGES = 0x8000

SYSTEM_PAGE_SPEEDS = (
    (0x2000, SLOW),
    (0x4000, FAST),
    (0x4200, XSLOW),
    (0x6000, FAST),
    (SYSTEM_PAGES, SLOW),
)

SYSTEM_BANKS = 0x40

LOROM_PAGE = 0x8000
BANK_BYTES = 0x10000

SAVE_RAM_BANKS = range(0x70, 0x7E)
HIROM_SAVE_BANKS = range(0x20, 0x40)
HIROM_SAVE_WINDOW = (0x6000, 0x8000)

FAST_HALF = 0x80

EXHIROM_HALF = 0x400000

WHOLEBANK_WINDOW_FIRST_BANK = 0xC0

WHOLEBANK_BANKS = 0xC0

WHOLEBANK_BYTES = 0xC00000


EXHIROM_BYTES = 0x800000


class Resolution:
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


def _speed(bank: int, page: int, fast: bool) -> int:
    if (bank & 0x7F) < SYSTEM_BANKS and page < SYSTEM_PAGES:
        return next(cycles for end, cycles in SYSTEM_PAGE_SPEEDS if page < end)
    return FAST if fast and bank >= FAST_HALF else SLOW


def _lorom_offset(bank: int, page: int) -> int:
    return ((bank & 0x7F) * LOROM_PAGE) + (page - LOROM_PAGE)


def _hirom_offset(bank: int, page: int) -> int:
    return ((bank & 0x3F) * BANK_BYTES) + page


def _exhirom_offset(bank: int, page: int) -> int:
    return _hirom_offset(bank, page) + (0 if bank & FAST_HALF else EXHIROM_HALF)


def _wholebank_offset(bank: int, page: int, banks: int) -> int:
    return image.address_to_file(bank, page, banks)


def resolve(
    kind: str,
    address: int,
    fast: bool = False,
    banks: int | None = None,
    save: bool = False,
) -> Resolution:
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

    return Resolution(address, region, offset, _speed(bank, page, fast))
