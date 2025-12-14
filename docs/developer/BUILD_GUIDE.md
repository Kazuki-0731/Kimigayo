# Kimigayo OS ビルドガイド

このガイドでは、Kimigayo OSのビルド方法とカスタマイズについて詳しく説明します。

## 目次

- [ビルド環境のセットアップ](#ビルド環境のセットアップ)
- [ビルドプロセス](#ビルドプロセス)
- [カスタムビルド](#カスタムビルド)
- [クロスコンパイル](#クロスコンパイル)
- [トラブルシューティング](#トラブルシューティング)

## ビルド環境のセットアップ

### 必要なソフトウェア

| ソフトウェア | バージョン | 目的 |
|------------|-----------|------|
| Docker | 20.10+ | ビルド環境の提供 |
| Docker Compose | 1.29+ | マルチコンテナ管理 |
| Git | 2.30+ | ソースコード管理 |
| Make | 4.3+ | ビルド自動化 |

### システム要件

- **CPU**: x86_64（クロスコンパイル用にARM64も推奨）
- **RAM**: 最低2GB、推奨4GB以上
- **ディスク**: 10GB以上の空き容量
- **OS**: Linux, macOS, Windows（WSL2）

### 初期セットアップ

```bash
# 1. リポジトリをクローン
git clone https://github.com/Kazuki-0731/Kimigayo.git
cd Kimigayo

# 2. サブモジュールの初期化（将来使用する可能性）
git submodule update --init --recursive

# 3. Docker環境を構築
docker-compose build

# 4. ビルド環境の確認
docker-compose run --rm kimigayo-build make info
```

## ビルドプロセス

### フェーズ別ビルド

Kimigayo OSは段階的なビルドプロセスを採用しています。

#### Phase 0: 開発環境のセットアップ（完了）

```bash
# Docker環境の構築
docker-compose build
```

#### Phase 1: プロジェクト構造とコアインターフェース（完了）

```bash
# テストの実行
docker-compose run --rm kimigayo-build pytest tests/ -v
```

#### Phase 2: カーネル設定とビルドシステム（実装中）

```bash
# カーネル設定の生成
docker-compose run --rm kimigayo-build make kernel-config

# カーネルのビルド
docker-compose run --rm kimigayo-build make kernel
```

#### Phase 3以降: コアユーティリティとライブラリ（計画中）

```bash
# 完全なOSイメージのビルド
docker-compose run --rm kimigayo-build make build
```

### ビルドコマンド

Makefileを使用したビルドコマンド：

```bash
# すべてのターゲットを表示
make help

# ビルド情報の表示
make info

# クリーンビルド
make clean
make build

# テストの実行
make test              # すべてのテスト
make test-unit         # 単体テスト
make test-property     # プロパティテスト
make test-integration  # 統合テスト

# 静的解析
make lint
make static-analysis

# ドキュメント生成
make docs
```

### ビルドターゲット

#### イメージバリエーション

Kimigayo OSは3つのイメージバリエーションを提供します：

```bash
# Minimalイメージ（< 5MB）
make build-minimal

# Standardイメージ（< 15MB）
make build-standard

# Extendedイメージ（< 50MB）
make build-extended
```

各イメージの内容：

| イメージ | サイズ | 含まれるコンポーネント |
|---------|--------|---------------------|
| **Minimal** | < 5MB | カーネル、BusyBox、musl libc、OpenRC（最小構成） |
| **Standard** | < 15MB | Minimal + isn、基本的なネットワークツール、SSH |
| **Extended** | < 50MB | Standard + 開発ツール、追加ユーティリティ |

#### アーキテクチャ別ビルド

```bash
# x86_64アーキテクチャ（デフォルト）
make build ARCH=x86_64

# ARM64アーキテクチャ
make build ARCH=arm64

# すべてのアーキテクチャ
make build-all-arch
```

## カスタムビルド

### カーネル設定のカスタマイズ

```bash
# カーネル設定エディタを起動
docker-compose run --rm kimigayo-build make kernel-menuconfig

# カスタム設定ファイルを使用
docker-compose run --rm kimigayo-build make kernel KERNEL_CONFIG=./custom-kernel.config
```

カーネル設定ファイルの場所：
- デフォルト設定: `src/kernel/config/default.config`
- アーキテクチャ別: `src/kernel/config/x86_64.config`

### パッケージリストのカスタマイズ

```bash
# パッケージリストを編集
vi build/packages/minimal.list
vi build/packages/standard.list
vi build/packages/extended.list
```

パッケージリストの例：
```
# build/packages/custom.list
busybox
musl
openrc
isn
vim
curl
python3
```

```bash
# カスタムパッケージリストでビルド
make build PACKAGE_LIST=custom.list
```

### ビルドオプションの設定

環境変数でビルドをカスタマイズ：

```bash
# デバッグビルド
make build BUILD_TYPE=debug

# 最適化レベルの設定
make build OPTIMIZATION=-O3

# セキュリティフラグの追加
make build CFLAGS="-fstack-protector-strong -D_FORTIFY_SOURCE=2"

# 並列ビルド
make build JOBS=4
```

### カスタムイメージの作成

```bash
# ビルド設定ファイルを作成
vi build/config/custom-image.yaml
```

```yaml
# custom-image.yaml
name: custom-kimigayo
version: 1.0.0
architecture: x86_64
base: minimal

packages:
  - busybox
  - musl
  - openrc
  - isn
  - nginx
  - postgresql

kernel:
  config: src/kernel/config/custom.config
  modules:
    - ext4
    - overlay
    - veth

security:
  enable_aslr: true
  enable_dep: true
  enable_pie: true
  fortify_source: 2

size_target: 20MB
```

```bash
# カスタム設定でビルド
make build CONFIG=build/config/custom-image.yaml
```

## クロスコンパイル

### ARM64向けクロスコンパイル

```bash
# ARM64ツールチェーンのセットアップ
docker-compose run --rm kimigayo-build make setup-cross-arm64

# ARM64イメージのビルド
docker-compose run --rm kimigayo-build make build ARCH=arm64
```

### RISC-V向けクロスコンパイル（将来対応予定）

```bash
# RISC-Vツールチェーンのセットアップ
docker-compose run --rm kimigayo-build make setup-cross-riscv

# RISC-Vイメージのビルド
docker-compose run --rm kimigayo-build make build ARCH=riscv64
```

### マルチアーキテクチャビルド

```bash
# すべてのサポートアーキテクチャでビルド
make build-multi-arch

# 出力の確認
ls output/
# kimigayo-minimal-x86_64-1.0.0.tar.gz
# kimigayo-minimal-arm64-1.0.0.tar.gz
```

## ビルド出力

### 生成されるファイル

ビルド成功後、`output/`ディレクトリに以下のファイルが生成されます：

```
output/
├── kimigayo-minimal-x86_64-1.0.0.tar.gz       # Minimalイメージ
├── kimigayo-minimal-x86_64-1.0.0.tar.gz.sha256 # SHA-256チェックサム
├── kimigayo-minimal-x86_64-1.0.0.tar.gz.sig   # Ed25519署名
├── kimigayo-standard-x86_64-1.0.0.tar.gz      # Standardイメージ
├── kimigayo-extended-x86_64-1.0.0.tar.gz      # Extendedイメージ
├── kimigayo-1.0.0.iso                         # ブータブルISO
└── build-report.json                          # ビルドレポート
```

### ビルドレポート

ビルドレポート（`build-report.json`）には以下の情報が含まれます：

```json
{
  "version": "1.0.0",
  "architecture": "x86_64",
  "build_date": "2025-12-15T12:34:56Z",
  "build_duration": "180.5s",
  "image_sizes": {
    "minimal": "4.8MB",
    "standard": "14.2MB",
    "extended": "48.9MB"
  },
  "boot_time": "8.3s",
  "memory_usage": "112MB",
  "packages": {
    "count": 127,
    "list": ["busybox", "musl", "openrc", "..."]
  },
  "tests": {
    "unit": "passed",
    "property": "passed",
    "integration": "passed"
  },
  "security": {
    "aslr": "enabled",
    "dep": "enabled",
    "pie": "enabled",
    "fortify_source": "level 2"
  }
}
```

## 再現可能ビルド

Kimigayo OSは再現可能ビルド（Reproducible Builds）をサポートしています。

### ビルドの再現性確保

```bash
# SOURCE_DATE_EPOCHを設定して再現可能ビルド
export SOURCE_DATE_EPOCH=1640000000
make build

# 2回ビルドしてハッシュを比較
make build
sha256sum output/kimigayo-minimal-x86_64-1.0.0.tar.gz > hash1.txt

make clean
make build
sha256sum output/kimigayo-minimal-x86_64-1.0.0.tar.gz > hash2.txt

# ハッシュが一致することを確認
diff hash1.txt hash2.txt
```

### ビルド環境の固定

```bash
# Dockerイメージのダイジェストを固定
docker-compose build --pull
docker images --digests | grep kimigayo-build

# Dockerfileで特定のダイジェストを使用
# FROM alpine:3.18@sha256:...
```

## ビルドのデバッグ

### 詳細ログの有効化

```bash
# Verbose モード
make build VERBOSE=1

# デバッグモード
make build DEBUG=1

# ビルドログの保存
make build 2>&1 | tee build.log
```

### ビルド中間ファイルの確認

```bash
# 中間ファイルを削除しない
make build KEEP_TEMP=1

# 中間ファイルの確認
ls build/tmp/
```

### ビルドのステップ実行

```bash
# ステップごとにビルド
make kernel
make rootfs
make bootloader
make create-image
```

## パフォーマンス最適化

### ビルド時間の短縮

```bash
# 並列ビルド（CPUコア数に応じて調整）
make build -j$(nproc)

# ccacheの使用
export USE_CCACHE=1
make build

# ビルドキャッシュの活用
docker-compose build --build-arg BUILDKIT_INLINE_CACHE=1
```

### ディスクI/Oの最適化

```bash
# tmpfsを使用してビルド速度を向上
docker-compose run --rm \
  --tmpfs /tmp:rw,size=2G \
  kimigayo-build make build
```

## トラブルシューティング

### よくあるビルドエラー

#### エラー: "Docker daemon is not running"

```bash
# Dockerデーモンを起動
sudo systemctl start docker

# または macOS/Windows
# Docker Desktopを起動
```

#### エラー: "No space left on device"

```bash
# Dockerイメージとコンテナのクリーンアップ
docker system prune -a

# ビルドキャッシュのクリーンアップ
make clean-all
```

#### エラー: "Permission denied"

```bash
# Dockerグループにユーザーを追加
sudo usermod -aG docker $USER

# ログアウト/ログインして変更を反映
```

#### エラー: "Kernel config not found"

```bash
# デフォルトカーネル設定を生成
make kernel-defconfig

# または既存の設定をコピー
cp /boot/config-$(uname -r) src/kernel/config/custom.config
```

### ビルドログの解析

```bash
# エラーのみ表示
make build 2>&1 | grep -i error

# 警告のみ表示
make build 2>&1 | grep -i warning

# 特定のコンポーネントのログ
make build 2>&1 | grep -i kernel
```

### ビルド環境のリセット

```bash
# すべてのビルド成果物を削除
make clean-all

# Docker環境を再構築
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## CI/CDとの統合

### GitHub Actions

`.github/workflows/build.yml`:

```yaml
name: Build Kimigayo OS

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2

    - name: Build Docker image
      run: docker-compose build

    - name: Build Kimigayo OS
      run: docker-compose run --rm kimigayo-build make build

    - name: Run tests
      run: docker-compose run --rm kimigayo-build make test

    - name: Upload artifacts
      uses: actions/upload-artifact@v3
      with:
        name: kimigayo-images
        path: output/*.tar.gz
```

## 参考リソース

- [DEVELOPMENT.md](../../DEVELOPMENT.md) - 開発環境の詳細
- [CONTRIBUTING.md](../../CONTRIBUTING.md) - コントリビューションガイドライン
- [Makefile](../../Makefile) - ビルドシステムの実装
- [Dockerfile](../../Dockerfile) - ビルド環境の定義

---

**質問やサポートが必要な場合**:
- GitHub Issues: https://github.com/Kazuki-0731/Kimigayo/issues
- Discussions: https://github.com/Kazuki-0731/Kimigayo/discussions
