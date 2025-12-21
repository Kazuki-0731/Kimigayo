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

Kimigayo OSは以下のGitHub Actionsワークフローを使用しています:

### 1. Docker Build and Push (`.github/workflows/docker-publish.yml`)

**トリガー:**
- タグプッシュ (`v*.*.*`)
- 手動実行 (workflow_dispatch)

**処理内容:**
1. マルチアーキテクチャ・マルチバリアントビルド
2. セキュリティスキャン（ShellCheck, Trivy）
3. 統合テスト実行
4. Docker Hubへプッシュ
5. マルチアーキテクチャマニフェスト作成
6. GitHub Releasesの作成

**マトリックス戦略:**
```yaml
strategy:
  matrix:
    variant: [minimal, standard, extended]
    arch: [x86_64, arm64]
```

これにより、6つのイメージが並列ビルドされます:
- minimal-x86_64
- minimal-arm64
- standard-x86_64
- standard-arm64
- extended-x86_64
- extended-arm64

### 2. Scheduled Security Scan (`.github/workflows/scheduled-security-scan.yml`)

**トリガー:**
- 週次スケジュール（毎週日曜 00:00 UTC）
- 手動実行

**処理内容:**
1. 全イメージバリアントのTrivyスキャン
2. ファイルシステムスキャン
3. 脆弱性検出時にIssue自動作成

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

```yaml
- name: Run ShellCheck (Static Analysis)
  uses: ludeeus/action-shellcheck@master
  continue-on-error: true
  with:
    scandir: './scripts'
    severity: warning
    ignore_paths: build output
```

### Trivy（脆弱性スキャン）

```yaml
- name: Run Trivy vulnerability scanner
  uses: aquasecurity/trivy-action@master
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
  uses: github/codeql-action/upload-sarif@v4
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
5. CHANGELOG.md生成
6. GitHub Releasesを作成
7. リリースアセット（tar.gz, SHA256SUMS, SHA512SUMS）を添付

#### 3. リリースノートの確認

GitHub Releasesページで以下を確認:

- リリースハイライト
- 利用可能なイメージタグ
- ビルド成果物（tar.gz）
- チェックサム（SHA256, SHA512）

### 手動リリース（workflow_dispatch）

```bash
# GitHub CLI を使用
gh workflow run docker-publish.yml -f tag=v0.2.0
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
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: myapp:scan
          format: 'sarif'
          output: 'trivy-results.sarif'

      - name: Upload to Security tab
        uses: github/codeql-action/upload-sarif@v4
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
