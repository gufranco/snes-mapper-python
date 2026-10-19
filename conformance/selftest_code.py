from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import NamedTuple

STORE = "store"
LOAD = "load"
COMPARE = "compare"
CALL = "call"
BOUND = "bound"

ACCUMULATOR_FLAG = 0x20
INDEX_FLAG = 0x10

WALK_LIMIT = 0x10000


class Unreadable(Exception):
    pass


class Event(NamedTuple):
    kind: str
    address: int
    value: int
    width: int


class State(NamedTuple):
    m16: bool
    x16: bool
    a: int
    x: int
    bank: int
    stack: tuple[int, ...]


class Walk(NamedTuple):
    base: int
    run: int
    skip: int
    end: int
    kind: str


Step = tuple[State, tuple[Event, ...], int]

Handler = Callable[[bytes, int, State], Step]


def operand(rom: bytes, at: int, width: int) -> int:
    if at + 1 + width > len(rom):
        raise Unreadable(f"the instruction at {at:#x} runs past the image")
    return int.from_bytes(rom[at + 1 : at + 1 + width], "little")


def width(wide: bool) -> int:
    return 2 if wide else 1


def stored(address: int, value: int, size: int) -> tuple[Event, ...]:
    return tuple(Event(STORE, address + k, (value >> (8 * k)) & 0xFF, 1) for k in range(size))


def rep(rom: bytes, at: int, state: State) -> Step:
    flags = operand(rom, at, 1)
    return (
        state._replace(
            m16=state.m16 or bool(flags & ACCUMULATOR_FLAG),
            x16=state.x16 or bool(flags & INDEX_FLAG),
        ),
        (),
        2,
    )


def sep(rom: bytes, at: int, state: State) -> Step:
    flags = operand(rom, at, 1)
    return (
        state._replace(
            m16=state.m16 and not flags & ACCUMULATOR_FLAG,
            x16=state.x16 and not flags & INDEX_FLAG,
        ),
        (),
        2,
    )


def load_a(rom: bytes, at: int, state: State) -> Step:
    size = width(state.m16)
    return state._replace(a=operand(rom, at, size)), (), 1 + size


def load_x(rom: bytes, at: int, state: State) -> Step:
    size = width(state.x16)
    return state._replace(x=operand(rom, at, size)), (), 1 + size


def load_y(rom: bytes, at: int, state: State) -> Step:
    return state, (), 1 + width(state.x16)


def absolute(state: State, rom: bytes, at: int) -> int:
    return (state.bank << 16) | operand(rom, at, 2)


def store_a(rom: bytes, at: int, state: State) -> Step:
    return state, stored(absolute(state, rom, at), state.a, width(state.m16)), 3


def store_x(rom: bytes, at: int, state: State) -> Step:
    return state, stored(absolute(state, rom, at), state.x, width(state.x16)), 3


def store_zero(rom: bytes, at: int, state: State) -> Step:
    return state, stored(absolute(state, rom, at), 0, width(state.m16)), 3


def store_a_direct(rom: bytes, at: int, state: State) -> Step:
    return state, stored(operand(rom, at, 1), state.a, width(state.m16)), 2


def store_x_direct(rom: bytes, at: int, state: State) -> Step:
    return state, stored(operand(rom, at, 1), state.x, width(state.x16)), 2


def store_zero_direct(rom: bytes, at: int, state: State) -> Step:
    return state, stored(operand(rom, at, 1), 0, width(state.m16)), 2


def load_absolute(rom: bytes, at: int, state: State) -> Step:
    return state, (Event(LOAD, absolute(state, rom, at), 0, width(state.m16)),), 3


def load_direct(rom: bytes, at: int, state: State) -> Step:
    return state, (Event(LOAD, operand(rom, at, 1), 0, width(state.m16)),), 2


def load_long_indexed(rom: bytes, at: int, state: State) -> Step:
    address = (operand(rom, at, 3) + state.x) & 0xFFFFFF
    return state, (Event(LOAD, address, state.x, width(state.m16)),), 4


def compare_a(rom: bytes, at: int, state: State) -> Step:
    size = width(state.m16)
    return state, (Event(COMPARE, 0, operand(rom, at, size), size),), 1 + size


def compare_x(rom: bytes, at: int, state: State) -> Step:
    size = width(state.x16)
    return state, (Event(BOUND, 0, operand(rom, at, size), size),), 1 + size


def call(rom: bytes, at: int, state: State) -> Step:
    return state, (Event(CALL, operand(rom, at, 2), 0, 0),), 3


