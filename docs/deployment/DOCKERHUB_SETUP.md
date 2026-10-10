# Docker Hub リポジトリ設定

## リポジトリ情報

### アカウント詳細
- **組織名/ユーザー名**: IshinoKazuki
- **リポジトリ名**: kimigayo-os
- **リポジトリ**: ishinokazuki/kimigayo-os
- **公開範囲**: Public
- **説明**: Alpine Linuxにインスパイアされた軽量・高速・セキュアなコンテナ向けOS

### リポジトリ説明文

**正本は [DOCKERHUB_README.md](../../DOCKERHUB_README.md)。**
Docker Hub の Overview に貼る文章はこのファイルだけで管理する。
ここに写すと2か所に分かれて必ず食い違うので、写さない。

> 2026-10-10 まで、この手順書に説明文の写しが2か所あり、どちらも
> 実装されていない機能（seccomp のデフォルト有効化・Cosign 署名・
> `stable` タグ）を宣伝していた。

## タグ戦略

### バージョンタグ

すべてのリリースで**セマンティックバージョニング（SemVer）**に従います:

#### フォーマット
- `MAJOR.MINOR.PATCH`（例: `1.0.0`）
  - **MAJOR**: 互換性のないAPI変更
  - **MINOR**: 後方互換性のある新機能
  - **PATCH**: 後方互換性のあるバグ修正

#### イメージバリアント

各バージョンは、イメージサイズと含まれる機能に基づいて3つのバリアントで提供されます:

1. **Minimal**（`-minimal`接尾辞）
   - サイズ: < 5MB
   - 含まれるもの: musl libc + 最小限のBusyBox + OpenRC
   - 用途: 特化したコンテナ向けの絶対最小フットプリント

2. **Standard**（接尾辞なし、デフォルト）
   - サイズ: < 15MB
   - 含まれるもの: Minimal + 一般的なユーティリティ
   - 用途: 汎用コンテナベースイメージ

3. **Extended**（`-extended`接尾辞）
   - サイズ: < 50MB
   - 含まれるもの: Standard + 開発ツール + 追加ユーティリティ
   - 用途: 開発環境と機能豊富なコンテナ

#### タグの例

**`release.yml` が実際に作るタグだけを書く。** 増やすときは
ワークフローを先に直す（書いただけのタグは永久に現れない）。

```
# バージョン指定（マルチアーキのマニフェスト）
kimigayo-os:3.0.0               # Standardバリアント
kimigayo-os:3.0.0-minimal
kimigayo-os:3.0.0-extended

# バリアント + アーキテクチャ（単一プラットフォーム）
kimigayo-os:3.0.0-standard-amd64
kimigayo-os:3.0.0-minimal-arm64

# ローリングタグ（リリースごとに更新。全12本）
kimigayo-os:latest              # standard のマニフェスト
kimigayo-os:latest-minimal
kimigayo-os:latest-extended
kimigayo-os:latest-amd64        # standard のアーキ別
kimigayo-os:latest-arm64
kimigayo-os:latest-standard-amd64
kimigayo-os:latest-minimal-arm64  # ...（バリアント × アーキの6本）
```

> **`3.0.0-amd64` のようなバリアント名なしのアーキ別タグは存在しない。**
> バージョン指定でアーキを固定するならバリアント名が必要。
>
> **`stable` と `edge` も存在しない。** 2026-10-10 までこの手順書が
> 両方を案内していたが、`release.yml` に生成箇所が無く、Docker Hub の
> タグ一覧にも1度も現れていない。

### タグ付けワークフロー

**Docker Hub へ push するのは `v*.*.*` タグを打ったときだけ。**
`main` へのコミットでは `ci.yml` が走るが、イメージは公開されない。

1. **安定版リリース**
   - `git tag -a v3.0.1` → push で `release.yml` が走る
   - バージョン指定タグ（10本）と `latest` 系（12本）を更新する
   - フォーマット: `3.0.0`、`3.0.1`

2. **手動リリース**
   - Actions から `release.yml` を `workflow_dispatch` で実行する
   - `tag` を指定しなければバージョンは `edge` になる（通常は使わない）

**プレリリース（beta / rc）は運用していない。**

