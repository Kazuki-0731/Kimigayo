# BusyBoxコマンド性能ベンチマーク

## 概要

`benchmark-busybox.sh`は、Kimigayo OSのBusyBoxコマンドの実行時間を測定し、Alpine Linuxと比較するベンチマークスクリプトです。日常的に使用する頻度の高いコマンドについて、Alpine と差があるかどうかを確かめます。

**結論を先に書くと、差は出ていません**（→「実測値」節）。測っている時間のほとんどは
`docker run` のコンテナ生成です（→「この指標の限界」節）。

## 測定項目

### 対象コマンド（8種類）

| コマンド | 測定内容 | 実際に実行するコマンド |
|---------|---------|--------|
| **ls** | ディレクトリ一覧表示 | `ls -la /bin` |
| **grep** | 再帰的テキスト検索 | `grep -r 'bin' /etc` |
| **find** | ファイル検索 | `find /usr -type f` |
| **awk** | テキスト処理 | `ls -la /bin \| awk '{print $1}'` |
| **sort** | データソート | `ls -la /bin \| sort` |
| **cat** | ファイル読み込み | `cat /etc/passwd` |
| **wc** | 行数カウント | `ls -laR /bin \| wc -l` |
| **head** | 先頭行抽出 | `ls -laR /bin \| head -n 10` |

1 回ごとに `docker run --rm <image> ...` でコンテナを作って実行します。

### 測定方法

- **反復回数**: 各コマンド10回実行して統計処理
- **測定単位**: ミリ秒（ms）
- **統計値**: 平均値、中央値
- **比較対象**: Alpine Linux（既定は `alpine:latest`）
- **比（`ratio_median`）**: Alpine の**中央値** / Kimigayo の**中央値**（1.00 より大きいと Kimigayo が速い）。
  画面の `Ratio(med)` 列はこれ
- **平均の比（`ratio_avg`）**: Alpine の平均 / Kimigayo の平均。JSON にだけ残す
- **`speedup`**: JSON 上の `ratio_median` の別名（既存の読み手のために残している）

> **2026-10-13 まで、スクリプトの「Speedup」は平均の比だった。** 一方
> [README.md](../../README.md) の「0.97〜1.01x」（v3.0.2 当時）は**中央値の比**で、同じ名前で
> 別の値を指していた（`docker run` の外れ値に平均が引っ張られる）。いまは中央値の比を
> 主にしている。**それ以前の記録（下の 2026-10-10・2026-10-11）の「Speedup」は平均の比。**

## 使用方法

### 基本実行

```bash
# Makefileから実行（推奨。対象は kimigayo-os:$(VARIANT)-$(ARCH)、既定は standard-x86_64）
make benchmark-busybox

# スクリプトを直接実行（対象の既定は ishinokazuki/kimigayo-os:latest-standard）
bash scripts/benchmark-busybox.sh

# 環境変数でカスタマイズ（スクリプトを直接呼ぶ）
IMAGE_NAME=ishinokazuki/kimigayo-os:3.1.0-standard \
ALPINE_IMAGE=alpine:3.24 \
BENCHMARK_ITERATIONS=20 \
bash scripts/benchmark-busybox.sh
```

> **`IMAGE_NAME=... make benchmark-busybox` は使えない。** Makefile が
> `IMAGE_NAME` の後ろに `:$(VARIANT)-$(ARCH)` を付け足すので、
> `kimigayo-os:minimal-x86_64:standard-x86_64` のような無効な名前になる。
> make 経由でバリアントを変えるときは `VARIANT=` / `ARCH=` を使い、
> 任意のイメージを測るときはスクリプトを直接呼ぶ。

### 環境変数

| 変数名 | デフォルト値 | 説明 |
|--------|------------|------|
| `IMAGE_NAME` | スクリプト直接: `ishinokazuki/kimigayo-os:latest-standard` / make 経由: `kimigayo-os:$(VARIANT)-$(ARCH)` | テスト対象イメージ |
| `ALPINE_IMAGE` | `alpine:latest` | 比較対象イメージ |
| `BENCHMARK_ITERATIONS` | `10` | 各測定の反復回数 |

### 出力ファイル

ベンチマーク結果は`benchmark-results/`ディレクトリに保存されます（毎回上書き）：

```
benchmark-results/
├── busybox.json    # JSON形式（機械可読）
└── busybox.txt     # テキスト形式（人間可読）
```

## 結果の読み方

### コンソール出力例

`benchmark-results/busybox.json`（2026-10-11、v3.0.1、arm64）の値を、いまの表示形式で
並べたもの（`Ratio(med)` は中央値から計算し直した値）:

