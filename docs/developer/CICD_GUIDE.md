# CI/CDパイプラインガイド

このガイドでは、Kimigayo OSのCI/CDパイプラインの構成と仕組みについて説明します。

## 📋 目次

- [GitHub Actionsワークフロー](#github-actionsワークフロー)
- [ビルドプロセス](#ビルドプロセス)
- [テスト戦略](#テスト戦略)
- [セキュリティスキャン](#セキュリティスキャン)
- [リリースプロセス](#リリースプロセス)
- [ローカルでのCI実行](#ローカルでのci実行)
- [カスタムプロジェクトへの適用](#カスタムプロジェクトへの適用)

## GitHub Actionsワークフロー

Kimigayo OS は以下の 7 つのワークフローを使用しています。

| ワークフロー | トリガー | 役割 |
|------------|---------|------|
| `ci.yml` | `main` / `develop` への push、`main` への PR | 日常の検証 |
| `release.yml` | `v*.*.*` タグ、手動 | **Docker Hub への公開** |
| `build-workflow.yml` | 他から `workflow_call` | 再利用可能なビルド本体 |
| `manual-build.yml` | 手動のみ | variant / arch を選んでビルド |
| `security.yml` | 毎日 02:00 UTC、手動 | 脆弱性スキャンと Issue 起票 |
| `base-image-update.yml` | 毎週月曜 03:00 UTC、手動 | 上流の更新を検知して PR 作成 |
| `dependency-review.yml` | `main` への PR、毎週月曜 04:00 UTC、手動 | 依存レビュー（`fail-on-severity: high`）|

### 1. CI (`.github/workflows/ci.yml`)

**トリガー:** `main` / `develop` への push、`main` への PR

**処理内容:**
1. ShellCheck（`scripts/` と `.claude/hooks`）
2. リンク検査（`scripts/check-links.py`）
3. pytest（単体 + プロパティ）
4. variant × arch の matrix でビルドとイメージ検証

**マトリックス戦略:**
```yaml
strategy:
  fail-fast: false
  matrix:
    variant: [minimal, standard, extended]
    arch: [x86_64, arm64]
```

これにより 6 つのイメージが並列でビルドされます。
**`fail-fast: false` は意図的です。** 以前は 1 つの失敗が兄弟ジョブを
キャンセルして、本当の失敗を隠していました。

> **`ci.yml` はカーネルをビルドしません**（2026-10-10 に外しました）。
> 成果物は rootfs だけを詰めた Docker イメージで、コンテナはホストの
> カーネルで動くため、CI がカーネルを作ってもイメージの中身は
> 1 バイトも変わりません。それでいて 1 run あたり数十分かかっていました。
>
> **したがってカーネル関連の変更は `ci.yml` が緑でも検証されていません。**
> `versions.mk` の `KERNEL_VERSION` や `src/kernel/` を触ったときは、
> `manual-build.yml` を `build_kernel=true` で手動実行するか、
> コンテナ内で `make kernel` を通してください。

### 2. Release (`.github/workflows/release.yml`)

**トリガー:**
- タグ push (`v*.*.*`)
- 手動実行 (workflow_dispatch、`tag` を入力)

**処理内容:**
1. 版の解決（`scripts/get-version.sh`）
2. ShellCheck
3. マルチアーキテクチャ・マルチバリアントビルド（6 ジョブ）
4. イメージ検証と Docker Hub への push
5. マルチアーキテクチャマニフェスト作成
6. **Cosign のキーレス署名**（`sign` ジョブ）
7. GitHub Release の作成（tarball 6 本 + `SHA256SUMS` + `SHA512SUMS`）
8. 通知

> **`CHANGELOG.md` は自動生成されません。手で書きます。**
> `make changelog` は `build/CHANGELOG.generated.md` に下書きを出すだけで、
> `CHANGELOG.md` を書き換えません。**タグを打つ前に必ず更新してください**
> （2026-10-09 まで 0.1.0 止まりで、2 回のリリースが抜けていました）。

> **タグを push した瞬間に Docker Hub の `latest` を含む公開イメージが
> 差し替わります。** 取り消せないので、タグとリリースは毎回明示的な承認を
> 取ってください（`.claude/hooks/guard-bash.sh` が機械的に止めます）。

### 3. Build Workflow (`.github/workflows/build-workflow.yml`)

**トリガー:** 他のワークフローからの `workflow_call` のみ

`ci.yml` と `release.yml` と `manual-build.yml` が共有するビルド本体です。
入力に `variant` / `arch` / `build_kernel` / `upload_artifacts` を取ります。
`build_kernel` の既定は `false` です。

### 4. Manual Build (`.github/workflows/manual-build.yml`)

**トリガー:** 手動のみ（workflow_dispatch）

variant と arch を選んでビルドします。**カーネルを CI でビルドする
唯一の経路**で、`build_kernel=true` を指定します。

```bash
gh workflow run manual-build.yml \
  -f variant=standard -f arch=x86_64 -f build_kernel=true
```

### 5. Security Scan (`.github/workflows/security.yml`)

**トリガー:**
- 毎日 02:00 UTC
- 手動実行

**処理内容:**
1. 構成要素の版の確認
2. 脆弱性スキャン（Trivy）
3. 脆弱性検出時に Issue を自動作成

> **イメージの Trivy スキャンは実質的に何も検査していません。**
> Kimigayo は `scratch` 上の手組み rootfs でパッケージデータベースを
> 持たないため、Trivy は対象を 1 つも識別できません
> （`Target: -` / `Not scanned` / `Results: 0`）。
> **「脆弱性 0 件」ではなく「スキャンしていない」**という意味です。
> 脆弱性の追跡は構成要素の版を手で突合します。
> ファイルシステムスキャン（`trivy-fs-scan`）はリポジトリ側の依存を
> 見るので有効です。

### 6. Base Image Update (`.github/workflows/base-image-update.yml`)

**トリガー:** 毎週月曜 03:00 UTC、手動（`force_rebuild` を入力）

上流（カーネル / musl / BusyBox / OpenRC / Alpine）の更新を検知して
PR を作成します。**この PR は「上流が動いた」という一次情報**なので、
バージョン更新の起点として先に見てください。

### 7. Dependency Review (`.github/workflows/dependency-review.yml`)

**トリガー:** `main` への PR、毎週月曜 04:00 UTC、手動

依存のレビューを行います（`fail-on-severity: high`）。

## ビルドプロセス

### ステップバイステップ

#### 1. リポジトリチェックアウト

```yaml
- name: Checkout repository
  uses: actions/checkout@v4
```

#### 2. ビルド環境イメージの用意

```yaml
- name: Set up Docker Buildx
  uses: docker/setup-buildx-action@8d2750c68a42422c14e847fe6c8ac0403b4cbd6f # v3.12.0

- name: Build build-environment image
  run: docker compose build
  env:
    KIMIGAYO_VERSION: ${{ needs.meta.outputs.version }}
```

> **QEMU は使いません。** arm64 のジョブは **`ubuntu-24.04-arm`
> ネイティブランナー**で走ります。
>
> ```yaml
> runs-on: ${{ matrix.arch == 'arm64' && 'ubuntu-24.04-arm' || 'ubuntu-latest' }}
> ```
>
> 以前は x86 ランナー上で QEMU エミュレーションしていましたが、
> 遅いうえに失敗もするため、ネイティブランナーに移しました。
> **開発機（Apple Silicon）で x86_64 を回すと QEMU になる**ので、
> フルビルドは Actions に任せます。

#### 3. Docker Hubログイン

```yaml
- name: Log in to Docker Hub
  uses: docker/login-action@c94ce9fb468520275223c153574b00df6fe4bcc9 # v3.7.0
  with:
    username: ${{ env.DOCKER_HUB_USERNAME }}
    password: ${{ secrets.DOCKER_HUB_ACCESS_TOKEN }}
```

**必要なシークレットは1つだけです:**

| 名前 | 種別 | 値 |
| --- | --- | --- |
| `DOCKER_HUB_ACCESS_TOKEN` | **Secret** | Docker Hub のアクセストークン |
| `DOCKER_HUB_USERNAME` | **env**（Secret ではない）| `ishinokazuki` をワークフローに直書き |
| `DISCORD_WEBHOOK` | Secret | 通知用（任意）|

**`DOCKER_HUB_TOKEN` というシークレットはありません。**

#### 4. メタデータの抽出

版は `meta` ジョブが `scripts/get-version.sh` で解決し、
後続のジョブへ `needs.meta.outputs.version` として渡します。

> **ここを渡し忘れると、タグ名だけ合っていて中身の版がずれます。**
> 以前 `release.yml` が版を渡さず、`os-release` が `dev` になる事故が
> ありました。下の検証（`EXPECT_VERSION`）はそれを止めるためのものです。

#### 5. Rootfsビルド

**`ci.yml` とまったく同じ入口を使います。** 経路が分かれていると、
CI が緑でもリリースで落ちる（逆も）ことになります。

```yaml
- name: Build Kimigayo OS rootfs
  run: |
    docker compose run --rm \
      -e IMAGE_TYPE=${{ matrix.variant }} \
      -e KIMIGAYO_VERSION=${{ needs.meta.outputs.version }} \
      kimigayo-build \
      make build-no-kernel TARGET_ARCH=${{ matrix.arch }} IMAGE_TYPE=${{ matrix.variant }}
```

**`build-no-kernel` です。** カーネルはイメージに入らないので作りません。

#### 6. パッチが黙ってスキップされていないか確認

```yaml
- name: Fail if patches were silently skipped
  run: |
    for log in build/kernel-patches.log build/busybox-patches.log; do
      [ -f "$log" ] || continue
      grep -iE 'skipped: [1-9]|not applicable' "$log" && exit 1
    done
```

`apply-*-patches.sh` は当たらないパッチを `log_warn` して `return 0`
するため、放置すると「適用されているつもり」で進みます。

#### 7. イメージのビルド

**`docker build` を直接使います**（`build-push-action` は使っていません）。
検証したものをそのまま push するため、ビルドは 1 回だけです。

```yaml
- name: Build Docker image
  run: |
    docker build \
      --platform "${{ steps.tags.outputs.platform }}" \
      -f Dockerfile.runtime \
      --build-arg TARBALL_PATH="output/kimigayo-${{ matrix.variant }}-${VERSION}-${{ matrix.arch }}.tar.gz" \
      --build-arg VERSION="${VERSION}" \
      --build-arg IMAGE_VARIANT="${{ matrix.variant }}" \
      -t "${{ steps.tags.outputs.primary }}" \
      -t "${{ steps.tags.outputs.moving }}" \
      .
```

#### 8. イメージを実際に起動して検証

**ここを通らなければ push しません。**

```yaml
- name: Verify image by running it
  env:
    EXPECT_VERSION: ${{ needs.meta.outputs.version }}
  run: |
    bash scripts/verify-image.sh \
      "${{ steps.tags.outputs.primary }}" \
      "${{ matrix.variant }}" \
      "${{ matrix.arch }}"
```

**検証の実体は `scripts/verify-image.sh`**（29 項目）で、`ci.yml` と
ローカルの `make` も同じものを呼びます。`EXPECT_VERSION` を渡すと、
`LABEL version` と `/etc/os-release` の `VERSION_ID` がこの版と
一致しなければ落ちます。

> **`release.yml` に Trivy も pytest も統合テストもありません。**
> Trivy のイメージスキャンは、パッケージデータベースが無く
> 何も識別できないため 2026-10-09 に外しました。
> pytest は `ci.yml` 側で回ります。
> 以前は検証に `continue-on-error` が付いており、
> tarball が小さくても `exit 0` でスキップしていました。

#### 9. 検証済みイメージを push

```yaml
- name: Push verified image
  run: |
    docker push "${{ steps.tags.outputs.primary }}"
    docker push "${{ steps.tags.outputs.moving }}"
```

#### 11. Cosign のキーレス署名

**鍵を持ちません。** GitHub Actions の OIDC トークンで署名し、署名は
Rekor の透明性ログに載ります。Secrets を増やさずに済みます。

```yaml
  sign:
    permissions:
      contents: read
      id-token: write      # これが無いと OIDC が取れない
    steps:
      - uses: sigstore/cosign-installer@6f9f17788090df1f26f669e9d70d6ae9567deba6 # v4.1.2
      ...
      - run: cosign sign --yes "${repo}@${digest}"
```

**署名するのはタグではなくダイジェストです。** タグは動くので、
タグへの署名では「どのイメージを署名したか」を特定できません。
`docker buildx imagetools inspect` の `Digest:` 行から引き
（`--format` は古い buildx に無い）、**重複を落としてから署名します**
（実測で 22 タグ → 9 ダイジェスト）。

署名した直後に `cosign verify` で検証まで行います
（「署名した」と「検証できる」は別）。

利用者側の検証:

```bash
cosign verify ishinokazuki/kimigayo-os:latest \
  --certificate-identity-regexp '^https://github.com/Kazuki-0731/Kimigayo/' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

> **v3.0.1 以前の公開イメージは署名されていません。**
> 配線は 2026-10-11 に入れたもので、効くのは次のリリース以降です。

#### 10. マルチアーキテクチャマニフェスト作成

**作るタグは1種類ではありません。** `create-manifest` ジョブが
次をすべて作ります。

| タグ | 中身 |
| --- | --- |
| `<ver>-<variant>` | そのバリアントの amd64 + arm64 |
| `latest-<variant>` | 同上の移動タグ |
| `<ver>` | standard の amd64 + arm64 |
| `latest` | standard の最新 |
| `latest-amd64` / `latest-arm64` | standard のアーキ別（単一プラットフォーム）|

```yaml
- name: Create and push multi-arch manifests
  run: |
    docker buildx imagetools create -t "${repo}:latest-${variant}" \
      "${repo}:latest-${variant}-amd64" \
      "${repo}:latest-${variant}-arm64"

    docker buildx imagetools create -t "${repo}:latest" \
      "${repo}:latest-standard-amd64" "${repo}:latest-standard-arm64"

    # latest-<arch> も standard の別名
    for a in amd64 arm64; do
      docker buildx imagetools create -t "${repo}:latest-${a}" \
        "${repo}:latest-standard-${a}"
    done
```

> **`latest-amd64` / `latest-arm64` は一度作り忘れて、
> 永久に更新されない状態になっていました。**
> `docs/RELEASE_CHECKLIST.md` がこのタグを案内しているため、
> 作る対象から漏らさないこと。

## テスト戦略

### 1. 単体テスト

```bash
# ローカル実行
docker compose run --rm kimigayo-build pytest tests/unit/ -v

# CI実行
python3 -m pytest tests/unit/ -v --cov
```

### 2. プロパティテスト

```bash
# Hypothesisベースのプロパティテスト
python3 -m pytest tests/property/ -v
```

### 3. 統合テスト

```bash
# Phase 1統合テスト
python3 -m pytest tests/integration/test_phase1_integration.py -v
```

### 4. スモークテスト

```bash
# Dockerイメージの基本動作確認
docker run --rm test-image /bin/sh -c "echo 'Test' && busybox --help"
```

### 5. セキュリティテスト

```bash
# リポジトリ側の依存をスキャン（有効）
make trivy-fs-scan

# ShellCheckスキャン
make shellcheck-scan
```

> **`trivy image` は Kimigayo のイメージに対して何も検査しません。**
> `scratch` 上の手組み rootfs でパッケージデータベースを持たないため、
> Trivy は対象を 1 つも識別できません
> （`Target: -` / `Not scanned` / `Results: 0`）。
> **「CRITICAL/HIGH が 0 件」ではなく「スキャンしていない」。**
> 構成要素（カーネル / musl / BusyBox / OpenRC）の脆弱性追跡は
> 版を手で突合します（→ `security-review` skill、
> `.github/workflows/security.yml`）。

## セキュリティスキャン

### ShellCheck（静的解析）

**外部 Action は必ずコミット SHA で固定します。** `@master` 参照は
供給網のリスクであり、再現性もありません（2026-10-09 に固定しました）。

```yaml
- name: Run ShellCheck (Static Analysis)
  uses: ludeeus/action-shellcheck@00cae500b08a931fb5698e11e79bfbd38e612a38 # 2.0.0
  with:
    additional_files: '.claude/hooks'
    scandir: './scripts'
    severity: warning
    ignore_paths: build output
```

`.claude/hooks` も検査対象です（Hook はこのプロジェクトの作業ルール
そのものなので、`scripts/` と同じ基準で静的解析します）。

### Trivy（脆弱性スキャン）

```yaml
- name: Run Trivy vulnerability scanner
  uses: aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25 # v0.36.0
  with:
    image-ref: ${{ steps.trivy_tag.outputs.tag }}
    format: 'sarif'
    output: 'trivy-results.sarif'
    severity: 'CRITICAL,HIGH'
    scanners: 'vuln,config,secret'
```

**SARIF形式でGitHub Security tabに結果をアップロード:**

```yaml
- name: Upload Trivy results to GitHub Security tab
  uses: github/codeql-action/upload-sarif@24c54180a607b1449ed407dd24f251e4e9147c8d # v4.38.3
  with:
    sarif_file: 'trivy-results.sarif'
```

## リリースプロセス

### セマンティックバージョニング

Kimigayo OSは[Semantic Versioning](https://semver.org/)に従います:

- **MAJOR** (1.x.x): 破壊的変更
- **MINOR** (x.1.x): 後方互換性のある新機能
- **PATCH** (x.x.1): 後方互換性のあるバグ修正

### リリース手順

#### 1. バージョンタグの作成

```bash
# 現在のバージョンを確認
make version

# 新しいバージョンでタグを作成（現行は v3.0.1）
git tag -a v3.0.2 -m "Release v3.0.2

- 新機能A
- バグ修正B
- セキュリティ強化C
"

# タグをプッシュ（**ユーザーの明示的な承認が必要**）
git push origin v3.0.2
```

#### 2. 自動ビルドとリリース

タグがプッシュされると、GitHub Actionsが自動的に:

1. 版の解決（`scripts/get-version.sh`）
2. ShellCheck
3. 全バリアント・全アーキテクチャをビルド（6 ジョブ）
4. **イメージを起動して検証**（`scripts/verify-image.sh`、29 項目）
5. 検証を通ったものだけ Docker Hub にプッシュ
6. マルチアーキテクチャマニフェスト作成
7. **Cosign のキーレス署名**（v3.0.2 から）
8. GitHub Releases を作成
9. リリースアセット（tar.gz 6 本 + SHA256SUMS + SHA512SUMS）を添付

**Trivy スキャンと pytest は `release.yml` では走りません**
（pytest は `ci.yml` 側。Trivy のイメージスキャンは何も識別できないため
2026-10-09 に外しました）。

**`CHANGELOG.md` は自動生成されません。** タグを打つ前に手で更新して
おいてください（→ [2. Release](#2-release-githubworkflowsreleaseyml)）。

#### 3. リリースノートの確認

GitHub Releasesページで以下を確認:

- リリースハイライト
- 利用可能なイメージタグ
- ビルド成果物（tar.gz）
- チェックサム（SHA256, SHA512）

### 手動リリース（workflow_dispatch）

```bash
# GitHub CLI を使用
gh workflow run release.yml -f tag=v3.0.2
```

または、GitHubのActionsタブから手動実行。

## ローカルでのCI実行

### act を使用したローカルCI実行

[act](https://github.com/nektos/act)をインストール:

```bash
# macOS
brew install act

# Linux
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash
```

ワークフローをローカルで実行:

```bash
# 全ジョブを実行
act

# 特定のイベントをシミュレート
act push

# 特定のジョブのみ実行
# release.yml の実際のジョブ名は次の7つ:
#   meta / shellcheck / build / verify-and-push /
#   create-manifest / create-github-release / notify
act -j build

# 環境変数を指定
act -s DOCKER_HUB_ACCESS_TOKEN=your_token
```

### Makefileでのローカルビルド

```bash
# CI相当のビルド
make ci-build-local

# CI相当のビルド + プッシュ
make ci-build-push
```

> **`make ci-build-local` は macOS ホストでは通りません。**
> ホスト側で `scripts/build-rootfs.sh` を直接叩き、その中で
> `build-musl.sh` を実際に呼ぶため、musl の `configure` が
> `unsupported long double type` で落ちます。
> さらに `ARCH` を省略すると `uname -m` から自動検出するので、
> Apple Silicon では `arm64` になります。
> **Linux ホストならそのまま通ります**（GitHub Actions はこの経路）。
> macOS での回避手順は
> [CLAUDE.md](../../CLAUDE.md) の「ビルドの全体像」節にあります。

## カスタムプロジェクトへの適用

### 基本的なワークフロー

```yaml
# .github/workflows/build.yml
name: Build and Test

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: false
          tags: myapp:test

      - name: Test Docker image
        run: |
          docker run --rm myapp:test /bin/sh -c "test-command"
```

### マルチアーキテクチャビルド

```yaml
# .github/workflows/multiarch-build.yml
name: Multi-Architecture Build

on:
  push:
    tags:
      - 'v*.*.*'

jobs:
  build:
    runs-on: ubuntu-latest

    strategy:
      matrix:
        platform:
          - linux/amd64
          - linux/arm64

    steps:
      - uses: actions/checkout@v4

      - name: Set up QEMU
        uses: docker/setup-qemu-action@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          platforms: ${{ matrix.platform }}
          push: true
          tags: myapp:latest
```

### セキュリティスキャン統合

```yaml
# .github/workflows/security.yml
name: Security Scan

on:
  schedule:
    - cron: '0 0 * * 0'  # 毎週日曜
  workflow_dispatch:

jobs:
  scan:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Build image
        run: docker build -t myapp:scan .

      - name: Run Trivy scanner
        uses: aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25 # v0.36.0
        with:
          image-ref: myapp:scan
          format: 'sarif'
          output: 'trivy-results.sarif'

      - name: Upload to Security tab
        uses: github/codeql-action/upload-sarif@24c54180a607b1449ed407dd24f251e4e9147c8d # v4.38.3
        with:
          sarif_file: 'trivy-results.sarif'
```

## ベストプラクティス

### 1. キャッシュの活用

```yaml
- name: Build and push
  uses: docker/build-push-action@v5
  with:
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

### 2. シークレットの管理

```yaml
env:
  DOCKER_HUB_USERNAME: ${{ secrets.DOCKER_HUB_USERNAME }}
  DOCKER_HUB_TOKEN: ${{ secrets.DOCKER_HUB_TOKEN }}
```

GitHub Settings > Secrets and variables > Actions で設定。

> **これは一般的な例です。Kimigayo 自身のシークレットは
> `DOCKER_HUB_ACCESS_TOKEN` だけ**で、ユーザー名は `env` に直書き
> しています（→ [3. Docker Hubログイン](#3-docker-hubログイン)）。

### 3. 並列実行の最適化

```yaml
strategy:
  matrix:
    variant: [minimal, standard]
    arch: [amd64, arm64]
  max-parallel: 4  # 同時実行数を制限
```

### 4. エラーハンドリング

```yaml
- name: Run tests
  run: pytest tests/ -v
  continue-on-error: false  # エラー時は停止

- name: Optional check
  run: shellcheck scripts/*.sh
  continue-on-error: true  # エラーでも続行
```

### 5. 条件付き実行

```yaml
- name: Push to Docker Hub
  if: github.event_name == 'push' && startsWith(github.ref, 'refs/tags/')
  run: docker push myimage:latest
```

## トラブルシューティング

### ビルドが失敗する

**原因:** 依存関係やパーミッションの問題

**解決策:**
1. ローカルで`make ci-build-local`を実行
2. ログを確認: GitHub Actions > 該当ワークフロー > ログ
3. `act`でローカルデバッグ

### キャッシュが効かない

**原因:** キャッシュキーが一致しない

**解決策:**
```yaml
cache-from: type=gha,scope=${{ github.ref }}
cache-to: type=gha,mode=max,scope=${{ github.ref }}
```

### セキュリティスキャンでエラー

**原因:** SARIF形式の生成失敗

**解決策:**
```yaml
- name: Check if SARIF file exists
  run: |
    if [ ! -f "trivy-results.sarif" ]; then
      echo "SARIF file not generated"
      exit 1
    fi
```

## 関連ドキュメント

- [GitHub Actions Documentation](https://docs.github.com/actions)
- [Docker Buildx Documentation](https://docs.docker.com/buildx/working-with-buildx/)
- [Trivy Documentation](https://trivy.dev/)
- [カスタムビルドガイド](CUSTOM_BUILD.md)
- [コミットメッセージガイド](COMMIT_GUIDE.md)

---

**CI/CDパイプラインを活用して、高品質なイメージを自動的にビルドしましょう！🚀**
