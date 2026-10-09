# Kimigayo OS 開発ガイド

## プロジェクト構造

```
Kimigayo/
├── .github/
│   └── workflows/          # CI/CD設定
│   └── specs/              # Kiro仕様
├── build/                  # ビルド作業ディレクトリ
├── docs/                   # ドキュメント
├── src/                    # ソースコード
│   ├── kernel/             # カーネル設定・パッチ
│   ├── libc/               # musl libc
│   ├── busybox/            # BusyBox設定・パッチ
│   ├── init/, openrc/      # Initシステム（OpenRC）
│   ├── security/           # 強化設定
│   ├── benchmark/          # 計測
│   └── toolchain/          # クロスコンパイル
├── tests/                  # テストコード
│   ├── unit/               # 単体テスト
│   ├── property/           # プロパティテスト
│   └── integration/        # 統合テスト
├── scripts/                # ビルドスクリプト
├── output/                 # ビルド出力
├── Dockerfile              # ビルド環境
├── docker-compose.yml      # Docker Compose設定
├── Makefile                # ビルドシステム
├── versions.mk             # 構成要素のバージョン（単一の真実の源）
├── CLAUDE.md               # 作業ルールとプロジェクト固有の勘所
└── SPECIFICATION.md        # 仕様書
```

## 開発環境

### Docker環境の使用

すべての開発はDockerコンテナ内で行うことを推奨します:

```bash
# ビルド環境イメージを構築
make docker-build

# シェルに入る（推奨。ビルドの進捗がリアルタイムで見える）
make shell

# 直接叩く場合
docker compose run --rm kimigayo-build /bin/bash
```

### ローカル環境（上級者向け）

Alpine Linux以外の環境で開発する場合:

```bash
# 必要なパッケージ（Ubuntu/Debian）
sudo apt-get install build-essential gcc g++ make cmake \
  musl-dev musl-tools linux-headers-generic \
  python3 python3-pip git
```

## ビルドシステム

### Makefileターゲット

全量は `make help`。

```bash
# ヘルプを表示（これが最新の一覧）
make help

# OSをビルド（コンテナ内で musl -> kernel -> BusyBox -> OpenRC）
make build

# アーキテクチャ指定ビルド
make build ARCH=x86_64
make build ARCH=arm64

# テスト実行
make test

# どこまで完了したか / ビルド設定
make status
make info

# クリーン（clean=成果物のみ / clean-cache=ダウンロード / clean-all=全部）
make clean

# セキュリティスキャン（Trivy + ShellCheck）
make security-scan

# rootfs から Docker イメージまで（GitHub Actions 相当）
make ci-build-local
```

**ISO イメージ生成（`make iso`）は無い。**
Kimigayo OS はコンテナ向けで、成果物は rootfs の tarball と Docker イメージ。

### ビルドプロセス

1. **カーネル設定**: `src/kernel/config/`
2. **musl libcビルド**: クロスコンパイル対応
3. **BusyBoxビルド**: カスタマイズ可能
4. **Initシステムビルド**: OpenRCベース
5. **ルートファイルシステム構築**
6. **イメージ生成**: rootfs tarball（`output/*.tar.gz`）→ Docker イメージ

**Docker イメージに入るのは rootfs だけで、カーネルは含まれない**
（コンテナはホストのカーネルで動く）。カーネルをビルドするのは
ベアメタル／QEMU 検証のため。

## テスト戦略

### プロパティベーステスト

すべての要件には対応するプロパティテストが必要です:

```python
# tests/property/test_build_constraints.py

from hypothesis import given, strategies as st
from kimigayo.build import build_base_image

# **Feature: kimigayo-os-core, Property 1: ビルドサイズ制約**
@given(build_config=st.builds(BuildConfig))
def test_build_size_constraint(build_config):
    """任意のビルド設定に対して、Base_Imageは5MB未満"""
    image = build_base_image(build_config)
    assert image.size_bytes < 5 * 1024 * 1024
```

### 単体テスト

個別のコンポーネントをテスト:

```bash
# 依存をインストール
pip install -r requirements-dev.txt

# 特定のテストを実行
pytest tests/unit/test_build_config.py -v

# マーカーで絞る（unit / property / integration / slow / security）
pytest -m "not slow" -q

# カバレッジ測定
pytest --cov=src tests/
```

### 統合テスト

システム全体をテスト:

```bash
# rootfs tarball に対する統合テスト
make test-integration

# Dockerイメージの起動テスト
make test-docker

# 機能テスト（BusyBox, Network）
make test-func

# QEMU でのカーネル起動テスト
ARCH=x86_64 bash scripts/test-kernel-qemu.sh
```

