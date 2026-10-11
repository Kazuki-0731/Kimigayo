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
# カーネルのビルド（成果物の Docker イメージには入りません）
docker compose run --rm kimigayo-build make kernel
```

> `make kernel-config` は存在しません。カーネル設定の選び方は
> `scripts/build-kernel.sh` が決めます（`src/kernel/config/<arch>.config`
> があればそれを、無ければ上流の defconfig を使う）。

#### Phase 3以降: コアユーティリティとライブラリ

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

# 静的解析（ホスト側）
make shellcheck-scan   # scripts/ と .claude/hooks/
make security-scan     # Trivy + ShellCheck
```

> `make lint` / `make static-analysis` / `make docs` は存在しません。
> 静的解析は上の2つ、カバレッジは `python3 -m pytest --cov`
> （設定は `.coveragerc`）です。

### ビルドターゲット

#### イメージバリエーション

Kimigayo OSは3つのイメージバリエーションを提供します：

**バリアントはターゲットではなく変数で選びます。**

```bash
# コンテナ内（build-system/Makefile）
docker compose run --rm kimigayo-build make build IMAGE_TYPE=minimal
docker compose run --rm kimigayo-build make build IMAGE_TYPE=standard
docker compose run --rm kimigayo-build make build IMAGE_TYPE=extended

# ホスト側（rootfs → イメージ → smoke まで通す）
make ci-build-local VARIANT=minimal ARCH=x86_64
make ci-build-all ARCH=x86_64          # 3バリアントを順に
```

既定は `VARIANT=standard` / `ARCH=x86_64`（`Makefile:211-212`）。

> `make build-minimal` / `build-standard` / `build-extended` という
> ターゲットは存在しません。

各イメージの内容：

| イメージ | サイズ | 含まれるコンポーネント |
|---------|--------|---------------------|
| **Minimal** | < 5MB | カーネル、BusyBox、musl libc、OpenRC（最小構成） |
| **Standard** | < 15MB | Minimal + 基本的なネットワークツール、SSH |
| **Extended** | < 50MB | Standard + 開発ツール、追加ユーティリティ |

#### アーキテクチャ別ビルド

```bash
# x86_64アーキテクチャ（デフォルト）
make build ARCH=x86_64

# ARM64アーキテクチャ
make build ARCH=arm64

```

> `make build-all-arch` は存在しません。両アーキテクチャを作るなら
> `ARCH` を変えて2回回すか、GitHub Actions に任せます
> （→ [CLAUDE.md](../../CLAUDE.md)「フルビルドは GitHub Actions で回す」）。

## カスタムビルド

### カーネル設定のカスタマイズ

**設定ファイルを直接編集します。**

```bash
# アーキテクチャごとの設定
vi src/kernel/config/x86_64.config
vi src/kernel/config/arm64.config     # 無ければ上流の defconfig が使われる

docker compose run --rm kimigayo-build make kernel TARGET_ARCH=x86_64
```

> `make kernel-menuconfig` は存在せず、`make kernel KERNEL_CONFIG=...` も
> 効きません（`KERNEL_CONFIG` は `scripts/build-kernel.sh` の内部変数で、
> Makefile から渡されません）。
> `menuconfig` を使いたいときはカーネルのソースツリーで直接叩きます
> （`build/kernel/linux-<version>/` で `make ARCH=... menuconfig`）。

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

**クロスツールチェーンのセットアップは不要です。** ビルド環境の
イメージ（`make docker-build`）に入っています。

```bash
docker compose run --rm kimigayo-build make build TARGET_ARCH=arm64
```

> `make setup-cross-arm64` / `setup-cross-riscv` は存在しません。
> **RISC-V は未対応**です（`SPECIFICATION.md` 8.2 の「将来的に」）。

### マルチアーキテクチャビルド

**両アーキテクチャを一度に作るターゲットはありません。**
`TARGET_ARCH` を変えて2回回します。

```bash
for a in x86_64 arm64; do
  docker compose run --rm kimigayo-build make build TARGET_ARCH=$a
done

# 出力の確認
ls output/
# kimigayo-minimal-latest-x86_64.tar.gz
# kimigayo-minimal-latest-arm64.tar.gz
```

