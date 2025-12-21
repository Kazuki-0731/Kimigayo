# コミットメッセージガイド

このドキュメントでは、Kimigayo OSプロジェクトにおけるコミットメッセージの書き方について詳しく説明します。

## 概要

Kimigayo OSでは以下の理由で、統一されたコミットメッセージ規約を採用しています:

- **CHANGELOG.mdの自動生成**: `make changelog`で自動的にリリースノートを作成
- **変更履歴の追跡**: 機能追加、バグ修正、セキュリティ修正を明確に分類
- **レビューの効率化**: コミットの目的が一目でわかる
- **セマンティックバージョニング**: 変更の種類に応じて適切なバージョンアップを判断

## Conventional Commits + 絵文字プレフィックス

Kimigayo OSでは[Conventional Commits](https://www.conventionalcommits.org/)に**絵文字プレフィックス**を組み合わせた独自のスタイルを採用しています。

### 基本フォーマット

```
<絵文字> <タイプ>: <概要>

<詳細説明（省略可）>

<フッター（省略可）>
```

### コミットタイプ一覧

| 絵文字 | タイプ | 説明 | CHANGELOGセクション | 例 |
|--------|--------|------|---------------------|-----|
| ✨ | `feat:` | 新機能の追加 | **Added** | ✨ feat: パッケージ検索機能を追加 |
| 🐛 | `fix:` | バグ修正 | **Fixed** | 🐛 fix: メモリリークを修正 |
| ♻️ | `refactor:` | リファクタリング | **Changed** | ♻️ refactor: コード構造を改善 |
| 🔒 | `security:` | セキュリティ修正 | **Security** | 🔒 security: XSS脆弱性を修正 |
| 📝 | `docs:` | ドキュメント更新 | **Documentation** | 📝 docs: READMEを更新 |
| 🏗️ | `build:` | ビルドシステム変更 | **Build/CI** | 🏗️ build: Makefileを最適化 |
| 👷 | `ci:` | CI/CD変更 | **Build/CI** | 👷 ci: GitHub Actionsを追加 |
| ✅ | `test:` | テスト追加・修正 | (含まれない) | ✅ test: 単体テストを追加 |
| 🚀 | `perf:` | パフォーマンス改善 | **Changed** | 🚀 perf: ビルド速度を向上 |
| 🎨 | `style:` | コードスタイル変更 | (含まれない) | 🎨 style: インデントを修正 |
| 🔧 | `chore:` | 雑務・メンテナンス | (含まれない) | 🔧 chore: 依存関係を更新 |
| 🔖 | `release:` | バージョンリリース | (含まれない) | 🔖 release: v0.2.0 |
| 🎉 | `init:` | 初回コミット | (含まれない) | 🎉 init: プロジェクト開始 |

## 実践例

### ✨ 新機能追加 (feat)

```bash
git commit -m "✨ feat: パッケージマネージャの依存関係解決機能を追加

- Dependency Graphアルゴリズムを実装
- 循環依存の検出機能を追加
- 要件4.2に対応するプロパティテストを追加

Resolves #42"
```

**CHANGELOG.mdでの表示:**
```markdown
### Added
- パッケージマネージャの依存関係解決機能を追加
```

### 🐛 バグ修正 (fix)

```bash
git commit -m "🐛 fix: rootfs構築時のシンボリックリンクエラーを修正

scripts/build-rootfs.sh:234で相対パスの解決に失敗していた問題を修正。
絶対パスに変換してからシンボリックリンクを作成するように変更。

Fixes #128"
```

**CHANGELOG.mdでの表示:**
```markdown
### Fixed
- rootfs構築時のシンボリックリンクエラーを修正
```

### 🔒 セキュリティ修正 (security)

```bash
git commit -m "🔒 security: パッケージ検証時のパストラバーサル脆弱性を修正

CVE-2024-XXXXX: ユーザー入力のパス処理で '../' を含むパスを
正しく検証していなかった問題を修正。

- realpath()による正規化を追加
- chroot環境外へのアクセスを防止
- セキュリティテストケースを追加

CVSS Score: 7.5 (High)"
```

**CHANGELOG.mdでの表示:**
```markdown
### Security
- パッケージ検証時のパストラバーサル脆弱性を修正
```

### 📝 ドキュメント (docs)

```bash
git commit -m "📝 docs: インストールガイドにトラブルシューティングを追加

よくある質問と解決方法を追加:
- Docker権限エラー
- ビルド失敗時の対処法
- メモリ不足エラー"
```

### 🏗️ ビルドシステム (build)

```bash
git commit -m "🏗️ build: マルチアーキテクチャビルド対応

- Docker Buildxを導入
- x86_64とarm64のクロスビルドをサポート
- QEMUエミュレーション設定を追加"
```

### 👷 CI/CD (ci)

```bash
git commit -m "👷 ci: セキュリティスキャンワークフローを追加

- Trivyによる脆弱性スキャン
- ShellCheckによる静的解析
- 週次スケジュールスキャンを設定"
```

## CHANGELOG自動生成

### 生成方法

```bash
# CHANGELOG.mdを生成
make changelog
```

### 仕組み

1. **git tagの取得**: すべてのリリースタグを取得
2. **コミットの抽出**: タグ間のコミットを`git log`で取得
3. **フィルタリング**: コミットメッセージの先頭でタイプを判定
4. **分類**: Conventional Commitsのタイプに応じてセクションに分類

### 検出ロジック

`scripts/generate-changelog.sh`は以下のパターンでコミットをフィルタリングします:

```bash
# Added セクション
git log --grep="^feat" --grep="^✨"

# Fixed セクション
git log --grep="^fix" --grep="^🐛"

# Security セクション
git log --grep="^security" --grep="^🔒"

# Documentation セクション
git log --grep="^docs" --grep="^📝"

# Build/CI セクション
git log --grep="^build" --grep="^ci" --grep="^🏗️" --grep="^👷"
```

**重要:** コミットメッセージの**先頭**に絵文字またはタイプキーワードがない場合、CHANGELOGに含まれません。

## よくある質問

### Q: 絵文字とタイプキーワードの両方が必要ですか？

A: いいえ、どちらか一方でOKです。ただし、両方使うことを推奨します:

```bash
# OK: 絵文字のみ
git commit -m "✨ パッケージ検索機能を追加"

# OK: タイプキーワードのみ
git commit -m "feat: パッケージ検索機能を追加"

# 推奨: 両方
git commit -m "✨ feat: パッケージ検索機能を追加"
```

### Q: 複数の変更を1つのコミットにまとめて良いですか？

A: いいえ、**1コミット1目的**を原則としてください。複数の変更は複数のコミットに分けてください:

```bash
# ❌ 悪い例
git commit -m "✨ 新機能追加とバグ修正とドキュメント更新"

# ✅ 良い例
git commit -m "✨ feat: パッケージ検索機能を追加"
git commit -m "🐛 fix: メモリリークを修正"
git commit -m "📝 docs: READMEを更新"
```

### Q: 日本語と英語のどちらで書くべきですか？

A: **日本語を推奨**します（プロジェクトの主言語が日本語のため）。ただし、グローバルなコントリビューターが多い場合は英語も可です。一貫性を保つことが重要です。

### Q: コミットメッセージを間違えた場合は？

A: 最新のコミットであれば`git commit --amend`で修正できます:

```bash
# コミットメッセージを修正
git commit --amend -m "✨ feat: 正しいメッセージ"
```

ただし、すでにpushした場合は修正しないでください（履歴の改変になります）。

## ツール

### コミットメッセージテンプレート

`.gitmessage`ファイルを作成してテンプレートを設定できます:

```bash
# .gitmessageを作成
cat > .gitmessage <<'EOF'
# <絵文字> <タイプ>: <概要>
#
# <詳細説明>
#
# Resolves: #<issue番号>
#
# タイプ:
#   ✨ feat:     新機能
#   🐛 fix:      バグ修正
#   🔒 security: セキュリティ
#   📝 docs:     ドキュメント
#   🏗️ build:    ビルド
#   👷 ci:       CI/CD
EOF

# テンプレートを設定
git config commit.template .gitmessage
```

### コミットリンター (commitlint)

プロジェクトにcommitlintを導入予定です。以下のルールでコミットメッセージを検証します:

- 先頭に絵文字またはタイプキーワードがあること
- 概要は72文字以内
- 本文は各行100文字以内

## まとめ

1. **コミットメッセージの先頭**に絵文字またはタイプキーワードを配置
2. **1コミット1目的**の原則を守る
3. **わかりやすい概要**を書く（何をしたか）
4. **詳細が必要な場合**は本文に記載（なぜそうしたか）
5. **Issue番号**を参照する（Resolves #42、Fixes #128など）

これらのルールに従うことで、CHANGELOG.mdが自動生成され、プロジェクトの変更履歴が明確になります。

## 参考資料

- [Conventional Commits](https://www.conventionalcommits.org/)
- [Keep a Changelog](https://keepachangelog.com/)
- [Semantic Versioning](https://semver.org/)
- [Gitmoji](https://gitmoji.dev/)
