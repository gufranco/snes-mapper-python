# Working in this repository

This file is for a coding agent. A person reading it will not be harmed, but
[README.md](README.md) is the document written for them.

## What this project is, in one paragraph

Where a Super Nintendo address lands, and what reaching it costs. It reads the
header a cartridge declares, decides which layout that means, resolves any address
to a region and a file offset, and reports the access in master clock cycles.

## The authority ladder

Every factual question is answered by the highest rung that has an answer, and a
lower rung never overrules a higher one.

1. **Nintendo's own documentation**, and anything that follows from it by
   arithmetic shown in [`conformance/hardware.json`](conformance/hardware.json).
   The two bus speeds in the official manual's Map Mode table are printed; the
   fast and slow access counts follow from them exactly, and that derivation is a
   test rather than a comment.
2. **Real cartridges.** 2781 of them were read to build the header corpus, so what
   a combination means is what shipped cartridges carry.
3. **Nothing else.** An emulator, a wiki and a forum post are the third rung at
   best. Every implementation in the field uses the same three access counts and
   they are right, but an emulator is not why they are right.

The one figure with no document behind it, the extra-slow count, is marked
unverified in `hardware.json` rather than presented beside the derived two as
though it had the same standing.

## The one rule that decides most questions

**A number that decides timing carries its derivation.**

`FAST`, `SLOW` and `XSLOW` are the whole cycle model. Two of the three are shown
to follow from figures Nintendo printed, and a test re-derives them. If you change
one, change `hardware.json` and say what document says so.

## Every gate, in the order to run them

```bash
ruff format --check .
ruff check .
mypy
pnpm run format:check
for f in mapper/*.test.py conformance/*.test.py; do python3 "$f"; done
python3 -m coverage report
python3 conformance/corpus.py
```

Coverage is collected per test file under `coverage run -a`, not by a runner.
These need cartridges and report as skipped rather than passed without them:

```bash
python3 conformance/against_cartridges.py
python3 conformance/census.py
```

## Things that will bite you

**Import conformance modules package-qualified.** `from conformance import corpus`,
never a bare `import corpus` with the directory pushed onto the path. The bare form
makes the same file reachable under two module names and the type checker refuses
to go further. `conformance/__init__.py` exists to make that possible.

**Run the suite as a machine that holds nothing.** Point the cartridge directory
somewhere empty and run everything before pushing. Coverage is total both ways, and
the only thing outside the gate is the file whose subject is a real library.

**Run on the oldest Python supported.** Annotations are evaluated eagerly before
3.14 and lazily from 3.14 on.

**A resolved offset is optional.** An address that lands on open bus or on save
memory has no file offset. Tests that do arithmetic on one go through a helper that
insists it exists, so a test that accidentally resolves into open bus fails on that
rather than on arithmetic with None.

**Never commit a cartridge.** A digest identifies a file and reconstructs nothing.

## Conventions that are not negotiable

| Thing | Rule |
|:------|:-----|
| Language | Python only |
| Comments | None in source. Docstrings carry the reasoning |
| Test layout | `<module>.test.py` beside the module it covers |
| Coverage | 100% statements and branches, enforced, on any machine |
| Types | `mypy` at strict, plus every optional error class |
| Commits | Conventional Commits, subject under 50 characters |
| Cartridges | Never committed, never vendored |

## Layout

```
mapper/
  header.py    finding the header and reading what it declares
  layout.py    resolving an address to a region, an offset and a cycle count
  image.py     where a byte sits in a file, both directions
  dump.py      copier stubs, split dumps, and measuring reuse
  models.py    the layouts, by name and alias
  transfer.py  the DMA channels and what each would move
conformance/
  hardware.json   the documented figures, and the arithmetic from them
  corpus.json     header combinations read out of real cartridges
  corpus.py       replaying them
  census.py       what a library is made of
cartridges/       a user's own copies; nothing here is ever committed
specs/current/    what this does now, as requirements with scenarios
```

## What a change is expected to leave behind

A gate that would have caught the bug. A timing change also leaves a line in
`hardware.json` naming the document.