## ビルド出力

### 生成されるファイル

ビルド成功後、`output/`ディレクトリに以下のファイルが生成されます：

```
output/
├── kimigayo-minimal-latest-x86_64.tar.gz      # Minimalイメージ
├── kimigayo-standard-latest-x86_64.tar.gz     # Standardイメージ
└── kimigayo-extended-latest-x86_64.tar.gz     # Extendedイメージ
```

ファイル名の `latest` の位置にはプロジェクトの版が入ります
（`KIMIGAYO_VERSION` 未指定なら `latest`）。

- **ISO イメージは生成されません。** ベアメタル起動は対象外です
  （→ [SPECIFICATION.md](../../SPECIFICATION.md) 6.2・9.2）
- **署名ファイルは生成されません。** リリース時に `SHA256SUMS` と
  `SHA512SUMS` が GitHub Release に添付されます
  （→ [SPECIFICATION.md](../../SPECIFICATION.md) 5.3）

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

## 再現可能ビルド（未達）

**Kimigayo は再現可能ビルドを達成していません**（2026-10-11 に確認）。

- `config.mk` に `SOURCE_DATE_EPOCH := 0` と
  `-fdebug-prefix-map` / `-fmacro-prefix-map` を入れる仕組みはある
- しかし `REPRODUCIBLE_BUILD=yes` のときだけ有効で、
  **この変数を `Makefile`・`.env.example`・compose のどこも設定していない**
- そもそも **`config.mk` はどの Makefile からも include されていない**
  （`grep -rn 'include.*config.mk' Makefile build-system/Makefile` が空）。
  実際のコンパイルフラグは `scripts/build-{musl,busybox,openrc}.sh` に
  直書きされており、そちらに再現性のための指定は無い
- **ビット同一性を検証した記録もない**

### 自分で確かめるには

```bash
docker compose run --rm kimigayo-build make build IMAGE_TYPE=minimal
cd build/rootfs && COPYFILE_DISABLE=1 tar czf /tmp/h1.tar.gz . && cd -
sha256sum /tmp/h1.tar.gz

docker compose run --rm kimigayo-build make clean build IMAGE_TYPE=minimal
cd build/rootfs && COPYFILE_DISABLE=1 tar czf /tmp/h2.tar.gz . && cd -
sha256sum /tmp/h2.tar.gz
```

**tar の時刻とファイル順でまず一致しません。**
`--sort=name --mtime=@0 --owner=0 --group=0 --numeric-owner` を
付けない限り、rootfs の中身が同じでも tarball のハッシュは変わります。

### ビルド環境の固定（これは効いている）

```bash
# ビルド環境イメージのダイジェストを確認
docker compose build --pull
docker images --digests | grep kimigayo-build
```

構成要素の版は [versions.mk](../../versions.mk) に固定し、
`scripts/download-*.sh` がチェックサムを検証します。
**「決定的な構成」までは担保していますが、「ビット同一の出力」は別の話です。**

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

個別ターゲットは**ビルドコンテナ内**の `build-system/Makefile` にあります。
ホストの `Makefile` には無いので、ホストで叩くと
`No rule to make target` になります。

```bash
# ステップごとにビルド（コンテナ内）
docker compose run --rm kimigayo-build make musl      # [1/4]
docker compose run --rm kimigayo-build make kernel    # [2/4] 成果物には入らない
docker compose run --rm kimigayo-build make busybox   # [3/4]
docker compose run --rm kimigayo-build make init      # [4/4]
docker compose run --rm kimigayo-build make rootfs
```

`make bootloader` と `make create-image` は存在しません
（ベアメタル起動は対象外。→ [SPECIFICATION.md](../../SPECIFICATION.md) 6.2）。
イメージ化はホスト側の `make package-rootfs` → `make build-image` です。

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

`src/kernel/config/<arch>.config` を置くか、置かずに上流の defconfig に
任せます（`scripts/build-kernel.sh` が自動で判断します）。

```bash
# 既存の設定を持ち込む場合（ファイル名は <arch>.config）
cp /boot/config-$(uname -r) src/kernel/config/x86_64.config
```

> `make kernel-defconfig` は存在しません。

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
