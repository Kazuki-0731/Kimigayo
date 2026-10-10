# Kimigayo OS Release Notes

## バージョン 3.0.1 "Himawari" (向日葵) - 2026-10-11

**イメージから「あってはいけないもの」を2種類外しました。**
パッケージマネージャー（BusyBox の `dpkg` / `rpm`）と、
Kimigayo では絶対に実行されない init スクリプト 9 本です。

### 🔒 パッケージマネージャーが入っていました

**v3.0.0 までの公開イメージには `dpkg` / `dpkg-deb` / `rpm` が
入っており、実際にパッケージをインストールできました。**

```console
$ docker run --rm ishinokazuki/kimigayo-os:3.0.0 dpkg --help
Usage: dpkg [-ilCPru] [-F OPT] PACKAGE
Install, remove and manage Debian packages
    -i,--install	Install the package
```

Kimigayo は**パッケージマネージャーを持たないこと**が設計の前提です
（`SPECIFICATION.md` 2.2 / 3.5）。README でも「パッケージマネージャー
なし」「不変インフラを徹底」と書いており、**実態と逆でした**。

原因は BusyBox の config の書き忘れです。BusyBox は `dpkg`・`dpkg-deb`・
`rpm` をいずれも**既定で有効**にしているため、config に `n` と
書かなければ有効になります。「書かなかった」だけで入っていました。

v3.0.1 では3バリアントとも明示的に無効化し、**成果物に
パッケージマネージャーが無いことを `verify-image.sh` が検査します**
（`apk`・`apt`・`opkg`・`yum`・`dnf`・`pacman` も同じ検査に載せました）。

> `rpm2cpio` は extended に残しています。rpm を**展開**するだけで
> インストール機能が無いため、`ar` や `unzip` と同じ扱いです。

### 🧹 動かない init スクリプトを外しました

OpenRC は、どのディストリでも使えるように init スクリプトを一式
同梱しています。そのうち次の 9 本は、Kimigayo の想定
（VPS / クラウド上の Docker コンテナ）では 1 度も実行されません。

| 外したもの | 何をするものか | なぜ動かないか |
| --- | --- | --- |
| `agetty` | 端末のログインプロンプト | `/sbin/agetty` が無い |
| `consolefont` | コンソールのフォント設定 | `/usr/bin/setfont` が無い |
| `numlock` | コンソールの NumLock | `/usr/bin/setleds` が無い |
| `runsvdir` | runit のサービス監視 | `/usr/bin/runsvdir` が無い |
| `s6-svscan` | s6 のサービス監視 | Kimigayo は OpenRC を使う |
| `user` | ユーザー単位の OpenRC セッション | コンテナでは使わない |
| `net-online` | ネットワーク疎通待ち | コンテナでは不要 |
| `osclock` | 「時計は OS 任せ」と宣言するだけ | — |
| `swclock` | RTC が無いマシンで時計を合わせる | — |

`/etc/init.d` は 36 本 → **27 本**になりました。

**動作が変わらないことを実測で確認しています。** 削除版をビルドし、
`openrc sysinit` / `boot` / `default` の終了コード、起動したサービス数、
`rc-update show` の行数、`--privileged` での `sysctl` 適用まで、
v3.0.0 と完全に一致しました。

> **サイズのためではありません**（約 12KB しか減りません）。
> 目的は、**root で解釈・実行されるシェルスクリプトを減らすこと**と、
> `/etc/init.d` に実際に動くものだけが並んでいる状態にすることです。
>
> `keyword -docker` が付いているだけのもの（`fsck`・`hwclock`・
> `modules`・`localmount` など 24 本）は**残しています**。
> Docker では飛ばされますが、ベアメタルや特権コンテナでは
> 正規に機能する OpenRC の構成要素だからです。

### 📊 起動時間とメモリを実測しました（v3.0.0 では「未測定」でした）

計測スクリプトが別物を測っていたのを直し、測り直しました。
**イメージの中身は変わりません。**

| 指標 | Kimigayo Standard | Alpine | Ubuntu 24.04 |
| --- | --- | --- | --- |
| 起動時間 | 0.61秒 | 0.62秒 | **0.59秒** |
| 常駐メモリ | **232KB** | 276KB | 312KB |
| イメージサイズ (arm64) | **3.13MB** | 8.66MB | 100.81MB |

