# GitHub Actions CI/CD セットアップガイド

## 概要

このドキュメントでは、Kimigayo OSのDocker Hubへの自動ビルド・プッシュを行うGitHub Actionsワークフローの設定方法を説明します。

## ワークフロー構成

### ファイル構成

```
.github/
└── workflows/
    └── docker-publish.yml    # Docker ビルド・プッシュワークフロー
```

### トリガー条件

ワークフローは以下のタイミングで実行されます:

1. **タグプッシュ時** (`v*.*.*` 形式)
   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```

2. **手動実行** (workflow_dispatch)
   - GitHub UIから手動でトリガー可能
   - カスタムタグを指定可能

## GitHub Secrets設定

### 必須シークレット

ワークフローを実行するには、以下のシークレットをGitHubリポジトリに設定する必要があります:

| シークレット名 | 説明 | 取得方法 |
|--------------|------|---------|
| `DOCKER_HUB_ACCESS_TOKEN` | Docker Hubアクセストークン | Docker Hub → Account Settings → Security → New Access Token |

### シークレットの設定手順

1. GitHubリポジトリページを開く
2. **Settings** → **Secrets and variables** → **Actions** に移動
3. **New repository secret** をクリック
4. 以下の情報を入力:
   - **Name**: `DOCKER_HUB_ACCESS_TOKEN`
   - **Value**: Docker Hubで生成したアクセストークン
5. **Add secret** をクリック

### Docker Hubアクセストークンの生成

1. [Docker Hub](https://hub.docker.com/)にログイン
2. 右上のアカウントアイコン → **Account Settings**
3. **Security** タブを選択
4. **New Access Token** をクリック
5. トークンの説明を入力（例: "GitHub Actions CI/CD"）
6. アクセス権限を選択（**Read, Write, Delete** 推奨）
7. **Generate** をクリック
8. 表示されたトークンをコピー（⚠️ 一度しか表示されません）

## ワークフロー詳細

### ビルドマトリックス

以下の組み合わせで並列ビルドを実行します:

| バリアント | アーキテクチャ | 合計 |
|----------|-------------|-----|
| minimal  | x86_64, arm64 | 2 |
| standard | x86_64, arm64 | 2 |
| extended | x86_64, arm64 | 2 |
| **合計** | | **6ビルド** |

### 生成されるDockerタグ

#### バージョンタグ (例: v0.1.0の場合)

**Standardバリアント:**
- `ishinokazuki/kimigayo-os:0.1.0-amd64`
- `ishinokazuki/kimigayo-os:0.1.0-arm64`
- `ishinokazuki/kimigayo-os:0.1.0` (マルチアーキマニフェスト)
- `ishinokazuki/kimigayo-os:latest-amd64`
- `ishinokazuki/kimigayo-os:latest-arm64`
- `ishinokazuki/kimigayo-os:latest` (マルチアーキマニフェスト)

**Minimalバリアント:**
- `ishinokazuki/kimigayo-os:0.1.0-minimal-amd64`
- `ishinokazuki/kimigayo-os:0.1.0-minimal-arm64`
- `ishinokazuki/kimigayo-os:0.1.0-minimal` (マルチアーキマニフェスト)
- `ishinokazuki/kimigayo-os:latest-minimal-amd64`
- `ishinokazuki/kimigayo-os:latest-minimal-arm64`
- `ishinokazuki/kimigayo-os:latest-minimal` (マルチアーキマニフェスト)

**Extendedバリアント:**
- `ishinokazuki/kimigayo-os:0.1.0-extended-amd64`
- `ishinokazuki/kimigayo-os:0.1.0-extended-arm64`
- `ishinokazuki/kimigayo-os:0.1.0-extended` (マルチアーキマニフェスト)
- `ishinokazuki/kimigayo-os:latest-extended-amd64`
- `ishinokazuki/kimigayo-os:latest-extended-arm64`
- `ishinokazuki/kimigayo-os:latest-extended` (マルチアーキマニフェスト)

### ワークフロージョブ

#### 1. build-and-push

各バリアント・アーキテクチャの組み合わせでOSイメージをビルドし、Docker Hubにプッシュします。

**ステップ:**
1. リポジトリをチェックアウト
2. Docker Buildxをセットアップ
3. Docker Hubにログイン
4. メタデータを抽出（バージョン、タグ等）
5. Kimigayo OS rootfsをビルド
6. **統合テストを実行**
   - Python環境のセットアップ
   - Phase 1統合テストの実行
   - rootfs構造の検証
7. **Dockerイメージのスモークテスト**
   - コンテナ起動テスト
   - 基本コマンド動作確認
   - BusyBox動作確認
8. テスト成功後、Dockerイメージをビルド・プッシュ
9. ビルド成果物をアップロード

#### 2. create-manifest

マルチアーキテクチャマニフェストを作成し、単一のタグで複数のアーキテクチャをサポートします。

**ステップ:**
1. Docker Hubにログイン
2. 各バリアントのマルチアーキマニフェストを作成・プッシュ

#### 3. create-github-release

GitHub Releasesを作成し、ビルド成果物を添付します。

**ステップ:**
1. リポジトリをチェックアウト
2. すべてのビルド成果物をダウンロード
3. リリース用アセットを準備
4. リリースノートを生成
5. GitHub Releaseを作成し、成果物を添付

## 使用方法

### リリースの作成

1. **バージョンタグを作成**
   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```

