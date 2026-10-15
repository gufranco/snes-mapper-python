from __future__ import annotations

from typing import override

ENABLE = 0x420B
ENABLE_INDIRECT = 0x420C

CHANNEL_BASE = 0x4300
CHANNEL_STRIDE = 0x10
CHANNEL_COUNT = 8

CHANNEL_WINDOW = (CHANNEL_BASE, CHANNEL_BASE + CHANNEL_COUNT * CHANNEL_STRIDE)

R_PARAMETERS = 0x00
R_DESTINATION = 0x01
R_SOURCE_LOW = 0x02
R_SOURCE_HIGH = 0x03
R_SOURCE_BANK = 0x04
R_COUNT_LOW = 0x05
R_COUNT_HIGH = 0x06

TO_CPU = 0x80
FIXED = 0x08
DECREMENT = 0x10

WHOLE_RANGE = 0x10000

DESTINATION_BASE = 0x2100


def channel_of(address: int) -> int | None:
    if not CHANNEL_WINDOW[0] <= address < CHANNEL_WINDOW[1]:
        return None
    return (address - CHANNEL_BASE) >> 4


class Plan:
    __slots__ = ("channel", "destination", "length", "source", "step", "to_cpu")

    def __init__(
        self,
        channel: int,
        source: int,
        length: int,
        step: int,
        destination: int,
        to_cpu: bool,
    ) -> None:
        self.channel = channel
        self.source = source
        self.length = length
        self.step = step
        self.destination = destination
        self.to_cpu = to_cpu

    def addresses(self) -> list[int]:
        bank = self.source & 0xFF0000
        at = self.source & 0xFFFF
        touched = []
        for _ in range(self.length):
            touched.append(bank | at)
            at = (at + self.step) & 0xFFFF
        return touched

    @override
    def __repr__(self) -> str:
        return f"<channel {self.channel}: {self.length} bytes from {self.source:06X}>"


class Channel:
    __slots__ = ("index", "registers")

    def __init__(self, index: int) -> None:
        self.index = index
        self.registers = bytearray(CHANNEL_STRIDE)

    def write(self, offset: int, value: int) -> None:
        self.registers[offset & 0x0F] = value & 0xFF

    @property
    def parameters(self) -> int:
        return self.registers[R_PARAMETERS]

    @property
    def to_cpu(self) -> bool:
        return bool(self.parameters & TO_CPU)

    @property
    def step(self) -> int:
        if self.parameters & FIXED:
            return 0
        return -1 if self.parameters & DECREMENT else 1

    @property
    def destination(self) -> int:
        return DESTINATION_BASE | self.registers[R_DESTINATION]

    @property
    def source(self) -> int:
        return (
            (self.registers[R_SOURCE_BANK] << 16)
            | (self.registers[R_SOURCE_HIGH] << 8)
            | self.registers[R_SOURCE_LOW]
        )

    @property
    def count(self) -> int:
        return (self.registers[R_COUNT_HIGH] << 8) | self.registers[R_COUNT_LOW]

    @property
    def length(self) -> int:
        return self.count or WHOLE_RANGE

    def plan(self) -> Plan:
        return Plan(self.index, self.source, self.length, self.step, self.destination, self.to_cpu)


class Engine:
    __slots__ = ("channels", "enable", "enable_indirect")

    def __init__(self) -> None:
        self.channels = [Channel(index) for index in range(CHANNEL_COUNT)]
        self.enable = 0x00
        self.enable_indirect = 0x00

    def write(self, address: int, value: int) -> None:
        value &= 0xFF
        if address == ENABLE:
            self.enable = value
            return
        if address == ENABLE_INDIRECT:
            self.enable_indirect = value
            return
        index = channel_of(address)
        if index is not None:
            self.channels[index].write(address & 0x0F, value)

    @property
    def enabled(self) -> list[int]:
        return [index for index in range(CHANNEL_COUNT) if self.enable & (1 << index)]

    def plans(self) -> list[Plan]:
        return [self.channels[index].plan() for index in self.enabled]