（2026-10-11、macOS / Apple Silicon、**arm64 ネイティブ**、中央値10回。
常駐メモリは 37 標本すべて 232KB）

**起動時間に差は出ません。それどころか 100MB の Ubuntu がいちばん速い。**
0.6 秒のほとんどは Docker 自身のコンテナ生成なので、イメージの中身は
ほとんど効きません。**「軽いから起動が速い」とは言えません。**
差が出るのは常駐メモリとサイズの方です。

> **`docker stop` はどのイメージでも約 10.4 秒かかります。**
> `docker stop` は PID 1 に SIGTERM を送って 10 秒待ちますが、
> カーネルは PID 1 のハンドラ無しシグナルを無視するためです
> （Alpine も 10.4 秒）。アプリ側で SIGTERM を扱えば両者 0.67 秒。
> → [docs/benchmarks/lifecycle.md](docs/benchmarks/lifecycle.md)

OpenRC が `default` ランレベルを完走するまでは **0.77 秒**でした。

> v2.0.1 まで公開していた **439ms / 0.2MB は撤回済み**です。
> 起動時間は `docker run -d <image> sleep 5` の終了までを測っており、
> **イメージが壊れているほど速く見える**計測でした。
> メモリは `KiB` の換算を誤ったうえ整数 MB に丸めており、
> 1MB 未満を 0 としか表せませんでした。

### 📝 仕様書と公開ドキュメントの訂正

**当初の計画のまま残っていた記述を落としました。**
Kimigayo は独自のパッケージマネージャを作りません（2026-10-11 決定）。

- `SPECIFICATION.md` の「Phase 2: パッケージシステム」（パッケージ
  マネージャの設計・実装・リポジトリシステム）を取り下げ
- 同「パッケージセキュリティ」の Ed25519 / GPG 署名検証を削除。
  パッケージという配布単位が無いので、検証する対象が存在しません。
  実際にやっている**上流 tarball のチェックサム検証**と
  **リリース資産の `SHA256SUMS` / `SHA512SUMS`** に差し替えました
- 同「独自のパッケージマネージャによる高速化」「東アジア圏の
  ミラーサーバー最適化」を削除（どちらも存在しません）

**Docker Hub の説明文にあった、実装していない機能の宣伝も消しました。**

| 消した記述 | 実態 |
| --- | --- |
| seccomp-BPF をデフォルトで有効化 | 成果物は rootfs だけでカーネルを含まない。seccomp を適用するのはホストの `docker run` 側 |
| 再現可能ビルド（ビット同一） | `REPRODUCIBLE_BUILD=yes` のときだけ効くフラグを、どこも設定していない |
| イメージ署名（Docker Content Trust / Cosign） | `release.yml` に署名工程が無い |
| Trivy でイメージを自動スキャン | パッケージデータベースが無いため対象を1つも識別できない |
| Minimal は「カーネル + musl libc + BusyBox」 | カーネルはイメージに入らない |
| `stable` / `edge` タグ | 生成箇所が無く、1度も公開されていない |

その他:

- README が「Docker Hub 上のイメージは v2.0.1 のまま」と書いたままでした
- README の目標値が `SPECIFICATION.md` 8.3 と食い違っていました
  （仕様は Minimal 5MB / Standard 15MB / Extended 50MB）
- `SPECIFICATION.md` 9.2 が ISO イメージを作ると書いていました
  （ベアメタルは対象外。`iso` ターゲットも削除しました）
- `make kernel` をホストのコマンドとして書いていました。正しくは
  `docker compose run --rm kimigayo-build make kernel` です

### ⬆️ v3.0.0 からの移行

**`dpkg` / `rpm` を使っていた場合は動かなくなります。**
Kimigayo は設計上パッケージマネージャーを持たないので、必要なものは
ビルド時にマルチステージビルドで入れてください。

```dockerfile
FROM alpine:3.24 AS builder
RUN apk add --no-cache nginx

FROM ishinokazuki/kimigayo-os:3.0.1
COPY --from=builder /usr/sbin/nginx /usr/sbin/nginx
```

