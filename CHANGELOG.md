# Changelog

All notable changes to Kimigayo OS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [Unreleased]

### Changed

- **構成要素をまとめて最新化**（約9か月ぶんの滞留を解消）
  - Linux カーネル 6.6.11 → **6.18.55**（LTS。EOL 2027-12 → 2028-12）
  - musl libc 1.2.4 → **1.2.6**
  - BusyBox 1.36.1 → **1.38.0**
  - OpenRC 0.52.1 → **0.63.2**
  - ビルド環境の Alpine 3.23 → **3.24**（LLVM 21 → 22）
- **バージョンを `versions.mk` に集約**（単一の真実の源）。
  以前は `config.mk`・`scripts/download-*.sh`・`scripts/build-*.sh`・
  `scripts/apply-kernel-patches.sh`・`src/kernel/build.py` の5箇所に散り、
  値も一致していなかった
- `Dockerfile` が aarch64 の `.apk` をバージョンごと URL 直打ちしていたのを
  `apk fetch` に変更（Alpine を上げるたび 404 になっていた）
- `Dockerfile` の `/usr/lib/llvm21/...` 直書きを `clang -print-resource-dir` に変更
- `Dockerfile` / `Dockerfile.runtime` / `docker-compose.yml` の Alpine 版と
  プロジェクト版を build arg 化（`ALPINE_VERSION` / `KIMIGAYO_VERSION`）
- `Dockerfile` の `LABEL version` と `org.opencontainers.image.base.name` が
  それぞれ `0.1.0` / `alpine:3.19` のまま実態とずれていたのを修正
- Python のテスト依存を `requirements-dev.txt` に1本化
  （`Dockerfile`・`Makefile`・CI がそれぞれ別に並べていた）
- 外部 GitHub Action の `@master` 参照を tag 固定
  （`trivy-action@v0.36.0`・`action-shellcheck@2.0.0`）

### Added

- **`CLAUDE.md`** — Claude Code 向けの作業ルールとプロジェクト固有の勘所
- **`versions.mk`** / `scripts/lib/versions.sh` — 構成要素のバージョンの
  単一の真実の源と、シェル側のローダ
- **`TODO.md`** / **`NEXT.md`** — 経緯・判断待ちと直近やること
- **`requirements-dev.txt`** — 開発・テスト用の Python 依存
- **`src/kernel/patches/README.md`** — 各パッチが存在する理由と、
  版上げ時に当たらなくなったパッケージの扱い
- カーネル tarball の SHA-256 照合（これまで計算して表示するだけだった）
- OpenRC tarball の SHA-256 照合（これまで「展開できたら OK」だった）
- `make show-version` に構成要素のバージョン表示を追加

### Fixed

- **`scripts/download-busybox.sh` がキャッシュ済み tarball を再利用すると
  必ず落ちていた** — `skip_checksum` と `github_tag_version` が
  ダウンロード分岐の中でしか定義されておらず `set -u` に殺されていた
- **`make version` が `2.0.1` ではなく `list` を返していた** —
  打ち間違いで出来たと思われる `list` タグが `git describe --tags` で
  最新タグとして拾われていた。`--match 'v[0-9]*'` で絞るようにした
- **CI のテストが絶対に落ちなかった** — `|| echo "... not ready yet"` で
  握り潰されていた（522件すべて通るのに意味を失っていた）
- **`dependency-review.yml` のバージョン報告が常に空だった** —
  存在しない `MUSL_VERSION=` を `scripts/build-rootfs.sh` から grep していた。
  ハードコードされた `OpenRC: 0.44+` / `Alpine: edge` も実態とずれていた
- **musl のチェックサム不一致が警告だけで通っていた**のを失敗させるようにした
- `scripts/download-openrc.sh` の第一 URL が全バージョンで 404 だったため
  毎回無駄な取得を試みていたのを修正
- OpenRC 0.63.2 でソース構成が変わった `src/rc/rc.c` → `src/openrc/rc.c` に追従
- `scripts/build-openrc.sh` が渡していた `-Dos=Linux` を除去
  （0.63.2 では上流から削除されており `meson setup` が失敗する）
- `scripts/apply-kernel-patches.sh` が1本も当てていないのに
  「Applied 1 patches successfully」と報告していたのを修正。
  適用／当たらなかった／プレースホルダを分けて数えるようにした
- `build-system/Makefile` の `VERSION := 0.1.0` を git タグ由来に変更

### Removed

- **カーネルパッチ3本**（`0002-disable-retpoline-realmode`・
  `0003-efi-stub-std-gnu11`・`0004-x86-boot-compressed-std-gnu11`）。
  いずれも GCC 15 で 6.6 系をビルドするための `-std=gnu11` 回避策で、
  6.18 では上流が取り込み済み
- `Dockerfile` から Rust ツールチェイン（rustup）のインストール。
  対象だった `isn` パッケージマネージャ（`src/pkg/`）は v0.1.1 で削除済みで、
  `cargo` を参照するコードもビルド経路も残っていなかった
- `config.mk` の死んでいた `ISN_VERSION`
- Git 管理下にあった `.hypothesis/` のキャッシュ59ファイルと
  `benchmark-optimized.log`（`.gitignore` に追加）

---

## [2.0.1] - 2026-01-16

