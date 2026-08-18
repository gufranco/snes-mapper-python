"""The transfer engine, and the three ways it is usually watched wrongly.

Block transfers are how most data actually moves on this console, which makes
them the thing a survey most needs to see and the thing a survey most often
misses. Three mistakes, each of which has cost real time:

**Watching the wrong registers.** The enable register is `$420B` and the channel
registers run from `$4300`. Those belong to the processor, not to the display,
so a hook placed on the display's own window sees every graphics write and not a
single transfer. The symptom is a survey that reports a quiet machine.

**Masking the channel index with three bits.** There are eight channels, so
`& 7` looks right and is not: the index is a whole nibble of the address, and
masking it narrower silently folds `$4380` onto channel zero instead of reporting
that it belongs to no channel at all.

**Reading channels that were never armed.** A channel holds whatever it last
held, so a channel that is not enabled still answers with a plausible source and
length. Anything that walks all eight without checking the enable register
reports transfers that never happened.

So this module names the registers, extracts the index from the whole nibble, and
`plan()` returns only the channels the enable register actually selected.
"""

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


def channel_of(address):
    """Which channel a register belongs to, or nothing when it belongs to none.

    The index is the whole nibble. Masking it to three bits would make `$4380`
    look like channel zero rather than an address outside the window.
    """
    if not CHANNEL_WINDOW[0] <= address < CHANNEL_WINDOW[1]:
        return None
    return (address - CHANNEL_BASE) >> 4


class Plan:
    """What one enabled channel would move, without moving anything."""

    def __init__(self, channel, source, length, step, destination, to_cpu):
        self.channel = channel
        self.source = source
        self.length = length
        self.step = step
        self.destination = destination
        self.to_cpu = to_cpu

    def addresses(self):
        """Every address this transfer would touch, in the order it touches them."""
        bank = self.source & 0xFF0000
        at = self.source & 0xFFFF
        touched = []
        for _ in range(self.length):
            touched.append(bank | at)
            at = (at + self.step) & 0xFFFF
        return touched

    def __repr__(self):
        return f"<channel {self.channel}: {self.length} bytes from {self.source:06X}>"


class Channel:
    """One channel's registers, holding whatever they were last given."""

    def __init__(self, index):
        self.index = index
        self.registers = bytearray(CHANNEL_STRIDE)

    def write(self, offset, value):
        self.registers[offset & 0x0F] = value & 0xFF

    @property
    def parameters(self):
        return self.registers[R_PARAMETERS]

    @property
    def to_cpu(self):
        return bool(self.parameters & TO_CPU)

    @property
    def step(self):
        """How far the source moves per byte: forward, backward, or not at all."""
        if self.parameters & FIXED:
            return 0
        return -1 if self.parameters & DECREMENT else 1

    @property
    def destination(self):
        return DESTINATION_BASE | self.registers[R_DESTINATION]

    @property
    def source(self):
        return (
            (self.registers[R_SOURCE_BANK] << 16)
            | (self.registers[R_SOURCE_HIGH] << 8)
            | self.registers[R_SOURCE_LOW]
        )

    @property
    def count(self):
        return (self.registers[R_COUNT_HIGH] << 8) | self.registers[R_COUNT_LOW]

    @property
    def length(self):
        """How many bytes move. A count of zero is the whole range, not nothing."""
        return self.count or WHOLE_RANGE

    def plan(self):
        return Plan(self.index, self.source, self.length, self.step, self.destination, self.to_cpu)


class Engine:
    """The eight channels and the register that says which of them are armed."""

    def __init__(self):
        self.channels = [Channel(index) for index in range(CHANNEL_COUNT)]
        self.enable = 0x00
        self.enable_indirect = 0x00

    def write(self, address, value):
        """Take a write, whether it selects channels or configures one."""
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
    def enabled(self):
        """Which channels the enable register selected, and only those."""
        return [index for index in range(CHANNEL_COUNT) if self.enable & (1 << index)]

    def plan(self):
        """What every armed channel would move, without moving anything."""
        return [self.channels[index].plan() for index in self.enabled]
