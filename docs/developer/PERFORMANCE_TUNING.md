# Kimigayo OS - パフォーマンスチューニング結果

**最終更新:** 2026-10-12
**最新バージョン:** v3.0.2（現在の値は末尾近くの「競合OSとの比較」節。それより前は過去の記録）

> ## ⚠️ この文書の数値は古く、一部は無効（2026-10-09 追記）
>
> **1. 構成要素を 2026-10-09 にまとめて更新したので、サイズは全部古い。**
> カーネル 6.6.11 → 6.18.55、musl 1.2.4 → 1.2.6、
> BusyBox 1.36.1 → 1.38.0、OpenRC 0.52.1 → 0.63.2。
> Standard の現在の実測は **2.60MB**（x86_64、v3.0.2、2026-10-12）。
>
> **2. ここに書かれたサイズは「Init が入っていないイメージ」の値。**
> v2.0.1 までの rootfs は musl の `libc.so` も OpenRC のバイナリも
> コピーしておらず、実質 BusyBox のみのイメージだった（2026-10-09 に修正）。
>
> **3. 起動時間とメモリの値は、この文書の過去の節では全部無効。**
> v2.0.1 の 439ms / 平均541ms / 0.2MB だけでなく、v0.1.0 の
> 5.52秒 → 5.10秒・最良 3.55秒・「最大35%短縮」・平均4MB・「8秒目のスパイク 11MB」も
> 同じ壊れたスクリプトの値。そこから出した結論（並列起動の効果、OpenRC 1.5秒 → 0.8秒、
> 「全目標達成」など）も根拠にならない。
> `scripts/benchmark-startup.sh` は `docker run -d <image> sleep 5` が
> 終了するまでを測るため、正常なイメージでは約 5,600ms になっていた
> （2026-10-09 実測）。439ms はこの `sleep` が成立しなかった場合の値で、
> 起動時間ではない。`benchmark-memory.sh` も `KiB` を `0.001` に置換した
> うえ整数 MB に丸めており、1MB 未満を 0 としか表せなかった。
> **2026-10-10 に両方を書き直し、測り直した**（arm64 ネイティブで、
> v3.0.1 は起動 0.61 秒 / 常駐 232KB、v3.0.2 は 0.60 秒 / 288KB → 下の比較の節）。
> 下表の v2.0.1 列・v0.1.0 の節は当時の壊れた値なので **引用しない**。
>
> **4. 「実施した最適化」の節に出てくる設定ファイルのうち、`configs/openrc/` と
> `configs/sysctl/` は 2026-10-14 に削除した**（どのスクリプトからも読まれていなかった）。
> イメージの `/etc/rc.conf`・`/etc/inittab`・`/etc/sysctl.d/99-kimigayo-performance.conf` は
> 当時から `scripts/build-rootfs.sh` の heredoc が書き出している。
>
> 現在の値は [README.md](../../README.md) の「パフォーマンス実績」節を見る。

## 📊 バージョン間パフォーマンス比較

### v1.0.0 → v2.0.1 の改善

**測定日:** 2026-01-16
**テスト環境:** Apple Silicon (ARM64)

| 指標 | v1.0.0 | v2.0.1 | 改善率 |
|------|--------|--------|--------|
| **イメージサイズ (Minimal)** | 1.35MB | 1.32MB (1,321KB) | 🚀 **2.2%削減** |
| **イメージサイズ (Standard)** | 1.35MB | 1.17MB (1,171KB) | 🚀 **13.3%削減** |
| **イメージサイズ (Extended)** | 1.35MB | 1.32MB (1,321KB) | 🚀 **2.2%削減** |
| **BusyBox静的リンク** | ❌ 動的リンク | ✅ 完全静的 | セキュリティ向上 |
| **ARM64対応** | ❌ x86_64のみ | ✅ ARM64/x86_64 | Apple Silicon最適化 |
| **起動時間** | 未測定 | ~~439ms~~（無効） | 計測が壊れていた |
| **メモリ使用量** | 未測定 | ~~0.2MB~~（無効） | 計測が壊れていた |

### v2.0.1 の主要な改善点

