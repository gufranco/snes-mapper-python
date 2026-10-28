# SNES Mapper

用 Python 实现的 SNES 卡带内存映射及其传输引擎：一个地址落在哪里、访问它的代价是多少、一个已启用的通道会搬运什么，并以 2,781 个零售版卡带的头部作为检验标准。

[English](README.md) | [日本語](README.ja.md) | 简体中文 | [繁體中文（香港）](README.zh-HK.md)

[![CI](https://github.com/gufranco/snes-mapper-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/snes-mapper-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/snes-mapper-python)](https://github.com/gufranco/snes-mapper-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

在 **2,781** 个零售版卡带上重放 **289** 种头部组合，**0** 处不一致，**6** 种布局中 **6** 种可解析，**8** 个传输通道，**1,110** 个测试，**100%** 语句和分支覆盖率，无依赖

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

该示例在低位布局上解析六个地址，对应的卡带在头部中请求了更快的总线。bank `$7E` 以及每个低位 bank 的最低 8 KB 是工作 RAM，这一点在考虑任何卡带 bank 之前就已确定。`$004016` 是手柄端口，耗费 12 个主时钟。`$008000` 和 `$808000` 都读取镜像偏移 0，只有位于 bank `$80` 及以上的那份副本以 6 个时钟运行。`$700000` 是存档内存，所以它不带镜像内的偏移。

## 安装

| 要求   | 版本        |
| :----- | :---------- |
| Python | 3.12 或更高 |
| git    | 任意        |

```bash
git clone https://github.com/gufranco/snes-mapper-python.git
cd snes-mapper-python
python3 mapper/doctor.py
```

该包不导入标准库之外的任何内容。

诊断脚本会报告本机信息，通过每种布局解析一个探测地址，从它自行构建的镜像中读取头部，统计清单和语料库，并说明找到了哪个卡带库。全新的检出中没有卡带库，诊断脚本会报告针对真实卡带的检查将被跳过。所有检查通过时退出码为 0，否则为 1。提交缺陷报告时请粘贴其完整输出。

```
  15 checks, nothing to report
```

版本遵循[语义化版本](https://semver.org/)，由 semantic-release 根据提交历史生成。每个版本都会打标签，并列在[发布页面](https://github.com/gufranco/snes-mapper-python/releases)上。

## 接口

这里没有任何东西是先构建再驱动的，也没有任何东西执行代码。每次调用都是关于一个地址、一个镜像或一个寄存器的提问。

### 地址

`resolve(kind, address, fast=False, banks=None, save=False)` 返回一个 `Resolution`。`kind` 为 `LOROM`、`HIROM`、`EXHIROM`、`WHOLEBANK`、`SA1` 或 `SPC7110`。`fast` 是头部对更快总线的请求。`banks` 是以 64 KB bank 计的镜像大小，`WHOLEBANK` 必须提供它。`save` 在 `WHOLEBANK` 上把 bank `$70` 到 `$7D` 映射为存档内存，否则这些 bank 属于卡带。`kind` 为其他任何字符串时，按 `HIROM` 的方式读取卡带 bank，且没有存档内存窗口。

| 属性      | 含义                                                                                                                                                                                                                                                        |
| :-------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `region`  | `ROM`、`WORK_RAM`、`SAVE_RAM`、`REGISTERS`、`OPEN_BUS` 或 `COPROCESSOR`，其值分别为 `rom`、`work-ram`、`save-ram`、`registers`、`open-bus` 和 `coprocessor`。`coprocessor` 是由卡带上的芯片解码的地址：SA-1 的寄存器和工作 RAM，SPC7110 的寄存器和端口 bank |
| `offset`  | 该地址读取的镜像位置，region 不是 `rom` 时为 `None`                                                                                                                                                                                                         |
| `cycles`  | 访问耗费的主时钟数：`FAST` 为 6，`SLOW` 为 8，`XSLOW` 为 12                                                                                                                                                                                                 |
| `address` | 所询问的地址，掩码为 24 位                                                                                                                                                                                                                                  |
| `is_rom`  | `region` 为 `rom` 时为 True                                                                                                                                                                                                                                 |

在 bank `$00` 到 `$3F` 和 `$80` 到 `$BF` 的 `$8000` 以下，主机按 Book I 图 2-21-1 所印固定速度，与 `fast` 无关：`$2000` 到 `$3FFF` 和 `$4200` 到 `$5FFF` 耗费 6，`$4000` 到 `$41FF` 的手柄端口耗费 12，工作 RAM 和 `$6000` 到 `$7FFF` 耗费 8。`fast` 只作用于 bank `$80` 到 `$BF` 的 `$8000` 及以上，以及 bank `$C0` 到 `$FF`。

`work_ram_offset(address)` 返回地址到达 131,072 个工作 RAM 单元中的哪一个，`resolve` 不认为是工作 RAM 的地址返回 `None`。存储体 `$7E` 和 `$7F` 按顺序存放这些单元，每个低位存储体的底部 8 KB 到达其中的前 8 KB，所以 `$00:1000`、`$20:1000` 和 `$7E:1000` 是同一个单元 `0x1000`。图 2-21-1 把这两块区域印为 8 KB 的 RAM 1 和位于存储体 `$7E`、`$7F` 的 120 KB 的 RAM 2，两者合起来正是这两个存储体寻址的 128 KB。

### 布局

`MODELS` 把每个可解析的布局名称映射到一个 `Model`。`layout_named(name)` 根据名称或别名返回 `Model`，忽略大小写、连字符和下划线，其他任何输入都会抛出 `UnknownModelError`。`Model` 带有 `name`、`aliases`、`header_at` 和 `summary`，`model.resolve(address, fast=False, banks=None, save=False)` 以它自己的名称调用 `resolve`。

| 布局        | 别名                                 | 头部位置                            |
| :---------- | :----------------------------------- | :---------------------------------- |
| `lorom`     | `lo`、`mode20`、`20`                 | `$7FC0`                             |
| `hirom`     | `hi`、`mode21`、`21`                 | `$FFC0`                             |
| `exhirom`   | `exhi`、`mode25`、`25`               | `$FFC0`，镜像足够大时还有 `$40FFC0` |
| `wholebank` | `whole`、`wholebanks`、`interleaved` | `$7FC0`                             |
| `sa1`       | `mode23`、`23`                       | `$7FC0`                             |
| `spc7110`   | 无                                   | `$FFC0`                             |

```python
import mapper

for name in ("lorom", "hirom", "exhirom", "wholebank", "sa1", "spc7110"):
    model = mapper.layout_named(name)
    print(model.name, model.aliases, f"{model.header_at:#06x}")

print(mapper.layout_named("Mode-20").name)

try:
    mapper.layout_named("superfx")
except mapper.UnknownModelError as error:
    print(error)
```

```
lorom ('lo', 'mode20', '20') 0x7fc0
hirom ('hi', 'mode21', '21') 0xffc0
exhirom ('exhi', 'mode25', '25') 0xffc0
wholebank ('whole', 'wholebanks', 'interleaved') 0x7fc0
sa1 ('mode23', '23') 0x7fc0
spc7110 () 0xffc0
lorom
superfx is not a layout this package covers; it has exhirom, hirom, lorom, sa1, spc7110, wholebank
```

### 头部

| 调用                   | 返回                                                                                       |
| :--------------------- | :----------------------------------------------------------------------------------------- |
| `read(rom)`            | 得分最高的候选位置上的 `Header`。没有任何位置得分达到 2 或以上时抛出 `NoHeader`            |
| `score(rom, at)`       | 一个候选位置获得的分数，0 到 4；该处放不下 32 字节时为 -1                                  |
| `board(found, size)`   | 给定 `Header` 和镜像大小对应的布局名称。在 12 MB 镜像上读作 `lorom` 的头部即为 `wholebank` |
| `has_copier_stub(rom)` | 镜像带有拷贝机前置的 512 字节时为 True                                                     |
| `stub_by_length(size)` | 仅凭长度进行同样的判断                                                                     |
| `Header(at, raw)`      | 由 32 字节及其来源偏移构建的头部                                                           |

候选位置为 `LOROM_HEADER`（`$7FC0`）、`HIROM_HEADER`（`$FFC0`）和 `$40FFC0`，镜像带有拷贝机前置数据时，每个位置都移动 `COPIER_BYTES`，即 `$200`。一个位置在以下每项上各得一分：标题的 21 字节中至少 19 字节可打印；校验和非零且与其补码一致；声明的大小在 8 到 13 之间；映射字节所指的布局，其头部正好位于该位置。

| 属性                                        | 含义                                                                                      |
| :------------------------------------------ | :---------------------------------------------------------------------------------------- |
| `at`、`shift`                               | 头部被找到的位置，以及拷贝机前置数据使它移动了多远                                        |
| `raw`                                       | 这 32 字节                                                                                |
| `title`                                     | 21 字节的标题，去掉末尾的空格和零字节                                                     |
| `mapping`、`declared`                       | 指明布局的字节，以及其高半字节是否为 2 或 3，只有这时才采信它                             |
| `layout`                                    | 采信时取自该字节，不采信时取自偏移。为 `lorom`、`hirom`、`exhirom`、`sa1`、`spc7110` 之一 |
| `rom_bytes`、`ram_bytes`                    | 以字节计的声明大小                                                                        |
| `checksum`、`complement`、`checksum_agrees` | 这一对值，以及它们之和是否为 `$FFFF`                                                      |
| `fast`、`battery`、`coprocessor`            | 是否请求更快的总线、是否带有电池供电的存档内存、是否带有芯片                              |
| `chipset`、`country`                        | 其余的声明字节                                                                            |

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

映射字节 `$30` 声明低位布局并置位快速位。芯片组 `$02` 表示 ROM 加电池供电的 RAM。大小字节 `$0A` 和 `$03` 声明 1 MB ROM 和 8 KB RAM。

### 镜像

| 名称                                                             | 内容                                                                             |
| :--------------------------------------------------------------- | :------------------------------------------------------------------------------- |
| `bank_count(size)`                                               | 该大小的镜像中完整 64 KB bank 的数量。不是整数个 bank 时抛出 `NotWholeBanks`     |
| `interleave(logical)`、`deinterleave(built)`                     | 在主机读取的顺序与交错转储的存储顺序之间转换：先是所有上半部分，再是所有下半部分 |
| `snes_to_file(bank, addr, banks)`、`file_to_snes(offset, banks)` | 在 bank 加地址与交错文件中的位置之间转换                                         |
| `window_to_file(bank, addr, banks)`                              | 对 `WINDOW_FIRST_BANK`（`$C0`）及以上的 bank 做同样的转换                        |
| `address_to_file(bank, addr, banks)`                             | 对该 bank 适用的上述两者之一                                                     |
| `BANK`、`HALF`                                                   | `$10000` 和 `$8000`                                                              |
| `WHOLEBANK_BANKS`、`WHOLEBANK_BYTES`                             | 192 个 bank 和 12 MB，这是 `WHOLEBANK` 唯一能解析的大小                          |

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

一个 4 MB 的交错文件在偏移 0 处存放 bank `$00` 的上半部分，其下半部分位于 64 个半 bank 之后。

### 传输

| 名称                                    | 内容                                                                                                                         |
| :-------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------- |
| `Engine()`                              | 八个通道 `channels`，以及两个启用寄存器 `enable` 和 `enable_indirect`                                                        |
| `engine.write(address, value)`          | 向 `ENABLE`（`$420B`）、`$420C` 或某个通道寄存器写入一个字节。其他任何地址都被忽略                                           |
| `engine.enabled`                        | `ENABLE` 选中的通道                                                                                                          |
| `engine.plans()`                        | 为上述每个通道各给出一个 `Plan`，其余通道没有                                                                                |
| `Plan`                                  | `channel`、`source`、`length`、`step`、`destination`、`to_cpu`，以及 `addresses()`，即按顺序排列的每个源地址，在 bank 内回绕 |
| `Channel(index)`                        | 一个通道：`index`、它的 16 个 `registers`、`write(offset, value)` 和 `plan()`                                                |
| `channel.parameters`、`channel.to_cpu`  | 寄存器 `$43x0`，以及它的第 7 位，传输朝处理器方向进行时置位                                                                  |
| `channel.step`                          | 默认为 1，参数的第 4 位置位时为 -1，第 3 位置位时总是 0                                                                      |
| `channel.destination`、`channel.source` | `$2100` 加上寄存器 `$43x1`，以及 `$43x2` 到 `$43x4` 中的 24 位地址                                                           |
| `channel.count`、`channel.length`       | `$43x5` 和 `$43x6` 中的 16 位计数，以及它搬运的字节数：即该计数，计数为 0 时为 65536                                         |
| `channel_of(address)`                   | 寄存器地址所属的通道，不在 `CHANNEL_BASE`（`$4300`）到 `$437F` 范围内时为 `None`                                             |
| `CHANNEL_COUNT`                         | 8                                                                                                                            |

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

通道 1 保存着一次完整的四字节传输，从 `$7E8000` 到 `$2118`，在 `ENABLE` 选中它之前，`plans()` 不报告任何内容。

### 错误

| 错误                | 抛出时机                                      |
| :------------------ | :-------------------------------------------- |
| `NoHeader`          | `read` 找不到得分达到 2 或以上的候选位置      |
| `NotWholeBanks`     | 镜像大小不是整数个 64 KB bank                 |
| `NeedsBankCount`    | 解析 `WHOLEBANK` 时未提供 `banks`，或少于 192 |
| `UnknownModelError` | 传给 `layout_named` 的名称不属于任何布局      |

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

每条消息在第一句之后还有更多内容：`NeedsBankCount` 接着说明为什么较小的镜像不可能使用这种映射，未提供 `banks` 时，它会指出用于统计 bank 数的调用。

### 模块内容

`mapper.__version__` 是已安装的版本。布局名称 `LOROM`、`HIROM`、`EXHIROM`、`WHOLEBANK`、`SA1` 和 `SPC7110` 分别是字符串 `lorom`、`hirom`、`exhirom`、`wholebank`、`sa1` 和 `spc7110`。子模块 `header`、`layout`、`image`、`transfer`、`models` 和 `errors` 可作为属性访问，`layout.EXHIROM_BYTES` 为 8 MB。

### 命令行工具

每个工具都在仓库根目录运行。`conformance/` 下的所有内容都以模块方式运行。

| 命令                                                            | 作用                                                           | 退出码                                                       |
| :-------------------------------------------------------------- | :------------------------------------------------------------- | :----------------------------------------------------------- |
| `python3 mapper/doctor.py`                                      | 报告本机和检出的状态                                           | 0 正常，1 有检查失败                                         |
| `python3 mapper/environment.py`                                 | 仅报告其中关于本机的一半                                       | 0 正常，1 有检查失败                                         |
| `python3 -m conformance.corpus [corpus]`                        | 重放每种已记录的头部组合                                       | 0 全部一致，1 有不一致，2 没有语料库                         |
| `python3 -m conformance.against_cartridges [directory]`         | 读取现有的每个卡带，并用其对应的用例逐一检验                   | 0 全部一致，1 有不一致，2 未找到卡带                         |
| `python3 -m conformance.testcarts [--record out.json]`          | 映射现有的每个测试卡带，并与记录的读取结果逐一对照             | 0 全部一致，1 有一个不一致，2 没有测试卡带或参数错误         |
| `python3 -m conformance.selftest [--record out.json]`           | 重放从现有每个自检卡带中读出的工厂自检，并与记录的结果逐一对照 | 0 全部一致，1 有一个不一致，2 没有自检卡带或参数错误         |
| `python3 -m conformance.census <directory> <out> [limit]`       | 统计一个卡带库的头部                                           | 0 已写入，1 没有卡带，2 参数错误                             |
| `python3 -m conformance.record <directory> [out] [limit]`       | 根据卡带库重建语料库                                           | 0 已写入，1 没有卡带，2 参数错误                             |
| `python3 -m conformance.documents [--check] [--only SUBSTRING]` | 下载手册并校验其摘要，或校验已有的副本                         | 0 已校验，1 被拒绝、无匹配或参数错误                         |
| `python3 -m conformance.quotes`                                 | 在手册中查找每一句被引用的句子                                 | 0 全部找到或手册不存在，1 某处引文缺失或某条出处指向错误位置 |
| `python3 -m conformance.speed`                                  | 吞吐量下限                                                     | 0 高于下限，1 低于下限                                       |
| `python3 -m conformance.links`                                  | 请求本 README 引用的每个地址，并以 JSON 打印每个状态           | 0 每个地址仍然存在，1 某个地址已失效，状态为 `404` 或 `410`  |
| `python3 -m conformance.package <wheel>`                        | 检查构建出的 wheel 是否包含每个模块且不含测试文件              | 0 正常，1 有问题或该处没有 wheel，2 未提供参数               |

## 本项目要防止的错误

### 交错转储的存储顺序不是主机读取的顺序

```python
from mapper import deinterleave, interleave

image = bytes(range(256)) * 1024

print(deinterleave(interleave(image)) == image)
```

```
True
```

有些转储先存放每个 bank 的上半部分，再存放所有下半部分。按已知地址写入交错镜像的补丁会落在半个 bank 之外，进入另一个 bank 的数据。

### bank `$7E` 和 `$7F` 不属于卡带

```python
from mapper import LOROM, resolve

print(resolve(LOROM, 0x7E0900).region)
print(resolve(LOROM, 0x001000).region)
```

```
work-ram
work-ram
```

它们位于 bank 编号的中间，读起来和其他任何地址一样。每个低位 bank 的最低 8 KB 镜像同一块工作 RAM，这就是第二行。

### 传输寄存器属于处理器

```python
from mapper import CHANNEL_BASE, ENABLE

print(f"{ENABLE:#06x} {CHANNEL_BASE:#06x}")
```

```
0x420b 0x4300
```

挂在显示部分 `$21xx` 窗口上的钩子能看到每一次图形写入，却看不到任何传输。

### 通道索引是一个半字节

```python
from mapper import channel_of

print(channel_of(0x4370))
print(channel_of(0x4380))
```

```
7
None
```

用 `& 7` 做掩码会把 `$4380` 折叠到通道 0，而不是报告它位于窗口之外。

### 从未启用的通道仍然会应答

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

寄存器保留着它们最后写入的值，所以遍历全部八个通道会报告从未发生过的传输。

## 布局

```python
from mapper import layout_named

print(f"{layout_named('lorom').header_at:#06x}")
print(f"{layout_named('hirom').header_at:#06x}")
print(f"{layout_named('exhirom').header_at:#06x}")
print(f"{layout_named('wholebank').header_at:#06x}")
print(f"{layout_named('sa1').header_at:#06x}")
print(f"{layout_named('spc7110').header_at:#06x}")

print(layout_named("mode20").name)
print(layout_named("hirom").resolve(0xC00000).region)
```

```
0x7fc0
0xffc0
0xffc0
0x7fc0
0x7fc0
0xffc0
lorom
rom
```

| 布局        | 形态                                                                                                                                                                  |
| :---------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `lorom`     | 每个 bank 一个 32 KB 页，位于每个 bank 的上半部分，存档内存占据 bank `$70` 到 `$7D` 以及 `$F0` 到 `$FD`                                                               |
| `hirom`     | 每个 bank 一个完整的 64 KB bank，存档内存位于 bank `$20` 到 `$3F` 以及 `$A0` 到 `$BF` 中的 `$6000` 到 `$7FFF`                                                         |
| `exhirom`   | 两个 4 MB 半区互换的 `hirom`                                                                                                                                          |
| `wholebank` | `$C0` 以下每个 bank 一个完整的 64 KB，来自交错的 12 MB 镜像                                                                                                           |
| `sa1`       | 四个 8 Mbit 块依次排列：`$00` 到 `$3F` 和 `$80` 到 `$BF` 每个 bank 一页 32 KB，从 `$C0` 起每个 bank 一个完整 bank，备份 RAM 在 `$40` 到 `$4F` 以及 `$6000` 到 `$7FFF` |
| `spc7110`   | 程序 ROM 即镜像的第一个兆字节，位于 `$00` 到 `$0F`、`$80` 到 `$8F` 和 `$C0` 到 `$CF`，其后的数据 ROM 位于其余每个 ROM bank                                            |

### The two coprocessor maps

```python
from mapper import SA1, SPC7110, resolve

for kind, addresses in (
    (SA1, (0x002200, 0x003000, 0x008000, 0x808000, 0x406000, 0xD00000)),
    (SPC7110, (0x004800, 0x500000, 0x008000, 0x108000, 0xD00000)),
):
    for address in addresses:
        landed = resolve(kind, address)
        where = "-" if landed.offset is None else f"{landed.offset:#08x}"
        print(kind, f"{address:06X}", landed.region, where)
```

```
sa1 002200 coprocessor -
sa1 003000 coprocessor -
sa1 008000 rom 0x000000
sa1 808000 rom 0x200000
sa1 406000 save-ram -
sa1 D00000 rom 0x100000
spc7110 004800 coprocessor -
spc7110 500000 coprocessor -
spc7110 008000 rom 0x008000
spc7110 108000 rom 0x108000
spc7110 D00000 rom 0x100000
```

SA-1 的映射是 Book II 为主机处理器印出的那一张，取 bank 寄存器 `$2220` 到 `$2223` 和备份 RAM 寄存器 `$2224` 的初始值。bank `$80` 到 `$BF` 承载第三和第四块，而不是前两块的镜像。程序写入这些寄存器会移动映射，`resolve` 不跟随。没有任何 Nintendo 文档印出 SPC7110 的电路板，所以它的映射取自固定提交的 ares 电路板数据库和 SPC7110 源码，记录中标记为未验证。在游戏选定数据 bank 之前，每个数据 bank 都读取程序 ROM 之后的第一个兆字节。

### 扩展布局互换了两个半区

bank `$80` 到 `$FF` 承载 `exhirom` 镜像的前 4 MB。bank `$00` 到 `$7D` 包含复位向量，承载其后的所有内容。

```python
from mapper import layout

print(f"{layout.resolve('exhirom', 0x00FFC0).offset:#08x}")
print(f"{layout.resolve('hirom', 0x00FFC0).offset:#08x}")
```

```
0x40ffc0
0x00ffc0
```

这就是扩展卡带在 4 MB 处保留一个头部的原因。上限是 `layout.EXHIROM_BYTES`，即 8 MB，其顶部只能通过 bank `$3E` 和 `$3F` 访问，因为 `$7E` 和 `$7F` 是工作 RAM。

### 96 兆位，以及能够触及它的映射

整 bank 映射在其窗口以下的空间全部用于卡带。bank `$00` 到 `$BF` 各承载 64 KB，所以能容纳 192 个 bank，镜像以交错方式存放全部这些 bank，由 [`mapper/image.py`](mapper/image.py) 负责转换。

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

第一个是 bank `$00` 的上半部分，与低位布局放置它的位置相同。第二个是 bank `$40` 的下半部分。第三个来自从 `$C0` 开始的 bank 所开启的窗口。

这个映射接受的最小大小来自一个等式。窗口从属于 bank `$80` 的那一段读取下半部分，因此其最高字节位于一个长 `2 * banks` 个半 bank 的文件中第 `191 + banks` 个半 bank 处。两者恰好在 192 个 bank 处相等，因此 `resolve` 拒绝任何更小的 bank 数。

`board()` 根据镜像大小选择这种映射，从不根据芯片组字节。通过移除协处理器构建的扩容版常常仍然声明该协处理器，而一个声明了 S-DD1 的 6 MB 卡带并不使用这种映射。

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

## 真实卡带库包含什么

仅从 2,781 个零售版卡带中读取，别无其他来源。修改版、翻译版和原型版都可能带有被编辑过的头部，所以都不计入。

| 声明的布局 | 卡带数 |
| :--------- | -----: |
| `lorom`    |  2,157 |
| `hirom`    |    572 |
| `sa1`      |     42 |
| `exhirom`  |      6 |
| `spc7110`  |      4 |

1,701 个请求更快的总线，957 个带有电池供电的存档内存，2,780 个的校验和与其补码一致。头部位于 `$7FC0` 的有 2,200 个，位于 `$FFC0` 的有 579 个，位于 `$40FFC0` 的有 2 个。另有 8 个文件没有 `read` 接受的头部，计为被拒绝。

### 映射字节并不总是映射字节

出现了 8 种不同的范围内映射字节，全部是 `$2x` 或 `$3x`。13 个卡带的映射字节超出该范围，其中 11 个是大写字母：22 个字符的标题溢出了 21 字节的字段，把最后一个字母写到了映射字节上。

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

`0x53` 是 `S`，即标题的最后一个字母。超出范围的字节不予参考，布局取决于头部所在的位置。在一个更大的卡带库中，读取这类字节的低半字节让 51 个零售版卡带得到了错误的布局、错误的总线速度，或两者皆错。范围内的字节即使与偏移矛盾也会被采信，因为每当远端副本会超出镜像末尾时，`exhirom` 就把头部放在 `hirom` 放置头部的位置。

在 7,314 个卡带中，在正确偏移处读到的大小字节有 98.85% 落在 8 到 13 之间，而在错误偏移处读到的字节落在这个区间的比例只有 3.18%，这就是 `score` 为该区间给一分的原因。

## 语料库，以及它为何可以随项目发布

头部是 32 个字节，卡带在其中描述自身的构造。

| 字段                                | 性质           | 是否发布 |
| :---------------------------------- | :------------- | :------- |
| 映射、芯片组、ROM 和 RAM 大小、国家 | 关于实物的事实 | 是       |
| 有多少卡带共享同一组合              | 一项测量       | 是       |
| 标题                                | 一个名称       | 否       |
| 头部之外的任何内容                  | 游戏本身       | 从不读取 |

依据 [17 U.S.C. 102(b)](https://www.law.cornell.edu/uscode/text/17/102) 和 _Feist_ 案，事实和功能性元素不在版权保护范围之内。[`conformance/census.py`](conformance/census.py) 只读取这 32 字节，不记录标题。这是本仓库的构建方式，不构成法律意见。

[`conformance/corpus.json`](conformance/corpus.json) 包含每种不同的组合，以及头部偏移、它产生的布局，和 14 个探测地址在该布局下的解析结果。

### 对你自己的卡带库进行普查

```bash
python3 -m conformance.census /path/to/roms census.json
```

在语料库所依据的卡带库上，它打印 `2781 cartridges read, 8 refused` 和 `287 distinct header combinations`。普查不以头部偏移作为键，所以它找到的组合比语料库少 2 种。

### 重建随项目发布的语料库

```bash
python3 -m conformance.record /path/to/roms conformance/corpus.json
```

持有相同卡带的任何人都能重建该文件，并逐字节比较。字段相同但偏移不同的两个卡带是两个用例，因为每当映射字节是一个误入的字母时，偏移就决定了布局。

### 使用你自己的卡带

把你拥有的副本放在 `external/cartridges/` 中、包含本检出目录的项目的 `external/cartridges/` 中，或 `SNES_CARTRIDGE_DIR` 指向的任何位置。指定的目录优先，其次是包含它的项目中的目录，最后是本检出目录内部的目录。会遍历子目录，并读取 `.sfc` 和 `.smc` 文件。

每个文件在读取之前都会与 [`cartridges.manifest.json`](cartridges.manifest.json) 中的全部四个摘要进行核对：以 `sha256` 为准，`crc32`、`md5` 和 `sha1` 也必须匹配。清单列出了 2,778 个卡带和 2 个坏转储。[CARTRIDGES.md](CARTRIDGES.md) 列出了每个文件名及其摘要，`external/` 中的内容都不会提交。

## 每项证据的价值

| 证据                                                                                    | 能确定什么                                                      | 不能确定什么                                |
| :-------------------------------------------------------------------------------------- | :-------------------------------------------------------------- | :------------------------------------------ |
| Nintendo 的手册，以及 [`conformance/hardware.json`](conformance/hardware.json) 中的计算 | 三种 CPU 时钟速度及各自适用的地址，因而确定 6、8 和 12 的时钟数 | 主时钟，手册中没有给出                      |
| Book II 第 1 部分第 3、4 章                                                             | 寄存器初始值下的 SA-1 映射                                      | 程序写入之后的映射                          |
| 固定提交的 ares 电路板数据库和 SPC7110 源码                                             | 无；它是线索，标记为未验证                                      | 没有任何 Nintendo 文档印出的 SPC7110 电路板 |
| 从 2,781 个卡带中读取的头部组合                                                         | 某种组合在已发售卡带上的含义                                    | 没有任何卡带使用的组合                      |
| 所读取的每个卡带的摘要                                                                  | 读取的文件就是所指名的文件                                      | 该发行版是否就是你想要的那个                |

未建模的内容：处理器，因而无法知道一条指令进行多少次访问；刷新和传输造成的停顿；以及到达某个地址之后发生的任何事情。

## 它是否正确

每种不同的头部组合都会针对其产生的布局和地址进行重放：289 种组合，0 处不一致。语料库携带的是测量结果而不是卡带，所以这可以在任何地方运行。

```bash
python3 -m conformance.corpus
```

它打印 `289 agreed, 0 did not` 并以 0 退出。

有卡带库时，这一遍历会读取每个文件，并用记录该卡带的用例检验每个卡带。在语料库所依据的卡带库上，它打印 `2781 agreed, 0 did not`。没有卡带库时，它打印原因并以 2 退出，CI 会对这次跳过加注。

```bash
python3 -m conformance.against_cartridges
```

[`conformance/hardware.json`](conformance/hardware.json) 引用了 Nintendo 在 Book I 第 21.1 节公布的三种 CPU 时钟速度 3.58 MHz、2.68 MHz 和 1.79 MHz，并给出从它们分别算到 6、8 和 12 个主时钟的过程。从扫描页面读出的图 2-21-1 把 1.79 MHz 的区域放在 `$4000` 到 `$41FF`。[`conformance/divergences.json`](conformance/divergences.json) 记录两个来源出现分歧的每一处，[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md) 记录本项目的保真度属于断言而非测量的每一处，以及什么能够解决它。

## 参与开发

| 需求                             | 位置                                                                   |
| :------------------------------- | :--------------------------------------------------------------------- |
| 每项门禁检查及其运行顺序         | [CONTRIBUTING.md](CONTRIBUTING.md)                                     |
| 面向编程代理的同一份材料         | [AGENTS.md](AGENTS.md)                                                 |
| 本仓库与同系列其他仓库共享的标准 | [FAMILY.md](FAMILY.md)                                                 |
| 缺陷报告                         | [GitHub Issues](https://github.com/gufranco/snes-mapper-python/issues) |
| 安全报告                         | [SECURITY.md](SECURITY.md)                                             |

```bash
uvx ruff@0.16.3 format --check .
uvx ruff@0.16.3 check .
uvx --python 3.12 --with types-setuptools==84.0.0.20260812 mypy==1.14.1
pnpm install --frozen-lockfile && pnpm run format:check
cov=(uvx --python 3.12 --from coverage==7.6.10 --with setuptools==84.0.0 coverage)
"${cov[@]}" erase
for file in $(find mapper conformance -name '*.test.py' | sort); do
  "${cov[@]}" run -a "$file"
done
"${cov[@]}" report
python3 -m conformance.corpus
python3 -m conformance.speed
```

每个模块旁边都有一个名为 `<module>.test.py` 的测试文件，每个都可以单独运行。覆盖率是一项硬性门禁检查，要求 100% 语句和分支覆盖，设置在 [`pyproject.toml`](pyproject.toml) 中。[`conformance/speed.py`](conformance/speed.py) 中的吞吐量下限是每秒 200,000 次 `resolve` 调用，在覆盖率步骤之外运行。需要卡带的测试位于 [`conformance/on_disk.test.py`](conformance/on_disk.test.py)，这是唯一不计入覆盖率的文件。

## 参考资料

| 文档                                                 | 发布方                   | 阅读日期   |     字节数 | SHA-256                                                            |
| :--------------------------------------------------- | :----------------------- | :--------- | ---------: | :----------------------------------------------------------------- |
| _SNES Development Manual, Book I_，存档的全文        | Nintendo of America Inc. | 2026-08-27 |    298,926 | `100beabe8e29d6e02b60b9a0f057a40063a4e33a83478f480ecc2e8696e77972` |
| _SNES Development Manual, Book I_，带文字层的扫描页  | Nintendo of America Inc. | 2026-10-19 | 21,022,582 | `f1405241000046abba7849376d2ec53cf85f1ad2e9950d69a7c2cf1f3ff6b791` |
| _SNES Development Manual, Book II_，存档的全文       | Nintendo of America Inc. | 2026-10-19 |    463,516 | `546f8e38caf6cb19c8aa9d5a1fef090d8cfc4a0a13b54c3b56d704975ab8398a` |
| _SNES Development Manual, Book II_，带文字层的扫描页 | Nintendo of America Inc. | 2026-10-19 | 29,575,127 | `05197923d9b73b63845fc5c2d609e753ec634dc1e4b403ce7a57326e1259c3ed` |

四者都不可再分发，也都不在本仓库中。`python3 -m conformance.documents` 从 archive.org 条目 https://archive.org/details/SNESDevManual 下载全部四个文件到 `docs/`，该目录被 git 忽略，摘要不同的任何文件都会被拒绝。`--check` 校验已有的副本。[`conformance/documents.json`](conformance/documents.json) 记录摘要和地址。从中摘取的句子在 [`conformance/hardware.json`](conformance/hardware.json) 中，每句都注明了出自哪个表格和哪一页。

[`conformance/corpus.json`](conformance/corpus.json) 所依据的 2,781 个头部来自作者拥有的一个零售版卡带库。除了 [`cartridges.manifest.json`](cartridges.manifest.json) 中的摘要之外，其中的任何内容都没有提交。

## 引用本项目

[CITATION.cff](CITATION.cff) 在每次发布时由写入包版本号的脚本更新。

## 许可证

MIT。参见 [LICENSE](LICENSE)。
