# Contributing to Kimigayo OS

Kimigayo OSへの貢献に興味を持っていただきありがとうございます！このドキュメントでは、プロジェクトへの貢献方法について説明します。

## 開発環境のセットアップ

### 必要な環境

- Docker & Docker Compose
- Git
- 最低2GB RAM、4GB推奨

### セットアップ手順

1. リポジトリをクローン:
```bash
git clone https://github.com/your-org/Kimigayo.git
cd Kimigayo
```

2. Docker環境を構築:
```bash
docker-compose build
```

3. コンテナを起動:
```bash
docker-compose run --rm kimigayo-build
```

4. ビルドシステムをテスト:
```bash
make test
```

## 開発ワークフロー

### ブランチ戦略

- `main`: 安定版リリース
- `develop`: 開発版
- `feature/*`: 新機能開発
- `bugfix/*`: バグ修正
- `security/*`: セキュリティ修正（優先）

### コミットメッセージ

Kimigayo OSでは**Conventional Commits**形式と**絵文字プレフィックス**を組み合わせて使用しています。これにより、CHANGELOG.mdが自動生成されます。

#### フォーマット

```
<絵文字> <タイプ>: <概要>

<詳細（オプション）>

<フッター（オプション）>
```

#### コミットタイプと絵文字

コミットメッセージの**先頭**に以下のいずれかを使用してください:

| 絵文字 | タイプ | 用途 | CHANGELOGセクション |
|--------|--------|------|---------------------|
| ✨ | `feat:` | 新機能追加 | **Added** |
| 🐛 | `fix:` | バグ修正 | **Fixed** |
| ♻️ | `refactor:` | リファクタリング | **Changed** |
| 🔒 | `security:` | セキュリティ修正 | **Security** |
| 📝 | `docs:` | ドキュメント | **Documentation** |
| 🏗️ | `build:` | ビルドシステム変更 | **Build/CI** |
| 👷 | `ci:` | CI/CD変更 | **Build/CI** |
| 🔖 | `release:` | バージョンリリース | - |
| ✅ | `test:` | テスト追加・修正 | - |
| 🚀 | `perf:` | パフォーマンス改善 | **Changed** |
| 🎉 | `init:` | 初回コミット | - |

#### コミット例

**新機能追加:**
```
✨ feat: パッケージマネージャの依存関係解決機能を追加

- 依存グラフ解決アルゴリズムを実装
- 競合検知機能を追加
- 要件4.2に対応するプロパティテストを追加
```

**バグ修正:**
```
🐛 fix: rootfs最適化の算術式エラーを修正

scripts/build-rootfs.sh:234でゼロ除算が発生していた問題を修正
```

**セキュリティ修正:**
```
🔒 security: パッケージ検証時のパストラバーサル脆弱性を修正

CVE-2024-XXXXX: 相対パス処理の検証を強化
```

**ドキュメント:**
```
📝 docs: CONTRIBUTING.mdにコミットメッセージ規約を追加

新規コントリビューター向けにConventional Commitsの説明を追加
```

#### CHANGELOG自動生成

コミットメッセージが規約に従っていれば、以下のコマンドで自動的にCHANGELOG.mdが生成されます:

```bash
make changelog
```

生成されるCHANGELOGは[Keep a Changelog](https://keepachangelog.com/)形式に準拠し、各コミットタイプが対応するセクションに分類されます。

**重要:** コミットメッセージの**先頭**に絵文字またはタイプキーワードを配置してください。そうしないとCHANGELOGに反映されません。

## コーディング規約

### C言語

- GNU Coding Standards に準拠
- インデント: 4スペース
- 関数名: `snake_case`
- 定数: `UPPER_SNAKE_CASE`

### Python（テストコード）

- PEP 8 に準拠
- インデント: 4スペース
- 関数名: `snake_case`
- クラス名: `PascalCase`

### セキュリティ

すべてのコードは以下を満たす必要があります:

- コンパイル時セキュリティフラグの適用
- 入力検証の実装
- メモリ安全性の確保
- バッファオーバーフロー対策

## テスト

### プロパティベーステスト

各機能には対応するプロパティテストが必要です:

```python
# **Feature: kimigayo-os-core, Property 1: ビルドサイズ制約**
@given(build_config=build_configurations())
def test_build_size_constraint(build_config):
    """任意のビルド設定に対して、生成されるBase_Imageのサイズは5MB未満"""
    image = build_base_image(build_config)
    assert image.size_bytes < 5 * 1024 * 1024
```

### テスト実行

```bash
# 全テスト実行
make test

# プロパティテストのみ
pytest tests/property/

# 単体テストのみ
pytest tests/unit/

# 統合テスト
make integration-test
```

## プルリクエスト

### プルリクエストの作成

1. `develop`ブランチから新しいブランチを作成
2. 変更を実装
3. テストを追加・更新
4. すべてのテストが通ることを確認
5. プルリクエストを作成

### プルリクエストのチェックリスト

- [ ] すべてのテストが通る
- [ ] 新機能にはプロパティテストを追加
- [ ] ドキュメントを更新
- [ ] コミットメッセージが規約に準拠
- [ ] セキュリティ要件を満たす
- [ ] ビルドサイズへの影響を確認

## ライセンス

貢献されたコードは、プロジェクトのライセンス（GPLv2/MIT/BSD）に従います。

## サポート

質問や提案がある場合は、以下の方法でお問い合わせください:

- GitHub Issues: バグレポート、機能リクエスト
- GitHub Discussions: 一般的な質問、アイデア

---

貢献に感謝します！🙏