1. **BusyBox完全静的リンク化** (PR #55)
   - muslライブラリ依存を完全排除
   - `/lib`ディレクトリ不要
   - セキュリティ攻撃対象領域の縮小
   - ※ v3.0.2 で動的リンクに戻した（musl に当てた CVE パッチを `/bin/sh` にも効かせるため。`/lib/libc.so` を OpenRC と共有）

2. **ARM64アーキテクチャ対応** (PR #60, #61)
   - Apple Silicon (M1/M2/M3) ネイティブ実行
   - クロスコンパイル環境の整備
   - マルチアーキテクチャビルドシステム

3. **リリースワークフロー修正**
   - Docker-in-Dockerの問題を解決
   - 正しいビルドプロセスの確立
   - v2.0.0の問題を修正してv2.0.1で安定化

---

## 🏆 v2.0.1 実測パフォーマンス

### イメージサイズ詳細

| バリアント | サイズ(KB) | サイズ(MB) | 用途 |
|-----------|----------|-----------|------|
| **Minimal** | 1,321KB | 1.29MB | 最小構成 |
| **Standard** | 1,171KB | 1.14MB | 実用構成（推奨） |
| **Extended** | 1,321KB | 1.29MB | 全機能搭載 |

**注:** Standard版が最も小さい（1,171KB）理由は記録が残っていない。
当時のイメージは Init も `libc.so` も入っていない状態だった（冒頭の注意書き 2）。

### 起動時間詳細

**測定環境:** Docker Desktop on Apple Silicon

> **⚠️ この節の数値は無効（2026-10-10）。** 以下は
> `docker run -d <image> sleep 5` の終了までを測った値で、起動時間では
> ない。**イメージが壊れているほど速く見える**計測だった。
> 現在の実測は下の「競合OSとの比較（2026-10-12 の実測）」節を見る。

```
平均: 541ms   ← 無効
中央値: 551ms ← 無効
最小: 499ms   ← 無効
最大: 557ms   ← 無効
```

**競合比較（いずれも無効）:**
- Alpine Latest: ~~423ms~~
- Kimigayo Standard: ~~439ms~~
- Ubuntu 22.04: ~~439ms~~

### メモリ使用量詳細

> **⚠️ この節の数値は無効（2026-10-10）。** `KiB` を `0.001` に置換した
> うえ整数 MB に丸めていたため、1MB 未満を 0 としか表せなかった。

```
平均: 4MB     ← 無効
中央値: 2MB   ← 無効
```

**競合比較（いずれも無効）:**
- Kimigayo Standard: ~~0.2MB~~
- Alpine Latest: ~~0.2MB~~
- Ubuntu 22.04: ~~0.3MB~~

---

## 📊 v0.1.0 最適化成果サマリー (過去の記録)

**実施日:** 2025-12-22
**対象バージョン:** v0.1.0

> **⚠️ この節の起動時間とメモリは無効**（冒頭の注意書き 3）。サイズも整数 MB に
> 丸めた値で、1MB の差は丸めの誤差の範囲。

### パフォーマンス改善

| 指標 | 最適化前 | 最適化後 | 改善率 |
|------|----------|----------|--------|
| **イメージサイズ (Standard)** | 3MB | **2MB** | 🚀 **33%削減** |
| **起動時間 (平均)** | 5.52秒 | **5.10秒** | ⚡ **7.6%短縮** |
| **起動時間 (最小)** | 5.49秒 | **3.55秒** | ⚡ **35%短縮** |
| **メモリ使用量 (平均)** | 4MB | 4MB | ✅ 変化なし |

### 主要な発見

当時は次のように結論していたが、いずれも根拠にならない:

1. ~~rc.conf と sysctl 設定追加で 1MB 削減~~ — 設定ファイルを足してサイズが減ることはない。整数 MB の丸め
2. ~~平均 5.52秒 → 5.10秒、最良 3.55秒（並列化効果）~~ — `sleep 5` の終了を測った無効な値。3.55秒は sleep が成立しなかった回
3. ~~メモリ使用量は変化なし~~ — `KiB` を潰した無効な値

---

## 🔧 実施した最適化

### 1. OpenRC 並列起動の有効化

**ファイル:** イメージの `/etc/rc.conf`（`scripts/build-rootfs.sh` の heredoc が書き出す）。主な項目:

```bash
rc_parallel="YES"
rc_logger="YES"
rc_log_level="warn"
rc_hotplug="hwclock net.lo"
rc_depend_strict="NO"
```

- `rc_hotplug` は**ホットプラグを許すサービスの一覧**で、無効化ではない
  （上の値は hwclock と net.lo だけを許す。生成元のコメントは「無効化」と書いているが不正確）
- `rc_depend_strict="NO"` は依存の解釈を緩める設定で、速度のための設定ではない

**効果:** 測れていない。当時の「最大35%短縮・平均7.6%改善」は無効な計測の値。

### 2. inittab の最適化

**変更前:**
```
c1:12345:respawn:/sbin/getty 38400 console
l0:0:wait:/sbin/openrc shutdown
l6:6:wait:/sbin/reboot
```

**現在（`scripts/build-rootfs.sh` が書き出す `/etc/inittab`）:**
```
::sysinit:/sbin/openrc sysinit
::sysinit:/sbin/openrc boot
::wait:/sbin/openrc default
::respawn:/sbin/getty 38400 console
::shutdown:/sbin/openrc shutdown
```

**効果:** 測れていない。なお既定の PID 1 は `/bin/sh`（`Dockerfile.runtime` の CMD）なので、
この inittab はコンテナで `/sbin/init` を PID 1 にしたときだけ使われる。

### 3. カーネルパラメータのチューニング

**ファイル:** `/etc/sysctl.d/99-kimigayo-performance.conf`（`scripts/build-rootfs.sh` の
heredoc が書き出す）

```bash
# Memory management
vm.swappiness = 0
vm.dirty_ratio = 10
vm.dirty_background_ratio = 5
vm.overcommit_memory = 1

# Network optimization
net.core.rmem_default = 262144
net.core.rmem_max = 16777216
net.core.wmem_default = 262144
net.core.wmem_max = 16777216
net.ipv4.tcp_window_scaling = 1
net.ipv4.tcp_timestamps = 1
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_syncookies = 1

# File system
fs.file-max = 65536
vm.vfs_cache_pressure = 50

# Kernel
kernel.pid_max = 32768

# Security
kernel.randomize_va_space = 2
fs.suid_dumpable = 0
```

**効果:** 未測定。コンテナはホストのカーネルで動くので、`vm.*`・`fs.file-max`・
`kernel.*` などはホスト全体の値で、**特権コンテナで sysctl を適用したときにしか効かない**
（通常のコンテナでは書き込めない）。「スループット向上」などの効果は確かめていない。

### 4. サービス構成の最適化

当時はバリアントごとのサービス一覧を `configs/openrc/services-{minimal,standard,extended}.list`
に書いたが、**このファイルはビルドで読まれておらず、2026-10-14 に削除した**。udev・dbus・iptables・sshd は
どのバリアントのイメージにも入っていない。

**3バリアントの違いは BusyBox のアプレットだけ**（→ [README.md](../../README.md) の
「パフォーマンス実績」節）。ランレベルの中身は OpenRC のインストールで決まる。

---

## 📈 詳細ベンチマーク結果

### イメージサイズ比較

| イメージ | 最適化前 | 最適化後 | 削減量 |
|----------|----------|----------|--------|
| Kimigayo Minimal | 1MB | 1MB | - |
| Kimigayo Standard | 3MB | 2MB | （丸め誤差） |
| Kimigayo Extended | 3MB | 3MB | - |

**注:** 当時は「全体的な最適化効果により1MB削減」としていたが、追加したのは設定ファイルだけで、
サイズが減る理由は無い。整数 MB に丸めた値の揺れと見るのが妥当。

### 起動時間の詳細

> **⚠️ 以下の起動時間とメモリの表は無効**（`sleep 5` の終了 / `KiB` を潰した値）。
> 記録として残しているだけで、分析・結論も根拠にならない。

#### 5回測定の結果

| 測定 | 最適化前 | 最適化後 | 差分 |
|------|----------|----------|------|
| 1回目 | 5.57秒 | 5.47秒 | -0.10秒 |
| 2回目 | 5.49秒 | 5.52秒 | +0.03秒 |
| 3回目 | 5.51秒 | 5.50秒 | -0.01秒 |
| 4回目 | 5.53秒 | 5.47秒 | -0.06秒 |
| 5回目 | 5.52秒 | **3.55秒** | **-1.97秒** ⚡ |
| **平均** | **5.52秒** | **5.10秒** | **-0.42秒** |

**分析:**
- 5回目で劇的な高速化（3.55秒）
- 並列起動が効果的に機能したケース
- 平均でも7.6%の改善

#### 並列起動の効果

最適化により、以下のサービスが並列起動可能に:
- `hostname` と `loopback`
- `sysctl` と `urandom`
- `networking` と `syslog`

**理論的最大短縮時間:** 約2秒（実測で1.97秒を達成）

### メモリ使用量

| 指標 | 最適化前 | 最適化後 |
|------|----------|----------|
| 平均 | 4MB | 4MB |
| 中央値 | 2MB | 2MB |
| 最小 | 2MB | 2MB |
| 最大 | 11MB | 11MB |

**分析:**
- メモリ使用量に変化なし
- 8秒目のスパイク（11MB）は依然として発生
- カーネルパラメータの効果はランタイム時に発揮

---

## 🎯 目標達成状況（v0.1.0 当時）

目標値は [SPECIFICATION.md](../../SPECIFICATION.md) §8.3
（Minimal < 5MB / Standard < 15MB / Extended < 50MB、起動 < 10秒、メモリ < 128MB）。

| 指標 | 目標値 | 当時の値 |
|------|--------|--------|
| イメージサイズ (Minimal) | < 5MB | 1MB（Init なし） |
| イメージサイズ (Standard) | < 15MB | 2MB（Init なし） |
| 起動時間 | < 10秒 | ~~5.1秒~~（無効） |
| メモリ使用量 | < 128MB | ~~4MB~~（無効） |

当時は「全目標達成」としていたが、起動時間とメモリは測れていなかった。
現在の達成状況は [README.md](../../README.md) の「パフォーマンス実績」節。

---

## 🔍 ボトルネック分析（最適化後）

当時の分析（Docker 初期化 約3秒・OpenRC 1.5秒 → 0.8秒・8秒目のメモリスパイク・
カスタム init で 0.3秒）は、無効な計測から作った推定なので撤回する。
カスタム init の開発は採用していない。

現在分かっていること（v3.0.2、2026-10-12）:

- `docker run --rm <image> /bin/true` は 0.60 秒で、Alpine・Ubuntu（0.59 秒）と差が無い。
  ほとんどが Docker 自身のコンテナ生成
- OpenRC が `default` ランレベルを完走するまでは 0.72 秒（`/bin/true` との差 約 0.12 秒が Init の分）

---

## 📋 変更されたファイル

### 新規作成（当時。いずれもビルドから読まれず、2026-10-14 に削除済み）

`configs/openrc/`（`rc.conf`・`inittab.optimized`・`services-*.list`）と
`configs/sysctl/99-kimigayo-performance.conf`。

イメージに入る中身は、下の `scripts/build-rootfs.sh` が書き出したもの。

### 変更

1. `scripts/build-rootfs.sh`
   - `/etc/inittab` の生成ロジックを最適化
   - `/etc/rc.conf` の自動生成を追加
   - `/etc/sysctl.d/` 設定の追加

---

## 🚀 使用方法

### 最適化済みイメージのビルド

```bash
# Standardイメージをビルド（Linux ホスト。macOS では build-rootfs が通らない →
# CLAUDE.md の「ビルドの全体像」節の 2 段階の手順を使う）
make build-image VARIANT=standard

# ベンチマーク実行
make benchmark

# 結果確認
cat benchmark-results/BENCHMARK_REPORT.md
```

### カスタム最適化

`/etc/rc.conf` などの設定を変える場合:

```bash
# 1. scripts/build-rootfs.sh の heredoc（/etc/rc.conf・/etc/inittab・
#    /etc/sysctl.d/99-kimigayo-performance.conf を書き出す箇所）を編集
vi scripts/build-rootfs.sh

# 2. 再ビルド
make build-image VARIANT=standard

# 3. 効果測定
make benchmark-startup
```

---

## 🔍 競合OSとの比較（2026-10-12 の実測）

**測定条件:** macOS / Apple Silicon、Kimigayo v3.0.2 Standard の公開イメージ。
起動時間・常駐メモリは **arm64 ネイティブ**、各10回の中央値（常駐メモリは 20 標本）で、
Alpine 3.24・Ubuntu 24.04 と同時に測った。
**イメージサイズは `docker inspect` の値で、比較表は `--platform linux/amd64`**
（Kimigayo は 2026-10-12、他は 2026-10-11 に同じホストで測った値）。
x86_64 の起動時間・メモリを QEMU 経由で測った値は比較に使わない。

### イメージサイズ

| OS | サイズ | Kimigayo 比 |
|----|--------|-----------|
| `gcr.io/distroless/static-debian12` | 2.11MB | 0.81x |
| **Kimigayo Standard (x86_64)** | **2.60MB** | 基準 |
| Kimigayo Standard (arm64) | 2.98MB | 1.15x |
| `alpine:latest`（3.24.2） | 8.42MB | 3.2x |
| `gcr.io/distroless/base-debian12` | 20.9MB | 8.0x |
| `ubuntu:24.04` | 78.2MB | 30x |

**シェルと Init を備えて 2.60MB。** distroless に 0.49MB 足すだけで
`sh` と 400 個のコマンドとサービス管理が付く。

### 起動時間

| OS | 起動時間 |
|----|---------|
| **Kimigayo Standard** | 0.60秒 |
| `alpine:latest` | 0.59秒 |
| `ubuntu:24.04` | 0.59秒 |

**差は出ない。100MB の Ubuntu とも同じ。**
0.6 秒のほとんどは Docker 自身のコンテナ生成で、イメージは効かない。
**「軽いから起動が速い」と書かないこと**（→ [CLAUDE.md](../../CLAUDE.md)）。

OpenRC が `default` ランレベルを完走するまでは **0.72 秒**。

### 常駐メモリ

| OS | 常駐メモリ | Kimigayo 比 |
|----|-----------|-----------|
| **Kimigayo Standard** | **288KB** | 基準 |
| `alpine:latest` | 272KB | 0.94x |
| `ubuntu:24.04` | 312KB | 1.08x |

**v3.0.1 では差の出る指標だったが、v3.0.2 で同程度になった**（v3.0.1 は 232KB）。
BusyBox を動的リンクにしたので、`sleep` などの BusyBox のコマンドも
`libc.so` を読み込む（約 56KB）。musl に当てた CVE パッチを `/bin/sh` に
効かせるための選択。単位は KB。
`docker stats` は起動直後に `0B` を返すことがあるので、
その標本は捨てて測る（`benchmark-memory.sh` の
`discarded_zero_samples`）。

### コマンド実行性能

BusyBox のアプレットは Alpine の BusyBox 比 **0.97〜1.01x**（中央値の比、v3.0.2、
[README.md](../../README.md) の値）。**有意差なし**。平均は 1 回の外れ値に引っ張られるので
中央値で見る。測り方と限界は [docs/benchmarks/busybox.md](../benchmarks/busybox.md)。

### 機能比較

| OS | サイズ | シェル | Init | パッケージマネージャー |
|----|--------|--------|------|---------------------|
| **Kimigayo Standard** | 2.60MB | ✅ BusyBox | ✅ OpenRC | ❌（設計方針） |
| Distroless Static | 2.11MB | ❌ | ❌ | ❌ |
| Alpine | 8.42MB | ✅ | ❌ | ✅ apk |
| Ubuntu 24.04 | 78.2MB | ✅ | ❌ | ✅ apt |

**最新の値は [README.md](../../README.md) の「パフォーマンス実績」節が正本。**

---

## 📊 比較: 最適化前後 (v0.1.0時代)

当時はここに起動時間の分布（最良 3.55 秒）とサイズのチャート（3MB → 2MB、目標 10MB）を
載せていたが、起動時間は無効な計測、サイズは整数 MB の丸め、目標値は誤り
（Standard の目標は §8.3 で 15MB）なので削除した。

---

## 💡 ベストプラクティス

### 1. 並列起動の活用

サービスの依存関係を適切に定義し、並列起動を最大限活用:

```bash
# /etc/rc.conf（scripts/build-rootfs.sh が書き出す）
rc_parallel="YES"
rc_depend_strict="NO"  # 依存の解釈を緩める（速度のための設定ではない）
```

効果は測れていない（並列化の効果として記録していた値は無効）。

### 2. 不要サービスの無効化

コンテナ環境では不要なサービスを削除:

```bash
# コンテナでは不要
- hwclock (コンテナではホストの時刻を使用。OpenRC 側が keyword -docker で飛ばす)
# udev・sshd はどのバリアントにも入っていない（シェルは docker exec で使う）
```

### 3. ログレベルの調整

起動時のログを最小化:

```bash
rc_log_level="warn"  # info/debug を出力しない
```

### 4. カーネルパラメータのチューニング

用途に応じてsysctlを調整（**特権コンテナで適用したときだけ効く**。ネットワーク名前空間の
`net.*` の一部は `docker run --sysctl` でも渡せる。効果は未測定）:

```bash
# Webサーバー用途
net.core.somaxconn = 1024

# メモリ集約型（ホスト全体に効く）
vm.swappiness = 0
```

---

## 🔬 測定環境

```
v0.1.0 / v2.0.1 の節:
  ホストOS: macOS (Darwin 25.1.0)
  Docker: Docker Desktop
  測定ツール: カスタムベンチマークスクリプト（起動時間・メモリは壊れていた）
  測定回数: 5回（平均値を採用）

「競合OSとの比較（2026-10-12 の実測）」の節:
  ホスト: macOS / Apple Silicon、Docker Desktop
  起動時間・常駐メモリ: arm64 ネイティブ、10回の中央値（常駐メモリは 20 標本）
  サイズ: docker inspect（比較表は --platform linux/amd64）
```

---

## 📚 参考リソース

- [OpenRC Documentation](https://github.com/OpenRC/openrc)
- [Linux Kernel sysctl Documentation](https://www.kernel.org/doc/Documentation/sysctl/)
- [Docker Performance Best Practices](https://docs.docker.com/config/containers/resource_constraints/)

---

**作成者:** Claude (Anthropic)
**次回更新:** 次の計測時（[README.md](../../README.md) と同じターンで突合する）