ビルド成果物とリリース経路の安定化。v1.0.0 から 70 コミット。
（`v2.0.0` タグは存在せず 1.0.0 → 2.0.1 となっている）

### Fixed

- BusyBox が動的リンクされ musl ランタイム不在で起動できない問題を解消
  （ARM64 で `-nostdlib` により CRT が落ちていた。
  詳細 → [docs/troubleshooting/busybox-static-linking.md](docs/troubleshooting/busybox-static-linking.md)）
- ARM64 の compiler-rt builtins の解決（`-rtlib=compiler-rt`）
- `release.yml` の rootfs ビルドコマンドとスクリプトパスの修正

### Changed

- ベンチマーク結果と `PERFORMANCE_TUNING.md` を v2.0.1 実測値へ更新
- README に Docker Hub リンクとバッジを追加

詳細は `git log v1.0.0..v2.0.1`。

---

## [1.0.0] - 2026-01-02

初の安定版リリース。v0.1.1 から 175 コミット。

### Added

- リリースノートの自動生成（前回タグからの PR 一覧）
- Discord 通知
- マルチアーキテクチャ対応の整備（x86_64 / arm64）

### Changed

- Docker Hub のタグ命名を `{version}-{variant}-{arch}` 形式に統一
- GitHub Advanced Security 対応として各ワークフローに `permissions` を明示

### Fixed

- `/etc/shadow` のパーミッションエラー
- Release ワークフローの artifact ダウンロード範囲を `kimigayo-*` に限定

詳細は `git log v0.1.1..v1.0.0`。

---

## [0.1.1] - 2025-12-22

**設計思想を Alpine 寄りから distroless 寄りへ移行。** v0.1.0 から 17 コミット。

### Removed

- **`isn` パッケージマネージャーを完全削除。**
  パッケージマネージャーを持たないこと自体を設計の中心に据え直した

### Changed

- ビルドステップ番号の整理（`Makefile` / `build-system/Makefile`）

詳細は `git log v0.1.0..v0.1.1`。


## [0.1.0] - 2025-12-21

### Added
- rootfsサイズ最適化を実装
- 個別コンポーネントのクリーンターゲットを追加
- ビルドマイルストーン表示とOpenRC検証修正
- make cleanに詳細な進捗表示を追加
- カーネルビルドの進捗表示を改善
- Makefileのhelpを視覚的に改善
- make infoコマンドを追加
- プロジェクトrootのMakefileに`make build`を追加
- OpenRCベースのInitシステムを実装 (タスク5.1, 5.2)

### Changed
- 組み込み関連の記述を削除しコンテナ向けOSであることを明記
- Makefileを再構成してDocker管理用の簡易コマンドを追加

### Fixed
- rootfs最適化の算術式エラーを修正
- OpenRCインストール検証でlib/rcディレクトリを追加
- カーネルソース抽出の検証を強化
- カーネルパッチ検証時のパス解決を修正
- make cleanでダウンロードキャッシュを保持するように修正
- ビルドスクリプトのパス解決を修正
- カーネルソースツリーのクリーニングを追加
- カーネルビルドの対話的プロンプトを回避して進捗表示を改善
- Docker Composeにplatform: linux/amd64を追加
- Alpine Linuxのgcc向けに-m64フラグを削除
- OpenRC brandingをスペースなしの単一単語に修正
- OpenRC brandingの文字列エスケープを修正
- BusyBox設定ファイルのパス解決を修正
- Fix SIGPIPE error (141) in musl build verification
- Fix musl-gcc wrapper creation and summary errors
- Fix libc.so verification path detection
- Fix binutils tools detection for musl build
- Fix C compiler detection for x86_64 musl build
- Improve error handling in musl build script
- Fix wget timeout error in ARM64 toolchain download
- PyYAMLをDockerfileに追加してimportエラーを修正
- FilesystemManagerのパス正規化を修正
- 統合テストのAttributeErrorを修正し、Phase 1を完了
- 統合テストのインポートエラーを修正
- モックバイナリのサイズ計算エラーを修正
- test_utility_add_removeのロジックエラーを修正

### Security
- Task 28にセキュリティ監査とペネトレーションテスト項目を統合
- セキュリティドキュメントから報奨金プログラムの記載を削除
- ランタイムセキュリティ強制を実装
- パッケージセキュリティ検証機能を実装 (タスク6.4, 6.5, 6.6)
- サービスセキュリティ機能を実装 (タスク5.3, 5.4)

### Documentation
- Docker Hub README構成を改善
- Phase 8以降をDocker Hub公開向けに修正
- README.mdにトラブルシューティングセクションを追加
- README.mdのビルド手順を新しいMakefileに合わせて更新
- ビルドログ確認手順を追加
- Docker volumeの削除コマンドを修正
- Add OpenRC init scripts and service definitions
- ドキュメントから「実装予定」「計画中」の記載を削除
- README.mdの「作成予定」表記を削除
- README.mdにドキュメントセクションを拡充
- README.mdにユーザー向けドキュメントへのリンクを追加
- Ed25519署名検証機能をドキュメントに追加
- エラーハンドリングとログ機能を実装 (タスク5.5, 5.6)
- タスク2.1と2.2を完了としてマーク
- 包括的なREADME.mdを作成
- spec.mdをSPECIFICATION.mdにリネーム

### Build/CI
- ビルドシステムとプロジェクト構造を追加

