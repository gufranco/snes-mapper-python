# Working in this repository

This file is for a coding agent. A person reading it will not be harmed, but
[README.md](README.md) is the document written for them.

## What this project is, in one paragraph

The cartridge memory map and the transfer engine reached through it: where an
address lands, what reaching it costs, and what an armed channel would move. It
is held to 289 distinct header combinations read out of a library of 2,781 retail
cartridges, and separately to the two bus speeds the manufacturer's manual
prints. It is a model of a board rather than of a processor, and it executes
nothing: what happens once an address is reached belongs to whatever answers
there.

## The interface a caller drives

Nothing here is built and then driven. Every call is a question about an address,
an image or a register, and the answer does not depend on anything having run.

- `read(rom)` scores every candidate place a header could sit and returns the
  best one. `score(rom, at)` is the same judgement for one place, exposed so the
  choice can be inspected rather than trusted.
- `board(found, size)` names the map from the image size, never from the chipset
  byte. A cartridge that had a coprocessor removed usually still declares it.
- `resolve(kind, address, ...)` returns the region, the offset into the image and
  the master cycles the access costs. Work RAM is decided before cartridge,
  because its banks look like cartridge banks and are not.
- `Engine()` holds the eight channels and the register that arms them.
  `plans()` returns only channels the enable register selected.
- `interleave` and `deinterleave` convert between the order a console reads and
  the order some dumps store, and each is its own inverse.

Everything the package raises lives in [`mapper/errors.py`](mapper/errors.py) and
nowhere else, and that module imports nothing from the package so it can never be
the far end of a cycle.

## The authority ladder

Every factual question is answered by the highest rung that has an answer, and a
lower rung never overrules a higher one.

1. **Manufacturer documentation.** What Nintendo printed. Every fact taken from
   it is in [`conformance/hardware.json`](conformance/hardware.json) with the
   sentence it came from and the table it was in, and every figure derived from
   one shows the arithmetic.
2. **The artifact itself.** The bytes of real cartridges. The 289 combinations in
   [`conformance/corpus.json`](conformance/corpus.json) were read out of 2,781 of
   them, and [`cartridges.manifest.json`](cartridges.manifest.json) names each
   file by four digests so a later run reads the same bytes.
3. **A recording from an independent implementation.** Nothing here rests on one.
4. **Anything else.** The access counts every emulator uses, reached for once,
   for the controller-port region, cited as what it is and marked unverified.

The corpus and the manual answer different questions and neither overrides the
other. The manual is an instruction issued to licensees, so a genuine cartridge
can disagree with it and still be genuine. Where a question is about the console
rather than about the cartridge, the corpus is silent however large it grows.

## What is settled and what is not

**Settled: which layout a cartridge is on.** 289 header combinations covering all
2,781 retail cartridges, no disagreements, including the thirteen whose mapping
byte is a letter left behind by a title overflowing its field.

**Settled: where an address lands.** Fourteen probe addresses per combination,
plus a sweep over the whole twenty-four-bit space in
[`mapper/layout.test.py`](mapper/layout.test.py).

**Settled: the fast and slow access counts.** Six and eight master cycles,
derived by arithmetic from the two speeds the manual prints, with the arithmetic
shown in the record rather than asserted.

**Not settled: 4 things**, each in [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) with
what would close it. Two are timing figures the manual never printed, one is the
manual itself not being pinned by digest, and one is a scope boundary listed so
nobody mistakes it for a gap. Do not close one by argument.

## The header has no fixed home

It sits at a different offset depending on the layout it describes, so you cannot
know where to look without already knowing the answer. Every candidate place is
scored on four independent signals and the best wins.

Each signal earns its point by measurement. The declared size counts when it
lands between 8 and 13, because across 7,314 cartridges that band holds the byte
at the right offset 98.85% of the time and at a wrong offset 3.18% of the time.
Widening it either way was measured and costs more than it buys. Changing a
threshold here is changing a measured figure, so it is changed by measuring
again rather than by reasoning.

## The mapping byte is often not a mapping byte

A title of twenty two characters overflows its twenty one byte field and writes
its last letter over the byte that names the layout. Thirteen of the 2,781 carry
one. The low nibble of a letter names a layout no cartridge has, so an out of
range byte is not consulted and the layout comes from where the header sits.

A byte that **is** in range is believed even where it disagrees with the offset,
because `exhirom` puts its header where `hirom` does whenever the image is small
enough that the far copy would sit past the end of the file.

## Every gate, in the order to run them

```bash
ruff format --check .
ruff check .
mypy
pnpm run format:check
python3 -m coverage erase
for file in $(find mapper conformance -name '*.test.py' | sort); do
  python3 -m coverage run -a "$file"
done
python3 -m coverage report
```

Then the two that are not part of the coverage step:

```bash
python3 -m conformance.corpus
python3 -m conformance.speed
```

The corpus needs no cartridge anywhere. The sweep over a real library does, and
it reports that it was skipped rather than passing:

```bash
python3 -m conformance.against_cartridges
```

Everything under `conformance/` runs as a module. Run as a script, its own
directory goes on the import path and a file there shadows any standard library
module of the same name.

## Conventions that are not negotiable