それ以外は `docker pull` し直すだけです。外した init スクリプト 9 本は
いずれも呼ぶバイナリがイメージに無いため、動作していた可能性はありません。

---

## バージョン 3.0.0 "Himawari" (向日葵) - 2026-10-10

### 🌻 このバージョンで初めて Init が動きます

**v0.1.0 から v2.0.1 までの公開イメージは、Init が1つもサービスを
起動できませんでした。** OpenRC のバイナリも musl の `libc.so` も `/tmp` も
入っておらず、BusyBox が static-pie で動くため `/bin/sh` だけは動いて
smoke テストに通っていた、という状態でした。

v3.0.0 は **6 バリアント（3 variant × 2 arch）すべてを実際に起動して
27 項目の検査**に通しています。

```console
$ docker run --rm ishinokazuki/kimigayo-os:3.0.0 /bin/sh -c '/sbin/openrc boot'
 * Caching service dependencies ... [ ok ]
mtab     | * Updating /etc/mtab ... [ ok ]
loopback | * Bringing up network interface lo ... [ ok ]
sysctl   | * Configuring kernel parameters ... [ ok ]
bootmisc | * Creating user login records ... [ ok ]
```

### 📦 サイズ（2026-10-10 実測、macOS / Apple Silicon ホスト）

| バリアント | x86_64 | arm64 | BusyBox アプレット |
| --- | --- | --- | --- |
| Minimal | **2.65MB** | 3.02MB | 370 |
| Standard | **2.78MB** | 3.16MB | 403 |
| Extended | **2.81MB** | 3.20MB | 413 |

同じホスト・同じ platform で測った比較対象:

| イメージ | サイズ | シェル | Init |
| --- | --- | --- | --- |
| `gcr.io/distroless/static-debian12` | 2.11MB | ❌ | ❌ |
| **Kimigayo Standard** | **2.78MB** | ✅ BusyBox | ✅ OpenRC |
| `alpine:latest` | 8.42MB | ✅ | ❌ |
| `ubuntu:24.04` | 78.2MB | ✅ | ❌ |

**シェルと Init を備えて 2.78MB。** distroless に 0.67MB 足すだけで、
`sh` と 403 個のコマンドとサービス管理が付きます。

### 🔒 セキュリティ

- **arm64 の BusyBox が PIE になりました（ASLR が有効化）。**
  これまで arm64 だけ ELF Type=EXEC で ASLR が効いていませんでした。
  x86_64 は Alpine の gcc が default-PIE なので同じ設定から PIE に
  なっており、**片方だけ弱い状態に気づけていませんでした**
- arm64 の BusyBox でスタックプロテクタ（`-fstack-protector-strong`）を
  有効化しました
- 全バリアントで BIND_NOW（完全な RELRO）を確認しています
- `/etc/sysctl.d/` のカーネルパラメータが**初めて実際に適用される**
  ようになりました（`--privileged` 付きのコンテナ、または
  `docker run --sysctl` で。非特権コンテナでは `/proc/sys` が
  read-only なのでホスト側の担当になります）

### ⬆️ 構成要素の更新（約9か月ぶん）

| | 旧 | 新 |
| --- | --- | --- |
| Linux カーネル | 6.6.11 | **6.18.55**（LTS、EOL 2028-12） |
| musl libc | 1.2.4 | **1.2.6** |
| BusyBox | 1.36.1 | **1.38.0** |
| OpenRC | 0.52.1 | **0.63.2** |
| ビルド環境 Alpine | 3.23 | **3.24**（LLVM 22） |

**カーネルは Docker イメージに入りません**（コンテナはホストの
カーネルで動きます）。`make kernel` でビルドできます。

### 🏷️ コードネームの運用開始

v3.0.0 から日本の通年の花をメジャーバージョンに割り当てます。
体系は [SPECIFICATION.md](SPECIFICATION.md)「10.3 リリース名」。

```console
$ docker run --rm ishinokazuki/kimigayo-os:3.0.0 /bin/sh -c 'cat /etc/os-release'
NAME="Kimigayo OS"
VERSION="3.0.0 (Himawari)"
PRETTY_NAME="Kimigayo OS 3.0.0 (Himawari)"
VERSION_ID="3.0.0"
VERSION_CODENAME=himawari
```