def step_x(state: State, by: int) -> State:
    return state._replace(x=(state.x + by) & (0xFFFF if state.x16 else 0xFF))


def push_x(_: bytes, __: int, state: State) -> Step:
    return state._replace(stack=(*state.stack, state.x & 0xFF)), (), 1


def pull_bank(_: bytes, at: int, state: State) -> Step:
    if not state.stack:
        raise Unreadable(f"the instruction at {at:#x} pulls a bank nothing pushed")
    return state._replace(bank=state.stack[-1], stack=state.stack[:-1]), (), 1


def skipped(length: int) -> Handler:
    def handler(rom: bytes, at: int, state: State) -> Step:
        operand(rom, at, length - 1)
        return state, (), length

    return handler


def indexing(by: int) -> Handler:
    def handler(_: bytes, __: int, state: State) -> Step:
        return step_x(state, by), (), 1

    return handler


HANDLERS: dict[int, Handler] = {
    0xC2: rep,
    0xE2: sep,
    0xA9: load_a,
    0xA2: load_x,
    0xA0: load_y,
    0x8D: store_a,
    0x8E: store_x,
    0x9C: store_zero,
    0x85: store_a_direct,
    0x86: store_x_direct,
    0x64: store_zero_direct,
    0xAD: load_absolute,
    0xA5: load_direct,
    0xBF: load_long_indexed,
    0xC9: compare_a,
    0xE0: compare_x,
    0x20: call,
    0x4C: skipped(3),
    0xD0: skipped(2),
    0xF0: skipped(2),
    0x80: skipped(2),
    0xC8: skipped(1),
    0x88: skipped(1),
    0xE8: indexing(1),
    0xCA: indexing(-1),
    0xDA: push_x,
    0xAB: pull_bank,
}


def handler_at(rom: bytes, at: int, known: dict[int, Handler]) -> Handler:
    found = known.get(rom[at])
    if found is None:
        raise Unreadable(f"opcode {rom[at]:02X} at {at:#x} is not one this reader knows")
    return found


def read_code(rom: bytes, start: int, stop: int, m16: bool, x16: bool) -> list[Event]:
    state = State(m16, x16, 0, 0, 0, ())
    events: list[Event] = []
    at = start
    while at < stop:
        state, found, length = handler_at(rom, at, HANDLERS)(rom, at, state)
        events = [*events, *found]
        at += length
    return events


WALK_LENGTHS = {
    0xA2: 3,
    0xA0: 3,
    0x9D: 3,
    0xBD: 3,
    0xA5: 2,
    0xAD: 3,
    0xC5: 2,
    0xCD: 3,
    0xD0: 2,
    0xF0: 2,
    0xE8: 1,
    0x88: 1,
    0xE0: 3,
}

JUMP = 0x4C


def walk_tokens(rom: bytes, at: int) -> list[tuple[int, int]]:
    tokens: list[tuple[int, int]] = []
    while at < len(rom) and rom[at] != JUMP:
        length = WALK_LENGTHS.get(rom[at])
        if length is None:
            raise Unreadable(f"opcode {rom[at]:02X} at {at:#x} is not one this reader knows")
        tokens = [*tokens, (rom[at], operand(rom, at, length - 1))]
        at += length
    if at >= len(rom):
        raise Unreadable(f"the register walk from {at:#x} runs past the image")
    return tokens


def last_run(ops: list[int], of: int) -> int:
    run = 0
    for one in ops:
        run = run + 1 if one == of else 0
    return run


def register_walk(rom: bytes, at: int) -> Walk:
    tokens = walk_tokens(rom, at)
    ops = [op for op, _ in tokens]
    numbers = dict(reversed(tokens))
    if not {0xA2, 0xA0, 0xE0} <= numbers.keys():
        raise Unreadable(f"the code at {at:#x} is not a register walk")
    kind = STORE if 0x9D in numbers else LOAD
    skip = last_run(ops[: len(ops) - 1 - ops[::-1].index(0xA0)], 0xE8)
    return Walk(numbers[0xA2], numbers[0xA0], skip, numbers[0xE0], kind)


def visiting(walk: Walk) -> Iterator[int]:
    x, y = walk.base, walk.run
    for _ in range(WALK_LIMIT):
        yield x
        x += 1
        if x == walk.end:
            return
        y -= 1
        if y == 0:
            x, y = x + walk.skip, walk.run


def addresses(walk: Walk) -> list[int]:
    return list(visiting(walk))
