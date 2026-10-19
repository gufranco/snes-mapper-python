# SNES Mapper

SNESカートリッジのメモリマップとその転送エンジンをPythonで実装したものです。アドレスがどこに着地するか、そこへのアクセスにどれだけかかるか、有効化されたチャンネルが何を転送するかを扱い、2,781本の市販カートリッジのヘッダーで検証しています。

[English](README.md) | 日本語 | [简体中文](README.zh-Hans.md) | [繁體中文（香港）](README.zh-HK.md)

[![CI](https://github.com/gufranco/snes-mapper-python/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/snes-mapper-python/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/gufranco/snes-mapper-python)](https://github.com/gufranco/snes-mapper-python/releases)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**289**通りのヘッダーの組み合わせを**2,781**本の市販カートリッジで再生、不一致**0**件、**6**種類のレイアウトのうち**6**種類を解決可能、転送チャンネル**8**本、テスト**1,016**件、ステートメントとブランチのカバレッジ**100%**、依存関係なし

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

この例は、ヘッダーで高速バスを要求するカートリッジについて、ローレイアウト上で6つのアドレスを解決します。バンク`$7E`と、すべてのローバンクの下位8 KBはワークRAMであり、これはカートリッジのバンクを考慮する前に決まります。`$004016`はコントローラーポートで、12マスタークロックかかります。`$008000`と`$808000`はどちらもイメージのオフセット0を読みますが、6クロックで動作するのはバンク`$80`以上にあるコピーだけです。`$700000`はセーブメモリなので、イメージ内のオフセットを持ちません。

## インストール

| 要件   | バージョン |
| :----- | :--------- |
| Python | 3.12以降   |
| git    | 任意       |

```bash
git clone https://github.com/gufranco/snes-mapper-python.git
cd snes-mapper-python
python3 mapper/doctor.py
```

このパッケージは標準ライブラリ以外を何もインポートしません。

ドクターはマシンの情報を報告し、プローブ用アドレスをすべてのレイアウトで解決し、自ら組み立てたイメージからヘッダーを読み、マニフェストとコーパスの件数を数え、見つかったカートリッジライブラリを示します。チェックアウト直後にはライブラリがないため、ドクターは実カートリッジに対するチェックがスキップされることを報告します。すべてのチェックに通れば0で、それ以外は1で終了します。バグ報告にはその出力全体を貼り付けてください。

```
  15 checks, nothing to report
```

リリースは[Semantic Versioning](https://semver.org/)に従い、semantic-releaseがコミット履歴から作成します。各リリースにはタグが付けられ、[リリースページ](https://github.com/gufranco/snes-mapper-python/releases)に掲載されます。

## インターフェース

ここでは何かを組み立ててから動かすことはなく、コードを実行することもありません。すべての呼び出しは、アドレス、イメージ、またはレジスタについての問い合わせです。

### アドレス

`resolve(kind, address, fast=False, banks=None, save=False)`は`Resolution`を返します。`kind`は`LOROM`、`HIROM`、`EXHIROM`、`WHOLEBANK`、`SA1`、`SPC7110`のいずれかです。`fast`はヘッダーによる高速バスの要求です。`banks`は64 KBバンク単位のイメージサイズで、`WHOLEBANK`では必須です。`save`は`WHOLEBANK`でバンク`$70`から`$7D`をセーブメモリとしてマップします。指定しない場合、これらのバンクはカートリッジです。`kind`にそれ以外の文字列を渡すと、カートリッジのバンクを`HIROM`と同じ方法で読み、セーブメモリのウィンドウは持ちません。

| 属性      | 意味                                                                                                                                                                                                                                                                                                  |
| :-------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `region`  | `ROM`、`WORK_RAM`、`SAVE_RAM`、`REGISTERS`、`OPEN_BUS`、`COPROCESSOR`のいずれかで、値はそれぞれ`rom`、`work-ram`、`save-ram`、`registers`、`open-bus`、`coprocessor`です。`coprocessor`はカートリッジのチップがデコードするアドレスで、SA-1のレジスタとワークRAM、SPC7110のレジスタとポートバンクです |
| `offset`  | そのアドレスがイメージ内のどこを読むか。リージョンが`rom`でない場合は`None`                                                                                                                                                                                                                           |
| `cycles`  | アクセスにかかるマスタークロック数。`FAST`は6、`SLOW`は8、`XSLOW`は12                                                                                                                                                                                                                                 |
| `address` | 問い合わせたアドレスを24ビットでマスクしたもの                                                                                                                                                                                                                                                        |
| `is_rom`  | `region`が`rom`のときTrue                                                                                                                                                                                                                                                                             |

バンク`$00`から`$3F`と`$80`から`$BF`の`$8000`未満では、Book Iの図2-21-1が記載するとおり、`fast`に関係なく本体が速度を固定します。`$2000`から`$3FFF`と`$4200`から`$5FFF`は6、`$4000`から`$41FF`のコントローラーポートは12、ワークRAMと`$6000`から`$7FFF`は8です。`fast`が効くのは、バンク`$80`から`$BF`の`$8000`以上と、バンク`$C0`から`$FF`だけです。

`work_ram_offset(address)`は、アドレスが131,072個のワークRAMセルのどれに届くかを返し、`resolve`がワークRAMと判定しないアドレスには`None`を返します。バンク`$7E`と`$7F`はセルを順に保持し、すべての低位バンクの下位8 KBはその先頭8 KBに届くため、`$00:1000`、`$20:1000`、`$7E:1000`は同じセル`0x1000`です。図2-21-1はこの2つの領域をRAM 1の8 KBと、バンク`$7E`と`$7F`にあるRAM 2の120 KBとして示しており、合わせるとこの2つのバンクが指す128 KBになります。

### レイアウト

`MODELS`は解決可能な各レイアウト名を`Model`に対応付けます。`layout_named(name)`は名前またはエイリアスに対応する`Model`を返します。大文字と小文字、ハイフン、アンダースコアは無視され、それ以外の名前には`UnknownModelError`を送出します。`Model`は`name`、`aliases`、`header_at`、`summary`を持ち、`model.resolve(address, fast=False, banks=None, save=False)`は自身の名前で`resolve`を呼び出します。

| レイアウト  | エイリアス                           | ヘッダーの位置                                       |
| :---------- | :----------------------------------- | :--------------------------------------------------- |
| `lorom`     | `lo`、`mode20`、`20`                 | `$7FC0`                                              |
| `hirom`     | `hi`、`mode21`、`21`                 | `$FFC0`                                              |
| `exhirom`   | `exhi`、`mode25`、`25`               | `$FFC0`、およびイメージがそこまで届く場合は`$40FFC0` |
| `wholebank` | `whole`、`wholebanks`、`interleaved` | `$7FC0`                                              |
| `sa1`       | `mode23`、`23`                       | `$7FC0`                                              |
| `spc7110`   | なし                                 | `$FFC0`                                              |

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

### ヘッダー

| 呼び出し               | 戻り値                                                                                                  |
| :--------------------- | :------------------------------------------------------------------------------------------------------ |
| `read(rom)`            | 最高スコアの候補位置にある`Header`。2点以上の位置がなければ`NoHeader`を送出します                       |
| `score(rom, at)`       | ひとつの候補位置が獲得する点数で0から4。そこに32バイトが収まらない場合は-1                              |
| `board(found, size)`   | `Header`とイメージサイズに対するレイアウト名。12 MBのイメージで`lorom`と読めるヘッダーは`wholebank`です |
| `has_copier_stub(rom)` | コピー機が先頭に付加する512バイトをイメージが持つときTrue                                               |
| `stub_by_length(size)` | 同じ判定を長さだけで行います                                                                            |
| `Header(at, raw)`      | 32バイトとその取得元オフセットから構築したヘッダー                                                      |

候補位置は`LOROM_HEADER`の`$7FC0`、`HIROM_HEADER`の`$FFC0`、そして`$40FFC0`で、イメージがコピー機のスタブを持つ場合はそれぞれ`COPIER_BYTES`の`$200`だけずれます。各位置は次の条件ごとに1点を獲得します。21バイト中19バイト以上が表示可能なタイトル、補数と整合する0以外のチェックサム、8から13の宣言サイズ、そしてその位置にヘッダーを置くレイアウトを示すマッピングバイトです。

| 属性                                        | 意味                                                                                                                                  |
| :------------------------------------------ | :------------------------------------------------------------------------------------------------------------------------------------ |
| `at`、`shift`                               | ヘッダーが見つかった位置と、コピー機のスタブによるずれの量                                                                            |
| `raw`                                       | 32バイト                                                                                                                              |
| `title`                                     | 21バイトのタイトルから末尾の空白とゼロバイトを除いたもの                                                                              |
| `mapping`、`declared`                       | レイアウトを示すバイトと、その上位ニブルが2または3であるかどうか。そうであるときにこのバイトが信用されます                            |
| `layout`                                    | バイトが信用される場合はバイトから、そうでない場合はオフセットから決まります。`lorom`、`hirom`、`exhirom`、`sa1`、`spc7110`のいずれか |
| `rom_bytes`、`ram_bytes`                    | 宣言されたサイズのバイト数                                                                                                            |
| `checksum`、`complement`、`checksum_agrees` | その組と、合計が`$FFFF`になるかどうか                                                                                                 |
| `fast`、`battery`、`coprocessor`            | 高速バスを要求するか、バッテリーバックアップ付きセーブメモリを持つか、チップを持つか                                                  |
| `chipset`、`country`                        | 残りの宣言バイト                                                                                                                      |

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

マッピングバイト`$30`は、高速ビットが立ったローレイアウトを宣言します。チップセット`$02`はROMとバッテリーバックアップ付きRAMです。サイズバイト`$0A`と`$03`は、1 MBのROMと8 KBのRAMを宣言します。

### イメージ

| 名前                                                             | 内容                                                                                                                                       |
| :--------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------- |
| `bank_count(size)`                                               | そのサイズのイメージに含まれる64 KBバンクの数。割り切れない場合は`NotWholeBanks`を送出します                                               |
| `interleave(logical)`、`deinterleave(built)`                     | 本体が読む順序と、インターリーブされたダンプが格納する順序の間の変換。格納順は、すべての上位半分が先で、その後にすべての下位半分が続きます |
| `snes_to_file(bank, addr, banks)`、`file_to_snes(offset, banks)` | バンクとアドレスの組と、インターリーブされたファイル内の位置との間の変換                                                                   |
| `window_to_file(bank, addr, banks)`                              | `WINDOW_FIRST_BANK`の`$C0`以上のバンクに対する同じ変換                                                                                     |
| `address_to_file(bank, addr, banks)`                             | そのバンクに当てはまる方の変換                                                                                                             |
| `BANK`、`HALF`                                                   | `$10000`と`$8000`                                                                                                                          |
| `WHOLEBANK_BANKS`、`WHOLEBANK_BYTES`                             | 192バンクと12 MB。`WHOLEBANK`が解決する唯一のサイズです                                                                                    |

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

4 MBのインターリーブされたファイルは、バンク`$00`の上位半分をオフセット0に、その下位半分を64ハーフバンク後に格納します。

### 転送

| 名前                                    | 内容                                                                                                                                                         |
| :-------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Engine()`                              | 8本のチャンネル`channels`と、2つの有効化レジスタ`enable`と`enable_indirect`                                                                                  |
| `engine.write(address, value)`          | `ENABLE`の`$420B`、`$420C`、またはチャンネルレジスタへの1バイトの書き込み。それ以外のアドレスは無視されます                                                  |
| `engine.enabled`                        | `ENABLE`が選択しているチャンネル                                                                                                                             |
| `engine.plans()`                        | それらの各チャンネルに対する`Plan`。その他のチャンネルには何も返しません                                                                                     |
| `Plan`                                  | `channel`、`source`、`length`、`step`、`destination`、`to_cpu`、および`addresses()`。`addresses()`はすべての転送元アドレスを順に返し、バンク内で折り返します |
| `Channel(index)`                        | 1本のチャンネル。`index`、16個の`registers`、`write(offset, value)`、`plan()`を持ちます                                                                      |
| `channel.parameters`、`channel.to_cpu`  | レジスタ`$43x0`と、そのビット7。ビット7は転送がプロセッサ方向に行われるときにセットされます                                                                  |
| `channel.step`                          | 1。パラメータのビット4がセットされていれば-1、ビット3がセットされていれば常に0                                                                               |
| `channel.destination`、`channel.source` | `$2100`にレジスタ`$43x1`を加えたもの、および`$43x2`から`$43x4`にある24ビットのアドレス                                                                       |
| `channel.count`、`channel.length`       | `$43x5`と`$43x6`にある16ビットのカウントと、それによって転送されるバイト数。バイト数はカウントの値で、カウントが0のときは65536です                           |
| `channel_of(address)`                   | レジスタアドレスが属するチャンネル。`CHANNEL_BASE`の`$4300`から`$437F`の範囲外では`None`                                                                     |
| `CHANNEL_COUNT`                         | 8                                                                                                                                                            |

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

チャンネル1は`$7E8000`から`$2118`への4バイトの完全な転送を保持していますが、`ENABLE`がそれを選択するまで`plans()`は何も報告しません。

### エラー

| エラー              | 送出される条件                                                 |
| :------------------ | :------------------------------------------------------------- |
| `NoHeader`          | `read`が2点以上の候補位置を見つけられないとき                  |
| `NotWholeBanks`     | イメージサイズが64 KBバンクの整数倍でないとき                  |
| `NeedsBankCount`    | `WHOLEBANK`を`banks`なしで、または192未満の値で解決したとき    |
| `UnknownModelError` | `layout_named`にどのレイアウトにも該当しない名前が渡されたとき |

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

各メッセージには最初の文の後に続きがあります。`NeedsBankCount`はさらに、より小さいイメージがこのマップに載らない理由を述べ、`banks`がない場合はバンク数を数える呼び出しを示します。

### モジュールの内容

`mapper.__version__`はインストールされているバージョンです。レイアウト名`LOROM`、`HIROM`、`EXHIROM`、`WHOLEBANK`、`SA1`、`SPC7110`は、それぞれ文字列`lorom`、`hirom`、`exhirom`、`wholebank`、`sa1`、`spc7110`です。サブモジュール`header`、`layout`、`image`、`transfer`、`models`、`errors`は属性としてアクセスでき、`layout.EXHIROM_BYTES`は8 MBです。

### コマンドラインツール

いずれもリポジトリのルートから実行します。`conformance/`以下のものはすべてモジュールとして実行します。

| コマンド                                                        | 動作                                                                                   | 終了コード                                                                           |
| :-------------------------------------------------------------- | :------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------- |
| `python3 mapper/doctor.py`                                      | マシンとチェックアウトの状態を報告します                                               | 0は問題なし、1はチェック失敗                                                         |
| `python3 mapper/environment.py`                                 | その報告のうちマシンに関する部分だけを出力します                                       | 0は問題なし、1はチェック失敗                                                         |
| `python3 -m conformance.corpus [corpus]`                        | 記録されたすべてのヘッダーの組み合わせを再生します                                     | 0はすべて一致、1は不一致あり、2はコーパスなし                                        |
| `python3 -m conformance.against_cartridges [directory]`         | 存在するすべてのカートリッジを読み、それぞれを対応するケースと照合します               | 0はすべて一致、1は不一致あり、2はカートリッジなし                                    |
| `python3 -m conformance.testcarts [--record out.json]`          | 手元のテストカートリッジをすべてマップし、それぞれを記録された読み取り結果と照合します | 0はすべて一致、1は不一致あり、2はテストカートリッジなしまたは引数の誤り              |
| `python3 -m conformance.census <directory> <out> [limit]`       | ライブラリのヘッダーを集計します                                                       | 0は書き込み完了、1はカートリッジなし、2は引数の誤り                                  |
| `python3 -m conformance.record <directory> [out] [limit]`       | ライブラリからコーパスを再構築します                                                   | 0は書き込み完了、1はカートリッジなし、2は引数の誤り                                  |
| `python3 -m conformance.documents [--check] [--only SUBSTRING]` | マニュアルを取得してダイジェストを検証するか、手元のコピーを検証します                 | 0は検証済み、1は拒否、一致なし、または引数の誤り                                     |
| `python3 -m conformance.quotes`                                 | マニュアル内の引用文をすべて探します                                                   | 0はすべて見つかったかマニュアルがない、1は引用が見つからないか出典の位置が誤っている |
| `python3 -m conformance.speed`                                  | スループットの下限                                                                     | 0は下限以上、1は下限未満                                                             |
| `python3 -m conformance.links`                                  | このREADMEが引用するすべてのアドレスにリクエストを送り、各ステータスをJSONで出力します | 0はすべてのアドレスが存在、1はステータス`404`または`410`で消えたものがある           |
| `python3 -m conformance.package <wheel>`                        | ビルドされたwheelがすべてのモジュールを含み、テストファイルを含まないことを確認します  | 0は問題なし、1は不備があるかwheelがない、2は引数なし                                 |

## このパッケージが防ぐ誤り

### インターリーブされたダンプは本体が読む順序で格納されていない

```python
from mapper import deinterleave, interleave

image = bytes(range(256)) * 1024

print(deinterleave(interleave(image)) == image)
```

```
True
```

一部のダンプは、すべてのバンクの上位半分を先に、すべての下位半分を後に格納します。インターリーブされたイメージに既知のアドレスで書き込んだパッチは、半バンク離れた別のバンクのデータに着地します。

### バンク`$7E`と`$7F`はカートリッジではない

```python
from mapper import LOROM, resolve

print(resolve(LOROM, 0x7E0900).region)
print(resolve(LOROM, 0x001000).region)
```

```
work-ram
work-ram
```

これらはバンク番号の中ほどにあり、ほかのアドレスと同じように読めます。すべてのローバンクの下位8 KBは同じワークRAMのミラーで、それが2行目です。

### 転送レジスタはプロセッサに属する

```python
from mapper import CHANNEL_BASE, ENABLE

print(f"{ENABLE:#06x} {CHANNEL_BASE:#06x}")
```

```
0x420b 0x4300
```

ディスプレイの`$21xx`ウィンドウに仕掛けたフックは、すべてのグラフィックスへの書き込みを捉えますが、転送は1つも捉えません。

### チャンネル番号はニブルである

```python
from mapper import channel_of

print(channel_of(0x4370))
print(channel_of(0x4380))
```

```
7
None
```

`& 7`でマスクすると、`$4380`がウィンドウの外にあることを報告せず、チャンネル0に重ねてしまいます。

### 有効化されていないチャンネルも応答する

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

レジスタは最後に書かれた値を保持し続けるため、8本のチャンネルをすべて調べると、実際には起きなかった転送が報告されます。

## レイアウト

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

| レイアウト  | 形                                                                                                                                                                                      |
| :---------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `lorom`     | 各バンクの上位半分に32 KBのページを1つずつ置き、セーブメモリがバンク`$70`から`$7D`と`$F0`から`$FD`を占めます                                                                            |
| `hirom`     | 各バンクに64 KBのバンク全体を置き、セーブメモリはバンク`$20`から`$3F`と`$A0`から`$BF`の`$6000`から`$7FFF`にあります                                                                     |
| `exhirom`   | `hirom`の4 MBずつの2つの半分を入れ替えたもの                                                                                                                                            |
| `wholebank` | `$C0`未満の各バンクに64 KB全体を置き、インターリーブされた12 MBのイメージから読みます                                                                                                   |
| `sa1`       | 8 Mbitのブロック4つを順に置きます。`$00`から`$3F`と`$80`から`$BF`では各バンクに32 KBのページ、`$C0`からは各バンクに1バンク全体、バックアップRAMは`$40`から`$4F`と`$6000`から`$7FFF`です |
| `spc7110`   | イメージの最初の1メガバイトであるプログラムROMを`$00`から`$0F`、`$80`から`$8F`、`$C0`から`$CF`に置き、その後ろのデータROMを他のすべてのROMバンクに置きます                              |

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

SA-1のマップは、Book IIが本体のプロセッサーから見たものとして記載しているもので、バンクレジスタ`$2220`から`$2223`とバックアップRAMレジスタ`$2224`の初期値におけるものです。バンク`$80`から`$BF`は最初の2ブロックのミラーではなく、3番目と4番目のブロックを持ちます。プログラムがこれらのレジスタに書き込むとマップは動き、`resolve`はそれを追いません。SPC7110のボードを記載したNintendoの文書はないため、そのマップは固定したコミットのaresのボードデータベースとSPC7110のソースから取っており、記録では未検証としています。ゲームがデータバンクを選ぶまで、すべてのデータバンクはプログラムROMの後ろの最初の1メガバイトを読みます。

### 拡張レイアウトは半分を入れ替える

バンク`$80`から`$FF`は`exhirom`イメージの最初の4 MBを持ちます。リセットベクターを含むバンク`$00`から`$7D`は、それより後ろのすべてを持ちます。

```python
from mapper import layout

print(f"{layout.resolve('exhirom', 0x00FFC0).offset:#08x}")
print(f"{layout.resolve('hirom', 0x00FFC0).offset:#08x}")
```

```
0x40ffc0
0x00ffc0
```

このため、拡張カートリッジは4 MBの位置にヘッダーを持ちます。上限は`layout.EXHIROM_BYTES`の8 MBで、その最上部にはバンク`$3E`と`$3F`を通してのみ到達できます。`$7E`と`$7F`はワークRAMだからです。

### 96メガビットと、そこに届くマップ

ホールバンクマップは、ウィンドウより下の領域をカートリッジ以外に一切使いません。バンク`$00`から`$BF`はそれぞれ64 KBを持つので192バンクが収まり、イメージはそのすべてを[`mapper/image.py`](mapper/image.py)が変換する形でインターリーブして保持します。

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

1つ目はバンク`$00`の上位半分で、ローレイアウトが置く場所と同じです。2つ目はバンク`$40`の下位半分です。3つ目は、`$C0`以降のバンクが開くウィンドウを通して届きます。

このマップが受け付ける最小サイズは等式から決まります。ウィンドウは下位半分をバンク`$80`に属する並びから読むため、その最上位バイトは`2 * banks`ハーフバンクの長さのファイルで`191 + banks`ハーフバンクの位置にあります。両者はちょうど192バンクで一致するため、`resolve`はそれより小さいバンク数を拒否します。

`board()`はこのマップをイメージサイズから選び、チップセットバイトからは決して選びません。コプロセッサを取り除いて作られた拡張版は、まだそれを宣言していることが多く、S-DD1を宣言する6メガバイトのカートリッジはこのマップには載りません。

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

## 実際のライブラリの中身

2,781本の市販カートリッジだけから読み取ったものです。改造版、翻訳版、試作版はいずれも編集されたヘッダーを持ちうるため、どれも数えていません。

| 宣言されたレイアウト | カートリッジ |
| :------------------- | -----------: |
| `lorom`              |        2,157 |
| `hirom`              |          572 |
| `sa1`                |           42 |
| `exhirom`            |            6 |
| `spc7110`            |            4 |

1,701本が高速バスを要求し、957本がバッテリーバックアップ付きセーブメモリを持ち、2,780本が補数と整合するチェックサムを持ちます。ヘッダーの位置は、2,200本が`$7FC0`、579本が`$FFC0`、2本が`$40FFC0`です。さらに8ファイルは`read`が受け入れるヘッダーを持たず、拒否として数えています。

### マッピングバイトは常にマッピングバイトとは限らない

範囲内のマッピングバイトは8種類あり、すべて`$2x`か`$3x`です。13本のカートリッジはその範囲外のバイトを持ち、そのうち11本は英大文字です。22文字のタイトルが21バイトのフィールドからあふれ、最後の文字がマッピングバイトを上書きしています。

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

`0x53`はタイトルの最後の文字`S`です。範囲外のバイトは参照されず、レイアウトはヘッダーの位置から決まります。このようなバイトの下位ニブルを読むと、より大きなライブラリの市販カートリッジ51本で、レイアウト、バス速度、またはその両方を誤りました。範囲内のバイトは、オフセットと食い違う場合でも信用されます。遠い方のコピーがイメージの末尾を越える場合、`exhirom`は`hirom`と同じ位置にヘッダーを置くからです。

7,314本のカートリッジ全体で、正しいオフセットで読んだサイズバイトは98.85%のカートリッジで8から13の間に収まり、誤ったオフセットで読んだバイトがその範囲に入るのは3.18%にすぎません。このため`score`はその範囲に1点を与えます。

## コーパスと、それを配布できる理由

ヘッダーは、カートリッジが自らの構成を記述する32バイトです。

| フィールド                                     | その性質                 | 配布         |
| :--------------------------------------------- | :----------------------- | :----------- |
| マッピング、チップセット、ROMとRAMのサイズ、国 | 物理的な物についての事実 | する         |
| ある組み合わせを共有するカートリッジの数       | 測定値                   | する         |
| タイトル                                       | 名前                     | しない       |
| ヘッダー以外のすべて                           | ゲーム本体               | 読み取らない |

事実と機能的要素は著作権の及ぶ範囲外にあります。根拠は[17 U.S.C. 102(b)](https://www.law.cornell.edu/uscode/text/17/102)と*Feist*判決です。[`conformance/census.py`](conformance/census.py)はその32バイトだけを読み、タイトルは記録しません。これはこのリポジトリの作り方の説明であり、法的助言ではありません。

[`conformance/corpus.json`](conformance/corpus.json)は、異なる組み合わせのそれぞれについて、ヘッダーのオフセット、それが生むレイアウト、そのもとで14個のプローブアドレスが解決される先を保持しています。

### 自分のライブラリの全数調査

```bash
python3 -m conformance.census /path/to/roms census.json
```

コーパスの元になったライブラリでは、`2781 cartridges read, 8 refused`と`287 distinct header combinations`を出力します。全数調査はヘッダーのオフセットをキーにしないため、見つかる組み合わせはコーパスより2つ少なくなります。

### 配布しているコーパスの再構築

```bash
python3 -m conformance.record /path/to/roms conformance/corpus.json
```

同じカートリッジを持っていれば、誰でもこのファイルを再構築してバイト単位で比較できます。同一のフィールドを異なるオフセットに持つ2本のカートリッジは2つのケースになります。マッピングバイトが紛れ込んだ文字である場合、オフセットがレイアウトを決めるからです。

### 自分のカートリッジを使う

所有しているコピーを[`cartridges/`](cartridges/)、チェックアウトと同じ階層の`../cartridges`、または`SNES_CARTRIDGE_DIR`が指す場所に置いてください。指定したディレクトリが最優先で、次にチェックアウトと同じ階層のもの、最後にその内部のものが使われます。サブディレクトリもたどり、`.sfc`と`.smc`ファイルを読みます。

各ファイルは読む前に[`cartridges.manifest.json`](cartridges.manifest.json)にある4つのダイジェストすべてと照合されます。決め手は`sha256`で、`crc32`、`md5`、`sha1`も一致する必要があります。マニフェストには2,778本のカートリッジと2本の不良ダンプが記載されています。[`cartridges/README.md`](cartridges/README.md)にはすべてのファイル名とそのダイジェストが一覧になっており、このディレクトリの中身は何もコミットされません。

## 各証拠の価値

| 証拠                                                                                       | 確定できること                                                                     | 確定できないこと                                  |
| :----------------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------- | :------------------------------------------------ |
| Nintendoのマニュアルと、[`conformance/hardware.json`](conformance/hardware.json)にある計算 | 3つのCPUクロック速度とそれぞれが適用されるアドレス、つまり6、8、12クロックという値 | マニュアルに記載のないマスタークロック            |
| Book IIのセクション1、第3章と第4章                                                         | レジスタの初期値におけるSA-1のマップ                                               | プログラムが書き込んだ後のマップ                  |
| 固定したコミットのaresのボードデータベースとSPC7110のソース                                | なし。手がかりであり、未検証として記されています                                   | Nintendoのどの文書も記載していないSPC7110のボード |
| 2,781本のカートリッジから読み取ったヘッダーの組み合わせ                                    | 出荷されたカートリッジにおいてその組み合わせが意味すること                         | どのカートリッジも持たない組み合わせ              |
| 読み取ったすべてのカートリッジのダイジェスト                                               | 読んだファイルが名前どおりのファイルであること                                     | そのリリースが意図したものであるかどうか          |

モデル化していないもの：プロセッサ、つまり1命令が何回アクセスするか。リフレッシュと転送によるストール。そしてアドレスに到達した後に起こるすべてのこと。

## 正しいのか

異なるヘッダーの組み合わせのそれぞれについて、レイアウトと生成されるアドレスを再生します。289通りの組み合わせで、不一致は0件です。コーパスが保持しているのはカートリッジではなく測定値なので、これはどこでも実行できます。

```bash
python3 -m conformance.corpus
```

`289 agreed, 0 did not`を出力し、0で終了します。

ライブラリがある場合、この一括検証はすべてのファイルを読み、各カートリッジをそれを記録したケースと照合します。コーパスの元になったライブラリでは`2781 agreed, 0 did not`を出力します。ライブラリがない場合はその理由を出力して2で終了し、CIはそのスキップに注釈を付けます。

```bash
python3 -m conformance.against_cartridges
```

[`conformance/hardware.json`](conformance/hardware.json)は、NintendoがBook Iの21.1節に記載した3つのCPUクロック速度3.58 MHz、2.68 MHz、1.79 MHzを引用し、それぞれから6、8、12マスタークロックへの計算を示しています。スキャンされたページから読み取った図2-21-1は、1.79 MHzの領域を`$4000`から`$41FF`に置いています。[`conformance/divergences.json`](conformance/divergences.json)には2つの情報源が食い違うすべての箇所が、[OPEN-QUESTIONS.md](OPEN-QUESTIONS.md)にはここでの忠実性が測定ではなく主張であるすべての箇所が、それを確定させる方法とともに記載されています。

## 開発に参加する

| 必要なもの                                                 | 場所                                                                   |
| :--------------------------------------------------------- | :--------------------------------------------------------------------- |
| すべてのゲートと実行順序                                   | [CONTRIBUTING.md](CONTRIBUTING.md)                                     |
| コーディングエージェント向けの同じ内容                     | [AGENTS.md](AGENTS.md)                                                 |
| このリポジトリがファミリーのほかのリポジトリと共有する基準 | [FAMILY.md](FAMILY.md)                                                 |
| バグ報告                                                   | [GitHub Issues](https://github.com/gufranco/snes-mapper-python/issues) |
| セキュリティ報告                                           | [SECURITY.md](SECURITY.md)                                             |

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

各モジュールには`<module>.test.py`という名前のテストファイルが隣にあり、それぞれ単独で実行できます。カバレッジはステートメントとブランチで100%を求める必須のゲートで、[`pyproject.toml`](pyproject.toml)で設定されています。[`conformance/speed.py`](conformance/speed.py)のスループットの下限は毎秒200,000回の`resolve`呼び出しで、カバレッジの段階とは別に実行されます。カートリッジを必要とするテストは[`conformance/on_disk.test.py`](conformance/on_disk.test.py)にあり、これがカバレッジの集計から除外される唯一のファイルです。

## 参考文献

| 文書                                                                     | 発行者                   | 参照日     |   バイト数 | SHA-256                                                            |
| :----------------------------------------------------------------------- | :----------------------- | :--------- | ---------: | :----------------------------------------------------------------- |
| _SNES Development Manual, Book I_、アーカイブされた全文                  | Nintendo of America Inc. | 2026-08-27 |    298,926 | `100beabe8e29d6e02b60b9a0f057a40063a4e33a83478f480ecc2e8696e77972` |
| _SNES Development Manual, Book I_、テキストレイヤー付きのスキャンページ  | Nintendo of America Inc. | 2026-10-19 | 21,022,582 | `f1405241000046abba7849376d2ec53cf85f1ad2e9950d69a7c2cf1f3ff6b791` |
| _SNES Development Manual, Book II_、アーカイブされた全文                 | Nintendo of America Inc. | 2026-10-19 |    463,516 | `546f8e38caf6cb19c8aa9d5a1fef090d8cfc4a0a13b54c3b56d704975ab8398a` |
| _SNES Development Manual, Book II_、テキストレイヤー付きのスキャンページ | Nintendo of America Inc. | 2026-10-19 | 29,575,127 | `05197923d9b73b63845fc5c2d609e753ec634dc1e4b403ce7a57326e1259c3ed` |

4つとも再配布できず、このリポジトリには含まれていません。`python3 -m conformance.documents`は4つすべてをarchive.orgのアイテム https://archive.org/details/SNESDevManual から、gitが無視する`docs/`にダウンロードし、ダイジェストが異なるファイルは拒否します。`--check`はすでにあるコピーを検証します。[`conformance/documents.json`](conformance/documents.json)はダイジェストとアドレスを保持しています。この文書から引用した文は、それぞれの出典の表とページとともに[`conformance/hardware.json`](conformance/hardware.json)にあります。

[`conformance/corpus.json`](conformance/corpus.json)の元になった2,781件のヘッダーは、作者が所有する市販カートリッジのライブラリから取得したものです。そこからコミットされているのは[`cartridges.manifest.json`](cartridges.manifest.json)のダイジェストだけです。

## 引用

[CITATION.cff](CITATION.cff)は、パッケージのバージョンを記録するスクリプトによってリリースごとに更新されます。

## ライセンス

MIT。[LICENSE](LICENSE)を参照してください。
