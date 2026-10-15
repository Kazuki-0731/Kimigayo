# Kimigayo OS 設計書

## 1. プロジェクト概要

Kimigayo OSは、Googleのdistrolessと Alpine Linux の設計思想を組み合わせた、軽量・セキュアなコンテナ向けオペレーティングシステムです。パッケージマネージャーを意図的に排除して不変インフラを徹底し、攻撃面とイメージサイズを小さく保ちながら、シェルとユーティリティでコンテナの中を確かめられる実用性を残します。

## 2. 設計思想

### 2.1 コアプリンシプル
- **軽量性（Lightweight）**: 最小限のフットプリント（目標はバリアントごとに設定。→ 8.3）
- **不変性（Immutability）**: パッケージマネージャー排除による不変インフラの実現
- **セキュリティ（Security）**: 最小攻撃面を実現するセキュアバイデフォルトの設計
- **小ささ（Footprint）**: イメージサイズと常駐メモリを小さく保つ（起動時間はほぼ Docker のコンテナ生成で決まり、イメージによる差は出ない。「軽いから起動が速い」とは言わない）
- **予測可能性（Predictability）**: ビルド時に全てが決定される予測可能な動作
- **デバッグ性（Debuggability）**: distrolessと異なり、シェルとユーティリティを含む
  - BusyBoxによる基本的なUnixコマンド
  - 本番環境でのトラブルシューティングが容易
  - コンテナ内でのデバッグ作業が可能

### 2.2 Distroless的アプローチの採用
- パッケージマネージャーの意図的な排除
- ランタイムでの変更を許さない不変インフラ
- マルチステージビルドによる依存関係管理
- 最小攻撃面によるセキュリティ強化
- コンテナファーストの思想

## 3. 主要コンポーネント

### 3.1 カーネル
- **種別**: Linuxカーネル
- **構成**: モノリシックカーネルから必要なモジュールのみを選択
- **セキュリティ**: Kernel hardening（ASLR, DEP, etc.）
- **成果物には含まれない**: Docker イメージは rootfs だけを詰めたもので、
  コンテナはホストのカーネルで動く。カーネルの config とビルドは、
  ベアメタルや QEMU を手元で試すために維持している（→ 9.2）

### 3.2 Cライブラリ
- **採用**: musl libc（Alpineと同様）
- **理由**: 軽量でシンプル、Alpine での実績、静的リンクと動的リンクの両方に対応（v3.0.2 から BusyBox と OpenRC は同じ `libc.so` に動的リンクする）

### 3.3 コアユーティリティ
- **採用**: BusyBox
- **理由**: 単一バイナリで多数のUnixコマンドを提供

### 3.4 initシステム
- **採用**: OpenRC
- **理由**: systemdより軽量でシンプル

### 3.5 パッケージマネージャ
- **設計方針**: パッケージマネージャーを意図的に排除（distroless的アプローチ）
- **理由**:
  - 最小攻撃面の実現
  - 不変インフラの徹底
  - マルチステージビルドでの利用を推奨
- **実装**: BusyBox の `dpkg` / `dpkg-deb` / `rpm` アプレットも無効にする。
  **BusyBox の既定は有効**（`archival/Config.in` が `default y`）なので、
  `src/busybox/config/*.config` に `CONFIG_DPKG=n` 等を明示する。
  書かないと `make oldconfig` が既定値で有効化する
- **検査**: `scripts/verify-image.sh` が成果物にパッケージマネージャーが
  無いことを確かめる（v3.0.0 までのイメージには `dpkg` が入っていた）
- **独自のパッケージマネージャは作らない**（2026-10-11 決定）。
  パッケージという単位を持たないことが 2.2 の前提であり、
  自作しても不変インフラと両立しない

## 4. アーキテクチャ

### 4.1 システム構成

```
┌─────────────────────────────────────────┐
│         User Applications               │
├─────────────────────────────────────────┤
│    Core Utilities (BusyBox)             │
├─────────────────────────────────────────┤
│    Init System (OpenRC)                 │
├─────────────────────────────────────────┤
│    C Library (musl libc)                │
├─────────────────────────────────────────┤
│    Linux Kernel (hardened)              │
├─────────────────────────────────────────┤
│    Hardware                             │
└─────────────────────────────────────────┘
```

**下2層（カーネル・ハードウェア）は Kimigayo の成果物ではない。**
Docker イメージに入るのは BusyBox / OpenRC / musl libc までで、
カーネルはホストのものを使う（→ 3.1・9.2）。

