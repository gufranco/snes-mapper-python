<div align="center">

<h1>SNES Mapper</h1>

<strong>The cartridge memory map and its transfer engine, measured against a real ROM library.</strong>

<br>
<br>

[![CI](https://github.com/gufranco/snes-mapper-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/snes-mapper-python/actions/workflows/ci.yml)
[![Corpus](https://img.shields.io/badge/corpus-386%20%2F%20386-brightgreen)](#the-corpus-and-why-it-can-ship)
[![Cartridges](https://img.shields.io/badge/measured%20across-5%2C145%20cartridges-blue)](#the-corpus-and-why-it-can-ship)
[![Coverage](https://img.shields.io/badge/coverage-100%25%20statement%20%2B%20branch-brightgreen)](#tests)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

</div>

<p align="center">
  <a href="#quick-start">Quick start</a> &nbsp;|&nbsp;
  <a href="#the-four-mistakes-this-exists-to-stop">The four mistakes</a> &nbsp;|&nbsp;
  <a href="#the-corpus-and-why-it-can-ship">Why the corpus is legal</a> &nbsp;|&nbsp;
  <a href="#what-a-real-library-actually-contains">What a library contains</a> &nbsp;|&nbsp;
  <a href="https://github.com/gufranco/snes-mapper-python/issues">Issues</a>
</p>

**386** header combinations, **0** failures · measured across **5,145** cartridges · **5** layouts · **8** transfer channels · **124** tests · **100%** statement and branch coverage

```python
from mapper import read, resolve

cartridge = read(open("game.sfc", "rb").read())

resolve(cartridge.layout, 0x7E0900).region
# 'work-ram', not cartridge, however much it looks like a bank number
```

---

## The problem

Every defect in a year of this work lived in one layer, and it was not a processor.

A replay harness read its script from banks `$7E` and `$7F`, believing they were cartridge. A ROM survey saw no transfers at all because it watched the display's registers when the transfer registers belong to the processor. A channel index was masked with three bits when the field is a whole nibble. Channels that were never armed were read as live, so the survey reported transfers that never happened.

Not one of those is a CPU bug. Every one is the same question asked wrongly: **which address is this, and who is allowed to read it?**

## The solution

Make that question something you assert rather than something you remember.

The map is a table, not a rule. The transfer registers are named constants, not literals copied from a datasheet at 2am. The channel index comes from the nibble the hardware uses. And `plan()` returns only channels the enable register actually selected, so an unarmed channel cannot pretend to be a transfer.

Correctness comes from a real library: **5,145 cartridges**, parsed for every distinct combination of header fields they declare, with each combination checked against the layout and addresses it produces.

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

`plan()` reports the addresses a transfer would touch, in order, without moving anything.

</td>
<td width="50%" valign="top">

### Measured against real cartridges

386 header combinations covering every cartridge in a 5,145-strong library.

</td>
</tr>
</table>

## Quick start

### Prerequisites

| Tool | Version | Install |
|:-----|:--------|:--------|
| Python | >= 3.12 | [python.org](https://www.python.org/downloads/) |

### Setup

```bash
git clone https://github.com/gufranco/snes-mapper-python.git
cd snes-mapper-python
```

### Verify

```bash
python3 conformance/corpus.py
#   386 header combinations from conformance/corpus.json
#   measured across 5145 cartridges
#   386 agreed, 0 did not
```

## The four mistakes this exists to stop

### Banks `$7E` and `$7F` are not cartridge

```python
resolve(LOROM, 0x7E0900).region
# 'work-ram'

resolve(LOROM, 0x008000).region
# 'rom'
```

They sit in the middle of the bank numbering and read like any other address. A patch written to one, or a script read from one, silently goes somewhere else. The bottom eight kilobytes of every low bank mirror the same work RAM, which catches the same mistake a second way.

### The transfer registers belong to the processor

```python
from mapper import ENABLE, CHANNEL_BASE

ENABLE, CHANNEL_BASE
# (0x420B, 0x4300)
```

Not `$21xx`. A hook placed on the display's window sees every graphics write and not one transfer, and the symptom is a survey that reports a machine doing nothing.

### The channel index is a nibble

```python
channel_of(0x4370)
# 7

channel_of(0x4380)
# None, not channel 0
```

There are eight channels, so `& 7` looks right. It folds `$4380` onto channel zero instead of reporting that it lies outside the window.

### A channel that was never armed still answers

```python
engine.write(0x4304, 0x7E)
engine.enabled
# [], because nothing enabled it

engine.write(ENABLE, 0x01)
engine.enabled
# [0]
```

Registers hold whatever they last held, so walking all eight channels reports transfers that never happened.

## What a real library actually contains

Measured across 5,145 cartridges:

| Layout | Cartridges |
|:-------|-----------:|
| `lorom` | 3,584 |
| `hirom` | 995 |
| `sa1` | 525 |
| `exhirom` | 35 |
| `spc7110` | 6 |

**2,671** ask for the faster bus and **1,895** carry battery-backed save memory. Headers were found at five distinct offsets, including 148 cartridges whose dumps carry a copier stub that shifts every offset by `$200`.

> [!NOTE]
> A further 447 files in the library carry no readable header. They are prototypes with a blank one and files that are not cartridges. They are counted as refused rather than guessed at, because inventing a layout for them would put fiction into a corpus of facts.

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
python3 conformance/census.py "/path/to/roms" census.json
#   5145 cartridges read, 447 refused, from /path/to/roms
#   386 distinct header combinations
#   written to census.json
```

## Layouts

```python
from mapper import describe

describe("mode20").name
# 'lorom'

describe("hirom").resolve(0xC00000).region
# 'rom'
```

| Layout | Header at | Notes |
|:-------|:---------:|:------|
| `lorom` | `$7FC0` | A 32 KB page per bank in the upper half. Aliases: `lo`, `mode20`, `20` |
| `hirom` | `$FFC0` | A whole bank per bank, save memory windowed into the lower banks. Aliases: `hi`, `mode21`, `21` |
| `exhirom` | `$FFC0` | The high layout with a second set of banks above it. Aliases: `exhi`, `mode25`, `25` |

The header itself recognises `sa1` and `spc7110` as declared layouts, because real cartridges declare them and a census must count them. They are not resolvable here yet, since neither has a corpus behind it, and a layout with nothing backing it would be a guess rather than a measurement.

## Project structure

```
mapper/
  __init__.py     the package
  header.py       the thirty two bytes, and finding which candidate place holds them
  layout.py       where an address lands and what reaching it costs
  transfer.py     the eight channels, and planning what one would move
  models.py       what each layout is
  version.py      rewritten by the release job and by nothing else
conformance/
  corpus.py       replays every real header combination
  corpus.json     386 combinations covering 5,145 cartridges
  census.py       takes a census of a library you own
```

## Tests

```bash
for f in mapper/*.test.py conformance/*.test.py; do python3 "$f"; done
```

| Suite | File | Covers |
|:------|:-----|:-------|
| Header | [`mapper/header.test.py`](mapper/header.test.py) | Candidate places, copier stubs, every field, scoring |
| Layout | [`mapper/layout.test.py`](mapper/layout.test.py) | Regions, mirrors, speeds, offsets, whole-space coverage |
| Transfer | [`mapper/transfer.test.py`](mapper/transfer.test.py) | Registers, the nibble index, arming, planning, wrapping |
| Models | [`mapper/models.test.py`](mapper/models.test.py) | The catalogue, aliases, resolution |
| Corpus | [`conformance/corpus.test.py`](conformance/corpus.test.py) | The whole shipped set, coverage, reporting |
| Census | [`conformance/census.test.py`](conformance/census.test.py) | Walking a library, the tally, and that no title is recorded |

Coverage is enforced at 100% of statements and branches by [`pyproject.toml`](pyproject.toml).

## Development

| Command | Description |
|:--------|:------------|
| `ruff format .` | Format |
| `ruff check .` | Lint |
| `python3 -m coverage report` | Coverage, which fails below 100% |
| `python3 conformance/corpus.py [file]` | Run the corpus |
| `python3 conformance/census.py <dir> <out> [limit]` | Census a library you own |

## Versioning

This project follows [Semantic Versioning](https://semver.org/), and every release is tagged from `main` by semantic-release. See [releases](https://github.com/gufranco/snes-mapper-python/releases).

> [!IMPORTANT]
> While the version is below `1.0.0`, the public interface may change on a minor release.

## FAQ

<details>
<summary><strong>Why is header detection a score rather than a test?</strong></summary>
<br>

Because the header has no fixed home. It sits at a different offset depending on the layout it describes, so you cannot know where to look without already knowing the answer. Every candidate is scored on four independent signals and the best wins. That is what every emulator does, and it is why two of them occasionally disagree about an unusual cartridge.

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

## License

[MIT](LICENSE)
