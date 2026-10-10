# Kimigayo OS

<div align="center">

**軽量・高速・セキュアなオペレーティングシステム**

[![Release](https://github.com/Kazuki-0731/Kimigayo/actions/workflows/release.yml/badge.svg)](https://github.com/Kazuki-0731/Kimigayo/actions/workflows/release.yml)
[![License: GPL-2.0](https://img.shields.io/badge/License-GPL%202.0-blue.svg)](https://www.gnu.org/licenses/gpl-2.0)
[![Docker Hub](https://img.shields.io/badge/Docker%20Hub-ishinokazuki%2Fkimigayo--os-blue?logo=docker)](https://hub.docker.com/r/ishinokazuki/kimigayo-os)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

[English](#english) | [日本語](#japanese)

</div>

---

## <a name="japanese"></a>🇯🇵 日本語

### 概要

Kimigayo OS は、Google の distroless と Alpine Linux の両方の設計思想をハイブリッド的に組み合わせた軽量・高速・セキュアなコンテナ向けオペレーティングシステムです。パッケージマネージャーを意図的に排除し、不変インフラを徹底することで、最小限のリソースで動作し、コンテナ環境やマイクロサービスアーキテクチャで高いパフォーマンスとセキュリティを実現します。

#### Docker Hub
- https://hub.docker.com/r/ishinokazuki/kimigayo-os

### ✨ 主な特徴

- 🪶 **軽量**: Standard で **2.78MB**（同時に実測した Alpine 8.42MB の約 1/3、
  Ubuntu 24.04 78.2MB の約 1/23）
- 🔒 **セキュアバイデフォルト**: パッケージマネージャー排除による最小攻撃面、包括的なセキュリティ強化
- 🧩 **モジュラー設計**: 必要な機能のみを選択可能な3つのバリアント（Minimal/Standard/Extended）
- 📦 **musl + BusyBox + OpenRC のみ**: BusyBox は static-pie。OpenRC は
  musl と自身の `librc` / `libeinfo` だけに依存し、libcap は静的リンク済みなので
  イメージ内に第三者の共有ライブラリを持たない
- 🌐 **マルチアーキテクチャ**: ARM64/x86_64完全対応（Apple Silicon M1/M2/M3最適化済み）

### 🎯 パフォーマンス実績

| 指標 | 実測値 | 目標値 | 達成状況 |
|------|-------|--------|---------|
| イメージサイズ (Minimal) | **2.65MB** / arm64 **3.02MB** | < 5MB | ✅ **目標の53%** / 60% |
| イメージサイズ (Standard) | **2.78MB** / arm64 **3.16MB** | < 15MB | ✅ **目標の19%** / 21% |
| イメージサイズ (Extended) | **2.81MB** / arm64 **3.20MB** | < 50MB | ✅ **目標の6%** / 6% |
| 起動時間 | **0.62秒** | < 10秒 | ✅ **目標の6%** |
| メモリ使用量 | **232KB** | < 128MB | ✅ **目標の0.2%** |
| BusyBoxコマンド性能 | Alpine比 **0.96〜1.01x** | Alpine同等 | ✅ **誤差範囲内** |

目標値は [SPECIFICATION.md](SPECIFICATION.md) §8.3 の定義
（Minimal 5MB / Standard 15MB / Extended 50MB）。
**実際には 3 バリアントとも、いちばん厳しい Minimal の目標 5MB を下回っている。**

2026-10-10 実測。サイズは 6 イメージすべて、起動時間・メモリ・コマンド性能は
arm64 ネイティブの Standard。6 バリアントすべてが
`scripts/verify-image.sh` の 27 項目を通過している。

> **起動時間の 0.62 秒は「Kimigayo が速い」という意味ではない。**
> 同じ方法で測ると Alpine も Ubuntu も 0.61 秒で、**イメージによる差は
> 出ない**（→「競合OS比較」節）。この 0.6 秒のほとんどは Docker 自身の
> コンテナ生成で、イメージの中身はほとんど効かない。
> 差が出るのはメモリの方（Kimigayo 232KB / Alpine 280KB / Ubuntu 316KB）。

<details>
<summary><b>6 バリアントの内訳と、サイズの中身の説明</b></summary>

**測定条件**: 2026-10-10 / ホストは macOS（Apple Silicon, arm64）/
Alpine 3.24 ベースのビルド環境 /
カーネル 6.18.55・musl 1.2.6・BusyBox 1.38.0・OpenRC 0.63.2。

| 何を | どう測ったか |
| --- | --- |
| サイズ | `docker images` の報告値。x86_64 は `--platform linux/amd64`（QEMU エミュレーション）|
| 起動時間 | `docker run --rm <image> /bin/true` の実時間、10 回の中央値。arm64 ネイティブ |
| メモリ | `sleep` で常駐させたコンテナの `docker stats` の値、10 回の中央値。arm64 ネイティブ |
| コマンド性能 | `ls`・`grep`・`find`・`awk`・`sort`・`cat`・`wc`・`head` の 8 つを Alpine と同条件で実行（`scripts/benchmark-busybox.sh`）|

**OpenRC が default ランレベルを完走するまでは 0.77 秒**
（`docker run --rm <image> /sbin/openrc default`、arm64、10 回の中央値）。
`/bin/true` の 0.62 秒との差 0.15 秒が Init の分。

| バリアント | BusyBox アプレット | BusyBox 本体 | tarball | イメージ |
| --- | --- | --- | --- | --- |
| Minimal (x86_64) | 370 | 1,067KB | 1.4MB | **2.65MB** |
| Standard (x86_64) | 403 | 1,202KB | 1.4MB | **2.78MB** |
| Extended (x86_64) | 413 | 1,231KB | 1.5MB | **2.81MB** |
| Minimal (arm64) | 370 | 1,144KB | 1.5MB | **3.02MB** |
| Standard (arm64) | 403 | 1,292KB | 1.6MB | **3.16MB** |
| Extended (arm64) | 413 | 1,324KB | 1.6MB | **3.20MB** |

**3バリアントの差は BusyBox のアプレット数だけで、x86_64 では 164KB しかない。**
イメージの大半は musl の `libc.so`・BusyBox 本体・
OpenRC（バイナリ9個 + 共有ライブラリ2本 + ヘルパ）で、どのバリアントにも入る。

**arm64 が x86_64 より 0.37-0.39MB 大きいのは BusyBox 本体の差**
（aarch64 は固定長命令なので同じコードでもコード量が増える。
v3.0.0 で ASLR のため static-PIE 化とスタックプロテクタを有効にした分も含む）。

> **v2.0.1（2026-01-16）では Standard 1.17MB だった。** 増えた主因は
> BusyBox 1.38.0 本体が単体で 1.17MB あること、および
> **v2.0.1 までは musl の `libc.so` と OpenRC のバイナリがイメージに
> 入っていなかった**こと（2026-10-09 に修正）。つまり 1.17MB は
> 「Init システムが入っていない状態」の数字で、現在の 2.78MB と
> 同じものを測った値ではない。
>
> **起動時間とメモリの旧値（439ms / 0.2MB）は破棄した。計測が壊れていた。**
> `scripts/benchmark-startup.sh` は `docker run -d <image> sleep 5` の
> 終了までを測っており、正常なイメージほど必ず約 5,600ms になっていた
> （439ms はこの `sleep` が成立しなかった＝コンテナが即死したときの値で、
> **イメージが壊れているほど速く見える**計測だった）。
> `scripts/benchmark-memory.sh` は `KiB` を `0.001` に置換したうえ
> 結果を整数 MB に丸めており、**1MB 未満を 0 としか表せなかった**。
> 2026-10-10 に両方を書き直し、測り直したのが上の値。

</details>

### 🏗️ アーキテクチャ

```
┌─────────────────────────────────────────┐
│         ユーザーアプリケーション          │
├─────────────────────────────────────────┤
│    コアユーティリティ (BusyBox)          │
├─────────────────────────────────────────┤
│    Initシステム (OpenRC)                 │
├─────────────────────────────────────────┤
│    Cライブラリ (musl libc)               │
├─────────────────────────────────────────┤
│    Linuxカーネル (強化版)                │
├─────────────────────────────────────────┤
│    ハードウェア                          │
└─────────────────────────────────────────┘
```

### 🔧 主要コンポーネント

| コンポーネント | バージョン | 役割 |
|---|---|---|
| **Linux カーネル** | 6.18.55 (LTS) | セキュリティ強化（ASLR, DEP, PIE 等）。EOL 2028-12 |
| **musl libc** | 1.2.6 | C ライブラリ（軽量・高速・セキュア） |
| **BusyBox** | 1.38.0 | コアユーティリティ（単一バイナリで多数の Unix コマンド） |
| **OpenRC** | 0.63.2 | Init システム（systemd より軽量でシンプル） |
| Alpine Linux | 3.24 | ビルド環境のベース（成果物には含まれない） |

バージョンの定義は [versions.mk](versions.mk) が唯一の場所。
現在の値は `make print-versions` で確認できる。

> **注**: カーネルは Docker イメージには含まれない（コンテナはホストの
> カーネルで動く）。カーネルをビルドするのはベアメタル／QEMU 検証のため。

### 🎯 設計思想: Distroless + Alpine のハイブリッドアプローチ

Kimigayo OS は、**Google の distroless** と **Alpine Linux** の両方の設計思想を組み合わせたハイブリッドアプローチを採用しています：

#### distroless からの継承

**パッケージマネージャーを意図的に排除**することで、以下を実現：

- ✅ **最小攻撃面**: パッケージインストール機能がないため、実行時の脆弱性リスクを大幅に削減
- ✅ **超軽量**: 1-3MBの極小イメージサイズ
- ✅ **不変インフラ**: コンテナ時代の「Build once, run anywhere」思想に完全準拠
- ✅ **予測可能性**: ランタイムでの変更が不可能なため、動作が完全に予測可能

#### Alpine Linux からの継承

- ✅ **musl libc**: 軽量で高速なCライブラリ（glibcの1/10のサイズ）
- ✅ **BusyBox**: 基本的なUnixコマンドとシェルを提供（デバッグ可能）
- ✅ **OpenRC**: シンプルで軽量なInitシステム
- ✅ **セキュリティ強化**: コンパイル時・実行時の包括的な保護（PIE, ASLR, Stack Protector等）

この組み合わせにより、**distroless のセキュリティ** と **Alpine の実用性** を両立し、コンテナ環境に最適化されたOSを実現しています。

**推奨される使用パターン:**

```dockerfile
# マルチステージビルドで必要なものを全てビルド時に準備
FROM alpine:3.24 AS builder
RUN apk add --no-cache python3 py3-pip
COPY requirements.txt .
RUN pip install -r requirements.txt

# Kimigayo OSで最小ランタイム環境を構築
FROM ishinokazuki/kimigayo-os:latest
COPY --from=builder /usr/lib/python3.11 /usr/lib/python3.11
COPY app.py .
CMD ["python3", "app.py"]
```

このアプローチにより、**開発の柔軟性**と**本番環境のセキュリティ**を両立します。

### 🚀 クイックスタート

#### Docker Hubから使用する（最も簡単）

**Docker Hub**: https://hub.docker.com/r/ishinokazuki/kimigayo-os

```bash
# Standardバリアント（推奨）
docker pull ishinokazuki/kimigayo-os:latest
docker run -it ishinokazuki/kimigayo-os:latest

# Minimalバリアント（最小サイズ）
docker pull ishinokazuki/kimigayo-os:latest-minimal
docker run -it ishinokazuki/kimigayo-os:latest-minimal
```

詳細は [Docker使用ガイド](docs/user/DOCKER_USAGE.md) を参照してください。

#### ソースからビルドする

##### 前提条件

- Docker & Docker Compose
- Git
- 最低 2GB RAM（推奨 4GB）

##### ビルド手順

**推奨方法（リアルタイム出力）：**

```bash
# リポジトリをクローン
git clone https://github.com/Kazuki-0731/Kimigayo.git
cd Kimigayo

# Docker環境を構築
make docker-build

# Dockerビルド環境に入る
make shell

# コンテナ内でビルド実行（リアルタイム出力で確認できる）
make build

# テスト実行（コンテナ内）
make test
```

**簡単コマンド（ホストOSから）：**

```bash
# ホストOSから直接ビルド（ログは完了後に表示）
make build

# ホストOSから直接テスト実行
make test
```

#### よく使うコマンド

**ホストOSから実行：**

```bash
# ヘルプ表示
make help

# Dockerビルド環境にログイン
make shell

# ビルド（簡単だがログは完了後）
make build

# クリーンアップ
make clean

# すべてクリーンアップ（コンテナ+volume）
make clean-all

# ビルドログを確認（最新100行）
make log-kernel
make log-musl
make log-openrc
```

**コンテナ内で実行（リアルタイム出力）：**

```bash
# まずコンテナに入る
make shell

# ビルド（リアルタイムで出力確認可能）
make build

# クリーンアップ
make clean

# テスト実行
make test
```

#### ビルド成果物

`make build` を実行すると、以下の場所にビルド成果物が生成されます：

##### 1. **rootfs（ルートファイルシステム）**

OSの実体となるファイルシステム構造が生成されます。

```bash
build/rootfs/
├── bin/          # 実行可能ファイル (sh, busybox, etc.)
├── etc/          # 設定ファイル
├── lib/          # 共有ライブラリ
├── sbin/         # システム管理コマンド
├── usr/          # ユーザープログラム
└── var/          # 可変データ
```

**確認方法:**
```bash
ls -la build/rootfs/
```

##### 2. **tarballイメージ**

配布用のtar.gzアーカイブファイルが生成されます。

```bash
output/
├── kimigayo-minimal-0.1.0-x86_64.tar.gz      # Minimal版 (約400KB)
├── kimigayo-standard-latest-x86_64.tar.gz    # Standard版 (約1.3MB)
├── kimigayo-minimal-0.1.0-x86_64.sha256      # SHA256チェックサム
└── kimigayo-minimal-0.1.0-x86_64.sig         # Ed25519署名
```

**使用方法:**
```bash
# tarballからDockerイメージを作成
docker import output/kimigayo-standard-latest-x86_64.tar.gz kimigayo:test

# 起動
docker run -it kimigayo:test /bin/sh
```

##### 3. **Dockerイメージ**

完全なCI/CDビルド (`make ci-build-local`) を実行するとDockerイメージが生成されます。

```bash
# 完全ビルド（rootfs + tarball + Dockerイメージ）
make ci-build-local

# 全バリアントビルド
make ci-build-all
```

**生成されるイメージ:**
```bash
# イメージ一覧表示
docker images | grep kimigayo

# 主要イメージ
kimigayo-os:standard-x86_64    # Standard版 (2.78MB / 2026-10-10 実測)
kimigayo-os:minimal-x86_64     # Minimal版 (2.65MB)
kimigayo-os:extended-x86_64    # Extended版 (2.81MB)
```

**使用方法:**
```bash
# ローカルビルドイメージを起動
docker run -it kimigayo-os:standard-x86_64 /bin/sh
```

##### ビルド成果物の関係

```
make build
    ↓
build/rootfs/ (ファイルシステム)
    ↓
make package-rootfs
    ↓
output/*.tar.gz (配布用アーカイブ)
    ↓
make build-image
    ↓
Dockerイメージ (コンテナ実行用)
```

#### 詳細なビルドオプション

Dockerビルド環境内で実行することで、リアルタイムなビルド出力が確認できます：

```bash
# Dockerビルド環境に入る
make shell

# コンテナ内で特定のアーキテクチャでビルド
make build ARCH=x86_64

# コンテナ内で詳細ログ付きでビルド
make build V=1

# コンテナ内でプロパティテストのみ実行
pytest tests/property/ -v

# コンテナ内で単体テストのみ実行
pytest tests/unit/ -v
```

**ダウンロードキャッシュについて：**

ローカルビルドでは、ダウンロードしたソースコード（カーネル、musl、BusyBox、OpenRC）がDocker Volumeにキャッシュされます。2回目以降のビルドは大幅に高速化されます。

```bash
# ホストOSから実行
make clean-cache  # キャッシュをクリア
make clean-all    # すべてクリア
```

**ビルドログの確認：**

Dockerビルド環境内でビルドを実行すると、リアルタイムでビルド出力を確認できます：

```bash
# Dockerビルド環境に入る
make shell

# コンテナ内でビルドログをリアルタイム確認
tail -f /build/kimigayo/build/logs/kernel-build.log   # カーネルビルドログ
tail -f /build/kimigayo/build/logs/musl-build.log     # musl libcビルドログ
tail -f /build/kimigayo/build/logs/openrc-build.log   # OpenRCビルドログ

# コンテナ内で過去のログを確認
tail -n 100 /build/kimigayo/build/logs/kernel-build.log
cat /build/kimigayo/build/logs/musl-build.log
```

**バックグラウンドビルド（tmux使用）：**

カーネルビルドなど時間のかかるビルドをバックグラウンドで実行し、完了時に通知を受け取れます：

```bash
# Dockerビルド環境に入る
make shell

# tmuxセッションを開始
tmux new -s build

# ビルド実行（完了したら通知メッセージを表示）
make build && echo "✅ Build Success" || echo "❌ Build Failed"

# Ctrl+B を押してから D を押してデタッチ（バックグラウンド実行）
# ビルドはバックグラウンドで継続される

# 後で状態を確認する場合
tmux attach -t build

# tmuxセッション一覧を確認
tmux ls

# セッションを終了する場合
tmux kill-session -t build
```

**トラブルシューティング：**

ビルドが失敗する場合や、途中で止まる場合は以下を試してください：

```bash
# Dockerビルド環境に入る
make shell

# コンテナ内でカーネルソースツリーのクリーニング
# ビルドスクリプトが自動で実行しますが、手動でも可能
cd /build/kimigayo/build/kernel-src/linux-$(make -s -C /build/kimigayo print-kernel)
make mrproper

# コンテナから出て完全クリーンビルド（すべてリセット）
exit
make clean-all
make docker-build
make shell  # 再度コンテナに入る
make build  # コンテナ内でビルド
```

**注意:** カーネルビルド中に "The source tree is not clean" エラーが出る場合、ビルドスクリプトが自動的に`make mrproper`を実行してクリーニングします。

### 📦 イメージバリエーション

| イメージタイプ | サイズ | 用途 | Docker Hubタグ |
| -------------- | ------ | ---- | -------------- |
| **Minimal** | **2.65MB**（370 アプレット） | コンテナ、最小限の環境 | `ishinokazuki/kimigayo-os:latest-minimal` |
| **Standard** | **2.78MB**（403 アプレット） | 一般的なサーバー環境（推奨） | `ishinokazuki/kimigayo-os:latest` |
| **Extended** | **2.81MB**（413 アプレット） | 開発環境、豊富なツール | `ishinokazuki/kimigayo-os:latest-extended` |

いずれも x86_64 / 2026-10-10 実測。arm64 は Minimal 3.02MB /
Standard 3.16MB / Extended 3.20MB（→「パフォーマンス実績」節）。

> 上のタグはいずれも **v3.0.0 "Himawari"（2026-10-10 公開）**を指す。
> `latest` 系はマルチアーキで、`linux/amd64` と `linux/arm64` の
> どちらを引いても同じ版が来る。版を固定したいときは
> `3.0.0-standard` のように版番号つきのタグを使う。

**比較**（2026-10-10 に同じホスト・`--platform linux/amd64` で
`docker images` の値を実測。Kimigayo Standard = 2.78MB）:

| イメージ | サイズ | Kimigayo 比 |
| --- | --- | --- |
| `gcr.io/distroless/static-debian12` | 2.11MB | 0.6倍（シェルも Init も無い） |
| `alpine:latest`（3.24.2） | 8.42MB | 2.5倍 |
| `ubuntu:24.04` | 78.2MB | 23倍 |

### 🔐 セキュリティ機能

#### コンパイル時

- PIE (Position Independent Executables)
- Stack-smashing protection
- FORTIFY_SOURCE
- RELRO (Relocation Read-Only)

#### ランタイム

- ASLR (Address Space Layout Randomization)
- DEP (Data Execution Prevention)
- Seccomp-BPF
- Namespace isolation

#### パッケージ署名検証

Kimigayo OS は、パッケージの真正性と完全性を保証するために、二重の署名検証方式を採用しています。

**Ed25519 署名検証（推奨）**

- 🚀 **高速**: RSA より署名生成・検証が高速
- 💾 **軽量**: 署名 64 バイト、公開鍵 32 バイト
- 🔒 **高セキュリティ**: 128 ビットセキュリティレベル
- 🐳 **コンテナ最適**: 最小限のリソースで動作
- ⚡ **決定論的**: ランダム性不要で実装が簡潔

**レガシーサポート**

- GPG 署名検証（既存パッケージとの互換性）

**追加のセキュリティ層**

- SHA-256 ハッシュ検証（改ざん検出）
- セキュリティアップデートの優先配信

### 🎯 ターゲット環境

- **コンテナ環境**: Docker, Kubernetes, Podman

### 🤝 コントリビューション

Kimigayo OS はオープンソースプロジェクトです。バグ報告、機能リクエスト、プルリクエストを歓迎します！

- [貢献ガイド](CONTRIBUTING.md)
- [コミットメッセージガイド](docs/developer/COMMIT_GUIDE.md)
- [開発ガイド](DEVELOPMENT.md)
- [行動規範](CODE_OF_CONDUCT.md)

#### コントリビューションの種類

- 🐛 バグ修正
- ✨ 新機能の追加
- 📝 ドキュメントの改善
- 🌐 翻訳（他言語への対応）
- 🧪 テストの追加
- 🔒 セキュリティ監査

### 📄 ライセンス

Kimigayo OS は Alpine Linux と同様、各コンポーネントが個別のライセンスを持ちます：

| コンポーネント             | ライセンス   |
| -------------------------- | ------------ |
| Linux カーネル             | GPL-2.0      |
| musl libc                  | MIT          |
| BusyBox                    | GPL-2.0      |
| OpenRC                     | BSD-2-Clause |
| ビルドシステム             | MIT          |

詳細は [LICENSE](LICENSE) を参照してください。

### 🌟 競合OS比較

**2026-10-10 に同じホスト（macOS / Apple Silicon）で実測。**
サイズは x86_64（`--platform linux/amd64`、QEMU）と arm64 の両方、
**起動時間とメモリは arm64 ネイティブ**（QEMU を挟むと時間の比較に
ならないため）。測り方は「パフォーマンス実績」節の折りたたみを参照。

| OS | サイズ (x86_64 / arm64) | 起動時間 | メモリ | シェル | パッケージマネージャー | Init |
|----|-------|---------|-------|-------|---------------------|------|
| **Kimigayo Minimal** | **2.65** / **3.02MB** | 0.63秒 | **232KB** | ✅ BusyBox | ❌ | ✅ OpenRC |
| **Kimigayo Standard** | **2.78** / **3.16MB** | 0.62秒 | **232KB** | ✅ BusyBox | ❌ | ✅ OpenRC |
| **Kimigayo Extended** | **2.81** / **3.20MB** | 0.60秒 | 240KB | ✅ BusyBox | ❌ | ✅ OpenRC |
| `gcr.io/distroless/static-debian12` | 2.11 / 2.11MB | — | — | ❌ | ❌ | ❌ |
| `alpine:latest`（3.24.2） | 8.42 / 8.66MB | 0.61秒 | 280KB | ✅ ash | ✅ apk | ❌ |
| `ubuntu:24.04` | 78.2 / 101MB | 0.61秒 | 316KB | ✅ bash | ✅ apt | ❌ |

> **起動時間に差は出ていない**（0.60〜0.63秒）。測っている時間のほとんどは
> Docker のコンテナ生成で、イメージの中身はほとんど効かない。
> **101MB の Ubuntu でも同じ**になるので、「軽いから起動が速い」とは
> 言えない。差が出るのは常駐メモリの方で、Kimigayo は Ubuntu の約 73%。
>
> distroless は実行ファイルを1つも持たないため、この方法では起動時間も
> メモリも測れない（`/bin/true` すら無い）。これは欠陥ではなく設計。

#### vs Alpine Linux
- ✅ **約3倍軽量**: 2.78MB vs 8.42MB（x86_64。arm64 でも 3.16 vs 8.66MB）
- ✅ **常駐メモリが少ない**: 232KB vs 280KB（arm64）
- ✅ **パッケージマネージャーなし**: セキュリティ優先の設計（Alpine は apk を含む）
- ✅ **Init を同梱**: OpenRC 0.63.2（Alpine のイメージには Init が入っていない）
- ✅ **不変インフラ**: ビルド時に全て決定、実行時の変更を排除

#### vs distroless
- ✅ **デバッグ可能**: シェルとUnixコマンドを含む（distroless はシェルなし）
- ✅ **Init がある**: サービスを起動・監視できる
- ⚠️ **サイズ**: Distroless Static（2.11MB）より大きいが、機能が豊富

#### 独自の強み
- 🏆 **シェルと Init を備えて 2.78MB**
- 🚀 **Apple Silicon最適化**: ARM64ネイティブ対応（M1/M2/M3）
- 🔒 **セキュリティとデバッグの両立**: 不変インフラ + シェルアクセス
- 🇯🇵 **充実した日本語ドキュメント**: 日本発のOSS

### 📚 ドキュメント

#### ユーザー向け

- [Docker使用ガイド](docs/user/DOCKER_USAGE.md) - Dockerイメージの使い方、ユースケース別サンプル
- [インストールガイド](docs/user/INSTALLATION.md) - Docker、Kubernetes、Podman でのインストール方法
- [クイックスタートガイド](docs/user/QUICKSTART.md) - 基本的な操作と使い方
- [システム設定ガイド](docs/user/CONFIGURATION.md) - ネットワーク、サービス、セキュリティの設定

#### 開発者向け

- [ビルドガイド](docs/developer/BUILD_GUIDE.md) - ビルド手順とカスタマイズ
- [カスタムビルドガイド](docs/developer/CUSTOM_BUILD.md) - カスタムイメージの作成方法
- [CI/CDガイド](docs/developer/CICD_GUIDE.md) - GitHub Actionsパイプラインの詳細
- [パフォーマンス分析レポート](docs/developer/PERFORMANCE_ANALYSIS.md) - ベンチマーク結果と最適化ロードマップ
- [パフォーマンスチューニング結果](docs/developer/PERFORMANCE_TUNING.md) - 実施した最適化と成果
- [アーキテクチャドキュメント](docs/developer/ARCHITECTURE.md) - システム設計と内部構造
- [API リファレンス](docs/developer/API_REFERENCE.md) - パッケージマネージャ、Init、カーネル API
- [開発ガイド](DEVELOPMENT.md) - 開発環境セットアップ
- [貢献ガイド](CONTRIBUTING.md) - コントリビューション方法
- [コミットメッセージガイド](docs/developer/COMMIT_GUIDE.md) - コミット規約とCHANGELOG生成
- [仕様書](SPECIFICATION.md) - プロジェクト仕様
- [アーキテクチャ](docs/developer/ARCHITECTURE.md) - 詳細設計
- [リリースチェックリスト](docs/RELEASE_CHECKLIST.md) - Docker Hub公開状況と最終チェック
- [v1.0.0リリース計画](docs/V1_RELEASE_PLAN.md) - 正式版リリースに向けたロードマップ

#### GitHub Actions ワークフロー

プロジェクトでは以下の自動化ワークフローが設定されています：

| ワークフロー | トリガー | 目的 | 処理内容 |
|------------|---------|------|---------|
| **ci.yml** | PR、main/develop push | 継続的インテグレーション | • ShellCheck<br>• **全variant × 全arch**ビルド（6パターン）<br>• セキュリティスキャン（Trivy）<br>• Discord通知 |
| **release.yml** | タグpush (v*.*.*) | リリース成果物生成 | • 全variant × 全archビルド<br>• Docker Hubへpush（マルチアーチマニフェスト作成）<br>• **前回タグからのPRリスト自動生成**<br>• GitHub Release作成<br>• Discord通知 |
| **build-workflow.yml** | 再利用可能ワークフロー | ビルド処理の共通化 | • rootfsビルド<br>• 統合テスト<br>• Docker imageビルド・push<br>• Trivyセキュリティスキャン |
| **manual-build.yml** | 手動実行 | 検証用ビルド | • variant/arch選択可能<br>• アーティファクトアップロード |
| **security.yml** | 日次 02:00 UTC | セキュリティチェック | • バージョンチェック（日次）<br>• Trivyスキャン（日次）<br>• イメージスキャン（週次・日曜） |
| **base-image-update.yml** | 週次（月曜 03:00 UTC） | コンポーネント更新チェック | • musl/BusyBox バージョンチェック<br>• 更新があればPR自動作成 |
| **dependency-review.yml** | PR時 | 依存関係レビュー | • 依存関係の変更を検証 |

**CI/CD改善点（v1.0.0）:**
- ✅ **全フレーバー×全アーキテクチャのテスト**: minimal/standard/extended × x86_64/arm64の6パターンを自動テスト
- ✅ **Docker Buildx標準準拠**: タグ命名規則を統一（`{version}-{variant}-{arch}`形式）
- ✅ **リリースノート自動生成**: 前回タグからのPRリストを自動抽出
- ✅ **Discord通知**: CI/CD成功/失敗時の通知機能
- ✅ **再利用可能ワークフロー**: build-workflow.ymlでビルド処理を共通化

**注意**: これらのワークフローは自動的に実行されます。GitHub Actions の使用量にご注意ください。

#### セキュリティ

- [セキュリティポリシー](docs/security/SECURITY_POLICY.md) - セキュリティ方針と脆弱性報告
- [セキュリティガイド](docs/security/SECURITY_GUIDE.md) - セキュリティ機能と運用ガイド
- [脆弱性報告手順](docs/security/VULNERABILITY_REPORTING.md) - 責任ある開示プロセス
- [セキュリティ強化ガイド](docs/security/HARDENING_GUIDE.md) - システム強化設定（3 段階）
- [セキュリティ監査ガイドライン](docs/security/SECURITY_AUDIT.md) - 監査プロセスと手順
- [ペネトレーションテストガイド](docs/security/PENETRATION_TEST.md) - 侵入テスト実施方法

#### リリース情報

- [リリースノート](RELEASE_NOTES.md) - バージョン履歴と変更点

### 💬 コミュニティ

- **GitHub Issues**: バグ報告、機能リクエスト
- **GitHub Discussions**: 質問、アイデア共有
- **Wiki**: 詳細なドキュメント（作成予定）

### 🙏 謝辞

Kimigayo OS は以下のプロジェクトにインスパイアされ、技術的な基盤を提供していただいています：

- [Google Distroless](https://github.com/GoogleContainerTools/distroless) - 不変インフラとセキュリティ優先の設計思想
- [Alpine Linux](https://alpinelinux.org/) - 軽量性とセキュリティのベストプラクティス
- [musl libc](https://musl.libc.org/) - 軽量・高速・セキュアな C ライブラリ
- [BusyBox](https://busybox.net/) - 最小限の Unix ユーティリティ
- [OpenRC](https://github.com/OpenRC/openrc) - シンプルで軽量な Init システム

---

## <a name="english"></a>🇬🇧 English

### Overview

Kimigayo OS is a lightweight, fast, and secure container-focused operating system that combines the design philosophies of both Google's distroless and Alpine Linux in a hybrid approach. By intentionally excluding package managers and enforcing immutable infrastructure, it operates with minimal resources while delivering high performance and security in container environments and microservice architectures.

### ✨ Key Features

- 🪶 **Lightweight**: 2.78MB for Standard (vs. Alpine 8.42MB and Ubuntu 24.04 78.2MB,
  measured on the same host)
- 🔒 **Secure-by-Default**: No package manager, minimal attack surface, comprehensive hardening
- 🧩 **Modular Design**: 3 variants (Minimal/Standard/Extended) for different use cases
- 📦 **musl + BusyBox + OpenRC only**: BusyBox is static-pie; OpenRC links only against
  musl and its own `librc`/`libeinfo`, with libcap linked statically, so the image
  carries no third-party shared libraries
- 🌐 **Multi-Architecture**: ARM64/x86_64 fully supported (Apple Silicon M1/M2/M3 optimized)

### 🎯 Performance Achievements

| Metric | Measured | Target | Status |
|--------|----------|--------|---------|
| Image size (Minimal) | **2.65MB** / arm64 **3.02MB** | < 5MB | ✅ **53% of target** / 60% |
| Image size (Standard) | **2.78MB** / arm64 **3.16MB** | < 15MB | ✅ **19% of target** / 21% |
| Image size (Extended) | **2.81MB** / arm64 **3.20MB** | < 50MB | ✅ **6% of target** / 6% |
| Boot time | **0.62s** | < 10s | ✅ **6% of target** |
| Memory usage | **232KB** | < 128MB | ✅ **0.2% of target** |
| BusyBox performance | **0.96-1.01x** of Alpine | Alpine equivalent | ✅ **within noise** |

Targets are the ones defined in [SPECIFICATION.md](SPECIFICATION.md) §8.3
(Minimal 5MB / Standard 15MB / Extended 50MB). **In practice all three
variants come in under 5MB — the strictest of the three targets.**

Measured on 2026-10-10: sizes for all six images, and boot time, memory and
command performance for Standard on native arm64. Every variant passes all 27
checks in `scripts/verify-image.sh`.

> **The 0.62s boot time does not mean Kimigayo is fast.** Measured the same
> way, Alpine and Ubuntu both come out at 0.61s — **the image makes no
> measurable difference**. Almost all of that 0.6s is Docker creating the
> container. Memory is where the difference actually shows
> (Kimigayo 232KB / Alpine 280KB / Ubuntu 316KB).

<details>
<summary><b>Per-variant breakdown, and where the bytes go</b></summary>

**Measurement conditions**: 2026-10-10, host is macOS on Apple Silicon
(arm64). Build environment is based on Alpine 3.24, with kernel 6.18.55 /
musl 1.2.6 / BusyBox 1.38.0 / OpenRC 0.63.2.

| What | How |
| --- | --- |
| Size | as reported by `docker images`; x86_64 under QEMU via `--platform linux/amd64` |
| Boot time | wall time of `docker run --rm <image> /bin/true`, median of 10, native arm64 |
| Memory | `docker stats` of an idle container, median of 10 samples, native arm64 |
| Command performance | `ls`, `grep`, `find`, `awk`, `sort`, `cat`, `wc` and `head` run against Alpine under identical conditions (`scripts/benchmark-busybox.sh`) |

**OpenRC reaches the `default` runlevel in 0.77s**
(`docker run --rm <image> /sbin/openrc default`, native arm64, median of 10).
The 0.15s over `/bin/true` is what the init system costs.

| Variant | BusyBox applets | BusyBox binary | tarball | image |
| --- | --- | --- | --- | --- |
| Minimal (x86_64) | 370 | 1,067KB | 1.4MB | **2.65MB** |
| Standard (x86_64) | 403 | 1,202KB | 1.4MB | **2.78MB** |
| Extended (x86_64) | 413 | 1,231KB | 1.5MB | **2.81MB** |
| Minimal (arm64) | 370 | 1,144KB | 1.5MB | **3.02MB** |
| Standard (arm64) | 403 | 1,292KB | 1.6MB | **3.16MB** |
| Extended (arm64) | 413 | 1,324KB | 1.6MB | **3.20MB** |

**The three variants differ only in the number of BusyBox applets — a span of
just 164KB on x86_64.** Most of the image is musl's `libc.so`, the BusyBox
binary and OpenRC (9 binaries, 2 shared libraries and the helpers), all of
which are present in every variant.

**arm64 is 0.37-0.39MB larger than x86_64 because of the BusyBox binary**
(aarch64 uses fixed-width instructions, so the same code takes more space;
this also includes the static-PIE and stack-protector work done in v3.0.0
to enable ASLR).

> v2.0.1 (2026-01-16) reported 1.17MB for Standard. That figure was measured on
> images that **did not actually contain musl's `libc.so` or any OpenRC binary**
> (fixed on 2026-10-09), so it is not the same thing as today's 2.78MB.
>
> The old boot time and memory figures (439ms / 0.2MB) were discarded — the
> benchmarks were broken. `scripts/benchmark-startup.sh` timed
> `docker run -d <image> sleep 5` until it exited, which always takes about
> 5,600ms on a working image; 439ms is what you get when that `sleep` never
> runs, so **the more broken the image, the faster it looked**.
> `scripts/benchmark-memory.sh` replaced `KiB` with `0.001` and then rounded to
> whole megabytes, so **anything under 1MB came out as 0**. Both were rewritten
> on 2026-10-10 and re-measured; the numbers above are from that run.

</details>

### 🚀 Quick Start

```bash
# Clone repository
git clone https://github.com/Kazuki-0731/Kimigayo.git
cd Kimigayo

# Build Docker environment
docker-compose build

# Run tests
docker-compose run --rm kimigayo-build make test
```

### 🤝 Contributing

Kimigayo OS is an open-source project. Bug reports, feature requests, and pull requests are welcome!

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

### 📄 License

Like Alpine Linux, Kimigayo OS components have individual licenses:

| Component             | License      |
| --------------------- | ------------ |
| Linux Kernel          | GPL-2.0      |
| musl libc             | MIT          |
| BusyBox               | GPL-2.0      |
| OpenRC                | BSD-2-Clause |
| Build System          | MIT          |

See [LICENSE](LICENSE) for details.

### 📚 Documentation

#### For Users

- [Installation Guide](docs/user/INSTALLATION.md) - Install on Docker, virtualization, and bare metal
- [Quick Start Guide](docs/user/QUICKSTART.md) - Basic operations and usage
- [Configuration Guide](docs/user/CONFIGURATION.md) - Network, services, and security configuration

#### For Developers

- [Specification](SPECIFICATION.md)
- [Architecture](docs/developer/ARCHITECTURE.md)
- [Development Guide](DEVELOPMENT.md)

---

<div align="center">

**Made with ❤️ by the Kimigayo OS Team**

[⭐ Star us on GitHub](https://github.com/Kazuki-0731/Kimigayo) | [🐛 Report Issues](https://github.com/Kazuki-0731/Kimigayo/issues) | [💬 Join Discussion](https://github.com/Kazuki-0731/Kimigayo/discussions)

</div>