## デバッグ

### QEMUでのデバッグ

`make qemu-debug` というターゲットは無い。スクリプトを直接使う。

```bash
# QEMUでカーネルを起動
ARCH=x86_64 TIMEOUT=30 bash scripts/test-kernel-qemu.sh

# ビルド済みカーネルイメージの場所
ls build/kernel/output/

# GDBアタッチ（QEMU 側に -s -S を渡して起動した場合）
gdb -ex "target remote :1234" build/kernel-src/linux-$(make -s print-kernel)/vmlinux
```

### ログ確認

```bash
# 各コンポーネントのビルドログ（最新100行）
make log-kernel
make log-musl
make log-openrc

# パッチ適用の結果（版上げ後は必ず見る）
grep -i 'skipped\|not applicable' build/kernel-patches.log build/busybox-patches.log

# 生ログ
ls build/logs/
```

## セキュリティ

### セキュリティチェック

すべてのビルドで以下が適用されます:

- **PIE**: Position Independent Executables
- **Stack Protection**: `-fstack-protector-strong`
- **FORTIFY_SOURCE**: `-D_FORTIFY_SOURCE=2`
- **RELRO**: `-Wl,-z,relro,-z,now`

### セキュリティスキャン

```bash
# 総合（Trivy イメージ + Trivy FS + ShellCheck）
make security-scan

# 個別
make trivy-scan
make trivy-fs-scan
make shellcheck-scan
```

依存関係のレビューは CI 側（`.github/workflows/dependency-review.yml`）で回る。

## パフォーマンス測定

### 起動時間測定

```bash
make benchmark-startup
```

### メモリ使用量測定

```bash
make benchmark-memory
```

全ベンチマークは `make benchmark`。
**取った数値は README とベンチマークドキュメントに反映するまでが1セット**
（→ [CLAUDE.md](CLAUDE.md)「数値を出したら反映まで」節）。

### ベンチマーク

```bash
# 総合ベンチマーク
make benchmark
```

## トラブルシューティング

### ビルドエラー

```bash
# クリーンビルド（成果物のみ削除。ダウンロードキャッシュは残る）
make clean && make build

# 完全リセット（ダウンロードキャッシュも消える。再取得は約150MB）
make clean-all && make build

# 個別のコンポーネントだけやり直す（コンテナ内）
make clean-kernel && make kernel
```

**版を上げた直後にビルドが通らないときは、まずパッチの適用結果を見る。**
当たらなかったパッチは黙ってスキップされる:

```bash
grep -i 'skipped\|not applicable' build/kernel-patches.log build/busybox-patches.log
```

### Dockerエラー

```bash
# イメージ再ビルド
make docker-rebuild

# コンテナ停止・削除
make down

# ボリューム（ダウンロードキャッシュ・出力）も削除
docker compose down -v
```

**開発機が Apple Silicon（arm64）の場合、`docker-compose.yml` が
`platform: linux/amd64` を固定しているため QEMU エミュレーションになる。**
musl / BusyBox / OpenRC は許容範囲だが、カーネルのフルビルドは
非現実的なので GitHub Actions に任せる（→ [CLAUDE.md](CLAUDE.md)
「ビルドの現実的な制約」節）。

## リリースプロセス

### バージョニング

セマンティックバージョニング（MAJOR.MINOR.PATCH）:

- **MAJOR**: 互換性のない変更
- **MINOR**: 後方互換性のある機能追加
- **PATCH**: 後方互換性のあるバグ修正

### リリース手順

1. `develop`ブランチで開発完了
2. すべてのテストが通ることを確認
3. バージョン番号を更新
4. リリースノート作成
5. `main`ブランチにマージ
6. タグ作成: `git tag -a v1.0.0 -m "Release 1.0.0"`
7. イメージ生成とリリース

## 参考資料

- [SPECIFICATION.md](./SPECIFICATION.md) - プロジェクト仕様
- [SPECIFICATION.md](./SPECIFICATION.md) - 仕様
- [CONTRIBUTING.md](./CONTRIBUTING.md) - 貢献ガイド
- [Alpine Linux](https://alpinelinux.org/) - 参考ディストリビューション
- [musl libc](https://musl.libc.org/) - Cライブラリ
- [BusyBox](https://busybox.net/) - コアユーティリティ
- [OpenRC](https://github.com/OpenRC/openrc) - Initシステム

## サポート

- **Issues**: バグ報告、機能リクエスト
- **Discussions**: 質問、アイデア共有
- **Wiki**: 詳細なドキュメント

---

Happy Hacking! 🚀
