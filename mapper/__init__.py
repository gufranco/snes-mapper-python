"""The SNES cartridge memory map and its transfer engine.

    from mapper import read, resolve

    cartridge = read(open("game.sfc", "rb").read())
    resolve(cartridge.layout, 0x7E0900).region
    # 'work-ram', not cartridge

Every defect this package exists to catch is an address question rather than a
processor one: whether a bank is cartridge or work RAM, whether a register
belongs to the processor or the display, and whether a transfer channel was ever
armed.

A file on disk is not yet a cartridge, so `dump` comes first: it takes off what
the copier added and joins back what the copier split, and only then is there an
image the rest of this package can answer questions about. It is reached as a
module rather than flattened into the root, because `dump.read` takes a path and
`read` takes bytes, and two functions that differ only in what they accept should
not differ only in the reader's memory.

    from mapper import dump, read

    cartridge = read(dump.read("game.smc"))
"""

from . import dump
from .dump import (
    COPIER_BYTES,
    block_ratios,
    chunk_index,
    deflate_ratio,
    has_copier_stub,
    join_game_doctor,
    measure_reuse,
    strip_copier_stub,
)
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
    "block_ratios",
    "channel_of",
    "chunk_index",
    "deflate_ratio",
    "deinterleave",
    "describe",
    "dump",
    "file_to_snes",
    "has_copier_stub",
    "interleave",
    "join_game_doctor",
    "measure_reuse",
    "read",
    "resolve",
    "score",
    "snes_to_file",
    "strip_copier_stub",
    "window_to_file",
]
