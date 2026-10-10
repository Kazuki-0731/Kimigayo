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

**日本語で書き、先頭に絵文字を1つ置く。`feat:` のようなテキスト
プレフィックスは付けない。**

#### フォーマット

```
<絵文字> <何をしたか>

<なぜそうしたか。何を変えたかは diff を見れば分かる>
```

絵文字は先頭に1つだけで、`✨ feat: ...` のように併記しない。
このリポジトリの 609 コミットのうち、テキストプレフィックスが
付いているのは 1 件だけです（それが例外）。

#### 絵文字の一覧

| 種類 | 絵文字 | | 種類 | 絵文字 |
| --- | --- | --- | --- | --- |
| 機能追加 | ✨ | | リファクタ | ♻️ |
| バグ修正 | 🐛 | | テスト | ✅ |
| ドキュメント・記録 | 📝 | | 取り消し | ⏪ |
| 雑務・設定 | 🔧 | | マージ | 🔀 |
| 性能改善 | ⚡ | | 統計・計測の保存 | 📊 |
| 依存・バージョン更新 | ⬆️ | | 片付け・削除 | 🧹 |
| Docker 関連 | 🐳 | | セキュリティ | 🔒 |

**どれにも当てはまらないものは 📌。**

#### コミット例

**新機能追加:**
```
✨ パッケージマネージャーが入っていないことを検査する

- verify-image.sh にアプレット一覧とパスの両方を見る検査を追加
- apk / apt / opkg / yum / dnf / pacman も同じ検査に載せる
- 検査項目は 28 → 29 になる
```

**バグ修正:**
```
🐛 rootfs 最適化の算術式エラーを修正

scripts/build-rootfs.sh:234でゼロ除算が発生していた問題を修正
```

**セキュリティ修正:**
```
🔒 dpkg / rpm がイメージに入っていた

BusyBox の既定が有効なため、config に書かなければ入ってしまう
```

**ドキュメント:**
```
📝 CONTRIBUTING.md のコミット規約を実態に合わせる

テキストプレフィックスは 609 コミット中 1 件しか使われていなかった
```

#### CHANGELOG

**`CHANGELOG.md` は手で書きます。** コミットの件名は「何を変えたか」しか
持っていませんが、`CHANGELOG.md` には「なぜ」が必要です。

```bash
make changelog     # build/CHANGELOG.generated.md に下書きを出す
```

このコマンドは**下書きを `build/` に出すだけ**で、`CHANGELOG.md` は
書き換えません（2026-10-11 までは `CHANGELOG.md` を丸ごと上書きする
作りで、手で書いた内容が消える状態でした）。使える行をコピーして、
理由を足してください。

表に無い絵文字のコミットは `Uncategorized` に入ります（黙って
落とさないため）。

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