v1.0 と v2.0 はコードネームの運用開始前に公開済みのため名前を持ちません。

### ⚠️ 既知の制限

- **起動時間とメモリはリリース時点では未測定でした。** 既存の計測
  スクリプトは `docker run -d <image> sleep 5` の終了までを測っており、
  起動時間になっていませんでした。過去に公開していた 439ms / 0.2MB は
  撤回します。
  **※ 2026-10-10 中に計測方法を直し、実測しました。**
  値は版ごとに変わるので、ここには書きません。
  [README.md](README.md) の「パフォーマンス実績」節を参照してください
- **非特権コンテナでは一部のサービスが権限エラーを出します**
  （`ip: RTNETLINK answers: Operation not permitted`、
  `mount: permission denied`、`dmesg: klogctl: Operation not permitted`）。
  これは正常な挙動で、`--privileged` または必要な capability を
  付けると解消します
- **Trivy のイメージスキャンは Kimigayo に対して何も検査できません。**
  `scratch` 上の手組み rootfs でパッケージデータベースを持たないため、
  Trivy は対象を1つも識別できません（「脆弱性 0 件」ではなく
  「スキャンしていない」）。脆弱性の追跡は構成要素のバージョンを
  手で突合しています
- **組み込み・ベアメタル起動は対象外です。** 想定する使い方は
  VPS 上の Docker コンテナです

### 💥 破壊的変更

- **`latest` 系タグの中身が変わります。** 2026-10-09 の事故で
  `latest` を含む 9 タグが v0.1.1 の内容（Init なし）に差し替わって
  いました。v3.0.0 のリリースで正しい内容に戻ります
- **`/etc/os-release` の `VERSION_ID` が `0.1.0` から `3.0.0` に変わります。**
  これまで v1.0.0 / v2.0.1 のイメージも `0.1.0` と名乗っていました。
  この値でバージョンを判定している処理があれば影響します

---

## バージョン 0.1.0 - Phase 1完了 (2025-12-15)

### 🎉 初回リリース

Kimigayo OS Phase 1の開発が完了しました。Googleのdistrolessと同様の設計思想を採用した軽量・高速・セキュアなオペレーティングシステムのコアコンポーネントとインフラストラクチャが整備されました。

---

## 📦 実装された主要コンポーネント

### 1. カーネルとセキュリティ

#### Linuxカーネル設定
- ✅ セキュリティ強化設定（ASLR、DEP、PIE）
- ✅ モジュラーカーネル設定
- ✅ x86_64およびARM64アーキテクチャサポート
- ✅ カーネルパラメータの最適化

#### コンパイル時セキュリティ
- ✅ PIE (Position Independent Executables)
- ✅ Stack-smashing protection
- ✅ FORTIFY_SOURCE level 2
- ✅ RELRO (Relocation Read-Only)

#### ランタイムセキュリティ
- ✅ ASLR (Address Space Layout Randomization)
- ✅ DEP (Data Execution Prevention)
- ✅ Seccomp-BPF対応
- ✅ Namespace isolation

### 2. コアユーティリティ

#### BusyBox統合
- ✅ 必須Unixコマンドの選択と設定
- ✅ モジュラー構成（Minimal/Standard/Extended）
- ✅ サイズ最適化
- ✅ 静的リンク設定

#### musl libc
- ✅ 軽量Cライブラリの統合
- ✅ セキュリティ強化
- ✅ 静的・動的リンクサポート

### 3. Initシステム (OpenRCベース)

#### 基本機能
- ✅ システム初期化プロセス
- ✅ サービス管理機能
- ✅ 依存関係処理
- ✅ ランレベル管理

#### セキュリティ機能
- ✅ 名前空間分離
- ✅ Seccomp-BPFフィルタリング
- ✅ サービスセキュリティポリシー

#### エラーハンドリング
- ✅ サービス障害の検出と処理
- ✅ ログ記録機能
- ✅ 回復メカニズム

### 4. ビルドシステム

