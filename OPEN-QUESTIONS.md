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

A page of a manual, or a schematic. The question below about the master clock
would be closed by a printed frequency or by the crystal on a board, and the one
about the SPC7110 by the board's schematic or a logic analyser on its chip
selects.

Every entry is also carried in
[`conformance/divergences.json`](conformance/divergences.json) with its status
and severity, so a program can read what a person reads here.

## Where a document is silent and every implementation agrees

### Where the master clock in the arithmetic comes from.

**The document says.** Nothing. Book I prints three CPU clock speeds in
megahertz and never gives the master clock they divide.

**What this project follows.** 21,477,273 Hz, six times the NTSC colour carrier.

**Why.** The arithmetic that turns three printed speeds into six, eight and
twelve master cycles needs a master clock, and the one used is a property of the television
standard rather than a figure from the document. The derivation reads as though
every step came from Nintendo, and one step did not.

**What would settle or reopen it.** A passage in either book giving the master
clock frequency, or the crystal value from a schematic or a board photograph.

## Where no document exists and one implementation is the source

### Where the SPC7110 board puts its ROMs and its registers.

**The document says.** Nothing. Book I names the SPC7110's mapping byte and no
memory map, and Book II has no SPC7110 chapter.

**What this project follows.** ares at commit
`9408cb43d4948fc3ea6e152a307a34348df3fe04`: its board database for the
SPC7110 boards and its SPC7110 source for what the bank registers select after a
reset. Registers at `$4800` to `$483F`, the decompression port in banks `$50`
and `$58`, backup RAM at `$6000` to `$7FFF`, program ROM as the image's first
megabyte, and data ROM after it. It is recorded under `notStated` in
[`conformance/hardware.json`](conformance/hardware.json) with `verified: false`.
The header offset, `$FFC0`, is the corpus's rather than ares's: all four retail
SPC7110 cartridges carry it there.

**Why.** An implementation is a lead, not an authority, and with no document
above it the map is a claim about what ares does.

**What would settle or reopen it.** The board's schematic, or a logic analyser
on a cartridge: the chip select lines of the program and data ROMs for an access
to each bank, and the bank registers `$4830` to `$4834` read back after a reset.

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
- **Where an address lands under each of the six layouts.** Held to fourteen
  probe addresses per combination, and to a sweep over the whole
  twenty-four-bit space in [`mapper/layout.test.py`](mapper/layout.test.py).
  The SA-1 map is also held, page by page, to what Book II prints for the
  console's processor in section 1, chapters 3 and 4, in
  [`conformance/hardware_sa1.test.py`](conformance/hardware_sa1.test.py).
- **What the fast, slow and controller-port accesses cost.** Six, eight and
  twelve master cycles, derived by arithmetic from the three speeds Book I
  prints in section 21.1, with the arithmetic shown. Figure 2-21-1 labels
  `$4000` to `$41FF` as the 1.79 MHz controller region.
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
- **The SA-1's map once a program writes its bank or backup RAM registers.**
  Book II prints what every value of `$2220` to `$2224` selects. `resolve`
  keeps no state, so it answers for the initial values, which is the map before
  the first write.
- **The SPC7110's data bank selection and the Epson clock some of its boards
  carry.** Data banks read what the bank registers select after a reset, and
  `$4840` to `$4842` resolve as the console's registers, because `resolve` takes
  a layout rather than a chipset.
- **Anything outside a header.** The census reads thirty two bytes and never
  reads a byte past them, which is what lets a measurement over a library be
  published when the library cannot be.
