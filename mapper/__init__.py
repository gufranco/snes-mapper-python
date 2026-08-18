"""The SNES cartridge memory map and its transfer engine.

    from mapper import read, resolve

    cartridge = read(open("game.sfc", "rb").read())
    resolve(cartridge.layout, 0x7E0900).region
    # 'work-ram', not cartridge

Every defect this package exists to catch is an address question rather than a
processor one: whether a bank is cartridge or work RAM, whether a register
belongs to the processor or the display, and whether a transfer channel was ever
armed.
"""

from .header import (
    EXHIROM,
    HIROM,
    HIROM_HEADER,
    LOROM,
    LOROM_HEADER,
    Header,
    NoHeader,
    read,
    score,
)
from .image import (
    BANK,
    HALF,
    WINDOW_FIRST_BANK,
    NotWholeBanks,
    address_to_file,
    bank_count,
    deinterleave,
    file_to_snes,
    interleave,
    snes_to_file,
    window_to_file,
)
from .layout import FAST, OPEN_BUS, REGISTERS, ROM, SAVE_RAM, SLOW, WORK_RAM, XSLOW, resolve
from .models import MODELS, UnknownModelError, describe
from .transfer import CHANNEL_BASE, CHANNEL_COUNT, ENABLE, Channel, Engine, Plan, channel_of
from .version import VERSION

__version__ = VERSION

__all__ = [
    "BANK",
    "CHANNEL_BASE",
    "CHANNEL_COUNT",
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
    "WINDOW_FIRST_BANK",
    "WORK_RAM",
    "XSLOW",
    "Channel",
    "Engine",
    "Header",
    "NoHeader",
    "NotWholeBanks",
    "Plan",
    "UnknownModelError",
    "__version__",
    "address_to_file",
    "bank_count",
    "channel_of",
    "deinterleave",
    "describe",
    "file_to_snes",
    "interleave",
    "read",
    "resolve",
    "score",
    "snes_to_file",
    "window_to_file",
]