2. **GitHub Actionsで自動ビルドが開始**
   - リポジトリの **Actions** タブで進行状況を確認

3. **ビルド完了後、以下を確認**
   - Docker Hub: https://hub.docker.com/r/ishinokazuki/kimigayo-os
   - GitHub Releases: リポジトリの **Releases** タブでビルド成果物を確認

### 手動実行

1. GitHubリポジトリページを開く
2. **Actions** タブに移動
3. **Docker Build and Push** ワークフローを選択
4. **Run workflow** をクリック
5. タグを指定（任意）して **Run workflow** を実行

## トラブルシューティング

### ビルド失敗時の確認事項

1. **Secretsが正しく設定されているか**
   - Settings → Secrets and variables → Actions で確認

2. **Docker Hubアクセストークンが有効か**
   - トークンの有効期限を確認
   - 必要な権限（Read, Write, Delete）が付与されているか

3. **ビルドスクリプトの実行権限**
   ```bash
   chmod +x scripts/build-rootfs.sh
   ```

4. **ログの確認**
   - Actions タブで失敗したジョブのログを確認
   - エラーメッセージを確認して対処

### よくあるエラー

#### Docker Hubログイン失敗
```
Error: Cannot perform an interactive login from a non TTY device
```
**解決方法:** `DOCKER_HUB_ACCESS_TOKEN` シークレットが正しく設定されているか確認

#### ビルドスクリプトが見つからない
```
bash: scripts/build-rootfs.sh: No such file or directory
```
**解決方法:** スクリプトのパスと実行権限を確認

#### マルチアーキテクチャビルド失敗
```
ERROR: failed to solve: failed to push
```
**解決方法:** Docker Buildxが正しくセットアップされているか確認

## セキュリティのベストプラクティス

1. **アクセストークンの管理**
   - トークンは絶対にコードにハードコーディングしない
   - GitHub Secretsを使用して安全に管理
   - 定期的にトークンをローテーション

2. **最小権限の原則**
   - 必要最小限の権限のみをトークンに付与
   - 使用しないトークンは削除

3. **監査とモニタリング**
   - Docker Hubのアクティビティログを定期的に確認
   - 不審なアクセスがないか監視

## 次のステップ

1. セキュリティスキャンの統合（タスク27）
2. 自動テストの追加（タスク26.2）
3. GitHub Releasesとの連携

## 関連ドキュメント

- [Docker Hub セットアップガイド](./DOCKERHUB_SETUP.md)
- [GitHub Actions公式ドキュメント](https://docs.github.com/en/actions)
- [Docker Buildx公式ドキュメント](https://docs.docker.com/buildx/working-with-buildx/)
