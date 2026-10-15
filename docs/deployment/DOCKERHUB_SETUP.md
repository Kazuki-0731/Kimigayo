# Docker Hub リポジトリ設定

## リポジトリ情報

### アカウント詳細
- **組織名/ユーザー名**: ishinokazuki
- **リポジトリ名**: kimigayo-os
- **リポジトリ**: ishinokazuki/kimigayo-os
- **公開範囲**: Public
- **説明**: distroless と Alpine Linux の考え方を組み合わせた、軽量なコンテナ向けOS

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

サイズは目標（`SPECIFICATION.md` §8.3）で、実測（v3.0.2、x86_64 / arm64）は
Minimal 2.46MB / 2.83MB、Standard 2.60MB / 2.98MB、Extended 2.62MB / 3.01MB です。
3 つの違いは BusyBox のアプレットだけです。

1. **Minimal**（`-minimal`接尾辞）
   - サイズ目標: < 5MB
   - 含まれるもの: musl libc + BusyBox（367 アプレット）+ OpenRC
   - Standard と比べて `vi`・`wget`・`du`・`less`・`tr` などが無い

2. **Standard**（接尾辞なし、または `-standard`。デフォルト）
   - サイズ目標: < 15MB
   - 含まれるもの: musl libc + BusyBox（400 アプレット）+ OpenRC
   - 用途: 汎用コンテナベースイメージ

3. **Extended**（`-extended`接尾辞）
   - サイズ目標: < 50MB
   - 含まれるもの: Standard + 11 アプレット（`ar`・`ed`・`fbset`・`fdformat`・
     `flash_*`・`flashcp`・`inotifyd`・`rfkill`・`unlzop`）
   - 開発ツールやデバッガは入っていません

#### タグの例

**`release.yml` が実際に作るタグだけを書く。** 増やすときは
ワークフローを先に直す（書いただけのタグは永久に現れない）。

```
# バージョン指定（マルチアーキのマニフェスト）
kimigayo-os:3.1.0               # Standardバリアント
kimigayo-os:3.1.0-standard
kimigayo-os:3.1.0-minimal
kimigayo-os:3.1.0-extended

# バリアント + アーキテクチャ（単一プラットフォーム）
kimigayo-os:3.1.0-standard-amd64
kimigayo-os:3.1.0-minimal-arm64

# ローリングタグ（リリースごとに更新。全12本）
kimigayo-os:latest              # standard のマニフェスト
kimigayo-os:latest-standard
kimigayo-os:latest-minimal
kimigayo-os:latest-extended
kimigayo-os:latest-amd64        # standard のアーキ別
kimigayo-os:latest-arm64
kimigayo-os:latest-standard-amd64
kimigayo-os:latest-minimal-arm64  # ...（バリアント × アーキの6本）
```

> **`3.1.0-amd64` のようなバリアント名なしのアーキ別タグは存在しない。**
> バージョン指定でアーキを固定するならバリアント名が必要。
>
> **`stable` と `edge` も存在しない。** 2026-10-10 までこの手順書が
> 両方を案内していたが、`release.yml` に生成箇所が無く、Docker Hub の
> タグ一覧にも1度も現れていない。

### タグ付けワークフロー

**Docker Hub へ push するのは `release.yml` の `v*.*.*` タグの push だけ**。
`release.yml` の手動実行はビルドと検証だけで push しない。`main` へのコミットでは
`ci.yml` が走るが、イメージは公開されない。タグの push は公開物を変えるので、
ユーザーの明示的な承認を取る。

1. **安定版リリース**
   - `git tag -a v3.0.3` → push で `release.yml` が走る（版は例）
   - バージョン指定タグ（10本）と `latest` 系（12本）を更新し、Cosign で署名する
   - フォーマット: `3.1.0`、`3.1.1`

2. **手動実行**
   - Actions から `release.yml` を `workflow_dispatch` で実行する
   - **Docker Hub には push しない**。ビルド・検証・スキャン・SBOM の保存まで
     （2026-10-12 までは `<ver>-<variant>-<arch>` と `latest-<variant>-<arch>` を
     push していた）。マニフェスト作成・署名・GitHub Release も走らない
   - `tag` を指定しなければ版は `edge` になる

**プレリリース（beta / rc）は運用していない。**

## リポジトリセットアップ手順

### ステップ1: Docker Hubアカウント作成

1. https://hub.docker.com/signup にアクセス
2. ユーザー名 `ishinokazuki` でアカウント登録（公開イメージの名前空間）
3. メールアドレスを検証
4. プロフィール設定を完了

### ステップ2: リポジトリ作成

1. Docker Hubにログイン
2. "Create Repository"をクリック
3. リポジトリ詳細を入力:
   - **名前**: `kimigayo-os`
   - **説明**: 「アカウント詳細」の説明
   - **公開範囲**: Public
4. "Create"をクリック

### ステップ3: リポジトリ設定

以下の設定を行います:

#### Overviewタブ
- [DOCKERHUB_README.md](../../DOCKERHUB_README.md) を貼る（→ ステップ4）

