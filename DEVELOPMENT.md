# Kimigayo OS 開発ガイド

## プロジェクト構造

```
Kimigayo/
├── .github/
│   └── workflows/          # CI/CD設定
├── .kiro/
│   └── specs/              # Kiro仕様
├── build/                  # ビルド作業ディレクトリ
├── docs/                   # ドキュメント
├── src/                    # ソースコード
│   ├── kernel/             # カーネル設定
│   ├── init/               # Initシステム
│   ├── pkg/                # パッケージマネージャ
│   └── utils/              # ユーティリティ
├── tests/                  # テストコード
│   ├── unit/               # 単体テスト
│   ├── property/           # プロパティテスト
│   └── integration/        # 統合テスト
├── scripts/                # ビルドスクリプト
├── output/                 # ビルド出力
├── Dockerfile              # ビルド環境
├── docker-compose.yml      # Docker Compose設定
├── Makefile                # ビルドシステム
└── SPECIFICATION.md        # 仕様書
```

## 開発環境

### Docker環境の使用

すべての開発はDockerコンテナ内で行うことを推奨します:

```bash
# コンテナ起動
docker-compose run --rm kimigayo-build

# シェルに入る
docker-compose run --rm kimigayo-build /bin/bash
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

```bash
# ヘルプを表示
make help

# すべてをビルド
make all

# アーキテクチャ指定ビルド
make build ARCH=x86_64
make build ARCH=arm64

# テスト実行
make test

# クリーン
make clean

# セキュリティスキャン
make security-scan

# ISOイメージ生成
make iso

# Dockerイメージ生成
make docker-image
```

### ビルドプロセス

1. **カーネル設定**: `src/kernel/config/`
2. **musl libcビルド**: クロスコンパイル対応
3. **BusyBoxビルド**: カスタマイズ可能
4. **Initシステムビルド**: OpenRCベース
5. **パッケージマネージャビルド**: isn
6. **ルートファイルシステム構築**
7. **イメージ生成**: ISO/Docker

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
# 特定のテストを実行
pytest tests/unit/test_pkg_manager.py -v

# カバレッジ測定
pytest --cov=src tests/
```

### 統合テスト

システム全体をテスト:

```bash
# QEMU環境でのテスト
make integration-test

# Docker環境でのテスト
make docker-test
```

## デバッグ

### QEMUでのデバッグ

```bash
# QEMUで起動（デバッグモード）
make qemu-debug

# GDBアタッチ
gdb -ex "target remote :1234" build/kernel/vmlinuz
```

### ログ確認

```bash
# ビルドログ
tail -f build/build.log

# カーネルログ（QEMU内）
dmesg

# Initログ
cat /var/log/init.log
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
# 静的解析
make security-scan

# 依存関係チェック
make dependency-check
```

## パフォーマンス測定

### 起動時間測定

```bash
# QEMUでの起動時間計測
make measure-boot-time
```

### メモリ使用量測定

```bash
# メモリプロファイリング
make memory-profile
```

### ベンチマーク

```bash
# 総合ベンチマーク
make benchmark
```

## トラブルシューティング

### ビルドエラー

```bash
# クリーンビルド
make clean && make all

# 詳細ログ
make V=1 all
```

### Dockerエラー

```bash
# イメージ再ビルド
docker-compose build --no-cache

# ボリューム削除
docker-compose down -v
```

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
- [.kiro/specs/](./kiro/specs/) - Kiro仕様
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
