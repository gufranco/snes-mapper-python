# SNES Mapper

The SNES cartridge memory map and its transfer engine in Python: where an address lands, what reaching it costs and what an armed channel would move, held to the headers of 2,781 retail cartridges.

English &nbsp;|&nbsp; [日本語](README.ja.md) &nbsp;|&nbsp; [简体中文](README.zh-Hans.md) &nbsp;|&nbsp; [繁體中文（香港）](README.zh-HK.md)

[![CI](https://github.com/gufranco/snes-mapper-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/snes-mapper-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/snes-mapper-python)](https://github.com/gufranco/snes-mapper-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**289** header combinations replayed across **2,781** retail cartridges, **0** disagreements, **4** of **6** layouts resolvable, **8** transfer channels, **863** tests, **100%** statement and branch coverage, no dependencies

```python
from mapper import LOROM, resolve

for address in (0x7E0900, 0x001000, 0x004016, 0x008000, 0x808000, 0x700000):
    landed = resolve(LOROM, address, fast=True)
    print(f"{address:06X}", landed.region, landed.offset, landed.cycles)
```

```
7E0900 work-ram None 8
001000 work-ram None 8
004016 registers None 12
008000 rom 0 8
808000 rom 0 6
700000 save-ram None 8
```

The example resolves six addresses on the low layout for a cartridge whose header asks for the faster bus. Bank `$7E` and the bottom 8 KB of every low bank are work RAM, and that is decided before any cartridge bank is considered. `$004016` is a controller port and costs 12 master clocks. `$008000` and `$808000` both read image offset 0, and only the copy in banks `$80` and above runs at 6 clocks. `$700000` is save memory, so it carries no offset into the image.

## Install

| Requirement | Version |
|:--|:--|
| Python | 3.12 or newer |
| git | Any |

```bash
git clone https://github.com/gufranco/snes-mapper-python.git
cd snes-mapper-python
python3 mapper/doctor.py
```

The package imports nothing outside the standard library.

The doctor reports the machine, resolves a probe address through every layout, reads a header out of an image it builds, counts the manifest and the corpus, and says which cartridge library it found. A fresh checkout has none, and the doctor reports that the check against real cartridges will skip. It exits 0 when every check passes and 1 otherwise. Paste its whole output into any bug report.

```
  13 checks, nothing to report
```

Releases follow [Semantic Versioning](https://semver.org/) and are cut from the commit history by semantic-release. Every release is tagged and listed on the [releases page](https://github.com/gufranco/snes-mapper-python/releases).

## The interface

Nothing here is built and then driven, and nothing executes code. Every call is a question about an address, an image or a register.

### Addresses

`resolve(kind, address, fast=False, banks=None, save=False)` returns a `Resolution`. `kind` is `LOROM`, `HIROM`, `EXHIROM` or `WHOLEBANK`. `fast` is the header's request for the faster bus. `banks` is the image size in 64 KB banks, which `WHOLEBANK` requires. `save` maps banks `$70` to `$7D` as save memory on `WHOLEBANK`, where they are cartridge otherwise. Any other string for `kind` reads cartridge banks the way `HIROM` does, with no save memory window.

| Attribute | Meaning |
|:--|:--|
| `region` | `ROM`, `WORK_RAM`, `SAVE_RAM`, `REGISTERS` or `OPEN_BUS`, whose values are `rom`, `work-ram`, `save-ram`, `registers` and `open-bus` |
| `offset` | Where in the image the address reads, or `None` when the region is not `rom` |
| `cycles` | Master clocks the access costs: `FAST` is 6, `SLOW` is 8, `XSLOW` is 12 |
| `address` | The address asked about, masked to 24 bits |
| `is_rom` | True when `region` is `rom` |

### Layouts

`MODELS` maps each resolvable layout name to a `Model`. `layout_named(name)` returns the `Model` for a name or an alias, ignoring case, hyphens and underscores, and raises `UnknownModelError` for anything else. A `Model` carries `name`, `aliases`, `header_at` and `summary`, and `model.resolve(address, fast=False, banks=None, save=False)` calls `resolve` with its own name.

| Layout | Aliases | Header at |
|:--|:--|:--|
| `lorom` | `lo`, `mode20`, `20` | `$7FC0` |
| `hirom` | `hi`, `mode21`, `21` | `$FFC0` |
| `exhirom` | `exhi`, `mode25`, `25` | `$FFC0`, and `$40FFC0` when the image reaches it |
| `wholebank` | `whole`, `wholebanks`, `interleaved` | `$7FC0` |

```python
import mapper

for name in ("lorom", "hirom", "exhirom", "wholebank"):
    model = mapper.layout_named(name)
    print(model.name, model.aliases, f"{model.header_at:#06x}")

print(mapper.layout_named("Mode-20").name)

try:
    mapper.layout_named("sa1")
except mapper.UnknownModelError as error:
    print(error)
```

```
lorom ('lo', 'mode20', '20') 0x7fc0
hirom ('hi', 'mode21', '21') 0xffc0
exhirom ('exhi', 'mode25', '25') 0xffc0
wholebank ('whole', 'wholebanks', 'interleaved') 0x7fc0
lorom
sa1 is not a layout this package covers; it has exhirom, hirom, lorom, wholebank
```

### Headers

| Call | Returns |
|:--|:--|
| `read(rom)` | The `Header` at the candidate place that scores highest. Raises `NoHeader` when no place scores 2 or more |
| `score(rom, at)` | The points one candidate place earns, 0 to 4, or -1 when 32 bytes do not fit there |
| `board(found, size)` | The layout name for a `Header` and an image size. A header that reads as `lorom` on a 12 MB image is `wholebank` |
| `has_copier_stub(rom)` | True when the image carries the 512 bytes a copier prepends |
| `stub_by_length(size)` | The same test on a length alone |
| `Header(at, raw)` | A header built from its 32 bytes and the offset they came from |

The candidate places are `LOROM_HEADER`, `$7FC0`, `HIROM_HEADER`, `$FFC0`, and `$40FFC0`, each moved by `COPIER_BYTES`, `$200`, when the image carries a copier stub. A place earns one point each for a title with at least 19 of its 21 bytes printable, a nonzero checksum consistent with its complement, a declared size from 8 to 13, and a mapping byte that names a layout whose header sits at that place.

| Attribute | Meaning |
|:--|:--|
| `at`, `shift` | Where the header was found, and how far a copier stub moved it |
| `raw` | The 32 bytes |
| `title` | The 21-byte title, trailing spaces and zero bytes removed |
| `mapping`, `declared` | The byte that names a layout, and whether its high nibble is 2 or 3, which is when it is believed |
| `layout` | From the byte when it is believed, and from the offset when it is not. One of `lorom`, `hirom`, `exhirom`, `sa1`, `spc7110` |
| `rom_bytes`, `ram_bytes` | The declared sizes in bytes |
| `checksum`, `complement`, `checksum_agrees` | The pair, and whether they sum to `$FFFF` |
| `fast`, `battery`, `coprocessor` | Whether it asks for the faster bus, carries battery-backed save memory, carries a chip |
| `chipset`, `country` | The remaining declared bytes |

```python
from mapper import HIROM_HEADER, LOROM_HEADER, read, score

rom = bytearray(0x20000)
rom[0x7FC0:0x7FD5] = b"A WORKED EXAMPLE     "
rom[0x7FD5:0x7FDA] = bytes([0x30, 0x02, 0x0A, 0x03, 0x01])
rom[0x7FDC:0x7FE0] = bytes([0x34, 0x12, 0xCB, 0xED])
rom = bytes(rom)

print(score(rom, LOROM_HEADER), score(rom, HIROM_HEADER))
found = read(rom)
print(found)
print(found.at, found.shift, f"{found.mapping:#04x}", found.declared, found.layout)
print(found.rom_bytes, found.ram_bytes, f"{found.checksum:#06x}", found.checksum_agrees)
print(found.fast, found.battery, found.coprocessor, found.chipset, found.country)
```

```
4 1
<Header 'A WORKED EXAMPLE' lorom at 0x007fc0>
32704 0 0x30 True lorom
1048576 8192 0xedcb True
True True False 2 1
```

Mapping byte `$30` declares the low layout with the fast bit set. Chipset `$02` is ROM with battery-backed RAM. Size bytes `$0A` and `$03` declare 1 MB of ROM and 8 KB of RAM.

### Images

| Name | Content |
|:--|:--|
| `bank_count(size)` | Whole 64 KB banks in an image of that size. Raises `NotWholeBanks` otherwise |
| `interleave(logical)`, `deinterleave(built)` | Between the order the console reads and the order an interleaved dump stores: every upper half first, then every lower half |
| `snes_to_file(bank, addr, banks)`, `file_to_snes(offset, banks)` | Between a bank and address and a position in an interleaved file |
| `window_to_file(bank, addr, banks)` | The same for banks `WINDOW_FIRST_BANK`, `$C0`, and above |
| `address_to_file(bank, addr, banks)` | Whichever of the two applies to that bank |
| `BANK`, `HALF` | `$10000` and `$8000` |
| `WHOLEBANK_BANKS`, `WHOLEBANK_BYTES` | 192 banks and 12 MB, the only size `WHOLEBANK` resolves |

```python
from mapper import bank_count, file_to_snes, snes_to_file, stub_by_length

banks = bank_count(4 * 1024 * 1024)
print(banks, snes_to_file(0x00, 0x8000, banks), file_to_snes(0, banks))
print(file_to_snes(banks * 0x8000, banks))
print(stub_by_length(0x100200), stub_by_length(0x100000))
```

```
64 0 (0, 32768)
(0, 0)
True False
```

A 4 MB interleaved file holds the upper half of bank `$00` at offset 0 and its lower half 64 half-banks later.

### Transfers

| Name | Content |
|:--|:--|
| `Engine()` | The eight channels, `channels`, and the two arming registers, `enable` and `enable_indirect` |
| `engine.write(address, value)` | One byte to `ENABLE`, `$420B`, to `$420C`, or to a channel register. Any other address is ignored |
| `engine.enabled` | The channels `ENABLE` selects |
| `engine.plans()` | A `Plan` for each of those channels and none for the rest |
| `Plan` | `channel`, `source`, `length`, `step`, `destination`, `to_cpu`, and `addresses()`, every source address in order, wrapping inside the bank |
| `Channel(index)` | One channel: `index`, its 16 `registers`, `write(offset, value)`, and `plan()` |
| `channel.parameters`, `channel.to_cpu` | Register `$43x0`, and its bit 7, set when the transfer runs toward the processor |
| `channel.step` | 1, then -1 when bit 4 of the parameters is set, and 0 whenever bit 3 is set |
| `channel.destination`, `channel.source` | `$2100` plus register `$43x1`, and the 24-bit address in `$43x2` to `$43x4` |
| `channel.count`, `channel.length` | The 16-bit count in `$43x5` and `$43x6`, and the bytes it moves: the count, or 65536 when the count is 0 |
| `channel_of(address)` | The channel a register address belongs to, or `None` outside `CHANNEL_BASE`, `$4300`, to `$437F` |
| `CHANNEL_COUNT` | 8 |

```python
from mapper import ENABLE, Engine, channel_of

engine = Engine()
written = {0x4310: 0x01, 0x4311: 0x18, 0x4313: 0x80, 0x4314: 0x7E, 0x4315: 0x04}
for register, value in written.items():
    engine.write(register, value)
print(engine.plans())

engine.write(ENABLE, 0x02)
plan = engine.plans()[0]
print(plan, f"{plan.destination:#06x}", plan.step, plan.to_cpu)
print([f"{one:06X}" for one in plan.addresses()])
print(channel_of(0x4370), channel_of(0x4380))
```

```
[]
<channel 1: 4 bytes from 7E8000> 0x2118 1 False
['7E8000', '7E8001', '7E8002', '7E8003']
7 None
```

Channel 1 holds a complete four-byte transfer from `$7E8000` to `$2118`, and `plans()` reports nothing until `ENABLE` selects it.

### Errors

| Error | Raised when |
|:--|:--|
| `NoHeader` | `read` finds no candidate place scoring 2 or more |
| `NotWholeBanks` | An image size is not a whole number of 64 KB banks |
| `NeedsBankCount` | `WHOLEBANK` is resolved without `banks`, or with fewer than 192 |
| `UnknownModelError` | `layout_named` is given a name no layout goes by |

```python
from mapper import WHOLEBANK, NeedsBankCount, NoHeader, NotWholeBanks, bank_count, read, resolve

for attempt in (
    lambda: read(bytes(0x10000)),
    lambda: bank_count(1000),
    lambda: resolve(WHOLEBANK, 0x008000, banks=64),
):
    try:
        attempt()
    except (NoHeader, NotWholeBanks, NeedsBankCount) as error:
        print(type(error).__name__, str(error).split(". ")[0])
```

```
NoHeader no header found in 65536 bytes
NotWholeBanks 1000 is not a whole number of 65536 byte banks
NeedsBankCount wholebank needs 192 banks and this image has 64
```

Each message carries more after its first sentence: `NeedsBankCount` goes on to say why a smaller image cannot be on this map, and without `banks` it names the call that counts them.

### Module contents

`mapper.__version__` is the installed version. The layout names `LOROM`, `HIROM`, `EXHIROM` and `WHOLEBANK` are the strings `lorom`, `hirom`, `exhirom` and `wholebank`. The submodules `header`, `layout`, `image`, `transfer`, `models` and `errors` are reachable as attributes, and `layout.EXHIROM_BYTES` is 8 MB.

### Command-line tools

Each runs from the repository root. Everything under `conformance/` runs as a module.

| Command | Does | Exit codes |
|:--|:--|:--|
| `python3 mapper/doctor.py` | Reports the machine and the checkout | 0 clean, 1 a check failed |
| `python3 mapper/environment.py` | The machine half of that report alone | 0 clean, 1 a check failed |
| `python3 -m conformance.corpus [corpus]` | Replays every recorded header combination | 0 all agree, 1 one did not, 2 no corpus |
| `python3 -m conformance.against_cartridges [directory]` | Reads every cartridge present and holds each to its case | 0 all agree, 1 one did not, 2 no cartridge found |
| `python3 -m conformance.census <directory> <out> [limit]` | Tallies the headers of a library | 0 written, 1 no cartridge, 2 bad arguments |
| `python3 -m conformance.record <directory> [out] [limit]` | Rebuilds the corpus from a library | 0 written, 1 no cartridge, 2 bad arguments |
| `python3 -m conformance.documents [--check] [--only SUBSTRING]` | Fetches the manual and verifies its digest, or verifies the copy present | 0 verified, 1 refused, no match or bad arguments |
| `python3 -m conformance.quotes` | Finds every quoted sentence in the manual | 0 found or no manual present, 1 a quote is missing or a citation points at the wrong place |
| `python3 -m conformance.speed` | The throughput floor | 0 above it, 1 below it |
| `python3 -m conformance.links` | Requests every address this README cites and prints each status as JSON | 0 every address still exists, 1 one is gone with status `404` or `410` |
| `python3 -m conformance.package <wheel>` | Checks a built wheel carries every module and no test file | 0 clean, 1 a fault or no wheel there, 2 no argument |

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

Some dumps store every bank's upper half first and every lower half afterwards. A patch written at a known address into an interleaved image lands half a bank away, in another bank's data.

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

They sit in the middle of the bank numbering and read like any other address. The bottom 8 KB of every low bank mirror the same work RAM, which is the second line.

### The transfer registers belong to the processor

```python
from mapper import CHANNEL_BASE, ENABLE

print(f"{ENABLE:#06x} {CHANNEL_BASE:#06x}")
```

```
0x420b 0x4300
```

A hook on the display's `$21xx` window sees every graphics write and no transfer.

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

Masking with `& 7` folds `$4380` onto channel 0 instead of reporting that it lies outside the window.

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
from mapper import layout_named

print(f"{layout_named('lorom').header_at:#06x}")
print(f"{layout_named('hirom').header_at:#06x}")
print(f"{layout_named('exhirom').header_at:#06x}")
print(f"{layout_named('wholebank').header_at:#06x}")

print(layout_named("mode20").name)
print(layout_named("hirom").resolve(0xC00000).region)
```

```
0x7fc0
0xffc0
0xffc0
0x7fc0
lorom
rom
```

| Layout | Shape |
|:--|:--|
| `lorom` | A 32 KB page per bank, in the upper half of each bank, with save memory filling banks `$70` to `$7D` and `$F0` to `$FD` |
| `hirom` | A whole 64 KB bank per bank, with save memory at `$6000` to `$7FFF` in banks `$20` to `$3F` and `$A0` to `$BF` |
| `exhirom` | `hirom` with its two 4 MB halves swapped |
| `wholebank` | A whole 64 KB per bank below `$C0` from an interleaved 12 MB image |

A header also declares `sa1` and `spc7110`. The census counts them, and `layout_named` refuses them: neither has a corpus behind its address mapping.

### The extended layout swaps its halves

Banks `$80` to `$FF` carry the first 4 MB of an `exhirom` image. Banks `$00` to `$7D`, which hold the reset vector, carry everything past it.

```python
from mapper import layout

print(f"{layout.resolve('exhirom', 0x00FFC0).offset:#08x}")
print(f"{layout.resolve('hirom', 0x00FFC0).offset:#08x}")
```

```
0x40ffc0
0x00ffc0
```

That is why an extended cartridge keeps a header 4 MB in. The ceiling is `layout.EXHIROM_BYTES`, 8 MB, and the top of it is reachable only through banks `$3E` and `$3F`, because `$7E` and `$7F` are work RAM.

### 96 megabits, and the map that reaches it

The whole-bank map spends nothing below its window on anything but cartridge. Banks `$00` to `$BF` each carry 64 KB, so 192 banks fit, and the image holds all of them interleaved, as [`mapper/image.py`](mapper/image.py) converts.

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

The first is the upper half of bank `$00`, where the low layout puts it. The second is the lower half of bank `$40`. The third comes through the window the banks from `$C0` open.

The smallest size this map accepts comes from an equation. The window reads its lower halves from the run belonging to bank `$80`, so its top byte sits `191 + banks` half-banks into a file `2 * banks` half-banks long. The two meet at exactly 192 banks, so `resolve` refuses any smaller bank count.

`board()` picks this map from the image size and never from the chipset byte. An expansion built by removing a coprocessor often still declares it, and a six megabyte cartridge that declares S-DD1 is not on this map.

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

## What a real library contains

Read out of 2,781 retail cartridges and nothing else. A modified release, a translation and a prototype can each carry an edited header, so none of them is counted.

| Declared layout | Cartridges |
|:--|--:|
| `lorom` | 2,157 |
| `hirom` | 572 |
| `sa1` | 42 |
| `exhirom` | 6 |
| `spc7110` | 4 |

1,701 ask for the faster bus, 957 carry battery-backed save memory, and 2,780 carry a checksum consistent with its complement. Headers sit at `$7FC0` in 2,200, at `$FFC0` in 579 and at `$40FFC0` in 2. A further 8 files carry no header `read` accepts and are counted as refused.

### The mapping byte is not always a mapping byte

8 distinct in-range mapping bytes occur, all `$2x` or `$3x`. 13 cartridges carry one outside that range, 11 of them a capital letter: a 22-character title overflows its 21-byte field and writes its last letter over the mapping byte.

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

`0x53` is `S`, the title's last letter. An out-of-range byte is not consulted, and the layout comes from where the header sits. Reading the low nibble of such a byte gave 51 retail cartridges in a wider library the wrong layout, the wrong bus speed, or both. An in-range byte is believed even where it disagrees with the offset, because `exhirom` puts its header where `hirom` does whenever the far copy would sit past the end of the image.

Across 7,314 cartridges, the size byte read at the right offset falls between 8 and 13 in 98.85% of them, while a byte read at a wrong offset falls in that band only 3.18% of the time, which is why `score` gives that band a point.

## The corpus, and why it can ship

A header is 32 bytes in which a cartridge describes how it is built.

| Field | What it is | Shipped |
|:--|:--|:--|
| Mapping, chipset, ROM and RAM size, country | Facts about a physical object | Yes |
| How many cartridges share a combination | A measurement | Yes |
| The title | A name | No |
| Anything outside the header | The game | Never read |

Facts and functional elements sit outside what copyright reaches, per [17 U.S.C. 102(b)](https://www.law.cornell.edu/uscode/text/17/102) and *Feist*. [`conformance/census.py`](conformance/census.py) reads only those 32 bytes and records no title. This is how the repository is built, not legal advice.

[`conformance/corpus.json`](conformance/corpus.json) carries every distinct combination with the header offset, the layout it produces, and what 14 probe addresses resolve to under it.

### Taking a census of your own library

```bash
python3 -m conformance.census /path/to/roms census.json
```

On the library behind the corpus it prints `2781 cartridges read, 8 refused` and `287 distinct header combinations`. The census does not key on the header offset, so it finds 2 fewer combinations than the corpus.

### Rebuilding the corpus that ships

```bash
python3 -m conformance.record /path/to/roms conformance/corpus.json
```

Anyone holding the same cartridges rebuilds the file and compares it byte for byte. Two cartridges with identical fields at different offsets are two cases, because the offset names the layout whenever the mapping byte is a stray letter.

### Bringing your own cartridges

Put copies you own in [`cartridges/`](cartridges/), in `../cartridges` beside the checkout, or wherever `SNES_CARTRIDGE_DIR` points. A named directory wins, then the one beside the checkout, then the one inside it. Subdirectories are walked, and `.sfc` and `.smc` files are read.

Every file is checked against all four digests in [`cartridges.manifest.json`](cartridges.manifest.json) before it is read: `sha256` decides, and `crc32`, `md5` and `sha1` must match too. The manifest names 2,778 cartridges and 2 bad dumps. [`cartridges/README.md`](cartridges/README.md) lists every filename and its digests, and nothing in the directory is committed.

## What each piece of evidence is worth

| Evidence | What it settles | What it cannot |
|:--|:--|:--|
| Nintendo's manual, with arithmetic in [`conformance/hardware.json`](conformance/hardware.json) | The two bus speeds, so the 6 and 8 clock counts | The 12 clock count, which the manual does not print |
| Header combinations read out of 2,781 cartridges | What a combination means on shipped cartridges | Combinations no cartridge carries |
| Digests of every cartridge read | That the file read is the file named | Whether that release is the one you meant |

Not modelled: the processor, so how many accesses an instruction makes; refresh and transfer stalls; and anything that happens once an address is reached.

## Is it right

Every distinct header combination is replayed against the layout and the addresses it produces: 289 combinations, 0 disagreements. The corpus carries the measurements, not the cartridges, so this runs anywhere.

```bash
python3 -m conformance.corpus
```

It prints `289 agreed, 0 did not` and exits 0.

With a library present, the sweep reads every file and holds each cartridge to the case that recorded it. On the library behind the corpus it prints `2781 agreed, 0 did not`. With no library it prints why and exits 2, and CI annotates that skip.

```bash
python3 -m conformance.against_cartridges
```

[`conformance/hardware.json`](conformance/hardware.json) quotes the two bus speeds Nintendo printed, 2.68 MHz and 3.58 MHz, and shows the arithmetic from each to 8 and 6 master clocks. The 12-clock count follows from no document and is marked unverified. [`conformance/divergences.json`](conformance/divergences.json) holds every place two sources part, and [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) holds every place fidelity here is a claim rather than a measurement, with what would settle it.

## Working on it

| Need | Where |
|:--|:--|
| Every gate and the order to run them | [CONTRIBUTING.md](CONTRIBUTING.md) |
| The same material for a coding agent | [AGENTS.md](AGENTS.md) |
| The standard this repository shares with the rest of the family | [FAMILY.md](FAMILY.md) |
| Bug reports | [GitHub Issues](https://github.com/gufranco/snes-mapper-python/issues) |
| Security reports | [SECURITY.md](SECURITY.md) |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 mypy==1.14.1
pnpm install --frozen-lockfile && pnpm run format:check
python3 -m coverage erase
for file in $(find mapper conformance -name '*.test.py' | sort); do
  python3 -m coverage run -a "$file"
done
python3 -m coverage report
python3 -m conformance.corpus
python3 -m conformance.speed
```

Each module has a test file beside it, named `<module>.test.py`, and each runs on its own. Coverage is a hard gate at 100% statement and branch, set in [`pyproject.toml`](pyproject.toml). The throughput floor in [`conformance/speed.py`](conformance/speed.py) is 200,000 `resolve` calls per second and runs outside the coverage step. Tests that need a cartridge live in [`conformance/on_disk.test.py`](conformance/on_disk.test.py), the one file kept out of the coverage count.

## References

| Document | Publisher | Read on | Bytes | SHA-256 |
|:--|:--|:--|--:|:--|
| *SNES Development Manual, Book I*, full text as archived | Nintendo of America Inc. | 2026-08-27 | 298,926 | `100beabe8e29d6e02b60b9a0f057a40063a4e33a83478f480ecc2e8696e77972` |

It is not redistributable and is not in this repository. `python3 -m conformance.documents` downloads it from https://archive.org/download/SNESDevManual/book1_djvu.txt into `docs/`, which git ignores, and refuses any file whose digest differs. `--check` verifies the copy already present. [`conformance/documents.json`](conformance/documents.json) carries the digest and the address. The sentences taken from it are in [`conformance/hardware.json`](conformance/hardware.json), each with the table and page it came from.

The 2,781 headers behind [`conformance/corpus.json`](conformance/corpus.json) come from a retail cartridge library the author owns. Nothing from it is committed beyond the digests in [`cartridges.manifest.json`](cartridges.manifest.json).

## Citing this

[CITATION.cff](CITATION.cff) is updated with each release by the script that stamps the package version.

## License

MIT. See [LICENSE](LICENSE).