```
=== Benchmark Summary ===

Command                 Kimigayo Avg      Alpine Avg        K Median        A Median   Ratio(med)
-------------------- --------------- --------------- --------------- --------------- ------------
ls                              879             884             884             880        1.00x
grep                            952             934             909             921        1.01x
find                            861             850             862             849        0.98x
awk                             871             883             868             867        1.00x
sort                            828             845             825             850        1.03x
cat                             847             854             833             856        1.03x
wc                              891             884             891             885        0.99x
head                            880             885             873             871        1.00x

Ratio(med) = Alpine median / Kimigayo median (> 1.00 means Kimigayo is faster)
```

### JSON出力例

いまの形式（値は上と同じ v3.0.1 の測定。当時のファイルには `ratio_median`・`ratio_avg`・
`ratio_definition` が無く、`speedup` は平均の比だった）:

```json
{
  "timestamp": "2026-10-11T17:55:17Z",
  "kimigayo_image": "ishinokazuki/kimigayo-os:3.0.1",
  "alpine_image": "alpine:3.24",
  "iterations": 10,
  "ratio_definition": "ratio_median = alpine_median_ms / kimigayo_median_ms; ratio_avg = ...",
  "results": {
    "ls": {
      "kimigayo_avg_ms": 879,
      "kimigayo_median_ms": 884,
      "alpine_avg_ms": 884,
      "alpine_median_ms": 880,
      "ratio_median": 1.00,
      "ratio_avg": 1.01,
      "speedup": 1.00,
      "kimigayo_samples": [830, 910, 890, ...]
    },
    ...
  }
}
```

## 実測値

### v3.1.0（2026-10-15）

**測定条件:** `ishinokazuki/kimigayo-os:3.1.0-standard-arm64` vs `alpine:3.24`、
macOS / Apple Silicon、arm64 ネイティブ、各10回。単位は ms。

| コマンド | Kimigayo 中央値 | Alpine 中央値 | 中央値の比 |
|---|---|---|---|
| ls | 586 | 570 | 0.97x |
| grep | 580 | 578 | 1.00x |
| find | 595 | 605 | 1.02x |
| awk | 584 | 587 | 1.01x |
| sort | 592 | 586 | 0.99x |
| cat | 583 | 583 | 1.00x |
| wc | 595 | 579 | 0.97x |
| head | 585 | 586 | 1.00x |

**中央値の比は 0.97〜1.02x で、有意差なし。** 1 コマンドあたり約 0.58 秒のほとんどは
コンテナ生成で、これまでの回と同じ結論。

### v3.0.2（2026-10-12）

v3.0.2 の公開イメージ（Standard、arm64 ネイティブ）で **中央値の比 0.97〜1.01x**
（当時の [README.md](../../README.md) の「パフォーマンス実績」節に記録）。
**このときの生データ（`busybox.json`）はリポジトリに残っていない**ので、
コマンドごとの値はここに書けない。結論は下の 2 回と同じで、有意差なし。

### v3.0.1（2026-10-11）

**測定条件:** `ishinokazuki/kimigayo-os:3.0.1` vs `alpine:3.24`、arm64 ネイティブ、各10回。
値は上の「コンソール出力例」のとおりで、中央値の比は **0.98〜1.03x**
（当時のスクリプトが出した Speedup ＝平均の比は 0.98〜1.02x）。
生データは `benchmark-results/busybox.json`。

### Kimigayo OS vs Alpine Linux（2026-10-10）

**測定条件:** `kimigayo-os:standard-arm64` vs `alpine:latest`、
arm64 ネイティブ、各10回。

2回測った結果を並べる。**同じコマンドが走るたびに前後する。**

| コマンド | 1回目 Speedup（平均の比） | 2回目 Speedup（平均の比） |
|---------|-------------|-------------|
| ls | 1.01x | 1.01x |
| grep | 1.00x | **1.12x** |
| find | 0.96x | 1.00x |
| awk | 0.97x | 1.03x |
| sort | 1.00x | **0.90x** |
| cat | 0.98x | 1.01x |
| wc | 1.01x | 1.03x |
| head | 0.98x | 1.02x |

1回目の中央値（ms）: ls 762/793・grep 759/771・find 758/737・awk 595/578・
sort 570/575・cat 578/570・wc 685/687・head 705/703（Kimigayo / Alpine）。

**有意差なし。** `sort` は 1.00x → 0.90x、`grep` は 1.00x → 1.12x と
走るたびに ±10% 動くので、**どちらが速いとは言えません。**
計測のばらつきが、あるかもしれない差より大きい状態です。

> **v1.0.0 の記録（~1.11〜1.16x、「目標 > 1.10x を達成」）は撤回する。**
> 2026-10-10 に測り直すと、どのコマンドも Alpine と差が無かった。
> 当時の測定条件（ホスト・アーキテクチャ・イメージ）が記録されて
> いないため、何が違ったのかを検証できない。
> 以前この文書にあった「grep が 12% 高速」「全体で 10-16% 高速」なども同じ値から
> 作ったものなので削除した。

### この指標の限界

