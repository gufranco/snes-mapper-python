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
from .layout import FAST, OPEN_BUS, REGISTERS, ROM, SAVE_RAM, SLOW, WORK_RAM, XSLOW, resolve
from .models import MODELS, UnknownModelError, describe
from .transfer import CHANNEL_BASE, CHANNEL_COUNT, ENABLE, Channel, Engine, Plan, channel_of
from .version import VERSION

__version__ = VERSION

__all__ = [
    "CHANNEL_BASE",
    "CHANNEL_COUNT",
    "ENABLE",
    "EXHIROM",
    "FAST",
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
    "WORK_RAM",
    "XSLOW",
    "Channel",
    "Engine",
    "Header",
    "NoHeader",
    "Plan",
    "UnknownModelError",
    "__version__",
    "channel_of",
    "describe",
    "read",
    "resolve",
    "score",
]