### 4.2 ディレクトリ構造

```
/
├── bin/          # 基本コマンド（BusyBox）
├── dev/          # デバイスファイル
├── etc/          # 設定ファイル
├── home/         # ユーザーディレクトリ
├── lib/          # 共有ライブラリ
├── media/        # リムーバブルメディアのマウントポイント
├── mnt/          # 一時マウントポイント
├── opt/          # オプションソフトウェア
├── proc/         # プロセス情報
├── root/         # rootユーザーのホーム
├── run/          # ランタイムデータ
├── sbin/         # システム管理コマンド
├── srv/          # サービスデータ
├── sys/          # システム情報
├── tmp/          # 一時ファイル
├── usr/          # ユーザープログラム
└── var/          # 可変データ
```

## 5. セキュリティ仕様

### 5.1 コンパイル時のセキュリティ
- PIE (Position Independent Executables) — 全 ELF（`scripts/verify-image.sh` が検査）
- Full RELRO (RELRO + BIND_NOW) — 全 ELF（同上）
- Stack-smashing protection — 全構成要素を `-fstack-protector-strong` でビルドする
  （`scripts/verify-image.sh` が検査）。**v3.0.2 の arm64 の OpenRC には付いていない**
  （`scripts/build-openrc.sh` が arm64 だけ外していた。v3.1.0 で修正）
- FORTIFY_SOURCE — `-D_FORTIFY_SOURCE=2`（Alpine の `fortify-headers` 経由。musl 自身は
  実装しない）。**v3.0.2 の arm64 には効いていない**（v3.1.0 で修正。
  `scripts/verify-image.sh` が BusyBox で検査する）

### 5.2 ランタイムセキュリティ

**イメージ側が用意するもの**

- ASLR が効く形のバイナリ（全実行ファイルを PIE でビルドする。
  `scripts/verify-image.sh` が ELF の型を検査する）
- DEP (Data Execution Prevention) — `-Wl,-z,noexecstack`

**ホストのコンテナランタイムが与えるもの**

- Seccomp-BPF
- Namespace isolation
- Capabilities の制限

**後者はイメージの属性ではない。** 成果物は rootfs だけでカーネルを
含まないため、seccomp プロファイルを適用するのは `docker run` 側
（`--security-opt seccomp=...`）であり、「イメージがデフォルトで
有効にしている」という書き方はできない。

### 5.3 完全性の検証

**パッケージ署名検証は対象外。** パッケージという配布単位を持たないため
（→ 3.5）、検証する対象が存在しない。代わりに次の2点で担保する。

- **上流ソースのチェックサム検証**: `scripts/download-*.sh` が
  ダウンロードした tarball の SHA256 を検証する。チェックサムは
  上流の公開値と突合して登録する（musl と OpenRC は公式の SHA256 一覧が
  無いため Alpine aports の `sha512sums` と突合する）
- **リリース資産のハッシュ配布**: `release.yml` が `SHA256SUMS` と
  `SHA512SUMS` を GitHub Release に添付する

**公開イメージは v3.0.2 から Cosign でキーレス署名する**（`release.yml` の `sign`
ジョブ。検証には cosign v3 以上が要る）。SBOM（CycloneDX）は GitHub Release に
添付する（イメージへの attestation ではない）。Docker Content Trust は使わない。

## 6. ターゲット環境

### 6.1 コンテナ環境（主要ターゲット）
- Docker
- Kubernetes
- Podman

Kimigayo OSはDockerイメージとして実行されることを前提に設計されており、コンテナ環境での利用を最優先としています。
想定する配置先は VPS 上の Docker コンテナ（クラウドのマネージドなコンテナサービスでも使える）で、
Web アプリケーションやバッチ処理を載せる用途です。

### 6.2 対象外

- **ベアメタル起動・組み込み**（2026-10-10 決定）。成果物は rootfs だけの
  Docker イメージであり、ISO イメージも作らない（→ 9.2）
- **ランタイムでのソフトウェア追加**。パッケージマネージャーを持たない
  （→ 3.5）ので、必要なものはビルド時に入れる

## 7. 開発ロードマップ

### 完了

- [x] ビルドシステムの構築（GNU Make + shell scripts、Docker ビルド環境）
- [x] musl libc の統合
- [x] BusyBox の統合（バリアントごとの config）
- [x] init システムの実装（OpenRC）
- [x] カーネル設定とビルド（手元と手動 CI 専用。成果物には含まない → 3.1）
- [x] 3 バリアント × 2 アーキテクチャのビルドと公開
- [x] 成果物の検査（`scripts/verify-image.sh`）
- [x] テスト（`tests/unit` の pytest と `tests/integration` のシェル）
- [x] ドキュメント整備

