# SNES Mapper

以 Python 實現的 SNES 卡帶記憶體映射及其傳輸引擎：一個位址落在哪裏、存取它要付出多少代價、一個已啟用的通道會搬移甚麼，並以 2,781 盒零售版卡帶的標頭加以驗證。

[English](README.md) | [日本語](README.ja.md) | [简体中文](README.zh-Hans.md) | 繁體中文（香港）

[![CI](https://github.com/gufranco/snes-mapper-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/snes-mapper-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/snes-mapper-python)](https://github.com/gufranco/snes-mapper-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**289** 種標頭組合在 **2,781** 盒零售版卡帶上重放，**0** 處不一致，**6** 種佈局中 **4** 種可解析，**8** 個傳輸通道，**865** 個測試，**100%** 語句及分支覆蓋率，沒有任何依賴

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

這個示例在低位佈局上解析六個位址，對應的卡帶標頭要求較快的匯流排。Bank `$7E` 及每個低位 bank 的最底 8 KB 都是工作 RAM，而這一點在考慮任何卡帶 bank 之前已經決定。`$004016` 是控制器埠，花費 12 個主時鐘。`$008000` 和 `$808000` 都讀取映像檔偏移 0，只有位於 bank `$80` 及以上的副本以 6 個時鐘運行。`$700000` 是存檔記憶體，所以不帶映像檔內的偏移。

## 安裝

| 需求 | 版本 |
|:--|:--|
| Python | 3.12 或更新 |
| git | 任何版本 |

```bash
git clone https://github.com/gufranco/snes-mapper-python.git
cd snes-mapper-python
python3 mapper/doctor.py
```

這個套件只匯入標準程式庫的內容。

診斷腳本會報告機器資訊，將一個探測位址經過每種佈局解析，從它自行建立的映像檔讀出標頭，統計清單和語料庫，並說明找到了哪個卡帶庫。全新的 checkout 沒有卡帶庫，診斷腳本會報告針對真實卡帶的檢查將被略過。所有檢查通過時以 0 結束，否則以 1 結束。提交錯誤報告時請貼上它的完整輸出。

```
  13 checks, nothing to report
```

發佈版本遵循 [Semantic Versioning](https://semver.org/)，由 semantic-release 根據提交歷史產生。每個發佈版本都有標籤，並列於[發佈頁面](https://github.com/gufranco/snes-mapper-python/releases)。

## 介面

這裏沒有任何東西需要先建立再驅動，也沒有任何東西會執行程式碼。每個呼叫都是關於一個位址、一個映像檔或一個暫存器的提問。

### 位址

`resolve(kind, address, fast=False, banks=None, save=False)` 傳回一個 `Resolution`。`kind` 是 `LOROM`、`HIROM`、`EXHIROM` 或 `WHOLEBANK`。`fast` 是標頭對較快匯流排的要求。`banks` 是以 64 KB bank 計算的映像檔大小，`WHOLEBANK` 必須提供。`save` 在 `WHOLEBANK` 上把 bank `$70` 至 `$7D` 映射為存檔記憶體，否則它們屬於卡帶。`kind` 若為其他字串，則以 `HIROM` 的方式讀取卡帶 bank，且沒有存檔記憶體窗口。

| 屬性 | 含義 |
|:--|:--|
| `region` | `ROM`、`WORK_RAM`、`SAVE_RAM`、`REGISTERS` 或 `OPEN_BUS`，其值分別為 `rom`、`work-ram`、`save-ram`、`registers` 和 `open-bus` |
| `offset` | 該位址讀取映像檔中的哪個位置；區域不是 `rom` 時為 `None` |
| `cycles` | 該次存取花費的主時鐘數：`FAST` 為 6，`SLOW` 為 8，`XSLOW` 為 12 |
| `address` | 所查詢的位址，遮罩至 24 位元 |
| `is_rom` | `region` 為 `rom` 時為 True |

### 佈局

`MODELS` 將每個可解析的佈局名稱對應到一個 `Model`。`layout_named(name)` 為一個名稱或別名傳回對應的 `Model`，忽略大小寫、連字號和底線，其他任何輸入都會引發 `UnknownModelError`。`Model` 帶有 `name`、`aliases`、`header_at` 和 `summary`，而 `model.resolve(address, fast=False, banks=None, save=False)` 會以自身的名稱呼叫 `resolve`。

| 佈局 | 別名 | 標頭位置 |
|:--|:--|:--|
| `lorom` | `lo`、`mode20`、`20` | `$7FC0` |
| `hirom` | `hi`、`mode21`、`21` | `$FFC0` |
| `exhirom` | `exhi`、`mode25`、`25` | `$FFC0`，映像檔夠大時還有 `$40FFC0` |
| `wholebank` | `whole`、`wholebanks`、`interleaved` | `$7FC0` |

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

### 標頭

| 呼叫 | 傳回 |
|:--|:--|
| `read(rom)` | 得分最高的候選位置上的 `Header`。沒有任何位置得分達 2 或以上時引發 `NoHeader` |
| `score(rom, at)` | 一個候選位置得到的分數，0 至 4；該處容不下 32 位元組時為 -1 |
| `board(found, size)` | 給定一個 `Header` 和映像檔大小時的佈局名稱。在 12 MB 映像檔上讀作 `lorom` 的標頭屬於 `wholebank` |
| `has_copier_stub(rom)` | 映像檔帶有拷貝機在開頭加上的 512 位元組時為 True |
| `stub_by_length(size)` | 只憑長度作同樣的判斷 |
| `Header(at, raw)` | 由 32 位元組及其來源偏移建立的標頭 |

候選位置是 `LOROM_HEADER`（`$7FC0`）、`HIROM_HEADER`（`$FFC0`）及 `$40FFC0`，映像檔帶有拷貝機前置資料時，各自移動 `COPIER_BYTES`，即 `$200`。一個位置每符合以下一項便得一分：標題的 21 個位元組中至少 19 個可列印；校驗和非零且與其補數一致；宣告的大小介乎 8 至 13；映射位元組所指的佈局，其標頭正好位於該位置。

| 屬性 | 含義 |
|:--|:--|
| `at`、`shift` | 標頭所在位置，以及拷貝機前置資料把它移動了多遠 |
| `raw` | 該 32 位元組 |
| `title` | 21 位元組的標題，已移除結尾的空格和零位元組 |
| `mapping`、`declared` | 指明佈局的位元組，以及其高半位元組是否為 2 或 3，只有此時才採信它 |
| `layout` | 採信該位元組時由它得出，不採信時由偏移得出。為 `lorom`、`hirom`、`exhirom`、`sa1`、`spc7110` 之一 |
| `rom_bytes`、`ram_bytes` | 以位元組計的宣告大小 |
| `checksum`、`complement`、`checksum_agrees` | 這一對數值，以及兩者相加是否為 `$FFFF` |
| `fast`、`battery`、`coprocessor` | 是否要求較快的匯流排、是否帶有電池供電的存檔記憶體、是否帶有晶片 |
| `chipset`、`country` | 其餘的宣告位元組 |

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

映射位元組 `$30` 宣告低位佈局並設定了快速位元。晶片組 `$02` 是 ROM 加電池供電的 RAM。大小位元組 `$0A` 和 `$03` 宣告 1 MB 的 ROM 和 8 KB 的 RAM。

### 映像檔

| 名稱 | 內容 |
|:--|:--|
| `bank_count(size)` | 該大小的映像檔所含的完整 64 KB bank 數。否則引發 `NotWholeBanks` |
| `interleave(logical)`、`deinterleave(built)` | 在主機讀取的次序與交錯傾印的儲存次序之間轉換：先是所有上半部，然後是所有下半部 |
| `snes_to_file(bank, addr, banks)`、`file_to_snes(offset, banks)` | 在 bank 加位址與交錯檔案中的位置之間轉換 |
| `window_to_file(bank, addr, banks)` | 對 bank `WINDOW_FIRST_BANK`（`$C0`）及以上作同樣轉換 |
| `address_to_file(bank, addr, banks)` | 按該 bank 適用的情況選用上述兩者之一 |
| `BANK`、`HALF` | `$10000` 和 `$8000` |
| `WHOLEBANK_BANKS`、`WHOLEBANK_BYTES` | 192 個 bank 和 12 MB，是 `WHOLEBANK` 唯一能解析的大小 |

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

一個 4 MB 的交錯檔案把 bank `$00` 的上半部放在偏移 0，其下半部則在 64 個半 bank 之後。

### 傳輸

| 名稱 | 內容 |
|:--|:--|
| `Engine()` | 八個通道 `channels`，以及兩個啟用暫存器 `enable` 和 `enable_indirect` |
| `engine.write(address, value)` | 向 `ENABLE`（`$420B`）、`$420C` 或某個通道暫存器寫入一個位元組。其他位址一概忽略 |
| `engine.enabled` | `ENABLE` 所選的通道 |
| `engine.plans()` | 為上述每個通道提供一個 `Plan`，其餘通道則沒有 |
| `Plan` | `channel`、`source`、`length`、`step`、`destination`、`to_cpu`，以及 `addresses()`，即按次序列出的每個來源位址，在 bank 內循環 |
| `Channel(index)` | 一個通道：`index`、其 16 個 `registers`、`write(offset, value)` 和 `plan()` |
| `channel.parameters`、`channel.to_cpu` | 暫存器 `$43x0`，及其位元 7，傳輸朝處理器方向進行時設定 |
| `channel.step` | 為 1；參數的位元 4 設定時為 -1；位元 3 設定時一律為 0 |
| `channel.destination`、`channel.source` | `$2100` 加上暫存器 `$43x1`，以及 `$43x2` 至 `$43x4` 中的 24 位元位址 |
| `channel.count`、`channel.length` | `$43x5` 和 `$43x6` 中的 16 位元計數，以及它搬移的位元組數：即該計數，計數為 0 時則為 65536 |
| `channel_of(address)` | 一個暫存器位址所屬的通道；在 `CHANNEL_BASE`（`$4300`）至 `$437F` 範圍外時為 `None` |
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

通道 1 持有一次從 `$7E8000` 到 `$2118` 的完整四位元組傳輸，而在 `ENABLE` 選中它之前，`plans()` 甚麼也不報告。

### 錯誤

| 錯誤 | 引發時機 |
|:--|:--|
| `NoHeader` | `read` 找不到任何得分達 2 或以上的候選位置 |
| `NotWholeBanks` | 映像檔大小不是 64 KB bank 的整數倍 |
| `NeedsBankCount` | 解析 `WHOLEBANK` 時沒有提供 `banks`，或少於 192 |
| `UnknownModelError` | 傳給 `layout_named` 的名稱不屬於任何佈局 |

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

每條訊息在第一句之後還有更多內容：`NeedsBankCount` 接着說明為何較小的映像檔不可能使用這種映射，而在沒有 `banks` 時，它會指出用來計算 bank 數的呼叫。

### 模組內容

`mapper.__version__` 是已安裝的版本。佈局名稱 `LOROM`、`HIROM`、`EXHIROM` 和 `WHOLEBANK` 分別是字串 `lorom`、`hirom`、`exhirom` 和 `wholebank`。子模組 `header`、`layout`、`image`、`transfer`、`models` 和 `errors` 可作為屬性存取，而 `layout.EXHIROM_BYTES` 為 8 MB。

### 命令列工具

每個工具都在儲存庫根目錄執行。`conformance/` 下的所有內容都以模組方式執行。

| 命令 | 作用 | 結束碼 |
|:--|:--|:--|
| `python3 mapper/doctor.py` | 報告機器及 checkout 的狀況 | 0 正常，1 有檢查失敗 |
| `python3 mapper/environment.py` | 只報告上述報告中機器的一半 | 0 正常，1 有檢查失敗 |
| `python3 -m conformance.corpus [corpus]` | 重放每種已記錄的標頭組合 | 0 全部一致，1 有一項不一致，2 沒有語料庫 |
| `python3 -m conformance.against_cartridges [directory]` | 讀取現有的每盒卡帶，並逐一以其案例核對 | 0 全部一致，1 有一項不一致，2 找不到卡帶 |
| `python3 -m conformance.census <directory> <out> [limit]` | 統計一個卡帶庫的標頭 | 0 已寫入，1 沒有卡帶，2 參數錯誤 |
| `python3 -m conformance.record <directory> [out] [limit]` | 從一個卡帶庫重建語料庫 | 0 已寫入，1 沒有卡帶，2 參數錯誤 |
| `python3 -m conformance.documents [--check] [--only SUBSTRING]` | 下載手冊並驗證其摘要，或驗證現有的副本 | 0 已驗證，1 被拒絕、沒有相符項或參數錯誤 |
| `python3 -m conformance.quotes` | 在手冊中找出每個被引用的句子 | 0 全部找到或沒有手冊，1 有引文缺失或出處指向錯誤位置 |
| `python3 -m conformance.speed` | 吞吐量下限 | 0 高於下限，1 低於下限 |
| `python3 -m conformance.links` | 請求本 README 引用的每個網址，並以 JSON 列印每個狀態 | 0 每個網址仍然存在，1 有一個以狀態 `404` 或 `410` 消失 |
| `python3 -m conformance.package <wheel>` | 檢查已建置的 wheel 包含每個模組且不含測試檔案 | 0 正常，1 有錯誤或該處沒有 wheel，2 沒有參數 |

## 本專案要防止的錯誤

### 交錯傾印的儲存次序不是主機讀取的次序

```python
from mapper import deinterleave, interleave

image = bytes(range(256)) * 1024

print(deinterleave(interleave(image)) == image)
```

```
True
```

有些傾印先儲存每個 bank 的上半部，之後才儲存每個下半部。在交錯映像檔中按已知位址寫入的修補，會落在半個 bank 之外，寫進另一個 bank 的數據。

### Bank `$7E` 和 `$7F` 不屬於卡帶

```python
from mapper import LOROM, resolve

print(resolve(LOROM, 0x7E0900).region)
print(resolve(LOROM, 0x001000).region)
```

```
work-ram
work-ram
```

它們位於 bank 編號的中間，讀起來與其他位址無異。每個低位 bank 的最底 8 KB 是同一工作 RAM 的鏡像，這就是第二行。

### 傳輸暫存器屬於處理器

```python
from mapper import CHANNEL_BASE, ENABLE

print(f"{ENABLE:#06x} {CHANNEL_BASE:#06x}")
```

```
0x420b 0x4300
```

掛在顯示器 `$21xx` 窗口上的鈎子會看到每次圖形寫入，卻看不到任何傳輸。

### 通道索引是一個半位元組

```python
from mapper import channel_of

print(channel_of(0x4370))
print(channel_of(0x4380))
```

```
7
None
```

用 `& 7` 遮罩會把 `$4380` 摺疊到通道 0，而不是報告它在窗口之外。

### 從未啟用的通道仍然會回應

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

暫存器保留它們最後持有的值，所以逐一走訪全部八個通道會報告從未發生過的傳輸。

## 佈局

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

| 佈局 | 形態 |
|:--|:--|
| `lorom` | 每個 bank 一個 32 KB 頁面，位於各 bank 的上半部，存檔記憶體佔據 bank `$70` 至 `$7D` 及 `$F0` 至 `$FD` |
| `hirom` | 每個 bank 一個完整的 64 KB bank，存檔記憶體位於 bank `$20` 至 `$3F` 及 `$A0` 至 `$BF` 的 `$6000` 至 `$7FFF` |
| `exhirom` | 兩個 4 MB 半部互換的 `hirom` |
| `wholebank` | `$C0` 以下每個 bank 一個完整的 64 KB，來自一個交錯的 12 MB 映像檔 |

標頭也會宣告 `sa1` 和 `spc7110`。普查會統計它們，而 `layout_named` 拒絕它們：兩者的位址映射背後都沒有語料庫。

### 擴展佈局互換其兩個半部

Bank `$80` 至 `$FF` 承載 `exhirom` 映像檔的首 4 MB。Bank `$00` 至 `$7D` 存放重設向量，承載此後的所有內容。

```python
from mapper import layout

print(f"{layout.resolve('exhirom', 0x00FFC0).offset:#08x}")
print(f"{layout.resolve('hirom', 0x00FFC0).offset:#08x}")
```

```
0x40ffc0
0x00ffc0
```

這就是擴展卡帶在 4 MB 處保留一個標頭的原因。上限是 `layout.EXHIROM_BYTES`，即 8 MB，而其頂端只能經由 bank `$3E` 和 `$3F` 到達，因為 `$7E` 和 `$7F` 是工作 RAM。

### 96 megabit，以及能到達它的映射

整 bank 映射在其窗口以下的空間只用於卡帶。Bank `$00` 至 `$BF` 各承載 64 KB，所以可容納 192 個 bank，而映像檔以交錯方式存放全部 bank，轉換方式見 [`mapper/image.py`](mapper/image.py)。

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

第一個是 bank `$00` 的上半部，與低位佈局放置它的位置相同。第二個是 bank `$40` 的下半部。第三個經由從 `$C0` 開始的 bank 所開啟的窗口到達。

這個映射接受的最小大小來自一條等式。窗口從屬於 bank `$80` 的那一段讀取其下半部，所以它的最高位元組位於一個長 `2 * banks` 個半 bank 的檔案中第 `191 + banks` 個半 bank 處。兩者恰好在 192 個 bank 相等，所以 `resolve` 會拒絕任何較小的 bank 數。

`board()` 根據映像檔大小選用這種映射，從不根據晶片組位元組。移除協處理器而製成的擴充版本往往仍然宣告該協處理器，而一盒宣告 S-DD1 的 6 MB 卡帶並不使用這種映射。

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

## 真實卡帶庫的內容

僅從 2,781 盒零售版卡帶讀出，別無其他來源。修改版、翻譯版和原型版都可能帶有經編輯的標頭，所以全部不計算在內。

| 宣告的佈局 | 卡帶數 |
|:--|--:|
| `lorom` | 2,157 |
| `hirom` | 572 |
| `sa1` | 42 |
| `exhirom` | 6 |
| `spc7110` | 4 |

1,701 盒要求較快的匯流排，957 盒帶有電池供電的存檔記憶體，2,780 盒的校驗和與其補數一致。標頭位於 `$7FC0` 的有 2,200 盒，位於 `$FFC0` 的有 579 盒，位於 `$40FFC0` 的有 2 盒。另有 8 個檔案沒有 `read` 接受的標頭，計為被拒絕。

### 映射位元組不一定是映射位元組

共出現 8 個不同的範圍內映射位元組，全部是 `$2x` 或 `$3x`。13 盒卡帶帶有範圍外的位元組，其中 11 盒是一個大寫字母：22 個字元的標題溢出其 21 位元組的欄位，把最後一個字母寫到映射位元組上。

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

`0x53` 就是 `S`，即標題的最後一個字母。範圍外的位元組不予參考，佈局由標頭所在位置決定。若讀取這種位元組的低半位元組，在一個更大的卡帶庫中會令 51 盒零售版卡帶得到錯誤的佈局、錯誤的匯流排速度，或兩者皆錯。範圍內的位元組即使與偏移不符也會被採信，因為每當遠處的副本會超出映像檔末端時，`exhirom` 都把標頭放在 `hirom` 放置的位置。

在 7,314 盒卡帶中，在正確偏移處讀到的大小位元組有 98.85% 介乎 8 至 13，而在錯誤偏移處讀到的位元組落在這個範圍的比例只有 3.18%，這就是 `score` 為這個範圍給一分的原因。

## 語料庫，以及它為何可以隨附發佈

標頭是 32 個位元組，卡帶在其中描述自己的構造。

| 欄位 | 性質 | 是否隨附 |
|:--|:--|:--|
| 映射、晶片組、ROM 和 RAM 大小、地區 | 關於實物的事實 | 是 |
| 有多少盒卡帶共用同一組合 | 一項量度 | 是 |
| 標題 | 一個名稱 | 否 |
| 標頭以外的任何內容 | 遊戲本身 | 從不讀取 |

根據 [17 U.S.C. 102(b)](https://www.law.cornell.edu/uscode/text/17/102) 及 *Feist* 案，事實和功能性元素不在版權保護範圍之內。[`conformance/census.py`](conformance/census.py) 只讀取那 32 個位元組，不記錄任何標題。這是本儲存庫的構建方式，並非法律意見。

[`conformance/corpus.json`](conformance/corpus.json) 載有每種不同的組合，連同標頭偏移、它產生的佈局，以及 14 個探測位址在該組合下解析的結果。

### 為你自己的卡帶庫進行普查

```bash
python3 -m conformance.census /path/to/roms census.json
```

在語料庫所依據的卡帶庫上，它列印 `2781 cartridges read, 8 refused` 和 `287 distinct header combinations`。普查不以標頭偏移作為鍵，所以找到的組合比語料庫少 2 種。

### 重建隨附的語料庫

```bash
python3 -m conformance.record /path/to/roms conformance/corpus.json
```

任何持有相同卡帶的人都可以重建該檔案，並逐位元組比較。欄位相同但偏移不同的兩盒卡帶算作兩個案例，因為每當映射位元組是一個錯置的字母時，偏移就決定了佈局。

### 使用你自己的卡帶

把你擁有的副本放在 [`cartridges/`](cartridges/)、checkout 旁邊的 `../cartridges`，或 `SNES_CARTRIDGE_DIR` 所指的位置。指定的目錄優先，其次是 checkout 旁邊的目錄，然後是 checkout 內的目錄。子目錄會被走訪，並讀取 `.sfc` 和 `.smc` 檔案。

每個檔案在讀取前都會以 [`cartridges.manifest.json`](cartridges.manifest.json) 中的全部四個摘要核對：以 `sha256` 為準，而 `crc32`、`md5` 和 `sha1` 也必須相符。清單列出 2,778 盒卡帶和 2 個損壞的傾印。[`cartridges/README.md`](cartridges/README.md) 列出每個檔案名稱及其摘要，而該目錄中的任何內容都不會提交。

## 每項證據的價值

| 證據 | 能確定甚麼 | 不能確定甚麼 |
|:--|:--|:--|
| Nintendo 的手冊，連同 [`conformance/hardware.json`](conformance/hardware.json) 中的算式 | 兩種匯流排速度，從而確定 6 和 8 的時鐘數 | 12 的時鐘數，手冊沒有印出 |
| 從 2,781 盒卡帶讀出的標頭組合 | 一種組合在已發行卡帶上的含義 | 沒有任何卡帶帶有的組合 |
| 每盒已讀取卡帶的摘要 | 讀取的檔案就是所指名的檔案 | 該發行版本是否就是你想要的那一版 |

未模擬的部分：處理器，因此不知道一條指令會作多少次存取；刷新和傳輸造成的停頓；以及到達位址之後發生的任何事情。

## 它正確嗎

每種不同的標頭組合都會針對佈局及其產生的位址重放：289 種組合，0 處不一致。語料庫載有的是量度結果而不是卡帶，所以這可以在任何地方執行。

```bash
python3 -m conformance.corpus
```

它列印 `289 agreed, 0 did not` 並以 0 結束。

有卡帶庫時，這次掃描會讀取每個檔案，並以記錄每盒卡帶的案例逐一核對。在語料庫所依據的卡帶庫上，它列印 `2781 agreed, 0 did not`。沒有卡帶庫時，它會列印原因並以 2 結束，CI 會為這次略過加上註解。

```bash
python3 -m conformance.against_cartridges
```

[`conformance/hardware.json`](conformance/hardware.json) 引述了 Nintendo 印出的兩種匯流排速度，2.68 MHz 和 3.58 MHz，並列出由每種速度推算出 8 和 6 個主時鐘的算式。12 個時鐘的數值並非出自任何文件，已標記為未經驗證。[`conformance/divergences.json`](conformance/divergences.json) 記錄兩個來源出現分歧的每一處，而 [OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) 記錄這裏的準確性屬於聲稱而非量度的每一處，以及甚麼可以解決它。

## 參與開發

| 需要 | 位置 |
|:--|:--|
| 每項關卡檢查及其執行次序 | [CONTRIBUTING.md](CONTRIBUTING.md) |
| 寫給程式編寫代理的同一份材料 | [AGENTS.md](AGENTS.md) |
| 本儲存庫與同系列其他儲存庫共用的標準 | [FAMILY.md](FAMILY.md) |
| 錯誤報告 | [GitHub Issues](https://github.com/gufranco/snes-mapper-python/issues) |
| 安全報告 | [SECURITY.md](SECURITY.md) |

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

每個模組旁邊都有一個名為 `<module>.test.py` 的測試檔案，各自獨立執行。覆蓋率是 100% 語句及分支的硬性關卡，在 [`pyproject.toml`](pyproject.toml) 中設定。[`conformance/speed.py`](conformance/speed.py) 中的吞吐量下限是每秒 200,000 次 `resolve` 呼叫，在覆蓋率步驟之外執行。需要卡帶的測試放在 [`conformance/on_disk.test.py`](conformance/on_disk.test.py)，這是唯一不計入覆蓋率的檔案。

## 參考資料

| 文件 | 出版者 | 閱讀日期 | 位元組 | SHA-256 |
|:--|:--|:--|--:|:--|
| *SNES Development Manual, Book I*，存檔的全文 | Nintendo of America Inc. | 2026-08-27 | 298,926 | `100beabe8e29d6e02b60b9a0f057a40063a4e33a83478f480ecc2e8696e77972` |

該文件不可再分發，也不在本儲存庫中。`python3 -m conformance.documents` 從 https://archive.org/download/SNESDevManual/book1_djvu.txt 下載它到 git 忽略的 `docs/`，並拒絕摘要不同的任何檔案。`--check` 驗證已存在的副本。[`conformance/documents.json`](conformance/documents.json) 載有摘要和網址。取自該文件的句子在 [`conformance/hardware.json`](conformance/hardware.json) 中，每句都附有其出處的表格和頁碼。

[`conformance/corpus.json`](conformance/corpus.json) 背後的 2,781 個標頭來自作者擁有的一個零售版卡帶庫。除了 [`cartridges.manifest.json`](cartridges.manifest.json) 中的摘要之外，其中的任何內容都沒有提交。

## 引用本專案

[CITATION.cff](CITATION.cff) 會在每次發佈時，由為套件蓋上版本號的腳本更新。

## 授權

MIT。見 [LICENSE](LICENSE)。
