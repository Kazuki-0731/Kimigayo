# Kimigayo OS パッケージマネージャ（isn）使用方法

`isn`は、Kimigayo OS専用の高速パッケージマネージャです。依存関係の自動解決、セキュリティアップデートの自動適用などの機能を提供します。

## 目次

- [基本的な使い方](#基本的な使い方)
- [パッケージの検索とインストール](#パッケージの検索とインストール)
- [パッケージの更新と削除](#パッケージの更新と削除)
- [リポジトリの管理](#リポジトリの管理)
- [高度な機能](#高度な機能)
- [トラブルシューティング](#トラブルシューティング)

## 基本的な使い方

### isnとは

`isn`（Kimigayo Package Manager）の特徴：

- **高速**: Alpine Linuxのapkマネージャをベースにした高速なパッケージ管理
- **軽量**: 最小限のオーバーヘッド
- **セキュア**: GPG署名検証とSHA-256ハッシュ検証
- **シンプル**: 直感的なコマンド体系

### ヘルプの表示

```bash
# 一般的なヘルプ
isn help

# 特定のコマンドのヘルプ
isn help install
isn help search
```

## パッケージの検索とインストール

### パッケージの検索

```bash
# 名前でパッケージを検索
isn search vim

# 説明も含めて検索
isn search --description editor

# 正確な名前で検索
isn search --exact vim
```

### パッケージのインストール

```bash
# 単一パッケージのインストール
isn install vim

# 複数パッケージのインストール
isn install vim git curl

# 確認なしでインストール
isn install -y nginx

# シミュレーション（実際にはインストールしない）
isn install --simulate vim
```

### パッケージ情報の表示

```bash
# パッケージ情報の表示
isn info vim

# 詳細情報の表示
isn info --verbose vim

# パッケージの依存関係を表示
isn info --depends vim

# パッケージのファイルリストを表示
isn info --files vim
```

## パッケージの更新と削除

### リポジトリの更新

```bash
# リポジトリインデックスの更新
isn update

# 強制的に更新
isn update --force

# 特定のリポジトリのみ更新
isn update --repository main
```

### パッケージのアップグレード

```bash
# 利用可能なアップデートの確認
isn upgrade --check

# すべてのパッケージをアップグレード
isn upgrade

# 確認なしでアップグレード
isn upgrade -y

# 特定のパッケージをアップグレード
isn upgrade vim

# セキュリティアップデートのみ適用
isn upgrade --security-only
```

### パッケージの削除

```bash
# パッケージの削除
isn remove vim

# 依存関係も含めて削除
isn remove --recursive vim

# 設定ファイルも削除
isn remove --purge vim

# 確認なしで削除
isn remove -y vim
```

### パッケージのダウングレード

```bash
# 特定バージョンをインストール
isn install vim=8.2.0

# 以前のバージョンにダウングレード
isn downgrade vim
```

## リポジトリの管理

### リポジトリの確認

```bash
# 登録されているリポジトリの一覧
isn repository list

# リポジトリの詳細情報
isn repository info main
```

### リポジトリの追加

```bash
# 新しいリポジトリを追加
isn repository add community https://repo.kimigayo-os.org/community

# テストリポジトリを追加
isn repository add testing https://repo.kimigayo-os.org/testing --testing

# ミラーサーバーを追加
isn repository add mirror https://mirror.example.com/kimigayo
```

### リポジトリの削除

```bash
# リポジトリを削除
isn repository remove community

# すべてのリポジトリを削除（警告）
isn repository remove --all
```

### リポジトリの優先順位

```bash
# リポジトリの優先順位を設定
isn repository priority main 100
isn repository priority community 50

# 優先順位の確認
isn repository list --show-priority
```

## 高度な機能

### キャッシュの管理

```bash
# キャッシュの確認
isn cache list

# キャッシュのクリーンアップ
isn cache clean

# 古いパッケージキャッシュを削除
isn cache clean --old

# すべてのキャッシュを削除
isn cache clean --all
```

### パッケージの検証

```bash
# インストール済みパッケージの検証
isn verify vim

# すべてのパッケージを検証
isn verify --all

# 破損したファイルを修復
isn verify --fix vim
```

### パッケージのロック

```bash
# パッケージをロック（更新を防ぐ）
isn lock vim

# ロックの解除
isn unlock vim

# ロックされているパッケージの確認
isn lock --list
```

### 依存関係の管理

```bash
# 依存関係グラフの表示
isn depends vim --tree

# 逆依存関係の表示（このパッケージに依存しているパッケージ）
isn rdepends vim

# 孤立したパッケージの検索
isn orphans

# 孤立したパッケージの削除
isn orphans --remove
```

### バックアップと復元

```bash
# インストール済みパッケージリストのバックアップ
isn list --installed > packages.txt

# バックアップから復元
isn install $(cat packages.txt)

# システム全体のバックアップ
isn backup create /backup/system.tar.gz

# バックアップから復元
isn backup restore /backup/system.tar.gz
```

## セキュリティ機能

### GPG署名検証

```bash
# GPG署名検証を有効化（デフォルトで有効）
isn config set verify-signatures true

# 署名検証なしでインストール（非推奨）
isn install --no-verify vim
```

### セキュリティアップデート

```bash
# セキュリティアップデートのチェック
isn security check

# セキュリティアップデートの自動適用を有効化
isn config set auto-security-updates true

# セキュリティアップデートのみ適用
isn upgrade --security-only

# セキュリティ情報の表示
isn security info CVE-2024-XXXX
```

## 設定ファイル

### 主要な設定ファイル

- `/etc/isn/isn.conf`: メイン設定ファイル
- `/etc/isn/repositories.conf`: リポジトリ設定
- `/var/lib/isn/installed`: インストール済みパッケージデータベース

### 設定の変更

```bash
# 設定値の確認
isn config get

# 特定の設定値を取得
isn config get verify-signatures

# 設定値の変更
isn config set auto-update true

# 設定のリセット
isn config reset
```

### よく使う設定

```bash
# 自動アップデートを有効化
isn config set auto-update true

# プログレスバーを無効化
isn config set progress-bar false

# 並列ダウンロード数を設定
isn config set parallel-downloads 5

# キャッシュディレクトリの変更
isn config set cache-dir /var/cache/isn
```

## トラブルシューティング

### パッケージのインストールに失敗する

```bash
# リポジトリインデックスを再同期
isn update --force

# キャッシュをクリア
isn cache clean --all

# 依存関係の問題を修復
isn fix-broken

# 詳細なログを出力
isn install --verbose vim
```

### リポジトリにアクセスできない

```bash
# ネットワーク接続の確認
ping repo.kimigayo-os.org

# ミラーサーバーに切り替え
isn repository add mirror https://mirror.example.com/kimigayo

# タイムアウト時間を延長
isn config set timeout 60
```

### ディスク容量不足

```bash
# ディスク使用量の確認
df -h

# パッケージキャッシュのクリア
isn cache clean --all

# 孤立したパッケージの削除
isn orphans --remove

# 古いカーネルの削除
isn remove --old-kernels
```

### 依存関係の問題

```bash
# 破損した依存関係を修復
isn fix-broken

# 依存関係を強制的に解決
isn install --force-depends vim

# 依存関係を無視してインストール（非推奨）
isn install --no-depends vim
```

## パフォーマンスの最適化

### ダウンロードの高速化

```bash
# 並列ダウンロードを有効化
isn config set parallel-downloads 5

# 最速のミラーを自動選択
isn mirror --fastest

# ミラーリストを更新
isn mirror --refresh
```

### キャッシュの最適化

```bash
# キャッシュサイズの制限
isn config set cache-size-limit 500M

# 古いキャッシュを自動削除
isn config set cache-auto-clean true

# キャッシュの最適化
isn cache optimize
```

## よく使うコマンドのまとめ

```bash
# リポジトリの更新
isn update

# パッケージの検索
isn search <package-name>

# パッケージのインストール
isn install <package-name>

# パッケージの削除
isn remove <package-name>

# すべてのパッケージをアップグレード
isn upgrade

# インストール済みパッケージの一覧
isn list

# パッケージ情報の表示
isn info <package-name>

# キャッシュのクリア
isn cache clean

# セキュリティアップデートのチェック
isn security check
```

## 参考リソース

- **公式ドキュメント**: https://docs.kimigayo-os.org/isn
- **パッケージリポジトリ**: https://packages.kimigayo-os.org
- **Issue報告**: https://github.com/kimigayo/isn/issues
- **コミュニティフォーラム**: https://forum.kimigayo-os.org/isn
