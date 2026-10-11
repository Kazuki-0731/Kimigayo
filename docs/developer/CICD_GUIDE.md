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
6. GitHub Release の作成（tarball 6 本 + `SHA256SUMS` + `SHA512SUMS`）
7. SARIF 連携・通知

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

#### 2. QEMUとBuildxのセットアップ

```yaml
- name: Set up QEMU
  uses: docker/setup-qemu-action@v3
  with:
    platforms: linux/amd64,linux/arm64

- name: Set up Docker Buildx
  uses: docker/setup-buildx-action@v3
  with:
    driver-opts: |
      image=moby/buildkit:latest
      network=host
    buildkitd-flags: --debug
```

**説明:**
- QEMU: ARM64のエミュレーションを可能にする
- Buildx: マルチアーキテクチャビルドを実行

#### 3. Docker Hubログイン

```yaml
- name: Log in to Docker Hub
  uses: docker/login-action@v3
  with:
    username: ${{ env.DOCKER_HUB_USERNAME }}
    password: ${{ secrets.DOCKER_HUB_ACCESS_TOKEN }}
```

**必要なシークレット:**
- `DOCKER_HUB_ACCESS_TOKEN`: Docker Hubアクセストークン

#### 4. メタデータの抽出

```yaml
- name: Extract metadata
  id: meta
  run: |
    # バージョン抽出
    VERSION=${GITHUB_REF#refs/tags/v}
    echo "version=${VERSION}" >> $GITHUB_OUTPUT

    # アーキテクチャ変換
    if [[ "${{ matrix.arch }}" == "x86_64" ]]; then
      DOCKER_ARCH="amd64"
    else
      DOCKER_ARCH="arm64"
    fi
    echo "docker_arch=${DOCKER_ARCH}" >> $GITHUB_OUTPUT
```

#### 5. Rootfsビルド

```yaml
- name: Build Kimigayo OS rootfs
  run: |
    export ARCH=${{ matrix.arch }}
    export IMAGE_TYPE=${{ matrix.variant }}
    bash scripts/build-rootfs.sh
```

#### 6. 統合テスト実行

```yaml
- name: Run integration tests
  run: |
    python3 -m pip install --upgrade pip
    pip3 install pytest hypothesis pytest-cov pytest-xdist pyyaml
    python3 -m pytest tests/integration/test_phase1_integration.py -v
```

#### 7. スモークテスト

```yaml
- name: Test Docker image (smoke test)
  run: |
    docker build -f Dockerfile.runtime -t test-image:${{ matrix.variant }}-${{ matrix.arch }} .
    docker run --rm test-image:${{ matrix.variant }}-${{ matrix.arch }} /bin/sh -c "echo 'Test passed'"
```

#### 8. Docker Hubへプッシュ

```yaml
- name: Build and push Docker image
  uses: docker/build-push-action@v5
  with:
    context: .
    file: ./Dockerfile.runtime
    platforms: linux/${{ steps.meta.outputs.docker_arch }}
    push: true
    tags: ${{ steps.meta.outputs.tags }}
    build-args: |
      VERSION=${{ steps.meta.outputs.version }}
      BUILD_DATE=${{ github.event.repository.updated_at }}
      VCS_REF=${{ github.sha }}
      IMAGE_VARIANT=${{ matrix.variant }}
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

#### 9. マルチアーキテクチャマニフェスト作成

```yaml
- name: Create and push multi-arch manifests
  run: |
    VERSION=${GITHUB_REF#refs/tags/v}

    docker buildx imagetools create \
      -t ${{ env.DOCKER_HUB_USERNAME }}/${{ env.IMAGE_NAME }}:${VERSION} \
      ${{ env.DOCKER_HUB_USERNAME }}/${{ env.IMAGE_NAME }}:${VERSION}-amd64 \
      ${{ env.DOCKER_HUB_USERNAME }}/${{ env.IMAGE_NAME }}:${VERSION}-arm64
```

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
# Trivyスキャン
trivy image --severity CRITICAL,HIGH myimage:latest

# ShellCheckスキャン
shellcheck scripts/*.sh
```

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

# 新しいバージョンでタグを作成
git tag -a v0.2.0 -m "Release v0.2.0

- 新機能A
- バグ修正B
- セキュリティ強化C
"

# タグをプッシュ
git push origin v0.2.0
```

#### 2. 自動ビルドとリリース

タグがプッシュされると、GitHub Actionsが自動的に:

1. 全バリアント・全アーキテクチャをビルド
2. テスト実行
3. セキュリティスキャン
4. Docker Hubにプッシュ
5. GitHub Releasesを作成
6. リリースアセット（tar.gz, SHA256SUMS, SHA512SUMS）を添付

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
gh workflow run release.yml -f tag=v0.2.0
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
act -j build-and-push

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