#### 再現可能ビルド
- ✅ ビット同一出力の保証
- ✅ SOURCE_DATE_EPOCH対応
- ✅ ビルドメタデータの記録

#### クロスコンパイル
- ✅ x86_64ターゲット
- ✅ ARM64ターゲット
- ✅ musl libcツールチェーン

#### パッケージ生成
- ✅ isn互換パッケージ生成
- ✅ アーキテクチャ固有バイナリ処理
- ✅ 暗号化検証機能

### 6. モジュラーシステム

#### カーネルモジュール
- ✅ モジュール選択システム
- ✅ 動的管理
- ✅ 設定管理インターフェース

#### サービス制御
- ✅ サービス起動制御
- ✅ 管理コマンド（rc-service, rc-update）
- ✅ 設定管理

---

## 🧪 テストカバレッジ

### プロパティテスト
- ✅ **341件成功** / 10件失敗 / 2件スキップ
- 実装された31のプロパティテスト：
  - ビルドサイズ制約
  - メモリ使用量制約
  - 必須ユーティリティ完全性
  - セキュリティ強化適用
  - ランタイムセキュリティ強制
  - パッケージ検証完全性
  - サービスセキュリティ適用
  - セキュリティアップデート優先
  - カーネルモジュール選択柔軟性
  - コンポーネント動的管理
  - 依存関係最適解決
  - サービス起動制御
  - 依存関係解決完全性
  - パッケージ整合性検証
  - アトミックアップデート操作
  - マルチアーキテクチャサポート
  - クロスアーキテクチャ機能一貫性
  - アーキテクチャ固有バイナリ処理
  - 再現可能ビルド一貫性
  - 環境独立ビルド
  - ビルド依存関係記録
  - ビルド検証機能
  - ビルドメタデータ包含
  - サービス依存関係順序
  - サービス障害処理
  - システムシャットダウン処理
  - サービス管理コマンド
  - musl libc使用
  - リンクオプションサポート
  - パッケージ互換性ラウンドトリップ
  - カーネルセキュリティ設定

### 統合テスト
- ✅ **151件成功** / 2件失敗
- エンドツーエンドテスト：
  - コンテナ環境（Docker、Kubernetes）
  - 仮想化環境（QEMU/KVM、VirtualBox）
  - ベアメタル環境（x86_64、ARM64）

### 既知の問題
- Ed25519テスト: cryptographyライブラリの依存関係問題（10件）
- ハードウェア検出テスト: モック制限によるmacOS環境での失敗（2件）

---

## 📊 パフォーマンス目標

### 設計目標

| 項目 | 目標値 | ステータス |
|------|--------|----------|
| ベースイメージサイズ (Minimal) | < 5MB | ✅ テスト実装済み |
| ベースイメージサイズ (Standard) | < 15MB | ✅ テスト実装済み |
| ベースイメージサイズ (Extended) | < 50MB | ✅ テスト実装済み |
| 起動時間 | < 10秒 | ✅ 測定ツール実装済み |
| 最小RAM要件 | 128MB | ✅ テスト実装済み |
| 最小ストレージ要件 | 512MB | ✅ 検証済み |

### 実装されたパフォーマンステスト
- ✅ 起動時間の測定と最適化
- ✅ メモリ使用量の実測と最適化
- ✅ ベースイメージサイズの検証

---

## 📚 ドキュメント

### ユーザー向け
- ✅ [インストールガイド](docs/user/INSTALLATION.md) - Docker、仮想化環境、ベアメタルへのインストール
- ✅ [クイックスタートガイド](docs/user/QUICKSTART.md) - 基本的な操作と使い方
- ✅ [システム設定ガイド](docs/user/CONFIGURATION.md) - ネットワーク、サービス、セキュリティ設定

### 開発者向け
- ✅ [ビルドガイド](docs/developer/BUILD_GUIDE.md) - ビルド手順とカスタマイズ
- ✅ [アーキテクチャドキュメント](docs/developer/ARCHITECTURE.md) - システム設計
- ✅ [APIリファレンス](docs/developer/API_REFERENCE.md) - Init、カーネルAPI
- ✅ [開発ガイド](DEVELOPMENT.md) - 開発環境セットアップ
- ✅ [コントリビューションガイド](CONTRIBUTING.md) - 貢献方法

