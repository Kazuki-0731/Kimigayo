# Kimigayo OS

<div align="center">

**軽量・高速・セキュアなオペレーティングシステム**

[![Build Status](https://github.com/Kazuki-0731/Kimigayo/workflows/Kimigayo%20OS%20Build/badge.svg)](https://github.com/Kazuki-0731/Kimigayo/actions)
[![License: GPL-2.0](https://img.shields.io/badge/License-GPL%202.0-blue.svg)](https://www.gnu.org/licenses/gpl-2.0)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

[English](#english) | [日本語](#japanese)

</div>

---

## <a name="japanese"></a>🇯🇵 日本語

### 概要

Kimigayo OSは、Alpine Linuxの設計思想を受け継いだ軽量・高速・セキュアなオペレーティングシステムです。最小限のリソースで動作し、コンテナ環境、組み込みデバイス、サーバー環境などで高いパフォーマンスを発揮することを目指します。

### ✨ 主な特徴

- 🪶 **軽量性**: ベースイメージ5MB以下の極小フットプリント
- ⚡ **高速性**: 10秒以下での起動時間、低メモリ消費（128MB最小要件）
- 🔒 **セキュリティ**: セキュアバイデフォルトの設計、コンパイル時・実行時の包括的なセキュリティ強化
- 🧩 **モジュラー性**: 必要な機能のみを選択可能、GUIモジュールの追加も可能
- 🔄 **再現可能ビルド**: ビット同一の出力を保証する再現可能なビルドシステム
- 🌐 **マルチアーキテクチャ**: x86_64とARM64をサポート（将来的にRISC-Vにも対応予定）

### 🎯 設計目標

| 項目 | 目標値 |
|------|--------|
| ベースイメージサイズ | < 5MB (Minimal) |
| 起動時間 | < 10秒 |
| 最小RAM要件 | 128MB |
| 最小ストレージ要件 | 512MB |

### 🏗️ アーキテクチャ

```
┌─────────────────────────────────────────┐
│         ユーザーアプリケーション          │
├─────────────────────────────────────────┤
│    パッケージマネージャ (isn)            │
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

- **カーネル**: セキュリティ強化されたLinuxカーネル（ASLR, DEP, PIE等）
- **Cライブラリ**: musl libc（軽量・高速・セキュア）
- **コアユーティリティ**: BusyBox（単一バイナリで多数のUnixコマンドを提供）
- **Initシステム**: OpenRCベース（systemdより軽量でシンプル）
- **パッケージマネージャ**: isn（高速・セキュア・アトミック操作）

### 🚀 クイックスタート

#### 前提条件

- Docker & Docker Compose
- Git
- 最低2GB RAM（推奨4GB）

#### ビルド手順

```bash
# リポジトリをクローン
git clone https://github.com/Kazuki-0731/Kimigayo.git
cd Kimigayo

# Docker環境を構築
docker-compose build

# ビルドシステムをテスト
docker-compose run --rm kimigayo-build make info

# OSをビルド（Phase 2以降で実装予定）
docker-compose run --rm kimigayo-build make build
```

#### テスト実行

```bash
# 全テスト実行
docker-compose run --rm kimigayo-build make test

# プロパティテストのみ
docker-compose run --rm kimigayo-build pytest tests/property/ -v

# 単体テストのみ
docker-compose run --rm kimigayo-build pytest tests/unit/ -v
```

### 📦 イメージバリエーション

| イメージタイプ | サイズ | 用途 |
|---------------|--------|------|
| Minimal | < 5MB | コンテナ、最小限の環境 |
| Standard | < 15MB | 一般的なサーバー環境 |
| Extended | < 50MB | 開発環境、豊富なツール |

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

#### パッケージ
- GPG署名検証
- SHA-256ハッシュ検証
- セキュリティアップデートの優先配信

### 🎯 ターゲット環境

- **コンテナ環境**: Docker, Kubernetes, Podman
- **仮想化環境**: KVM, VirtualBox, VMware
- **ベアメタル**: サーバー, 組み込みデバイス, IoTデバイス

### 🗺️ ロードマップ

現在の進捗: **Phase 1完了** ✅

- [x] **Phase 0**: 開発環境のセットアップ（完了）
- [x] **Phase 1**: プロジェクト構造とコアインターフェース（完了）
- [ ] **Phase 2**: カーネル設定とビルドシステム（進行中）
- [ ] **Phase 3**: コアユーティリティとライブラリの統合
- [ ] **Phase 4**: Initシステムの実装
- [ ] **Phase 5**: パッケージマネージャの設計と実装
- [ ] **Phase 6**: システム最適化とテスト
- [ ] **Phase 7**: ベータリリース

詳細は [実装計画](.kiro/specs/kimigayo-os-core/tasks.md) を参照してください。

### 🤝 コントリビューション

Kimigayo OSはオープンソースプロジェクトです。バグ報告、機能リクエスト、プルリクエストを歓迎します！

- [貢献ガイド](CONTRIBUTING.md)
- [開発ガイド](DEVELOPMENT.md)
- [行動規範](CODE_OF_CONDUCT.md)（作成予定）

#### コントリビューションの種類

- 🐛 バグ修正
- ✨ 新機能の追加
- 📝 ドキュメントの改善
- 🌐 翻訳（他言語への対応）
- 🧪 テストの追加
- 🔒 セキュリティ監査

### 📄 ライセンス

- **OSコア**: GPLv2（Linuxカーネルに準拠）
- **ユーザーランドツール**: MIT/BSD/GPL（各コンポーネントによる）

詳細は [LICENSE](LICENSE)（作成予定）を参照してください。

### 🌟 Alpine Linuxとの違い

- より充実した日本語ドキュメント
- 東アジア圏のミラーサーバー最適化
- 独自のパッケージマネージャによる高速化
- モダンなツールチェインの積極採用
- プロパティベーステストによる品質保証

### 📚 ドキュメント

- [仕様書](SPECIFICATION.md)
- [設計書](.kiro/specs/kimigayo-os-core/design.md)
- [実装計画](.kiro/specs/kimigayo-os-core/tasks.md)
- [開発ガイド](DEVELOPMENT.md)
- [貢献ガイド](CONTRIBUTING.md)

### 💬 コミュニティ

- **GitHub Issues**: バグ報告、機能リクエスト
- **GitHub Discussions**: 質問、アイデア共有
- **Wiki**: 詳細なドキュメント（作成予定）

### 🙏 謝辞

Kimigayo OSは以下のプロジェクトにインスパイアされ、技術的な基盤を提供していただいています：

- [Alpine Linux](https://alpinelinux.org/) - 設計思想とインスピレーション
- [musl libc](https://musl.libc.org/) - 軽量なCライブラリ
- [BusyBox](https://busybox.net/) - Unixユーティリティ
- [OpenRC](https://github.com/OpenRC/openrc) - Initシステム

---

## <a name="english"></a>🇬🇧 English

### Overview

Kimigayo OS is a lightweight, fast, and secure operating system that inherits the design philosophy of Alpine Linux. It aims to operate with minimal resources and deliver high performance in container environments, embedded devices, and server environments.

### ✨ Key Features

- 🪶 **Lightweight**: Base image under 5MB
- ⚡ **Fast**: Boot time under 10 seconds, low memory consumption (128MB minimum)
- 🔒 **Secure**: Secure-by-default design with comprehensive compile-time and runtime hardening
- 🧩 **Modular**: Select only needed features, GUI modules can be added
- 🔄 **Reproducible Builds**: Guaranteed bit-identical build outputs
- 🌐 **Multi-Architecture**: Supports x86_64 and ARM64 (RISC-V planned)

### 🎯 Design Goals

| Item | Target |
|------|--------|
| Base Image Size | < 5MB (Minimal) |
| Boot Time | < 10 seconds |
| Minimum RAM | 128MB |
| Minimum Storage | 512MB |

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

- **OS Core**: GPLv2 (following Linux kernel)
- **Userland Tools**: MIT/BSD/GPL (depending on components)

### 📚 Documentation

- [Specification](SPECIFICATION.md)
- [Design Document](.kiro/specs/kimigayo-os-core/design.md)
- [Development Guide](DEVELOPMENT.md)

---

<div align="center">

**Made with ❤️ by the Kimigayo OS Team**

[⭐ Star us on GitHub](https://github.com/Kazuki-0731/Kimigayo) | [🐛 Report Issues](https://github.com/Kazuki-0731/Kimigayo/issues) | [💬 Join Discussion](https://github.com/Kazuki-0731/Kimigayo/discussions)

</div>