## リポジトリセットアップ手順

### ステップ1: Docker Hubアカウント作成

1. https://hub.docker.com/signup にアクセス
2. ユーザー名`kimigayo-os`でアカウント登録
3. メールアドレスを検証
4. プロフィール設定を完了

### ステップ2: リポジトリ作成

1. Docker Hubにログイン
2. "Create Repository"をクリック
3. リポジトリ詳細を入力:
   - **名前**: `kimigayo-os`
   - **説明**: （上記の説明を使用）
   - **公開範囲**: Public
4. "Create"をクリック

### ステップ3: リポジトリ設定

以下の設定を行います:

#### Overviewタブ
- 上記の完全な説明を追加
- 以下のリンクを追加:
  - GitHubリポジトリ: `https://github.com/Kazuki-0731/Kimigayo`

#### Buildsタブ（将来のCI/CD統合用）
- GitHub Actionsで設定予定
- タグプッシュ時の自動ビルド
- buildxを使用したマルチアーキテクチャビルド

#### Collaboratorsタブ
- 必要に応じてチームメンバーを追加
- 適切な権限レベルを設定

### ステップ4: Docker Hub README

[DOCKERHUB_README.md](../../DOCKERHUB_README.md) の中身をそのまま
Docker Hub の Overview に貼る。**ここに文章を写さない**（上記参照）。

Docker Hub の Overview は API からも更新できる:

```bash
# .env の DOCKER_HUB_ACCESS_TOKEN を使う（トークンはコミットしない）
curl -s -X PATCH \
  -H "Authorization: Bearer ${DOCKER_HUB_TOKEN}" \
  -H "Content-Type: application/json" \
  --data "$(python3 -c 'import json,sys; print(json.dumps({"full_description": open("DOCKERHUB_README.md").read()}))')" \
  https://hub.docker.com/v2/repositories/ishinokazuki/kimigayo-os/
```


## セキュリティに関する考慮事項

### イメージ署名

**未実装。** Docker Content Trust も Cosign も `release.yml` に
工程が無い。利用者に案内できるのはダイジェスト指定での pull と、
GitHub Release に添付する `SHA256SUMS` / `SHA512SUMS` だけ。

### 脆弱性スキャン

ソースツリーとビルド環境は Trivy で自動スキャンし、結果を
GitHub の Security タブに公開している。

**イメージ自体のスキャンは成立しない。** パッケージデータベースを
持たないため Trivy が対象を1つも識別できない（「脆弱性 0 件」ではなく
「スキャン対象を認識できない」）。構成要素の脆弱性はバージョンを
手で追跡する（→ `security-review` skill）。

### 更新ポリシー

**正本は [SECURITY_POLICY.md](../security/SECURITY_POLICY.md)。**

- **脆弱性報告の受領確認**: 24時間以内
- **初期評価**: 72時間以内
- **修正のリリース**: Critical 7日以内 / High 30日以内 / Medium 90日以内
- **バグ修正**: 定期的なパッチリリースに含める
- **機能更新**: SemVer のマイナー版で出す

## メタデータラベル

すべてのイメージにOpenContainer Initiative（OCI）ラベルを含めます:

```dockerfile
LABEL org.opencontainers.image.title="Kimigayo OS"
LABEL org.opencontainers.image.description="軽量・高速・セキュアなコンテナ向けOS"
LABEL org.opencontainers.image.authors="Kimigayo OS Team"
LABEL org.opencontainers.image.url="https://github.com/kimigayo-os/kimigayo"
LABEL org.opencontainers.image.documentation="https://github.com/kimigayo-os/kimigayo/tree/main/docs"
LABEL org.opencontainers.image.source="https://github.com/kimigayo-os/kimigayo"
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.revision="${GIT_COMMIT}"
LABEL org.opencontainers.image.created="${BUILD_DATE}"
LABEL org.opencontainers.image.licenses="GPL-2.0"
```

## 次のステップ

リポジトリセットアップ後:
1. 自動ビルド用のGitHub Actions設定（タスク26）
2. セキュリティスキャンの実装（タスク27）
3. マルチアーキテクチャビルドの設定（タスク28）
4. 最初のリリース準備（タスク29）
