# Kimigayo OS

<div align="center">

**軽量・セキュアなコンテナ向けオペレーティングシステム**

[![Release](https://github.com/Kazuki-0731/Kimigayo/actions/workflows/on-tag-publish-release.yml/badge.svg)](https://github.com/Kazuki-0731/Kimigayo/actions/workflows/on-tag-publish-release.yml)
[![License: GPL-2.0 / MIT / BSD](https://img.shields.io/badge/License-GPL--2.0%20%7C%20MIT%20%7C%20BSD-blue.svg)](LICENSE)
[![Docker Hub](https://img.shields.io/badge/Docker%20Hub-ishinokazuki%2Fkimigayo--os-blue?logo=docker)](https://hub.docker.com/r/ishinokazuki/kimigayo-os)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

[English](#english) | [日本語](#japanese)

</div>

---

## <a name="japanese"></a>🇯🇵 日本語

### 概要

Kimigayo OS は、Google の distroless と Alpine Linux の両方の設計思想をハイブリッド的に組み合わせた、軽量・セキュアなコンテナ向けオペレーティングシステムです。パッケージマネージャーを意図的に排除して不変インフラを徹底し、攻撃面とイメージサイズを小さく保ちながら、シェルで中を確かめられる実用性を残しています。

#### Docker Hub
- https://hub.docker.com/r/ishinokazuki/kimigayo-os

### ✨ 主な特徴

- 🪶 **軽量**: Standard で **2.64MB**（同じ platform で実測した
  Alpine 8.42MB の約 1/3、Ubuntu 24.04 78.2MB の約 1/30）
- 🔒 **セキュアバイデフォルト**: パッケージマネージャー排除による最小攻撃面、全 ELF を PIE・Full RELRO・非実行スタックでビルド
- 🧩 **モジュラー設計**: 必要な機能のみを選択可能な3つのバリアント（Minimal/Standard/Extended）
- 📦 **musl + BusyBox + OpenRC のみ**: BusyBox と OpenRC は同じ musl の
  `libc.so` に動的リンクする（v3.0.2 から。Kimigayo が musl に当てた
  パッチが `/bin/sh` にも効く）。OpenRC はほかに自身の `librc` / `libeinfo`
  だけに依存し、libcap は静的リンク済みなので
  イメージ内に第三者の共有ライブラリを持たない
- 🌐 **マルチアーキテクチャ**: x86_64 / ARM64 のイメージを公開（arm64 はネイティブイメージなので、Apple Silicon でもエミュレーションなしで動く）

### 🎯 パフォーマンス実績

| 指標 | 実測値 | 目標値 | 達成状況 |
|------|-------|--------|---------|
| イメージサイズ (Minimal) | **2.34MB** / arm64 **2.73MB** | < 5MB | ✅ **目標の47%** / 55% |
| イメージサイズ (Standard) | **2.64MB** / arm64 **3.06MB** | < 15MB | ✅ **目標の18%** / 20% |
| イメージサイズ (Extended) | **2.67MB** / arm64 **3.10MB** | < 50MB | ✅ **目標の5%** / 6% |
| 起動時間 | **0.65秒** | —（目標は未定義） | —（Alpine 0.61秒・Ubuntu 0.65秒で差なし） |
| 常駐メモリ | **288KB** | —（目標は未定義） | —（Alpine 268KB・Ubuntu 316KB） |
| BusyBoxコマンド性能 | Alpine比 **0.97〜1.02x** | —（目標は未定義） | —（Alpine と有意差なし） |

<details>
<summary><b>6 バリアントの内訳と、サイズの中身の説明</b></summary>

目標値は [SPECIFICATION.md](SPECIFICATION.md) §8.3 の定義
（Minimal 5MB / Standard 15MB / Extended 50MB）。仕様が目標を定めているのはサイズだけで、
起動時間・常駐メモリ・コマンド性能には目標値が無い。
**実際には 3 バリアントとも、いちばん厳しい Minimal の目標 5MB を下回っている。**

v3.1.0 の公開イメージを 2026-10-15 に実測。サイズは 6 イメージすべて、起動時間・メモリ・
コマンド性能は arm64 ネイティブの Standard（Minimal / Extended の起動時間とメモリも
同じ条件で測っており、値は「競合OS比較」節の表）。6 バリアントすべてが
`scripts/verify-image.sh` の検査（40 項目、wget を持たない Minimal は 39）を通過している。

> **起動時間の 0.65 秒は「Kimigayo が速い」という意味ではない。**
> 同じ条件で同時に測ると **Alpine 0.61 秒・Ubuntu 24.04 0.65 秒**で、
> 差は出ない（同じイメージでも回によって 0.55〜0.70 秒の間で前後する）。この 0.6 秒のほとんどは Docker 自身の
> コンテナ生成なので、イメージの中身はほとんど効かない。
>
> **常駐メモリは v3.0.2 から Alpine をわずかに上回っている**（v3.1.0 で Kimigayo **288KB** /
> Alpine 268KB / Ubuntu 316KB）。v3.0.1 は 232KB だった。BusyBox を
> 動的リンクにしたため、`sleep` のような BusyBox のコマンドも `libc.so` を
> 読み込むようになった分（約 56KB）。Kimigayo が musl に当てた CVE パッチを
> `/bin/sh` にも効かせるための選択で、目標（128MB 未満）には影響しない。


**測定条件**: 2026-10-15 / 対象は v3.1.0 の公開イメージ / ホストは macOS（Apple Silicon, arm64）/
Alpine 3.24 ベースのビルド環境 /
カーネル 6.18.55・musl 1.2.6・BusyBox 1.38.0・OpenRC 0.63.2。

| 何を | どう測ったか |
| --- | --- |
| サイズ | `docker inspect` のバイト数を 10 進 MB に換算。x86_64 は `--platform linux/amd64`（QEMU エミュレーション）|
| 起動時間 | `docker run --rm <image> /bin/true` の実時間、10 回の中央値。arm64 ネイティブ |
| 常駐メモリ | `sleep` で常駐させたコンテナの `docker stats`、1 秒おきに 40 回読み、`docker stats` が返す `0B`（今回は 22 回）を捨てた **18 標本すべてが同じ値**。arm64 ネイティブ。同じ日に 20 回読みで先に測った回は Kimigayo 292KB・Alpine 268KB・Ubuntu 532KB で、Ubuntu だけ大きく外れたので標本を増やして測り直した |
| コマンド性能 | `ls`・`grep`・`find`・`awk`・`sort`・`cat`・`wc`・`head` の 8 つを Alpine と同条件で実行（`scripts/benchmark-busybox.sh`）。**中央値の比で 0.97〜1.02x**（平均は 1 回の外れ値に引っ張られるので中央値で見る）ので、どちらが速いとは言えない |

**OpenRC が default ランレベルを完走するまでは 0.76 秒**
（`docker run --rm <image> /sbin/openrc default`、arm64、10 回の中央値）。
`/bin/true` の 0.65 秒との差が Init の分。

| バリアント | BusyBox アプレット | BusyBox 本体 | tarball | イメージ |
| --- | --- | --- | --- | --- |
| Minimal (x86_64) | 329 | 710KB | 1,103KB | **2.34MB** |
| Standard (x86_64) | 400 | 1,002KB | 1,290KB | **2.64MB** |
| Extended (x86_64) | 411 | 1,030KB | 1,313KB | **2.67MB** |
| Minimal (arm64) | 329 | 781KB | 1,265KB | **2.73MB** |
| Standard (arm64) | 400 | 1,105KB | 1,472KB | **3.06MB** |
| Extended (arm64) | 411 | 1,140KB | 1,493KB | **3.10MB** |

> **v3.1.0 で Minimal が約 120KB 小さくなり、Standard・Extended は約 45KB 大きくなった**
> （v3.0.2 は 2.46 / 2.60 / 2.62MB）。Minimal は httpd・telnetd・udhcpc などの
> ネットワーク系 38 アプレットを外した（367 → 329。どれも Standard に入っている）。
> 増えた分は主に `/usr/share/licenses/` に入れた条文。arm64 はさらに、
> FORTIFY_SOURCE が効くようになった分だけ BusyBox 本体が約 20KB 大きい。

> **v3.0.2 で BusyBox 本体が約 160KB 小さくなった**（v3.0.1 の Standard x86_64 は
> 1,162KB / イメージ 2.76MB）。BusyBox を動的リンクにし、静的リンクで中に
> 取り込んでいた libc を、OpenRC と共有の `/lib/libc.so` に寄せたため。

> **v3.0.0 からアプレットが 3 つ減っている**（370/403/413 → 367/400/411）。
> `dpkg`・`dpkg-deb`・`rpm` を外したため
> （→ [CHANGELOG.md](CHANGELOG.md) の 3.0.1）。

**3バリアントの差は BusyBox のアプレット数だけで、x86_64 では 330KB しかない。**
イメージの大半は musl の `libc.so`・BusyBox 本体・
OpenRC（バイナリ9個 + 共有ライブラリ2本 + ヘルパ）で、どのバリアントにも入る。

**arm64 が x86_64 より 0.39-0.43MB 大きいのは主に BusyBox 本体と libc.so の差**
（aarch64 は固定長命令なので同じコードでもコード量が増える）。

> **v2.0.1（2026-01-16）では Standard 1.17MB だった。** 増えた主因は
> **v2.0.1 までは musl の `libc.so` と OpenRC のバイナリがイメージに
> 入っていなかった**こと（2026-10-09 に修正）。v3.0.1 までは BusyBox 1.38.0 を
> 静的リンクしており、本体が単体で 1.16MB あったことも効いていた
> （v3.0.2 で動的リンクにして約 1,001KB）。つまり 1.17MB は
> 「Init システムが入っていない状態」の数字で、現在の 2.64MB と
> 同じものを測った値ではない。
>
> **起動時間とメモリの旧値（439ms / 0.2MB）は破棄した。計測が壊れていた。**
> `scripts/benchmark-startup.sh` は `docker run -d <image> sleep 5` の
> 終了までを測っており、正常なイメージほど必ず約 5,600ms になっていた
> （439ms はこの `sleep` が成立しなかった＝コンテナが即死したときの値で、
> **イメージが壊れているほど速く見える**計測だった）。
> `scripts/benchmark-memory.sh` は `KiB` を `0.001` に置換したうえ
> 結果を整数 MB に丸めており、**1MB 未満を 0 としか表せなかった**。
> 2026-10-10 に両方を書き直した。上の値は 2026-10-15 に v3.1.0 で測ったもの。

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

下2層（カーネル・ハードウェア）はイメージに含まれない。コンテナはホストのものを使う。

### 🔧 主要コンポーネント

| コンポーネント | バージョン | 役割 |
|---|---|---|
| **Linux カーネル** | 6.18.55 (LTS) | ベアメタル／QEMU 検証用（イメージには含まれない）。EOL 2028-12 |
| **musl libc** | 1.2.6 | C ライブラリ（軽量でシンプル） |
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

- ✅ **最小攻撃面**: パッケージインストール機能がないため、侵入者がパッケージマネージャーで道具を足せない
- ✅ **超軽量**: 数MBのイメージサイズ（実測は「パフォーマンス実績」を参照）
- ✅ **不変インフラ**: 実行時にソフトウェアを足さず、変更はイメージを作り直して入れ替える
- ✅ **予測可能性**: 実行時にソフトウェアを足す仕組みを持たないため、動くものはビルド時に決まる

#### Alpine Linux からの継承

- ✅ **musl libc**: 軽量でシンプルなCライブラリ
- ✅ **BusyBox**: 基本的なUnixコマンドとシェルを提供（デバッグ可能）
- ✅ **OpenRC**: シンプルで軽量なInitシステム
- ✅ **セキュリティ強化**: 全 ELF を PIE・Full RELRO（BIND_NOW）・非実行スタックでビルド（`scripts/verify-image.sh` が検査。ASLR はホストのカーネルが効かせる）。Stack Protector は x86_64 では全 ELF に付くが、v3.0.2 の arm64 の OpenRC には付いていない（v3.1.0 で修正。`verify-image.sh` が検査する）

この組み合わせにより、**distroless のセキュリティ** と **Alpine の実用性** を両立し、コンテナ環境に最適化されたOSを実現しています。

**推奨される使用パターン:**

```dockerfile
# マルチステージビルドで必要なものを全てビルド時に準備
FROM alpine:3.24 AS builder
RUN apk add --no-cache python3

# 共有ライブラリは手で列挙せず ldd で集める（拡張モジュールの依存も含める）
RUN mkdir -p /stage/usr/bin /stage/usr/lib \
    && cp -a /usr/bin/python3* /stage/usr/bin/ \
    && cp -a /usr/lib/python3* /stage/usr/lib/ \
    && for f in "$(readlink -f /usr/bin/python3)" /usr/lib/python3*/lib-dynload/*.so; do ldd "$f"; done \
       | awk '/=>/ { print $3 } /^\/lib|^\/usr\/lib/ { print $1 }' \
       | grep -v 'ld-musl' | sort -u \
       | xargs -I{} cp -L {} /stage/usr/lib/

# Kimigayo OSで最小ランタイム環境を構築（版を固定する）
FROM ishinokazuki/kimigayo-os:3.1.0
COPY --from=builder /stage/ /
COPY app.py /app/
USER 65534
CMD ["python3", "/app/app.py"]
```

動く完全な例は [examples/python/Dockerfile](examples/python/Dockerfile)（nginx・Node.js もあり）。

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

前提条件・ビルド手順・よく使うコマンド・ビルド成果物・詳細なビルドオプション・トラブルシューティングは、
[ビルドガイド](docs/developer/BUILD_GUIDE.md#ソースからビルドする) を参照してください。

### 📦 イメージバリエーション

| イメージタイプ | サイズ | 用途 | Docker Hubタグ |
| -------------- | ------ | ---- | -------------- |
| **Minimal** | **2.34MB**（329 アプレット） | コンテナ、最小限の環境 | `ishinokazuki/kimigayo-os:latest-minimal` |
| **Standard** | **2.64MB**（400 アプレット） | 一般的なサーバー環境（推奨） | `ishinokazuki/kimigayo-os:latest` |
| **Extended** | **2.67MB**（411 アプレット） | Standard に `ar`・`ed`・`inotifyd`・`rfkill`・MTD/flash・framebuffer 系など 11 アプレットを足したもの | `ishinokazuki/kimigayo-os:latest-extended` |

いずれも x86_64 / v3.1.0 を 2026-10-15 実測。arm64 は Minimal 2.73MB /
Standard 3.06MB / Extended 3.10MB（→「パフォーマンス実績」節）。

> **`latest` 系は最新リリースを指す**（公開済みの版は
> [Releases](https://github.com/Kazuki-0731/Kimigayo/releases) を参照）。
> マルチアーキなので `linux/amd64` と `linux/arm64` の
> どちらを引いても同じ版が来る。
> **本番では版を固定する**（`3.1.0-standard` のように版番号つきのタグ、
> またはダイジェスト指定）。

**比較**（`--platform linux/amd64`。Kimigayo Standard = 2.64MB・Alpine・Ubuntu は 2026-10-15、
distroless は 2026-10-11 に同じホストで実測）:

| イメージ | サイズ | Kimigayo 比 |
| --- | --- | --- |
| `gcr.io/distroless/static-debian12` | 2.11MB | 0.8倍（シェルも Init も無い） |
| `alpine:latest`（3.24.2） | 8.42MB | 3.2倍 |
| `gcr.io/distroless/base-debian12` | 20.9MB | 7.9倍 |
| `ubuntu:24.04` | 78.2MB | 30倍 |

### 🔐 セキュリティ機能

#### コンパイル時

- PIE (Position Independent Executables) — 全 ELF（`scripts/verify-image.sh` が検査）
- Full RELRO (Relocation Read-Only + BIND_NOW) — 全 ELF（同上）
- Stack-smashing protection — x86_64 は全 ELF。**v3.0.2 の arm64 の OpenRC（`openrc`・`openrc-run`・`librc`・`libeinfo` など）には付いていない**（v3.1.0 で修正。`scripts/verify-image.sh` が検査する）
- FORTIFY_SOURCE — Alpine の `fortify-headers` で実装（musl 自身は実装しない）。**v3.0.2 の arm64 には効いていない**（v3.1.0 で修正。`scripts/verify-image.sh` が検査する）

#### ランタイム（イメージ側）

- ASLR が効く形のバイナリ（全実行ファイルを PIE でビルド）
- DEP (Data Execution Prevention)

#### ランタイム（ホストのコンテナランタイム側）

Seccomp-BPF・Namespace isolation・Capabilities の制限は、
**イメージの属性ではなくホストの `docker run` が与えるもの**です。
Kimigayo の成果物は rootfs だけでカーネルを含まないため、
seccomp プロファイルの適用はホスト側で行います。

```bash
docker run --rm \
  --security-opt no-new-privileges \
  --cap-drop ALL \
  --read-only \
  ishinokazuki/kimigayo-os:latest /bin/sh
```

#### 完全性の検証

**パッケージ署名検証はありません。** パッケージという配布単位を持たない
ため（パッケージマネージャーを排除する設計）、検証する対象が存在しません。
代わりに次の2点で担保しています。

- **上流ソースのチェックサム検証**: ダウンロードした musl / カーネル /
  BusyBox / OpenRC の tarball の SHA256 を検証。登録する値は、カーネルと BusyBox は
  上流の公開値と、公式一覧の無い musl と OpenRC は Alpine aports の `sha512sums` と突合したもの
- **リリース資産のハッシュ配布**: `SHA256SUMS` と `SHA512SUMS` を
  GitHub Release に添付

**公開イメージは v3.0.2 から Cosign で署名しています**（`on-tag-publish-release.yml` の
`sign` ジョブ）。鍵を持たないキーレス署名（Sigstore OIDC）で、署名は
Rekor の透明性ログに載ります。**検証には cosign v3 以降が必要です**
（署名は新しい形式で置いてあり、cosign v2 では `no signatures found` になる。
2026-10-12 に cosign v3.0.6 で検証を確認）。

```bash
cosign verify ishinokazuki/kimigayo-os:latest \
  --certificate-identity-regexp '^https://github.com/Kazuki-0731/Kimigayo/' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

> **v3.0.1 以前の公開イメージは署名されていません。**

**Docker Content Trust は使いません**（Docker Hub 側の仕組みに依存し、
鍵の保管と失効の運用が必要になるため）。

### 🎯 ターゲット環境

- **コンテナ環境**: VPS 上の Docker を想定（クラウドのマネージドなコンテナサービスでも使える）
- Kubernetes・Podman の手順は [インストールガイド](docs/user/INSTALLATION.md) にあるが、CI では検証していない

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
| BusyBox                    | GPL-2.0-only |
| musl libc                  | MIT          |
| OpenRC                     | BSD-2-Clause |
| libcap（OpenRC に静的リンク） | BSD-3-Clause |
| Linux カーネル（イメージに入らない） | GPL-2.0-only |
| ビルドシステム             | MIT          |

条文はイメージの `/usr/share/licenses/` にあります。対応するソース
（上流の tarball と、パッチ・config・ビルドスクリプトを含むリポジトリの
archive）は各 GitHub Release に添付しています。
詳細は [LICENSE](LICENSE) を参照してください。

### 🌟 競合OS比較

**同じホスト（macOS / Apple Silicon）で実測。** Kimigayo・Alpine・Ubuntu の
起動時間とメモリは 2026-10-15 に同時に測った値（Kimigayo は v3.1.0）。
distroless は 2026-10-11 の値。
サイズは x86_64（`--platform linux/amd64`、QEMU）と arm64 の両方、
**起動時間とメモリは arm64 ネイティブ**（QEMU を挟むと時間の比較に
ならないため）。測り方は「パフォーマンス実績」節の折りたたみを参照。

| OS | サイズ (x86_64 / arm64) | 起動時間 | 常駐メモリ | シェル | パッケージマネージャー | Init |
|----|-------|---------|-------|-------|---------------------|------|
| **Kimigayo Minimal** | **2.34** / **2.73MB** | 0.61秒 | 280KB | ✅ BusyBox | ❌ | ✅ OpenRC |
| **Kimigayo Standard** | **2.64** / **3.06MB** | 0.65秒 | 288KB | ✅ BusyBox | ❌ | ✅ OpenRC |
| **Kimigayo Extended** | **2.67** / **3.10MB** | 0.62秒 | 280KB | ✅ BusyBox | ❌ | ✅ OpenRC |
| `gcr.io/distroless/static-debian12` | 2.11 / 2.11MB | — | — | ❌ | ❌ | ❌ |
| `gcr.io/distroless/base-debian12` | 20.9 / 31.4MB | — | — | ❌ | ❌ | ❌ |
| `alpine:latest`（3.24.2） | 8.42 / 8.66MB | 0.61秒 | **268KB** | ✅ ash | ✅ apk | ❌ |
| `ubuntu:24.04` | 78.2 / 101MB | 0.65秒 | 316KB | ✅ bash | ✅ apt | ❌ |

> **起動時間に差は出ていない**（0.61〜0.65秒。101MB の Ubuntu も同じ範囲）。
> 測っている時間のほとんどは Docker のコンテナ生成で、イメージの中身は
> ほとんど効かないので、**「軽いから起動が速い」とは言えない。**
> 常駐メモリは Kimigayo（Standard）が Ubuntu の約 91%、**Alpine の約 107%**
> （v3.0.1 では Alpine より少なかった。BusyBox を動的リンクにした分。
> →「パフォーマンス実績」節）。
>
> **`docker stop` はどのイメージでも約 10.4 秒かかる**（PID 1 が SIGTERM を
> 処理しない場合。Alpine も 10.4 秒）。アプリ側で SIGTERM を扱えば
> 両者 0.67 秒（→ [docs/benchmarks/lifecycle.md](docs/benchmarks/lifecycle.md)。
> この 2 つは v3.0.1 で 2026-10-11 に測った値で、v3.0.2 以降は測り直していない）。
>
> distroless は実行ファイルを1つも持たないため、この方法では起動時間も
> メモリも測れない（`/bin/true` すら無い）。これは欠陥ではなく設計。

#### vs Alpine Linux
- ✅ **約3倍軽量**: 2.64MB vs 8.42MB（x86_64。arm64 でも 3.06 vs 8.66MB）
- ⚠️ **常駐メモリはほぼ同じ**: 288KB vs 268KB（arm64。v3.0.2 から BusyBox が動的リンク）
- ✅ **パッケージマネージャーなし**: セキュリティ優先の設計（Alpine は apk を含む）
- ✅ **Init を同梱**: OpenRC 0.63.2（Alpine のイメージには Init が入っていない）
- ✅ **不変インフラ**: ビルド時に全て決定、実行時の変更を排除

#### vs distroless
- ✅ **デバッグ可能**: シェルとUnixコマンドを含む（distroless はシェルなし）
- ✅ **Init がある**: OpenRC でサービスを起動・監視できる（既定の PID 1 は `/bin/sh`。
  OpenRC を使うのは `--entrypoint /sbin/init` で起動したときだけ）
- ⚠️ **サイズ**: Distroless Static（2.11MB）より大きいが、機能が豊富

#### 独自の強み
- 🏆 **シェルと Init を備えて 2.64MB**
- 🚀 **arm64 ネイティブイメージ**: Apple Silicon や arm64 の VPS でエミュレーションなしで動く
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
- [API リファレンス](docs/developer/API_REFERENCE.md) - Init、カーネル、ビルドシステム、CLI
- [開発ガイド](DEVELOPMENT.md) - 開発環境セットアップ
- [貢献ガイド](CONTRIBUTING.md) - コントリビューション方法
- [コミットメッセージガイド](docs/developer/COMMIT_GUIDE.md) - コミット規約とCHANGELOG生成
- [仕様書](SPECIFICATION.md) - プロジェクト仕様
- [リリースチェックリスト](docs/RELEASE_CHECKLIST.md) - v0.1.0 公開時の記録（現在の手順書ではありません）
- [v1.0.0リリース計画](docs/V1_RELEASE_PLAN.md) - 2025-12 時点の計画（v1.0.0 は公開済み。現在は v3.0.x）

#### GitHub Actions ワークフロー

プロジェクトでは以下の自動化ワークフローが設定されています：

| ワークフロー | トリガー | 目的 | 処理内容 |
|------------|---------|------|---------|
| **on-push-and-pr-build-and-verify-all-images.yml** | PR、main push、手動 | 継続的インテグレーション | • ShellCheck・リンク検査・pytest（unit）<br>• **全variant × 全arch**ビルドとイメージ検証（6パターン、reusable-build-and-verify-image.yml 経由。カーネルは作らない）<br>• Trivy ファイルシステムスキャン（リポジトリ側）<br>• Discord通知 |
| **on-tag-publish-release.yml** | タグpush (v*.*.*)、手動 | リリース成果物生成 | • 全variant × 全archビルド・`verify-image.sh`・`scan-image.sh`（CVE 照合と SBOM）<br>• Docker Hubへpush（マルチアーチマニフェスト作成）。**公開はタグpushのときだけ**で、手動実行はビルド・検証・スキャンまで<br>• Cosign のキーレス署名<br>• GitHub Release作成（rootfs tarball・SBOM・対応するソース・`SHA256SUMS`・`SHA512SUMS`、前回タグからのPRリスト。PR が無ければコミット一覧）<br>• Discord通知 |
| **reusable-build-and-verify-image.yml** | 再利用可能ワークフロー | ビルド処理の共通化 | • rootfsビルド<br>• Docker imageビルド（push はしない）<br>• `verify-image.sh` でイメージを実行して検証<br>• `scan-image.sh` で CVE 照合（SBOM + Grype）と秘密情報スキャン |
| **manual-build-image-and-kernel.yml** | 手動実行 | 検証用ビルド | • variant/arch選択可能<br>• `build_kernel=true` でカーネルも作る（**CI でカーネルを作る唯一の経路**）<br>• アーティファクトアップロード |
| **upstream-security-watch.yml** | 日次 02:00 UTC | セキュリティチェック | • 構成要素のバージョンチェック（新版を検知したら非公開の Project に追加）<br>• 上流のセキュリティ情報（Debian・Alpine・上流 git・CISA KEV）との差分（差分が出たら非公開の Project と Discord 通知）<br>• Trivy ファイルシステムスキャン |
| **component-update-pr.yml** | 週次（月曜 03:00 UTC） | コンポーネント更新チェック | • musl/BusyBox/OpenRC バージョンチェック<br>• 更新があればPR自動作成 |
| **on-pr-dependency-review.yml** | PR時 | 依存関係レビュー | • 依存関係の変更を検証（`fail-on-severity: high`） |
| **published-image-cve-scan.yml** | 週次（月曜 04:00 UTC）、手動 | 公開イメージの CVE 照合 | • 公開中の `latest` を `scan-image.sh` で照合（定期実行で失敗したら非公開の Project に追加） |

**CI/CD改善点（v1.0.0 時点の記録）:**
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
- **ドキュメント**: 正本はこのリポジトリの `docs/` 配下（Wiki は使っていない）

### 🙏 謝辞

Kimigayo OS は以下のプロジェクトにインスパイアされ、技術的な基盤を提供していただいています：

- [Google Distroless](https://github.com/GoogleContainerTools/distroless) - 不変インフラとセキュリティ優先の設計思想
- [Alpine Linux](https://alpinelinux.org/) - 軽量性とセキュリティのベストプラクティス
- [musl libc](https://musl.libc.org/) - 軽量でシンプルな C ライブラリ
- [BusyBox](https://busybox.net/) - 最小限の Unix ユーティリティ
- [OpenRC](https://github.com/OpenRC/openrc) - シンプルで軽量な Init システム

---

## <a name="english"></a>🇬🇧 English

### Overview

Kimigayo OS is a lightweight, secure container-focused operating system that combines the design philosophies of Google's distroless and Alpine Linux in a hybrid approach. By intentionally excluding package managers and enforcing immutable infrastructure, it keeps the attack surface and image size small while still letting you inspect the container with a shell.

### 🎯 Design Philosophy: a Distroless + Alpine Hybrid

**From distroless: no package manager, by design**

- ✅ **Minimal attack surface**: nothing can be installed at runtime, so an intruder cannot fetch extra tools with a package manager
- ✅ **Immutable infrastructure**: everything is added at build time through multi-stage builds
- ✅ **Predictability**: what runs is decided at build time

**From Alpine Linux: practical enough to debug**

- ✅ **musl libc**: a lightweight, simple C library
- ✅ **BusyBox**: a shell and the basic Unix commands
- ✅ **OpenRC**: a simple, lightweight init system
- ✅ **Hardening**: every ELF is built with PIE, full RELRO (BIND_NOW) and a non-executable stack, checked by `scripts/verify-image.sh` (ASLR itself is provided by the host kernel). Stack Protector covers every ELF on x86_64 but not OpenRC on arm64

A working multi-stage example is in [examples/python/Dockerfile](examples/python/Dockerfile) (nginx and Node.js examples are there too).

### ✨ Key Features

- 🪶 **Lightweight**: 2.64MB for Standard (vs. Alpine 8.42MB and Ubuntu 24.04 78.2MB,
  measured on the same host)
- 🔒 **Secure-by-Default**: No package manager, minimal attack surface, PIE / full RELRO / non-executable stack on every ELF
- 🧩 **Modular Design**: 3 variants (Minimal/Standard/Extended) for different use cases
- 📦 **musl + BusyBox + OpenRC only**: BusyBox and OpenRC link dynamically against
  the same musl `libc.so` (since v3.0.2, so the musl patches Kimigayo applies also
  cover `/bin/sh`). OpenRC otherwise links only against its own `librc`/`libeinfo`,
  with libcap linked statically, so the image carries no third-party shared libraries
- 🌐 **Multi-Architecture**: x86_64 and ARM64 images (arm64 is native, so it runs without emulation on Apple Silicon)

### 🎯 Performance Achievements

| Metric | Measured | Target | Status |
|--------|----------|--------|---------|
| Image size (Minimal) | **2.34MB** / arm64 **2.73MB** | < 5MB | ✅ **47% of target** / 55% |
| Image size (Standard) | **2.64MB** / arm64 **3.06MB** | < 15MB | ✅ **18% of target** / 20% |
| Image size (Extended) | **2.67MB** / arm64 **3.10MB** | < 50MB | ✅ **5% of target** / 6% |
| Boot time | **0.65s** | — (no target defined) | — (Alpine 0.61s, Ubuntu 0.65s, no difference) |
| Resident memory | **288KB** | — (no target defined) | — (Alpine 268KB, Ubuntu 316KB) |
| BusyBox performance | **0.97-1.02x** of Alpine | — (no target defined) | — (no measurable difference from Alpine) |

<details>
<summary><b>Per-variant breakdown, and where the bytes go</b></summary>

Targets are the ones defined in [SPECIFICATION.md](SPECIFICATION.md) §8.3
(Minimal 5MB / Standard 15MB / Extended 50MB). The specification sets targets for size only;
boot time, memory and command performance have none. **In practice all three
variants come in under 5MB — the strictest of the three targets.**

The published v3.1.0 images measured on 2026-10-15: sizes for all six images, and
boot time, memory and command performance for Standard on native arm64 (Minimal and Extended
boot time and memory were measured the same way; see the comparison table in the Japanese section). Every
variant passes `scripts/verify-image.sh` (40 checks; 39 for Minimal, which has no wget).

> **The 0.65s boot time does not mean Kimigayo is fast.** Measured in the same
> session, Alpine comes out at 0.61s and Ubuntu 24.04 at 0.65s, and the same image
> moves between 0.55s and 0.70s from run to run. Almost all of that
> 0.6s is Docker creating the container, so the image barely matters.
>
> **Resident memory has been slightly above Alpine since v3.0.2** (v3.1.0: Kimigayo **288KB** /
> Alpine 268KB / Ubuntu 316KB; v3.0.1 was 232KB). BusyBox is now dynamically
> linked, so BusyBox commands such as `sleep` map `libc.so` too (about 56KB).
> That is the price of having Kimigayo's musl CVE patches cover `/bin/sh`; it is
> nowhere near the 128MB target.


**Measurement conditions**: 2026-10-15, published v3.1.0 images, host is macOS on Apple Silicon
(arm64). Build environment is based on Alpine 3.24, with kernel 6.18.55 /
musl 1.2.6 / BusyBox 1.38.0 / OpenRC 0.63.2.

| What | How |
| --- | --- |
| Size | `docker inspect` byte count converted to decimal MB; x86_64 under QEMU via `--platform linux/amd64` |
| Boot time | wall time of `docker run --rm <image> /bin/true`, median of 10, native arm64 |
| Resident memory | `docker stats` of an idle container, read 40 times one second apart; after discarding the `0B` readings (22 this time), **all 18 samples read the same value**. Native arm64. An earlier 20-read run the same day gave Kimigayo 292KB / Alpine 268KB / Ubuntu 532KB; Ubuntu was far off, so it was re-run with more samples |
| Command performance | `ls`, `grep`, `find`, `awk`, `sort`, `cat`, `wc` and `head` run against Alpine under identical conditions (`scripts/benchmark-busybox.sh`). **Medians fall between 0.97x and 1.02x** (means are skewed by single outliers, so medians are used), so neither is measurably faster |

**OpenRC reaches the `default` runlevel in 0.76s**
(`docker run --rm <image> /sbin/openrc default`, native arm64, median of 10).
The difference over `/bin/true` is what the init system costs.

| Variant | BusyBox applets | BusyBox binary | tarball | image |
| --- | --- | --- | --- | --- |
| Minimal (x86_64) | 329 | 710KB | 1,103KB | **2.34MB** |
| Standard (x86_64) | 400 | 1,002KB | 1,290KB | **2.64MB** |
| Extended (x86_64) | 411 | 1,030KB | 1,313KB | **2.67MB** |
| Minimal (arm64) | 329 | 781KB | 1,265KB | **2.73MB** |
| Standard (arm64) | 400 | 1,105KB | 1,472KB | **3.06MB** |
| Extended (arm64) | 411 | 1,140KB | 1,493KB | **3.10MB** |

> **In v3.1.0 Minimal shrank by about 120KB and Standard / Extended grew by about 45KB**
> (v3.0.2: 2.46 / 2.60 / 2.62MB). Minimal dropped 38 network applets such as httpd,
> telnetd and udhcpc (367 → 329; all of them remain in Standard). The growth is mostly
> the license texts now shipped in `/usr/share/licenses/`. On arm64 the BusyBox
> binary is also about 20KB larger because FORTIFY_SOURCE now takes effect.

> **The BusyBox binary shrank by about 160KB in v3.0.2** (v3.0.1 Standard x86_64:
> 1,162KB / 2.76MB image). BusyBox is now dynamically linked and shares
> `/lib/libc.so` with OpenRC instead of carrying its own copy of libc.

> **Three applets fewer than v3.0.0** (370/403/413 → 367/400/411): `dpkg`,
> `dpkg-deb` and `rpm` were removed (see [CHANGELOG.md](CHANGELOG.md), 3.0.1).

**The three variants differ only in the number of BusyBox applets — a span of
just 330KB on x86_64.** Most of the image is musl's `libc.so`, the BusyBox
binary and OpenRC (9 binaries, 2 shared libraries and the helpers), all of
which are present in every variant.

**arm64 is 0.39-0.43MB larger than x86_64, mostly because of the BusyBox binary
and `libc.so`** (aarch64 uses fixed-width instructions, so the same code takes
more space).

> v2.0.1 (2026-01-16) reported 1.17MB for Standard. That figure was measured on
> images that **did not actually contain musl's `libc.so` or any OpenRC binary**
> (fixed on 2026-10-09), so it is not the same thing as today's 2.64MB.
>
> The old boot time and memory figures (439ms / 0.2MB) were discarded — the
> benchmarks were broken. `scripts/benchmark-startup.sh` timed
> `docker run -d <image> sleep 5` until it exited, which always takes about
> 5,600ms on a working image; 439ms is what you get when that `sleep` never
> runs, so **the more broken the image, the faster it looked**.
> `scripts/benchmark-memory.sh` replaced `KiB` with `0.001` and then rounded to
> whole megabytes, so **anything under 1MB came out as 0**. Both were rewritten
> on 2026-10-10 and re-measured; the numbers above are from the 2026-10-15 run (v3.1.0).

</details>

### 🚀 Quick Start

```bash
# Clone repository
git clone https://github.com/Kazuki-0731/Kimigayo.git
cd Kimigayo

# Build Docker environment
make docker-build

# Run tests (inside the build container)
make test
```

Building from source, build artifacts and troubleshooting are covered in the
[Build Guide](docs/developer/BUILD_GUIDE.md#ソースからビルドする) (Japanese).

### 🤝 Contributing

Kimigayo OS is an open-source project. Bug reports, feature requests, and pull requests are welcome!

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

### 📄 License

Like Alpine Linux, Kimigayo OS components have individual licenses:

| Component             | License      |
| --------------------- | ------------ |
| BusyBox               | GPL-2.0-only |
| musl libc             | MIT          |
| OpenRC                | BSD-2-Clause |
| libcap (statically linked into OpenRC) | BSD-3-Clause |
| Linux Kernel (not in the image) | GPL-2.0-only |
| Build System          | MIT          |

The license texts are in `/usr/share/licenses/` in the image. The
corresponding source (upstream archives plus a repository archive with
the patches, configs and build scripts) is attached to each GitHub Release.
See [LICENSE](LICENSE) for details.

### 📚 Documentation

#### For Users

- [Installation Guide](docs/user/INSTALLATION.md) - Install on Docker, Kubernetes and Podman
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
