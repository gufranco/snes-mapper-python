"""How fast the map answers, and a floor it must not fall through.

Not a benchmark for its own sake. Resolving an address is the call every other
question here is built on, and a survey over a cartridge library makes millions
of them. The way that stops being usable is gradual: a lookup grows an
allocation, a table becomes a comprehension, and a year later a sweep nobody
changed takes an hour. A floor that fails loudly is cheaper than noticing.

The floor is deliberately far below what the map does today. It is there to
catch something several times slower, not to police the noise between one runner
and another, because a shared runner's variance is larger than any change worth
arguing about.

Every figure is a median across repeats rather than a mean, because one
scheduling hiccup moves a mean and moves a median much less, and the runtime
version is printed beside it because it is the single thing that changes these
numbers most.

Run it outside the coverage step. A tracer costs about ten times what this does,
so a floor measured under one measures the tracer.
"""

from __future__ import annotations

import statistics
import sys
import time
from typing import TYPE_CHECKING

import mapper

if TYPE_CHECKING:
    from collections.abc import Sequence

FLOOR = 200_000
"""Resolutions per second this must beat, several times below what it does."""

CALLS = 20_000
"""Resolutions per repeat. Enough that the clock's resolution does not decide."""

REPEATS = 5
"""How many repeats the median is taken across."""

ADDRESSES = (0x808000, 0x00FFC0, 0x7E0000, 0xC08000, 0x408000)
"""Five addresses that land in different regions, so no one path is measured."""


class Timed:
    """One measured run, and what it is allowed to say about itself."""

    __slots__ = ("calls", "seconds", "what")

    def __init__(self, what: str, calls: int, seconds: Sequence[float]) -> None:
        self.what = what
        self.calls = calls
        self.seconds = list(seconds)

    def median(self) -> float:
        return statistics.median(self.seconds)

    def rate(self) -> float:
        """Calls per second, or zero when the clock could not see the work.

        A run that measured zero seconds is a reading about the clock rather
        than about the code, and reporting it as unbounded speed would let a
        machine with a coarse timer pass a floor it never met.
        """
        taken = self.median()
        return self.calls / taken if taken > 0 else 0.0

    def beats(self, floor: int) -> bool:
        return self.rate() >= floor


def measure(calls: int = CALLS, repeats: int = REPEATS) -> Timed:
    """Resolve addresses across every region, and time it."""
    seconds = []
    for _ in range(repeats):
        started = time.perf_counter()
        for index in range(calls):
            mapper.resolve(mapper.LOROM, ADDRESSES[index % len(ADDRESSES)])
        seconds.append(time.perf_counter() - started)
    return Timed("resolve", calls, seconds)


def lines_for(found: Timed, floor: int = FLOOR) -> list[str]:
    """What the run reports, whether it passed or not."""
    runtime = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    lines = [
        f"  {found.what}: {found.rate():,.0f} per second"
        f" (median of {len(found.seconds)}) on Python {runtime}",
        f"  floor: {floor:,} per second",
    ]
    if not found.beats(floor):
        lines.append(f"  below the floor: {found.rate():,.0f} is under {floor:,}")
    return lines


def main(calls: int = CALLS, repeats: int = REPEATS, floor: int = FLOOR) -> int:
    found = measure(calls, repeats)
    for line in lines_for(found, floor):
        print(line)
    return 0 if found.beats(floor) else 1


if __name__ == "__main__":
    raise SystemExit(main())
