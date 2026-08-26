"""The SNES cartridge memory map and its transfer engine.

    from mapper import read, resolve

    cartridge = read(open("game.sfc", "rb").read())
    resolve(cartridge.layout, 0x7E0900).region
    # 'work-ram', not cartridge

Every defect this package exists to catch is an address question rather than a
processor one: whether a bank is cartridge or work RAM, whether a register
belongs to the processor or the display, and whether a transfer channel was ever
armed.

Reassembling a dump, and rewriting what a cartridge says about itself, are
separate jobs and live in `snes-rom-image` rather than here. This package answers
where an address lands; that one answers what the file containing it is.
"""

from . import models as models
from .errors import (
    NeedsBankCount,
    NoHeader,
    NotWholeBanks,
    UnknownModelError,
)
from .header import (
    COPIER_BYTES,
    EXHIROM,
    HIROM,
    HIROM_HEADER,
    LOROM,
    LOROM_HEADER,
    WHOLEBANK,
    Header,
    board,
    has_copier_stub,
    read,
    score,
    stub_by_length,
)
from .image import (
    BANK,
    HALF,
    WINDOW_FIRST_BANK,
    address_to_file,
    bank_count,
    deinterleave,
    file_to_snes,
    interleave,
    snes_to_file,
    window_to_file,
)
from .layout import (
    FAST,
    OPEN_BUS,
    REGISTERS,
    ROM,
    SAVE_RAM,
    SLOW,
    WHOLEBANK_BANKS,
    WHOLEBANK_BYTES,
    WORK_RAM,
    XSLOW,
    resolve,
)
from .models import MODELS, layout_named
from .transfer import CHANNEL_BASE, CHANNEL_COUNT, ENABLE, Channel, Engine, Plan, channel_of
from .version import VERSION

__version__ = VERSION

__all__ = [
    "BANK",
    "CHANNEL_BASE",
    "CHANNEL_COUNT",
    "COPIER_BYTES",
    "ENABLE",
    "EXHIROM",
    "FAST",
    "HALF",
    "HIROM",
    "HIROM_HEADER",
    "LOROM",
    "LOROM_HEADER",
    "MODELS",
    "OPEN_BUS",
    "REGISTERS",
    "ROM",
    "SAVE_RAM",
    "SLOW",
    "WHOLEBANK",
    "WHOLEBANK_BANKS",
    "WHOLEBANK_BYTES",
    "WINDOW_FIRST_BANK",
    "WORK_RAM",
    "XSLOW",
    "Channel",
    "Engine",
    "Header",
    "NeedsBankCount",
    "NoHeader",
    "NotWholeBanks",
    "Plan",
    "UnknownModelError",
    "__version__",
    "address_to_file",
    "bank_count",
    "board",
    "channel_of",
    "deinterleave",
    "file_to_snes",
    "has_copier_stub",
    "interleave",
    "layout_named",
    "read",
    "resolve",
    "score",
    "snes_to_file",
    "stub_by_length",
    "window_to_file",
]