**1コマンドあたり 570〜950ms という値のほとんどは `docker run` の
コンテナ生成時間**で、コマンド自身の処理時間ではない。
起動時間ベンチマークで分かったことと同じで、
78MB の Ubuntu でも同じオーダーになる。

- **「> 1.10x」という目標自体が、この測り方では意味を持たない。**
  差を見たいなら、コンテナを1つ起動したまま中で多数回繰り返す必要がある
- musl libc やビルドフラグの効果を主張する根拠にはならない

## 技術的考察

### BusyBox のビルドフラグ

`scripts/build-busybox.sh` が渡しているのは次のとおり（x86_64 の例）:

```bash
CFLAGS="-Os -fstack-protector-strong -fPIE -D_FORTIFY_SOURCE=2 ..."
LDFLAGS="-Wl,-z,relro -Wl,-z,now -Wl,-z,noexecstack"
# 最終リンク: 既定（BUSYBOX_LINK=dynamic）は -pie。BUSYBOX_LINK=static なら -static -static-pie
```

- **-Os**: サイズ最適化
- v3.0.2 から BusyBox は**動的リンク**（`/lib/libc.so` を OpenRC と共有）。
  静的リンクは `BUSYBOX_LINK=static` を渡したときだけ
- `-ffunction-sections` / `--gc-sections` は渡していない

これらが実行時間に効いているかは、上の測り方では分からない。

## トラブルシューティング

### ベンチマークが遅い

**原因**: Docker Desktopのリソース不足

**対策**:
```bash
# Docker Desktopの設定を確認
# Preferences → Resources → Advanced
# CPUs: 4以上推奨
# Memory: 4GB以上推奨
```

### Alpineイメージのプルに失敗

**原因**: Docker Hubへの接続エラー

**対策**:
```bash
# 手動でプル
docker pull alpine:latest

# または特定バージョンを指定
ALPINE_IMAGE=alpine:3.24 make benchmark-busybox
```

## ベストプラクティス

### 1. 複数回実行して統計を取る

```bash
# デフォルト10回 → 20回に増やす
BENCHMARK_ITERATIONS=20 make benchmark-busybox
```

### 2. 公開イメージで測定

```bash
# 公開イメージを使用（スクリプトを直接呼ぶ）
IMAGE_NAME=ishinokazuki/kimigayo-os:3.1.0-standard \
bash scripts/benchmark-busybox.sh
```

### 3. 異なるバリアント間での比較

```bash
# minimal vs standard vs extended（ローカルでビルドした kimigayo-os:<variant>-x86_64）
make benchmark-busybox VARIANT=minimal
make benchmark-busybox VARIANT=standard
make benchmark-busybox VARIANT=extended

# benchmark-results/busybox.json は毎回上書きされるので、都度コピーして比較する
```

## 関連ドキュメント

<!-- startup.md / memory.md / size.md / comparison.md は未作成。
     起動時間とメモリは 2026-10-10 に計測方法を直して実測済み
     （→ README.md「パフォーマンス実績」節）。 -->

- [ライフサイクルベンチマーク](./lifecycle.md)

## 参考情報

### 測定精度について

- **時間精度**: ミリ秒単位（1ms = 0.001秒）
- **統計手法**: 平均値と中央値を併用（比は中央値から計算。平均の比も JSON に残す）
- **ばらつき**: 同じ条件で走らせ直しても ±10% 程度動く（→「実測値」節）

### Docker操作のオーバーヘッド

```
実測値 = 実際の処理時間 + Docker CLIオーバーヘッド + コンテナ起動時間
```

- コンテナ起動時間: 約 0.6 秒（v3.0.2 の `docker run --rm <image> /bin/true`、
  arm64 ネイティブ。→ [README.md](../../README.md)）
- コマンド実行時間: 本ベンチマークでは上と切り分けられない

### BusyBox設定の検証

```bash
# Kimigayo OSのBusyBox設定確認
docker run --rm ishinokazuki/kimigayo-os:3.1.0-standard busybox --help

# 利用可能なコマンド一覧
docker run --rm ishinokazuki/kimigayo-os:3.1.0-standard busybox --list

# バージョン確認
docker run --rm ishinokazuki/kimigayo-os:3.1.0-standard busybox | head -1
```

## 更新履歴

- **2026-01-01 (v1.0.0)**: 初版リリース（Issue #30対応）
  - 8コマンドの測定を実装
  - Alpine Linuxとの比較機能
  - JSON/テキスト形式の出力
  - Makefile統合
  - Speedup計算機能
- **2026-10-10**: 実測で測り直し。v1.0.0 の数値を撤回し、
  この指標が何を測っているか（Docker のオーバーヘッド）を明記
- **2026-10-11 (v3.0.1)**: v3.0.1 で測り直し（0.98〜1.02x）
- **2026-10-12 (v3.0.2)**: README の v3.0.2 の値を記録。撤回済みの値から作った記述、
  実在しないビルドフラグ・CI の例を削除
