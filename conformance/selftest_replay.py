from __future__ import annotations

import sys
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any, NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mapper
from conformance.selftest_code import (
    BOUND,
    CALL,
    COMPARE,
    LOAD,
    STORE,
    Event,
    Unreadable,
    addresses,
    read_code,
    register_walk,
)

COUNT_LOW = 0x05

CHANNEL_REGISTERS = range(mapper.CHANNEL_BASE, mapper.CHANNEL_BASE + 0x80)


def window(spec: Mapping[str, str]) -> tuple[int, int]:
    return int(spec["start"], 16), int(spec["stop"], 16)


def in_program(address: int) -> int:
    found = mapper.resolve(mapper.LOROM, address).offset
    if found is None:
        raise Unreadable(f"the routine at ${address:04X} is not in the program")
    return found


def walked(rom: bytes, calls: Sequence[int]) -> list[int]:
    writer, reader = (register_walk(rom, in_program(one)) for one in calls[:2])
    if addresses(writer) != addresses(reader):
        raise Unreadable("the write and read routines do not visit the same registers")
    return addresses(writer)


def read_back(engine: mapper.Engine, address: int) -> int:
    channel = mapper.channel_of(address)
    assert channel is not None, "a register walk stays inside the channel window"
    return engine.channels[channel].registers[address & 0x0F]


def registers(rom: bytes, spec: Mapping[str, str]) -> dict[str, Any]:
    events = read_code(rom, *window(spec), m16=False, x16=True)
    patterns = [one.value for one in events if one.kind == STORE]
    visited = walked(rom, [one.address for one in events if one.kind == CALL])
    engine = mapper.Engine()
    agreed = 0
    for pattern in patterns:
        for address in visited:
            engine.write(address, pattern)
        agreed += sum(read_back(engine, address) == pattern for address in visited)
    return {
        "patterns": len(patterns),
        "registers": len(visited),
        "reads": len(patterns) * len(visited),
        "agreed": agreed,
        "first": f"${min(visited):04X}",
        "last": f"${max(visited):04X}",
    }


class Cells(NamedTuple):
    held: dict[int, int]
    outside: int


def stored(cells: Cells, event: Event) -> Cells:
    cell = mapper.work_ram_offset(event.address)
    if cell is None:
        return cells._replace(outside=cells.outside + 1)
    return cells._replace(held={**cells.held, cell: event.value})


def loaded(cells: Cells, event: Event) -> tuple[Cells, int | None]:
    cell = mapper.work_ram_offset(event.address)
    if cell is None:
        return cells._replace(outside=cells.outside + 1), None
    found = [cells.held.get(cell + k) for k in range(event.width)]
    if None in found:
        return cells, None
    return cells, sum(int(one or 0) << (8 * k) for k, one in enumerate(found))


def mirror(rom: bytes, spec: Mapping[str, str]) -> dict[str, Any]:
    events = read_code(rom, *window(spec), m16=True, x16=False)
    cells, value, agreed, banks = Cells({}, 0), None, 0, set[int]()
    for event in events:
        if event.kind == STORE:
            cells = stored(cells, event)
        elif event.kind == LOAD:
            cells, value = loaded(cells, event)
            banks = {*banks, event.address >> 16}
        elif event.kind == COMPARE:
            agreed += value == event.value
    return {
        "stores": sum(one.kind == STORE for one in events),
        "compares": sum(one.kind == COMPARE for one in events),
        "agreed": agreed,
        "outside": cells.outside,
        "banks": [f"${one:02X}" for one in sorted(banks)],
    }


def spans(events: Sequence[Event]) -> list[tuple[list[Event], int, list[Event]]]:
    marks = [
        k for k, one in enumerate(events) if one.kind == STORE and one.address == mapper.ENABLE
    ]
    starts = [0, *(one + 1 for one in marks[:-1])]
    return [
        (list(events[start:mark]), events[mark].value, list(events[mark + 1 : stop]))
        for start, mark, stop in zip(starts, marks, [*marks[1:], len(events)], strict=True)
    ]


def read_window(after: Iterable[Event]) -> set[int]:
    loads = [one for one in after if one.kind == LOAD and one.address >> 16]
    bounds = [one.value for one in after if one.kind == BOUND]
    if not loads or not bounds:
        return set()
    first = loads[0]
    return set(range(first.address, first.address - first.value + bounds[0]))


def landed(written: set[int], channel: int) -> list[str]:
    return [
        f"${one:04X}"
        for one in sorted(written)
        if one & 0x0F == COUNT_LOW and mapper.channel_of(one) != channel
    ]


def judged(plan: mapper.Plan, held: set[int], after: list[Event]) -> bool:
    if plan.to_cpu:
        wanted = read_window(after)
        return bool(wanted) and wanted <= set(plan.addresses())
    return plan.step == 0 and mapper.work_ram_offset(plan.source) in held


def channel_record(plan: mapper.Plan, written: set[int], agrees: bool) -> dict[str, Any]:
    stale = (mapper.CHANNEL_BASE | (plan.channel << 4) | COUNT_LOW) not in written
    return {
        "channel": plan.channel,
        "toCpu": plan.to_cpu,
        "step": plan.step,
        "destination": f"${plan.destination:04X}",
        "length": None if stale else plan.length,
        "countLanded": landed(written, plan.channel),
        "agrees": agrees,
    }


def held_cells(events: Iterable[Event]) -> set[int]:
    return {
        cell
        for one in events
        if one.kind == STORE and (cell := mapper.work_ram_offset(one.address)) is not None
    }


def transfers(rom: bytes, spec: Mapping[str, str]) -> dict[str, Any]:
    events = read_code(rom, *window(spec), m16=True, x16=False)
    engine, channels, held = mapper.Engine(), list[dict[str, Any]](), set[int]()
    for before, enable, after in spans(events):
        written = {one.address for one in before if one.address in CHANNEL_REGISTERS}
        for one in before:
            engine.write(one.address, one.value)
        held = held | held_cells(before)
        engine.write(mapper.ENABLE, enable)
        channels = [
            *channels,
            *(channel_record(plan, written, judged(plan, held, after)) for plan in engine.plans()),
        ]
    agreed = sum(one["agrees"] for one in channels)
    return {"enables": len(channels), "agreed": agreed, "channels": channels}


PARTS = {"registers": registers, "mirror": mirror, "transfers": transfers}


def replay(rom: bytes, spec: Mapping[str, Mapping[str, str]]) -> dict[str, Any]:
    return {name: PARTS[name](rom, spec[name]) for name in PARTS if name in spec}


def disagrees(name: str, found: Mapping[str, Any]) -> bool:
    if name == "registers":
        return bool(found["agreed"] != found["reads"])
    if name == "mirror":
        return bool(found["agreed"] != found["compares"] or found["outside"])
    return bool(found["agreed"] != found["enables"])


def failures(measured: Mapping[str, Any]) -> list[str]:
    return [name for name in PARTS if name in measured and disagrees(name, measured[name])]