#### Buildsタブ
- 使わない。ビルドと push は GitHub Actions の `release.yml` が行う
  （→ [GITHUB_ACTIONS_SETUP.md](GITHUB_ACTIONS_SETUP.md)）

#### Collaboratorsタブ
- 必要に応じてチームメンバーを追加
- 適切な権限レベルを設定

### ステップ4: Docker Hub README

[DOCKERHUB_README.md](../../DOCKERHUB_README.md) の中身をそのまま
Docker Hub の Overview に貼る。**ここに文章を写さない**（上記参照）。

**Overview は自動では同期されない。** `release.yml` も触らない。

- `.env` / GitHub Secrets の push 用トークン（`DOCKER_HUB_ACCESS_TOKEN`）では、
  API での更新は **403** になる（ログインは通るが説明文の書き換え権限が無い）
- 更新するには、Web の Overview 編集画面に貼るか、説明文を書き換えられる権限の
  トークンを別に用意して API（`PATCH /v2/repositories/ishinokazuki/kimigayo-os/`
  の `full_description`）で送る
- **貼ったあと、公開されている全文が `DOCKERHUB_README.md` と一致するかを
  突き合わせる。** 手順（読み取りだけなので権限は要らない）は
  [.claude/skills/release/SKILL.md](../../.claude/skills/release/SKILL.md) の
  「Docker Hub の Overview を更新する」にある


## セキュリティに関する考慮事項

### イメージ署名

**v3.0.2 から Cosign のキーレス署名を行う**（`release.yml` の `sign` ジョブ。
Sigstore OIDC、Rekor の透明性ログに載る）。**検証には cosign v3 以降が要る。**
署名は v3 の形式で置いてあり、cosign v2 では `no signatures found` になる
（2026-10-12 に v2.4.1 と v3.0.6 で確かめた）。Docker Content Trust は使わない。
v3.0.1 以前は未署名なので、ダイジェスト指定での pull と、
GitHub Release に添付する `SHA256SUMS` / `SHA512SUMS` を案内する。

### 脆弱性スキャン

リポジトリ（ソースツリー）は Trivy のファイルシステムスキャンで自動検査し、
結果を GitHub の Security タブに送っている。ビルド環境のイメージは
スキャンしていない。

**イメージ自体の Trivy スキャンは成立しない。** パッケージデータベースを
持たないため Trivy が対象を1つも識別できない（「脆弱性 0 件」ではなく
「スキャン対象を認識できない」）。

構成要素（BusyBox / musl / OpenRC）の CVE は `scripts/scan-image.sh`
（`make scan-image`）で照合する。イメージ内のバイナリから読んだ版で
SBOM を作り、Grype で照合する。公開中の `latest` には
`dependency-review.yml` の `published-image-scan` が毎週月曜
04:00 UTC に回す（→ [CICD_GUIDE.md](../developer/CICD_GUIDE.md#7-dependency-review-githubworkflowsdependency-reviewyml)）。

### 更新ポリシー

**正本は [SECURITY_POLICY.md](../security/SECURITY_POLICY.md)。**

- **脆弱性報告の受領確認**: 24時間以内
- **初期評価**: 72時間以内
- **修正のリリース**: Critical 7日以内 / High 30日以内 / Medium 90日以内 / Low 次回リリース
- **バグ修正**: 定期的なパッチリリースに含める
- **機能更新**: SemVer のマイナー版で出す

## メタデータラベル

すべてのイメージにOpenContainer Initiative（OCI）ラベルを含めます
（正本は [Dockerfile.runtime](../../Dockerfile.runtime)。以下はその抜粋）:

```dockerfile
LABEL org.opencontainers.image.title="Kimigayo OS"
LABEL org.opencontainers.image.description="Lightweight, secure container OS combining the distroless and Alpine Linux approaches"
LABEL org.opencontainers.image.authors="Kimigayo OS Team"
LABEL org.opencontainers.image.url="https://github.com/Kazuki-0731/Kimigayo"
LABEL org.opencontainers.image.documentation="https://github.com/Kazuki-0731/Kimigayo/tree/main/docs"
LABEL org.opencontainers.image.source="https://github.com/Kazuki-0731/Kimigayo"
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.created="${BUILD_DATE}"
LABEL org.opencontainers.image.revision="${VCS_REF}"
LABEL org.opencontainers.image.licenses="GPL-2.0-only AND MIT AND BSD-2-Clause AND BSD-3-Clause"
LABEL org.opencontainers.image.vendor="Kimigayo OS Project"
LABEL org.opencontainers.image.base.name="scratch"

# Kimigayo 独自のラベル
LABEL io.kimigayo.version="${VERSION}"
LABEL io.kimigayo.variant="${IMAGE_VARIANT}"
LABEL io.kimigayo.architecture="${TARGETARCH}"
```

`VERSION` / `IMAGE_VARIANT` / `BUILD_DATE` / `VCS_REF` は `release.yml` が
`--build-arg` で渡します。

## 次のステップ

リポジトリセットアップ後は、[GITHUB_ACTIONS_SETUP.md](GITHUB_ACTIONS_SETUP.md) の
手順で `DOCKER_HUB_ACCESS_TOKEN` を GitHub Secrets に登録すれば、
タグの push でリリースできます。