### セキュリティ
- ✅ [セキュリティポリシー](docs/security/SECURITY_POLICY.md) - セキュリティ方針と脆弱性報告
- ✅ [セキュリティガイド](docs/security/SECURITY_GUIDE.md) - セキュリティ機能と運用
- ✅ [脆弱性報告手順](docs/security/VULNERABILITY_REPORTING.md) - 責任ある開示プロセス
- ✅ [セキュリティ強化ガイド](docs/security/HARDENING_GUIDE.md) - 3段階の強化設定

---

## 🎯 アーキテクチャサポート

### 現在サポート
- ✅ x86_64 (AMD64)
- ✅ ARM64 (AArch64)

### 将来サポート予定
- ⏳ RISC-V
- ⏳ ARM32

---

## 🔒 セキュリティ機能

### 多層防御（Defense in Depth）
- アプリケーション層: Seccomp-BPF、Namespace isolation
- システム層: iptables、SSH強化
- ランタイム層: ASLR、DEP、Stack canaries
- コンパイル層: PIE、RELRO、FORTIFY_SOURCE
- カーネル層: Kernel hardening、Seccomp-BPF

---

## 🔄 次のフェーズ（Phase 2以降）

### 計画中の機能

#### カーネルとブートローダー
- Linuxカーネルの実際のビルド
- ブートローダー（GRUB）の統合
- カーネルモジュールの動的ロード

#### イメージ生成
- Minimal/Standard/Extendedイメージの実際の生成
- ブータブルISOイメージの作成
- Dockerイメージの最適化

#### GUI機能（オプション）
- Waylandサポート
- 軽量デスクトップ環境
- GUIモジュールの追加

#### 追加セキュリティ
- SELinux/AppArmorサポート
- Secure Boot対応
- TPM 2.0サポート

---

## 🙏 謝辞

Kimigayo OSは以下のプロジェクトの成果を活用しています：

- [Google Distroless](https://github.com/GoogleContainerTools/distroless) - 設計思想とインスピレーション
- [Alpine Linux](https://alpinelinux.org/) - 参考実装とベストプラクティス
- [musl libc](https://musl.libc.org/) - 軽量なCライブラリ
- [BusyBox](https://busybox.net/) - Unixユーティリティ
- [OpenRC](https://github.com/OpenRC/openrc) - Initシステム
- [Hypothesis](https://hypothesis.readthedocs.io/) - プロパティベーステスト
- Linux Kernelコミュニティ

---

## 📝 既知の制限事項

### Phase 1の制限
- 実際のOSイメージはまだ生成されていません（インフラストラクチャのみ）
- GUIサポートなし
- 一部のテストで環境依存の問題

### 推奨事項
- 本番環境での使用は次のフェーズ完了後を推奨
- 現在は開発環境とテスト環境での使用のみ
- フィードバックとコントリビューションを歓迎

---

## 🐛 バグ報告とフィードバック

### 報告方法
- **GitHub Issues**: https://github.com/Kazuki-0731/Kimigayo/issues
- **セキュリティ脆弱性**: security@kimigayo-os.org（PGP推奨）
- **一般的な質問**: GitHub Discussions

### コントリビューション
プルリクエスト、バグ報告、機能提案を歓迎します！
詳細は [CONTRIBUTING.md](CONTRIBUTING.md) を参照してください。

---

## 📅 リリース履歴

### v0.1.0 (2025-12-15) - Phase 1完了
- 初回リリース
- コアインフラストラクチャの完成
- 31のプロパティテスト実装
- 包括的なドキュメント整備

---

## 🔗 リンク

- **公式サイト**: https://kimigayo-os.org（予定）
- **GitHubリポジトリ**: https://github.com/Kazuki-0731/Kimigayo
- **ドキュメント**: https://docs.kimigayo-os.org（予定）
- **パッケージリポジトリ**: https://packages.kimigayo-os.org（予定）

---

**Made with ❤️ by the Kimigayo OS Team**

*Kimigayo OS - 軽量・高速・セキュアなオペレーティングシステム*
