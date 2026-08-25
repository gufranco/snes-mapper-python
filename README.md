<div align="center">

<h1>SNES Mapper</h1>

<strong>The cartridge memory map and its transfer engine, measured against a real ROM library.</strong>

<br>
<br>

[![CI](https://github.com/gufranco/snes-mapper-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/snes-mapper-python/actions/workflows/ci.yml)
[![Corpus](https://img.shields.io/badge/corpus-289%20%2F%20289-brightgreen)](#is-it-right)
[![Cartridges](https://img.shields.io/badge/measured%20across-2%2C781%20retail%20cartridges-blue)](#is-it-right)
[![Coverage](https://img.shields.io/badge/coverage-100%25%20statement%20%2B%20branch-brightgreen)](#working-on-it)
[![Types](https://img.shields.io/badge/mypy-strict-blue)](pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

</div>

<p align="center">
  <a href="#install">Install</a> &nbsp;|&nbsp;
  <a href="#the-interface">The interface</a> &nbsp;|&nbsp;
  <a href="#the-mistakes-this-exists-to-stop">The mistakes</a> &nbsp;|&nbsp;
  <a href="#the-corpus-and-why-it-can-ship">Why the corpus is legal</a> &nbsp;|&nbsp;
  <a href="#is-it-right">Is it right</a> &nbsp;|&nbsp;
  <a href="https://github.com/gufranco/snes-mapper-python/issues">Issues</a>
</p>

**6** layouts · **289** header combinations replayed across **2,781** retail cartridges, **0** disagreements · **8** transfer channels · **681** tests · **100%** statement and branch coverage · no dependencies

```python
from mapper import LOROM, resolve

print(resolve(LOROM, 0x7E0900).region)
print(resolve(LOROM, 0x008000).region)
```

```
work-ram
rom
```

The first of those two looks exactly like a cartridge bank and is not.

## Install

```bash
pip install git+https://github.com/gufranco/snes-mapper-python.git
```

Python 3.12 or newer. Nothing else.

To work on it instead:

```bash
git clone https://github.com/gufranco/snes-mapper-python.git
cd snes-mapper-python
```

## The interface

Everything a caller touches. Nothing else is public.

| Call | Does | Returns |
|:--|:--|:--|
| `read(rom)` | Scores every candidate place a header could sit and returns the best | a `Header` |
| `score(rom, at)` | What one candidate place scores, before choosing between them | `int` |
| `board(found, size)` | Which map a cartridge of that size is on, from size rather than from the chipset byte | a layout name |
| `resolve(kind, address, fast=False, banks=None, save=False)` | Where one address lands and what reaching it costs | a `Resolution` |
| `describe(name)` | The layout behind a name or an alias | a `Model` |
| `channel_of(address)` | Which transfer channel an address configures, or nothing when it is outside the window | `int` or `None` |
| `Engine()` | The eight channels and the register that arms them | an `Engine` |
| `engine.plans()` | What every armed channel would move, without moving anything | a list of `Plan` |
| `interleave(logical)` / `deinterleave(built)` | Between the order the console reads and the order some dumps store | `bytes` |
| `bank_count(size)` | How many whole banks an image of that size holds | `int` |
| `snes_to_file(bank, addr, banks)` / `file_to_snes(offset, banks)` | Between an address and a position in a file | `int` / a pair |
| `has_copier_stub(rom)` / `stub_by_length(size)` | Whether an image carries the extra `$200` bytes a copier prepends | `bool` |

| Attribute | Is |
|:--|:--|
| `header.at` / `header.shift` | Where the header was found, and how far a copier stub moved it |
| `header.mapping` / `header.declared` | The byte that names a layout, and whether it is in range to be believed |
| `header.layout` | The layout, from the byte when it can be believed and from the offset when it cannot |
| `header.rom_bytes` / `header.ram_bytes` | The declared sizes, in bytes |
| `header.checksum` / `header.complement` / `header.checksum_agrees` | The pair, and whether they are consistent |
| `header.fast` / `header.battery` / `header.coprocessor` | Whether it asks for the faster bus, carries save memory, carries a chip |
| `header.chipset` / `header.country` / `header.title` | The remaining declared fields |
| `resolution.region` | One of `rom`, `work-ram`, `save-ram`, `registers`, `open-bus` |
| `resolution.offset` | Where in the image that address reads from, or nothing when it is not cartridge |
| `resolution.cycles` | Master clocks the access costs: `FAST` 6, `SLOW` 8, `XSLOW` 12 |
| `plan.addresses()` | Every address a transfer would touch, in the order it touches them |

**Nothing here executes anything.** It answers where an address lands and what a
transfer would touch. Running code belongs to the processor packages, and mixing
the two would make each harder to test.

## The problem

Every defect in a year of this work lived in one layer, and it was not a processor.

A replay harness read its script from banks `$7E` and `$7F`, believing they were cartridge. A ROM survey saw no transfers at all because it watched the display's registers when the transfer registers belong to the processor. A channel index was masked with three bits when the field is a whole nibble. Channels that were never armed were read as live, so the survey reported transfers that never happened.

Not one of those is a CPU bug. Every one is the same question asked wrongly: **which address is this, and who is allowed to read it?**

## The solution

Make that question something you assert rather than something you remember.

The map is a table, not a rule. The transfer registers are named constants, not literals copied from a datasheet at 2am. The channel index comes from the nibble the hardware uses. And `plans()` returns only channels the enable register actually selected, so an unarmed channel cannot pretend to be a transfer.

Correctness comes from a real library: **2,781 retail cartridges**, parsed for every distinct combination of header fields they declare, with each combination checked against the layout and addresses it produces, and then every cartridge read again and held to the case that recorded it.

<table>
<tr>
<td width="50%" valign="top">

### The map is a table

Work RAM is decided before cartridge, because its banks look like cartridge banks and are not.

</td>
<td width="50%" valign="top">

### Speed is part of the answer

The same byte costs 6 or 8 master clocks depending on the half of the space and what the header asked for.

</td>
</tr>
<tr>
<td width="50%" valign="top">

### Transfers are planned, not guessed

`plans()` reports the addresses a transfer would touch, in order, without moving anything.

</td>
<td width="50%" valign="top">

### Measured against real cartridges

289 header combinations covering all 2,781 retail cartridges, each re-read by digest on every run.

</td>
</tr>
</table>

## The mistakes this exists to stop

### An interleaved dump is not stored in the order the console reads it

```python
from mapper import deinterleave, interleave

image = bytes(range(256)) * 1024

print(deinterleave(interleave(image)) == image)
```

```
True
```

Some dumps store every bank's upper half first and every lower half afterwards. The console never sees it; it is an artefact of how the dump was taken. A patch written at a known address into an interleaved image lands half a bank away, in another bank's data, and nothing complains.

### Banks `$7E` and `$7F` are not cartridge

```python
from mapper import LOROM, resolve

print(resolve(LOROM, 0x7E0900).region)
print(resolve(LOROM, 0x001000).region)
```

```
work-ram
work-ram
```

They sit in the middle of the bank numbering and read like any other address. A patch written to one, or a script read from one, silently goes somewhere else. The bottom eight kilobytes of every low bank mirror the same work RAM, which is the second of those two lines and catches the same mistake a second way.

### The transfer registers belong to the processor

```python
from mapper import CHANNEL_BASE, ENABLE

print(f"{ENABLE:#06x} {CHANNEL_BASE:#06x}")
```

```
0x420b 0x4300
```

Not `$21xx`. A hook placed on the display's window sees every graphics write and not one transfer, and the symptom is a survey that reports a machine doing nothing.

### The channel index is a nibble

```python
from mapper import channel_of

print(channel_of(0x4370))
print(channel_of(0x4380))
```

```
7
None
```

There are eight channels, so `& 7` looks right. It folds `$4380` onto channel zero instead of reporting that it lies outside the window.

### A channel that was never armed still answers

```python
from mapper import ENABLE, Engine

engine = Engine()
engine.write(0x4304, 0x7E)
print(engine.enabled)

engine.write(ENABLE, 0x01)
print(engine.enabled)
```

```
[]
[0]
```

Registers hold whatever they last held, so walking all eight channels reports transfers that never happened.

## Layouts

```python
from mapper import describe

print(f"{describe('lorom').header_at:#06x}")
print(f"{describe('hirom').header_at:#06x}")
print(f"{describe('exhirom').header_at:#06x}")
print(f"{describe('wholebank').header_at:#06x}")

print(describe("mode20").name)
print(describe("hirom").resolve(0xC00000).region)
```

```
0x7fc0
0xffc0
0xffc0
0x7fc0
lorom
rom
```

| Layout | Header at | Notes |
|:-------|:---------:|:------|
| `lorom` | `$7FC0` | A 32 KB page per bank in the upper half. Aliases: `lo`, `mode20`, `20` |
| `hirom` | `$FFC0` | A whole bank per bank, save memory windowed into the lower banks. Aliases: `hi`, `mode21`, `21` |
| `exhirom` | `$FFC0` or `$40FFC0` | The high layout with its two halves swapped. Aliases: `exhi`, `mode25`, `25` |
| `wholebank` | `$7FC0` | A whole 64 KB per bank below the window, from an interleaved image. Reaches 12 MB. Aliases: `whole`, `wholebanks`, `interleaved` |

The header itself recognises `sa1` and `spc7110` as declared layouts, because real cartridges declare them and a census must count them. They are not resolvable here yet, since neither has a corpus behind it, and a layout with nothing backing it would be a guess rather than a measurement. That is the difference between the six a header can name and the four an address can be resolved against.

### The extended layout swaps its halves

`exhirom` is `hirom` with its two halves exchanged. Banks `$80-$FF` carry the first four
megabytes and banks `$00-$7D`, which include the ones holding the reset vector, carry
everything past them.

```python
from mapper import layout

print(f"{layout.resolve('exhirom', 0x00FFC0).offset:#08x}")
print(f"{layout.resolve('hirom', 0x00FFC0).offset:#08x}")
```

```
0x40ffc0
0x00ffc0
```

Four megabytes in, which is why an extended cartridge keeps a header there, against a plain
high cartridge that never reaches past four megabytes at all.

The ceiling is `layout.EXHIROM_BYTES`, eight megabytes: four through `$80-$FF` and four
through `$00-$7D`, with the very top reachable only through banks `$3E` and `$3F` because
`$7E` and `$7F` are work RAM and never leave the console. An image larger than that is not
addressable by this layout however it is declared, so a ninety six megabit file is built
around a different map rather than a wider one.

### Ninety six megabit, and the map that reaches it

Every layout above spends part of a bank on something other than cartridge, which is why
none of them gets past eight megabytes. The whole-bank map spends nothing below its
window: banks `$00-$BF` each carry a full 64 KB, so 192 banks of cartridge fit and the
image holds all of them. The file stores every bank's upper half first and every lower
half afterwards, which is the interleaving [`mapper/image.py`](mapper/image.py) already
converts between.

```python
from mapper import WHOLEBANK, WHOLEBANK_BYTES, bank_count, resolve

banks = bank_count(WHOLEBANK_BYTES)
print(banks)

print(f"{resolve(WHOLEBANK, 0x008000, banks=banks).offset:#08x}")
print(f"{resolve(WHOLEBANK, 0x400000, banks=banks).offset:#08x}")
print(f"{resolve(WHOLEBANK, 0xC04D6A, banks=banks).offset:#08x}")
```

```
192
0x000000
0x800000
0xa04d6a
```

The first is the upper half of bank `$00`, exactly where plain LoROM puts it. The second is
the lower half of bank `$40`, one whole image further in. The third comes through the window
the high banks open.

It is named for its shape rather than for a chip. The S-DD1 boards were the first to need
it and are where it was first measured, but nothing in the arithmetic mentions a
coprocessor, and the traffic mostly runs the other way now: taking a chip out of a
cartridge by baking its answers into a lookup table makes the image larger and leaves the
map alone, so an expansion lands here **declaring no chipset at all**. A cartridge on this
map may carry a coprocessor, may have had one removed, or may never have had one.

> [!IMPORTANT]
> The size is an equality, not a floor. `layout.WHOLEBANK_BANKS` is 192 because the window reads its lower halves from the run belonging to bank `$80`, so its topmost byte sits `191 + banks` half-banks into a file that is `2 * banks` half-banks long. Those meet at exactly 192, and anything smaller has the window addressing bytes past the end. `resolve` refuses a smaller bank count rather than returning an offset outside the image.

That is also why `board()` reads size and never the chipset byte. Star Ocean's
retail six megabyte cartridge declares S-DD1 and is **not** on this map: it reaches past
the low layout by having the chip switch banks, which is a different mechanism. Reading the
chipset as the signal would have pointed its window a megabyte past the end of the file.

```python
from mapper import Header, board

plain = Header(0x7FC0, bytes(32))

print(board(plain, 12 * 1024 * 1024))
print(board(plain, 4 * 1024 * 1024))
```

```
wholebank
lorom
```

A stale chipset byte therefore costs nothing here. An expansion built from a cartridge that
had a coprocessor often still claims it, because clearing the field is a separate act from
removing the part, and this never reads the field.

## What a real library actually contains

Measured across 2,781 retail cartridges from every region, and nothing else. A modified
release, a translation and a prototype can each carry an edited header, and a header read
out of one describes somebody's edit rather than a cartridge that was manufactured.

| Layout | Cartridges |
|:-------|-----------:|
| `lorom` | 2,157 |
| `hirom` | 572 |
| `sa1` | 42 |
| `exhirom` | 6 |
| `spc7110` | 4 |

**1,701** ask for the faster bus and **957** carry battery-backed save memory. **2,780** of
2,781 carry a checksum consistent with its own complement. Headers were found at three
distinct offsets, two of them past a copier stub that shifts everything by `$200`.

> [!NOTE]
> A further 8 files carry no readable header. They are counted as refused rather than guessed at, because inventing a layout for them would put fiction into a corpus of facts.

### The mapping byte is not always a mapping byte

Ten mapping bytes exist and all of them are `0x2x` or `0x3x`. A title of twenty two
characters overflows its twenty one byte field and writes its last letter over the field
that follows, which is this one. Contra III leaves an `S`, Krusty's Super Fun House and
Space Football leave an `E`, and the low nibble of a letter names a layout no cartridge has.

```python
from mapper import Header

found = Header(0x7FC0, b"CONTRA3 THE ALIEN WARS" + bytes(10))

print(f"{found.mapping:#04x}")
print(found.declared)
print(found.layout)
```

```
0x53
False
lorom
```

`0x53` is `S`, the last letter of the title. Because it is out of range the byte is not
consulted, and the layout comes from the place the header sits, which is the signal that
survives.

13 of the 2,781 carry an overflowed byte. Reading the low nibble of one gave 51 retail
cartridges in a wider library the wrong layout, the wrong bus speed, or both. A byte that
**is** in range is believed even where it disagrees with the offset, because `exhirom` puts
its header where `hirom` does whenever the image is small enough that the far copy would
sit past the end of the file.

## The corpus, and why it can ship

A header is thirty two bytes in which a cartridge describes how it is built.

| Field | What it is | Ships? |
|:------|:-----------|:-------|
| Mapping, chipset, ROM and RAM size, country | Facts about a physical object | Yes |
| Counts of how many cartridges share a combination | A measurement | Yes |
| The title | A name rather than a measurement | No |
| Anything outside the header | The game | Never read |

Facts and functional elements sit outside what copyright reaches, per [17 U.S.C. 102(b)](https://www.law.cornell.edu/uscode/text/17/102) and `Feist`. [`conformance/census.py`](conformance/census.py) reads only those thirty two bytes, records no title, and never reads a byte outside the header.

[`conformance/corpus.json`](conformance/corpus.json) then carries every distinct combination the library contains, together with the layout it produces and what fourteen probe addresses resolve to under it. A model that gets a rare mapping byte wrong fails against the combination that names it.

> [!IMPORTANT]
> This is how the repository is built, not legal advice. The rule it follows: publish behaviour, never content.

### Taking a census of your own library

```bash
python3 -m conformance.census "/path/to/roms" census.json
```

```
  2781 cartridges read, 8 refused, from /path/to/roms
  289 distinct header combinations
  written to census.json
```

### Rebuilding the corpus that ships

A recording nothing can reproduce is a recording nobody can check, so the recorder ships
alongside the recording. Anyone holding the same cartridges can rebuild the file and
confirm it byte for byte.

```bash
python3 -m conformance.record "/path/to/roms" conformance/corpus.json
```

Two cartridges with identical header fields at different offsets are two cases rather than
one, because where a header sits is what names the layout whenever the byte that should
name it is a letter left behind by an overflowing title.

### Bringing your own cartridges

Put copies you already own in [`cartridges/`](cartridges/), or point `SNES_CARTRIDGE_DIR`
at a library. Subdirectories are walked, so an existing collection can be pointed at whole.
Every file is checked against all four of its digests before it is read: `sha256` decides,
and the other three are confirmed too, because a manifest that publishes a crc32 beside a
sha256 and never looks at the crc32 is publishing decoration.

Nothing in that directory is shared. [`cartridges/README.md`](cartridges/README.md) lists
every filename and its four digests, and a digest reconstructs nothing.

## What each piece of evidence is worth

| Evidence | What it settles | What it cannot |
|:--|:--|:--|
| Nintendo's manual, and arithmetic shown from it in [`conformance/hardware.json`](conformance/hardware.json) | The two bus speeds, and therefore the fast and slow access counts | The extra-slow count, which the manual does not print and which is marked unverified |
| Header combinations read out of 2781 real cartridges | What a combination means on shipped hardware | Combinations no cartridge carries |
| Digests of every cartridge read | That the file read was the file named | Nothing about whether that release is the one you meant |

What this does not model, stated so nobody inherits a stronger belief: the CPU,
and therefore how many accesses an instruction makes; refresh and DMA stalls; and
anything about what happens once an address is reached, which belongs to whatever
answers there.

## FAQ

<details>
<summary><strong>Why is header detection a score rather than a test?</strong></summary>
<br>

Because the header has no fixed home. It sits at a different offset depending on the layout it describes, so you cannot know where to look without already knowing the answer. Every candidate is scored on four independent signals and the best wins. That is what every emulator does, and it is why two of them occasionally disagree about an unusual cartridge.

Each signal earns its point by measurement rather than by argument. The declared size counts when it lands between 8 and 13, because across 7,314 cartridges that band holds the byte at the right offset 98.85% of the time and at a wrong offset 3.18% of the time. Widening it either way was measured and costs more than it buys: no cartridge declares 14 and fifteen wrong offsets do, and reaching down to 7 gains seven real cartridges at the price of twelve more wrong ones.

</details>

<details>
<summary><strong>Does this emulate anything?</strong></summary>
<br>

No, and deliberately. It answers where an address lands and what a transfer would touch. Executing code belongs to the processor packages, and mixing the two would make each harder to test.

</details>

<details>
<summary><strong>Why are SA-1 and SPC7110 recognised but not resolvable?</strong></summary>
<br>

Because recognising them is a measurement and resolving them would be a claim. Real cartridges declare both, so a census has to count them. Neither has a corpus behind its address mapping yet, and a layout with nothing backing it does not belong in a table of answers.

</details>

## Is it right

Every distinct combination of header fields the library declares is replayed against the
layout and the addresses it produces: **289 combinations, 0 disagreements**. The corpus
runs with no cartridge anywhere on the machine, because it carries the measurements rather
than the files they were taken from.

```bash
python3 -m conformance.corpus
```

```
  289 header combinations from conformance/corpus.json
  measured across 2781 cartridges
  289 agreed, 0 did not
```

With a library present, the sweep reads every file in it and holds each cartridge to the
case that recorded it:

```bash
python3 -m conformance.against_cartridges
```

```
  2781 cartridges read from cartridges
  2781 agreed, 0 did not
```

That sweep is skipped rather than passed when no cartridge is present, so a run that proved
nothing never reads as a run that proved something. CI attempts it on every push and
annotates the skip.

[`conformance/hardware.json`](conformance/hardware.json) holds what Nintendo printed about
bus timing, with the sentence it came from, and shows the arithmetic from those figures to
the two access counts this package returns. The third count, for the controller-port
region, follows from no document and is marked unverified rather than presented beside
them.

[`conformance/divergences.json`](conformance/divergences.json) holds every place two
sources part, with what would settle it, and [`OPEN-QUESTIONS.md`](OPEN-QUESTIONS.md)
carries every place fidelity here is a claim rather than a measurement.

## Working on it

```bash
python3 -m coverage erase
for file in $(find mapper conformance -name '*.test.py' | sort); do
  python3 -m coverage run -a "$file"
done
python3 -m coverage report
```

| Command | Description |
|:--------|:------------|
| `ruff format .` | Format |
| `ruff check .` | Lint |
| `mypy` | Types, at strict |
| `python3 -m coverage report` | Coverage, which fails below 100% |
| `python3 -m conformance.corpus` | Replay the corpus |
| `python3 -m conformance.speed` | The throughput floor |
| `python3 -m conformance.census <dir> <out>` | Census a library you own |

Everything under `conformance/` runs as a module rather than as a script. Run as a script,
its own directory goes on the import path and a file there shadows any standard library
module of the same name.

`python3 mapper/doctor.py` says what is actually on this machine: every layout, a header read out of an image built on the spot, and whether the cartridge library this repository cannot carry is here and holds anything. It is run as a file rather than with `-m` so that it still runs when the package itself will not import, which is the case it exists for. Its report is what an issue asks for, because a report is only as good as what it says about the machine that produced it.

Tests sit beside the module they cover, named `<module>.test.py`. Coverage is 100% of
statements and branches, enforced by [`pyproject.toml`](pyproject.toml). Types are `mypy` at
strict. Commits follow [Conventional Commits](https://www.conventionalcommits.org/), and
releases are cut from `main` by [semantic-release](https://semantic-release.gitbook.io/).

> [!IMPORTANT]
> While the version is below `1.0.0`, the public interface may change on a minor release.

[`AGENTS.md`](AGENTS.md) is the document for an agent working here.
[`FAMILY.md`](FAMILY.md) is the standard this repository shares with the rest of the
family, kept identical in every member above the marker at the end of its shared part.

```
mapper/
  __init__.py     the package
  errors.py       everything this package raises, importing nothing from it
  header.py       the thirty two bytes, and finding which candidate place holds them
  layout.py       where an address lands and what reaching it costs
  transfer.py     the eight channels, and planning what one would move
  image.py        where a byte sits in a file, which is not where the console sees it
  models.py       what each layout is
  version.py      rewritten by the release job and by nothing else
conformance/
  corpus.py               replays every real header combination
  corpus.json             289 combinations covering 2,781 retail cartridges
  record.py               rebuilds that corpus from a library, so it can be checked
  census.py               takes a census of a library you own
  cartridges.py           identifies a supplied cartridge by all four of its digests
  against_cartridges.py   reads every cartridge present and holds each to its case
  hardware.json           what Nintendo printed, with the sentence
  divergences.json        where sources part, with a status and a severity
  links.py                the weekly check that every cited address still answers
  speed.py                the throughput floor
cartridges/               a library you supply, ignored by git, never shared
cartridges.manifest.json  2,778 retail cartridges, four digests each, no content
```

| Suite | File | Covers |
|:------|:-----|:-------|
| Header | [`mapper/header.test.py`](mapper/header.test.py) | Candidate places, copier stubs, every field, scoring |
| Layout | [`mapper/layout.test.py`](mapper/layout.test.py) | Regions, mirrors, speeds, offsets, whole-space coverage |
| Transfer | [`mapper/transfer.test.py`](mapper/transfer.test.py) | Registers, the nibble index, arming, planning, wrapping |
| Models | [`mapper/models.test.py`](mapper/models.test.py) | The catalogue, aliases, resolution |
| Image | [`mapper/image.test.py`](mapper/image.test.py) | Interleaved dumps, windowed banks, and that every conversion is its own inverse |
| Errors | [`mapper/errors.test.py`](mapper/errors.test.py) | That every exception has one home and one name |
| Corpus | [`conformance/corpus.test.py`](conformance/corpus.test.py) | The whole shipped set, coverage, reporting |
| Recorder | [`conformance/record.test.py`](conformance/record.test.py) | Rebuilding the corpus, and that rebuilding twice writes the same file |
| Census | [`conformance/census.test.py`](conformance/census.test.py) | Walking a library, the tally, and that no title is recorded |
| Cartridges | [`conformance/cartridges.test.py`](conformance/cartridges.test.py) | The manifest, all four digests, where a library is looked for |
| Sweep | [`conformance/against_cartridges.test.py`](conformance/against_cartridges.test.py) | Every cartridge present, against the case that recorded it |
| Speed | [`conformance/speed.test.py`](conformance/speed.test.py) | The floor, and that a run too fast to time is not read as infinitely fast |
| Family | [`conformance/family.test.py`](conformance/family.test.py) | That this repository still matches the standard every member carries |

## References

This repository carries no documents and no cartridges. Every claim is traced to something
published elsewhere, or to a measurement taken from files a reader supplies themselves.

| Document | Publisher | Read on | Read via | Redistributable |
|:---------|:----------|:--------|:---------|:----------------|
| *Super Nintendo Entertainment System Development Manual, Book I* | Nintendo | 2026-08-20 | [The text archived at archive.org](https://archive.org/stream/SNESDevManual/book1_djvu.txt) | No |

The sentences taken from it are in
[`conformance/hardware.json`](conformance/hardware.json), each with the table it came from.
That record carries the reading rather than a digest of the file, which is the one place
this repository falls short of the family standard and is recorded as such in
[`OPEN-QUESTIONS.md`](OPEN-QUESTIONS.md).

| Source | Used for |
|:-------|:---------|
| A retail cartridge library the author owns | The 2,781 headers behind [`conformance/corpus.json`](conformance/corpus.json). Nothing from it is committed, and [`cartridges.manifest.json`](cartridges.manifest.json) carries only digests |

## Citing this

[CITATION.cff](CITATION.cff) is kept in step with the released version by the same script
that stamps the package, so the version it names is the version that shipped. GitHub
renders it as a Cite this repository button.

## License

[MIT](LICENSE)
