# Open questions

What this project does not know for certain, and what it would take to find out.

Everything here is a place where being faithful is still a claim rather than a
measurement. The list is short, and that is a fact about the subject rather than
about the effort: a memory map is mostly arithmetic over a table, and the table
was read out of the cartridges that were built to it.

The settled surface is large. 289 distinct header combinations, covering all
2,781 retail cartridges in the library, replay against the layout and the
addresses they produce with no disagreements, and every cartridge present is
read again and held to the case that recorded it. What follows is the residue.

## Why a corpus cannot close these

The corpus answers what cartridges declare. It cannot answer what the console
does with a declaration, because it was taken from the cartridges rather than
from a machine. Where a question is about the console rather than about the
cartridge, the corpus is silent however large it grows, and adding cartridges to
it does not move the answer.

## What would settle almost all of them

Two pages of a manual, or a logic analyser on a console. The three questions
below about timing would each be closed outright by a printed access time or by
counting master cycles on a real access; the one about a document would be
closed by a copy of the file somebody can hash.

Every entry is also carried in
[`conformance/divergences.json`](conformance/divergences.json) with its status
and severity, so a program can read what a person reads here.

## Where a document is silent and every implementation agrees

### What an access to the controller-port region costs.

**The document says.** The Map Mode table at page 1-2-17 lists two bus speeds,
2.68 MHz and 3.58 MHz, and no third.

Source: Nintendo, Super Nintendo Entertainment System Development Manual, Book I.

**What this project follows.** The implementations, which all use twelve master
cycles, and it is marked `verified: false` in
[`conformance/hardware.json`](conformance/hardware.json) rather than presented
beside the two that are derived from printed figures.

**Why.** Twelve is almost certainly right, and that is not the same as
documented. The other two counts here follow by arithmetic from speeds Nintendo
printed. Presenting the third without a mark would let a reader inherit a
stronger belief than the evidence supports.

**What would settle or reopen it.** A passage in Book I or Book II giving the
controller-port access time, or a measurement: drive an access to `$4016` and
count master cycles.

### Where the master clock in the arithmetic comes from.

**The document says.** Nothing. Book I prints the two bus speeds in megahertz and
never gives the master clock they divide.

**What this project follows.** 21,477,273 Hz, six times the NTSC colour carrier.

**Why.** The arithmetic that turns two printed speeds into six and eight master
cycles needs a master clock, and the one used is a property of the television
standard rather than a figure from the document. The derivation reads as though
every step came from Nintendo, and one step did not.

**What would settle or reopen it.** A passage in either book giving the master
clock frequency, or the crystal value from a schematic or a board photograph.

## Where the record is thinner than the family standard asks for

### The manual behind the timing figures is not pinned by digest.

**What the standard asks for.** Every document a claim rests on is read and
pinned by its SHA-256, because two scans of one book paginate differently and a
page number means nothing without saying which scan.

**What this project has.** The publisher, the title, the date it was read and the
address it was read through, in
[`conformance/hardware.json`](conformance/hardware.json). No digest, and no page
count.

**Why it is open rather than fixed.** The figures were read from a text
transcription hosted at an archive rather than from a file held on the machine
that recorded them, so there is nothing here to hash. Filling the field in from a
copy fetched later would pin a different artefact than the one that was read,
which is the failure the rule exists to prevent.

**What would settle it.** Fetch the file that was read, record its SHA-256 and
its page count beside the existing entry, and confirm that the two quoted figures
still sit where the record says they sit.

## Where the question is a scope boundary, not an unknown

### Whether an address that resolves to a register is one the console answers.

**What this project follows.** Nothing beyond the region name. `registers` says
the address is decoded by the console rather than by the cartridge, and stops
there.

**Why.** What happens once a register is reached belongs to whatever implements
it. A map that also claimed to know the answer would be two models in one file,
and the second would have no corpus behind it.

**What would settle or reopen it.** Nothing. This is a boundary rather than a
gap, and it is listed so that a reader does not mistake the first for the second.

## What is not in question

So the boundary is visible rather than implied:

- **Which layout a cartridge is on.** Held to 289 header combinations covering
  2,781 retail cartridges, with no disagreements, including the thirteen whose
  mapping byte is a letter left behind by an overflowing title.
- **Where an address lands under each of the four resolvable layouts.** Held to
  fourteen probe addresses per combination, and to a sweep over the whole
  twenty-four-bit space in [`mapper/layout.test.py`](mapper/layout.test.py).
- **What the fast and slow accesses cost.** Six and eight master cycles, derived
  by arithmetic from the two speeds the manual prints, with the arithmetic shown.
- **Which addresses configure a transfer channel, and which do not.** The window
  and the nibble, held to the register map rather than to a mask that happens to
  work for eight.
- **That an unarmed channel is not a transfer.** `plans()` reports only what the
  enable register selected.
- **That a conversion between an image and an address is its own inverse.** Held
  both ways for every conversion in [`mapper/image.py`](mapper/image.py).

## What is deliberately not modelled

Absent rather than unknown, and absent on purpose:

- **The processor.** How many accesses an instruction makes, and therefore what
  it costs, belongs to `mos65xx-python`. A per-access figure looks like a timing
  model and is not one.
- **Refresh and transfer stalls.** Every cycle the console spends on something
  other than the access itself.
- **The SA-1 and SPC7110 address maps.** A header declaring either is recognised
  and counted, because real cartridges declare them and a census has to count
  them. Neither is resolvable, because neither has a corpus behind it, and a
  layout with nothing backing it would be a guess sitting in a table of answers.
- **Anything outside a header.** The census reads thirty two bytes and never
  reads a byte past them, which is what lets a measurement over a library be
  published when the library cannot be.