### 残っていること

- [ ] パフォーマンスチューニング
- [ ] セキュリティ監査
- [ ] システム管理ツール・ネットワークツールの拡充
- [ ] RISC-V / ARM32 対応（→ 8.2）

### 取り下げた計画

**パッケージシステム（独自パッケージマネージャ・リポジトリ・ベース
パッケージ）は作らない**（2026-10-11 決定）。当初ロードマップに
「Phase 2: パッケージシステム」として載せていたが、2.2 の
distroless 的アプローチと両立しないため取り下げた。

## 8. 技術仕様

### 8.1 システム要件
- ホスト: Docker が動く Linux（x86_64 / ARM64）。カーネルはホストのものを使う
- イメージ自体: 2.3〜3.1MB（バリアント × アーキテクチャ）、常駐メモリは 300KB 程度（v3.1.0 の実測は [README.md](README.md) の「パフォーマンス実績」。サイズの目標は §8.3）
- 必要な RAM・ストレージは、載せるアプリケーションで決まる

### 8.2 サポートアーキテクチャ
- x86_64 (AMD64)
- ARM64 (AArch64)
- 将来的に: RISC-V, ARM32

### 8.3 ベースイメージサイズ目標
- Minimal: 5MB以下
- Standard: 15MB以下
- Extended: 50MB以下

## 9. ビルドシステム

### 9.1 ビルドツール
- ビルドシステム: GNU Make + shell scripts
- クロスコンパイル対応
- バージョンの固定（[versions.mk](versions.mk) が単一の真実の源）

**再現可能ビルド**: `build-system/Makefile` が `REPRODUCIBLE_BUILD ?= yes` と
`SOURCE_DATE_EPOCH` を設定し、`scripts/build-{musl,busybox,openrc}.sh` が
prefix-map を付ける（`config.mk` はどこからも include されていないので、
そちらの記述は効いていない）。**rootfs の tarball は 2026-10-12 にビット同一を
確認した**（同じコミット 46b05da を CI と Manual Build で別々にビルドし、
standard / x86_64 の 1 組で SHA-256 が一致）。**Docker イメージの digest は
確かめていない。**

### 9.2 ビルドプロセス
1. musl libcのビルド
2. BusyBoxのビルド
3. initシステムのビルド
4. ルートファイルシステムの構築
5. コンテナイメージ（rootfs の tarball と Docker イメージ）の生成

**ISO イメージは作らない。** ISO は CD/USB から起動してマシンへ
直接インストールするための形式で、ベアメタル起動を前提とする。
Kimigayo の想定は VPS やクラウド上の Docker コンテナであり、
ベアメタル・組み込みは対象外（2026-10-10 決定）。
`make` に `iso` ターゲットは存在しない。

**成果物を作るのにカーネルのビルドは要らない。** 成果物の Docker
イメージは rootfs だけを詰めたもので、コンテナはホストのカーネルで
動く。ただしビルドコンテナ内の `make build` はカーネルも作る
（`build-system/Makefile` の `build: musl kernel busybox init rootfs`）。
カーネル抜きは `make build-no-kernel` で、CI はこちらを使う。
カーネルだけ作りたいときは
`docker compose run --rm kimigayo-build make kernel` で作れるが
（`kernel` ターゲットはビルドコンテナ内の `build-system/Makefile` にある。
ホストの `Makefile` には無い）、CI では `manual-build.yml` を
`build_kernel=true` で回したとき以外はビルドしない
（→ [CLAUDE.md](CLAUDE.md)「カーネルは CI で作らない」）。

## 10. 命名規則とブランディング

### 10.1 プロジェクト名
- **Kimigayo OS**: メインプロジェクト名
- **Kimigayo**: 短縮形

### 10.2 バージョニング
- セマンティックバージョニング（例: 1.0.0）
- メジャー.マイナー.パッチ

### 10.3 リリース名（コードネーム）

**日本の通年の花を 12 本で循環させ、メジャーバージョンに割り当てる。**

Alpine が月の名前を使うのと同じ発想で、日本の季節と自然をテーマにする。
Ubuntu が `Warty` から `Yakkety` まで一巡したあと `Artful` で A に戻ったのと
同じく、**12 本を使い切ったら先頭に戻る**（v13.0 は再び Sakura）。

