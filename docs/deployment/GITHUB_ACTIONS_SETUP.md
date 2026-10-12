# GitHub Actions CI/CD セットアップガイド

## 概要

このドキュメントでは、Kimigayo OS のイメージを Docker Hub に公開する
GitHub Actions を動かすために、**リポジトリ側で用意するもの**と
**リリースの起動のしかた**を説明します。

ワークフローの中身（ジョブの構成・検証・作るタグ・署名）は
[CICD_GUIDE.md](../developer/CICD_GUIDE.md) にまとめてあり、ここでは繰り返しません。

## GitHub Secrets設定

| シークレット名 | 必須 | 用途 |
|--------------|------|------|
| `DOCKER_HUB_ACCESS_TOKEN` | 必須 | `release.yml` が Docker Hub にログインして push する |
| `DISCORD_WEBHOOK` | 任意 | `ci.yml` と `release.yml` の結果通知。未設定なら通知ステップを飛ばす |

- Docker Hub のユーザー名（`ishinokazuki`）はシークレットではなく、
  ワークフローの `env` に直書きしています。`DOCKER_HUB_TOKEN` という
  シークレットはありません
- `GITHUB_TOKEN` は Actions が自動で用意するので設定は要りません

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
3. **Personal access tokens** を開く
4. **Generate new token** をクリック
5. トークンの説明を入力（例: "GitHub Actions CI/CD"）
6. アクセス権限は **Read & Write** にする（push に必要な最小限。Delete は要らない）
7. **Generate** をクリック
8. 表示されたトークンをコピー（⚠️ 一度しか表示されません）

> このトークンでは Docker Hub の Overview（説明文）は更新できません
> （API が 403 を返します）。Overview の扱いは
> [DOCKERHUB_SETUP.md](DOCKERHUB_SETUP.md#ステップ4-docker-hub-readme) を参照。

## リリースの起動

### タグの push（通常のリリース）

```bash
git tag -a v3.0.3 -m "Release v3.0.3"   # 例。2026-10-12 時点の最新は v3.0.2
git push origin v3.0.3
```

**タグを push した瞬間に `release.yml` が走り、`latest` を含む公開イメージが
差し替わります。取り消せないので、タグの作成と push は毎回ユーザーの明示的な
承認を取ります**（`.claude/hooks/guard-bash.sh` も機械的に止めます）。
タグを打つ前に `CHANGELOG.md` を手で更新しておきます。

ビルド完了後に確認するもの:
- Docker Hub: https://hub.docker.com/r/ishinokazuki/kimigayo-os
- GitHub Releases: tarball 6 本・`SHA256SUMS`・`SHA512SUMS`・SBOM 6 本

### 手動実行（workflow_dispatch）

Actions タブの **Release** ワークフロー、または:

```bash
gh workflow run release.yml -f tag=v3.0.3
```

**手動実行は Docker Hub に push しません。** タグ push と同じ経路でビルドし、
`verify-image.sh`・`scan-image.sh` を通して SBOM を成果物に残すところまでです。
マルチアーキのマニフェスト作成・Cosign 署名・GitHub Release も走りません。
`tag` を省くと版は `edge` になります。**公開は `v*.*.*` タグの push だけです**
（2026-10-12 までは手動実行でも push していました）。
詳細は [CICD_GUIDE.md](../developer/CICD_GUIDE.md#手動実行workflow_dispatch)。

## トラブルシューティング

### ビルド失敗時の確認事項

1. **Secretsが正しく設定されているか**
   - Settings → Secrets and variables → Actions で確認
2. **Docker Hubアクセストークンが有効か**
   - トークンの有効期限と、権限が Read & Write あるか
3. **ログの確認**
   - Actions タブで失敗したジョブのログを確認
   - ビルドが落ちたときは `build-logs-<variant>-<arch>` の成果物にログが残る

### よくあるエラー

#### Docker Hubログイン失敗
```
Error: Cannot perform an interactive login from a non TTY device
```
**解決方法:** `DOCKER_HUB_ACCESS_TOKEN` シークレットが設定されているか確認
（未設定だとパスワードが空になりこのエラーになる）

#### 検証や CVE 照合で落ちる
`scripts/verify-image.sh` か `scripts/scan-image.sh` が落ちると push しません。
NVD に新しい CVE が載ると、コードを変えていなくても落ちます
（→ [CICD_GUIDE.md](../developer/CICD_GUIDE.md#出荷物のスキャンscriptsscan-imagesh)）。

## セキュリティのベストプラクティス

1. **アクセストークンの管理**
   - トークンは絶対にコードにハードコーディングしない（ローカルでは `.env` に置き、コミットしない）
   - GitHub Secretsを使用して管理
   - 定期的にトークンをローテーション
2. **最小権限の原則**
   - トークンの権限は Read & Write に留める
   - 使用しないトークンは削除
3. **監査とモニタリング**
   - Docker Hubのアクティビティログを定期的に確認

## 関連ドキュメント

- [CI/CD パイプラインガイド](../developer/CICD_GUIDE.md)
- [Docker Hub セットアップガイド](./DOCKERHUB_SETUP.md)
- [GitHub Actions公式ドキュメント](https://docs.github.com/en/actions)