| Thing | Rule |
|:------|:-----|
| Language | Python only |
| Comments | None in source. Docstrings carry the reasoning |
| Test layout | `<module>.test.py` beside the module it covers |
| Test shape | Arrange, blank line, one act, blank line, assert. No section labels |
| Coverage | 100% statements and branches, enforced |
| Types | `mypy` at strict, plus every optional error class |
| Commits | Conventional Commits, subject under 50 characters |
| Corpus | Measurements over cartridges, never cartridges |
| Cartridges | Never committed, in any form, for any reason. A digest is published; a byte of content is not |
| Titles | Never recorded. A title is a name rather than a measurement |
| Fidelity | Where the board and convenience disagree, the board wins |
| Public API | This and the rest of the family present the same shape. See [FAMILY.md](FAMILY.md) |

## Layout

```
mapper/
  errors.py       everything this package raises, importing nothing from it
  header.py       the thirty two bytes, and finding which candidate place holds them
  layout.py       where an address lands and what reaching it costs
  transfer.py     the eight channels, and planning what one would move
  image.py        where a byte sits in a file, which is not where the console sees it
  models.py       what each layout is, by name and alias
  version.py      rewritten by the release job and by nothing else
conformance/
  corpus.json           289 combinations covering 2,781 retail cartridges
  corpus.py             replaying every one of them
  record.py             rebuilding that file from a library, so it can be checked
  census.py             taking a census of a library you own
  cartridges.py         identifying a supplied cartridge by all four of its digests
  against_cartridges.py reading every cartridge present, against the case that recorded it
  on_disk.test.py       everything that needs a library, kept out of the coverage count
  hardware.json         what Nintendo printed, with the sentence
  divergences.json      where sources part, with a status and a severity
  links.py              the weekly check that every cited address still answers
  speed.py              the throughput floor
```

## Things that will bite you

**A digest updated to make a check pass is the failure this whole standard exists
to prevent.** [`cartridges.manifest.json`](cartridges.manifest.json) and
[`conformance/corpus.json`](conformance/corpus.json) record what was measured. If
a run disagrees with one of them, find out which of the two is wrong before
touching either.

- **`cartridges/` is not in the repository, and neither is `docs/`.** A test that
  reads from one and does not say so when it is absent passes here and fails
  everywhere else. [`conformance/on_disk.test.py`](conformance/on_disk.test.py)
  is where those live, and it is the only file kept out of the coverage count.
- **A skipped test contributes no coverage.** That is why the cartridge tests sit
  in their own file rather than beside the others: on a runner with no library,
  every line of them reads as uncovered and the gate fails for a reason that has
  nothing to do with the code.
- **The chipset byte is never the signal for a map.** Reading it would put Star
  Ocean's window a megabyte past the end of its own file.
- **`& 7` on a channel address looks right and is not.** The field is a nibble,
  so `$4380` is outside the window rather than channel zero.
- **The size for the whole-bank map is an equality, not a floor.** `resolve`
  refuses a smaller bank count rather than returning an offset past the end.
- **Copier stubs and split dumps belong to `snes-rom-image`, not here.** This
  package once carried a `dump.py` for them, unimported and unpublished, holding
  a second `read` and a second `has_copier_stub` beside the ones `header.py`
  publishes. The subject moved to the member whose job it is; the module stayed
  behind and was removed. Reach for `romimage.dump` rather than adding it back.

## Before calling anything finished

[`FAMILY.md`](FAMILY.md) carries a checklist under "What a new repository has to
have before it is a member". Every line on it was a defect found in one of these
repositories and fixed in all of them, so it is the list of things that have
actually gone wrong here rather than a list of good intentions. Read it before
adding a surface, and read it again before saying a change is done.

A change to `FAMILY.md` is a change to every member. Nothing here can catch it
being made in one of them and forgotten in the others, because a test in this
repository cannot see the others, so the check is a command rather than a suite:

```sh
shared() { sed '/^\*Everything above this line/q' "$1"; }

grep -o 'github\.com/[^/]*/\([a-z0-9-]*\))' FAMILY.md | sed 's|.*/||; s|)||' | sort -u |
while read -r member; do
  other="../$member/FAMILY.md"
  [ -f "$other" ] || { echo "not on this machine: $member"; continue; }
  cmp <(shared FAMILY.md) <(shared "$other") && echo "match: $member"
done
```

The members come from the table at the top of `FAMILY.md` rather than from a glob
over the parent directory. Several repositories beside these carry a copy of this
file because somebody started from one. Those are working notes: they bind
nothing, they are not expected to match, and a sweep that reports them as drifted
invites somebody to edit a file that was never a member.

Two rules from that file are worth repeating because they are the ones skipped
most often:

**A check nobody has seen fail is not known to work.** Drive it, once,
deliberately, against input that should fail it.

**Silence and success produce the same output.** A check that found no files, no
cartridges and no records exits zero exactly like one that examined everything.
Print what was examined, and say so when the answer is nothing.

## What a change is expected to leave behind

A gate that would have caught the bug. A change to how an address resolves, or to
how a header is scored, also runs the corpus and the sweep over a real library,
because those are the only things here that can tell you whether it is right.