| メジャー | コードネーム | 花 | 象徴・技術的連想 |
| --- | --- | --- | --- |
| v1.0 | （命名前） | — | コードネームの運用開始前に公開 |
| v2.0 | （命名前） | — | 同上 |
| **v3.0** | **Himawari** | 向日葵 | 太陽に向かう成長 |
| v4.0 | Kiku | 菊 | 長寿・高潔・安定性 |
| v5.0 | Momiji | 紅葉 | 成熟・変革 |
| v6.0 | Ume | 梅 | 先駆性・堅牢性 |
| v7.0 | Fuji | 藤 | 優雅・拡張性 |
| v8.0 | Asagao | 朝顔 | 朝の始まり・清々しさ |
| v9.0 | Tsubaki | 椿 | 常緑・常時稼働 |
| v10.0 | Satsuki | 皐月 | 軽量・精密設計 |
| v11.0 | Higanbana | 彼岸花 | 変革・リニューアル |
| v12.0 | Sazanka | 山茶花 | 厳しい環境での信頼性 |
| v13.0 | Sakura | 桜 | 新しい始まり（1周目に戻る） |
| v14.0 | Ajisai | 紫陽花 | 適応性・柔軟性 |

- **v1.0 / v2.0 には後付けしない**（2026-10-10 に決定）。
  名前を持たずに公開済みなので、事実に合わせる
- **コードネームはメジャーバージョンに付く。** パッチ・マイナーでは変わらない
  （3.0.0 も 3.1.4 も "Himawari"）
- **表に版を書き足す運用にしない。**
  [scripts/get-codename.sh](scripts/get-codename.sh) がメジャー番号から
  導出する。版ごとの表にすると更新を忘れる

#### どこに出るか

| 置き場 | 形 |
| --- | --- |
| `/etc/os-release` | `VERSION_CODENAME=himawari`（os-release の標準フィールド。Debian / Ubuntu と同じ） |
| `/etc/os-release` | `VERSION="3.0.0 (Himawari)"` / `PRETTY_NAME="Kimigayo OS 3.0.0 (Himawari)"` |
| `/etc/motd` | `Kimigayo OS v3.0.0 "Himawari"` |
| `/.kimigayo-build-info` | `CODENAME=Himawari` |
| `CHANGELOG.md` / `RELEASE_NOTES.md` | 見出しに併記 |

**版とコードネームは直書きしない。** 版は `git describe`
（[scripts/get-version.sh](scripts/get-version.sh)）、コードネームは
[scripts/get-codename.sh](scripts/get-codename.sh) から取る。
2026-10-10 まで `/etc/os-release`・`/etc/motd`・`/.kimigayo-build-info` の
3 箇所に `0.1.0` が直書きされており、**v1.0.0 と v2.0.1 を公開したあとの
イメージも 0.1.0 と名乗っていた**。

## 11. コミュニティとライセンス

### 11.1 ライセンス
- 各構成要素は元のライセンスに従う（BusyBox: GPL-2.0-only / musl libc: MIT / OpenRC: BSD-2-Clause /
  OpenRC に静的リンクした libcap: BSD-3-Clause。イメージに含まれない Linux カーネルは GPL-2.0-only）
- イメージは条文を `/usr/share/licenses/` に持つ（`verify-image.sh` が検査）。
  リリースは対応するソースを GitHub Release に添付し、集められなければ公開しない
- Kimigayo 自身のビルドシステム・ドキュメント・テスト: MIT（→ [LICENSE](LICENSE)）

### 11.2 開発モデル
- オープンソース開発
- GitHubでのコード管理
- 現在はメンテナー 1 人で開発（Issue・Pull Request は歓迎）

## 12. 差別化ポイント

### 12.1 Alpine Linuxとの違い
- **パッケージマネージャーを持たない**（Alpine は apk を含む）
- 用途別に 3 バリアントを用意（minimal / standard / extended）
- より日本語ドキュメントの充実
- モダンなツールチェインの積極採用（clang / lld によるクロスビルド）

### 12.2 他のディストリビューションとの違い
- シェルと Init を備えたうえで、数 MB のイメージサイズ
- コンテナ環境での最適化
- セキュリティファーストの設計
- シンプルで理解しやすいシステム構成

## 13. 今後の展望

- クラウドネイティブ環境での最適化
- Kubernetesとの統合強化
- マイクロサービスアーキテクチャへの最適化
- セキュリティ認証の取得
