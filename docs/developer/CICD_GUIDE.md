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
| `on-push-and-pr-build-and-verify-all-images.yml` | `main` への push・PR、手動（`component-update-pr.yml` が PR ブランチで起動する） | 日常の検証 |
| `on-tag-publish-release.yml` | `v*.*.*` タグ（公開）、手動（ビルドと検証だけ。push しない） | **Docker Hub への公開** |
| `reusable-build-and-verify-image.yml` | 他から `workflow_call` | 再利用可能なビルド本体 |
| `manual-build-image-and-kernel.yml` | 手動のみ | variant / arch を選んでビルド |
| `upstream-security-watch.yml` | 毎日 02:00 UTC、手動 | 脆弱性スキャン、上流のセキュリティ情報との差分（非公開の Project に追加） |
| `component-update-pr.yml` | 毎週月曜 03:00 UTC、手動 | 上流の更新を検知して PR 作成 |
| `on-pr-dependency-review.yml` | `main` への PR | 依存レビュー（`fail-on-severity: high`） |
| `published-image-cve-scan.yml` | 毎週月曜 04:00 UTC、手動 | 公開イメージの CVE 照合（`scan-image.sh`）。定期実行で落ちたら非公開の Project に足す |
| `on-issue-sync-private-project.yml` | Issue の作成・再開・クローズ・移動、毎日 02:30 UTC、手動 | Issue を非公開の Project にそろえる（`scripts/project-issue.py sync`。冪等） |

### 1. CI (`.github/workflows/on-push-and-pr-build-and-verify-all-images.yml`)

**トリガー:** `main` への push、`main` への PR、手動（workflow_dispatch）。
手動は `component-update-pr.yml` が更新 PR のブランチで CI を回すためにある
（`GITHUB_TOKEN` で作った PR ではワークフローが起動しないが、workflow_dispatch だけは例外）。
`develop` ブランチは 2026-10-13 にトリガーから外した（ブランチが存在しない）。

**処理内容:**
1. ShellCheck（`scripts/*.sh`・`scripts/lib/*.sh`・`.claude/hooks/*.sh`）
2. リンク検査（`scripts/check-links.py`。`#見出し` へのリンクも見る）と
   古い記述の検査（`scripts/check-stale-docs.py`）
3. pytest（`tests/unit`）
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

> **`on-push-and-pr-build-and-verify-all-images.yml` はカーネルをビルドしません**（2026-10-10 に外しました）。
> 成果物は rootfs だけを詰めた Docker イメージで、コンテナはホストの
> カーネルで動くため、CI がカーネルを作ってもイメージの中身は
> 1 バイトも変わりません。それでいて 1 run あたり数十分かかっていました。
>
> **したがってカーネル関連の変更は `on-push-and-pr-build-and-verify-all-images.yml` が緑でも検証されていません。**
> `versions.mk` の `KERNEL_VERSION` や `src/kernel/` を触ったときは、
> `manual-build-image-and-kernel.yml` を `build_kernel=true` で手動実行するか、
> コンテナ内で `make kernel` を通してください。

### 2. Release (`.github/workflows/on-tag-publish-release.yml`)

**トリガー:**
- タグ push (`v*.*.*`) — **公開するのはこれだけ**
- 手動実行 (workflow_dispatch、`tag` を入力。空なら版は `edge`) —
  ビルド・検証・スキャン・SBOM の保存まで。**Docker Hub には push しない**
  （→ [手動実行](#手動実行workflow_dispatch)）

**処理内容:**
1. 版の解決（`meta` ジョブ。タグ名から `v` を外す。手動実行では入力 `tag`、空なら `edge`）
2. ShellCheck
3. マルチアーキテクチャ・マルチバリアントビルド（6 ジョブ）
4. イメージ検証・スキャン・SBOM の保存と、Docker Hub への push（push はタグのときだけ）
5. マルチアーキテクチャマニフェスト作成（タグのときだけ）
6. **Cosign のキーレス署名**（`sign` ジョブ。タグのときだけ）
7. GitHub Release の作成（tarball 6 本 + `SHA256SUMS` + `SHA512SUMS` + SBOM 6 本 + 対応するソース 4 本。タグのときだけ）。
   ソースは `sources` ジョブ（`scripts/collect-sources.sh`）が集め、失敗したら Docker Hub に push しない
8. 通知（Cosign の署名結果も載せる）

> **`CHANGELOG.md` は自動生成されません。手で書きます。**
> `make changelog` は `build/CHANGELOG.generated.md` に下書きを出すだけで、
> `CHANGELOG.md` を書き換えません。**タグを打つ前に必ず更新してください**
> （2026-10-09 まで 0.1.0 止まりで、2 回のリリースが抜けていました）。

> **タグを push した瞬間に Docker Hub の `latest` を含む公開イメージが
> 差し替わります。** 取り消せないので、タグとリリースは毎回明示的な承認を
> 取ってください（`.claude/hooks/guard-bash.sh` が機械的に止めます）。

### 3. Build Workflow (`.github/workflows/reusable-build-and-verify-image.yml`)

**トリガー:** 他のワークフローからの `workflow_call` のみ

`on-push-and-pr-build-and-verify-all-images.yml` と `manual-build-image-and-kernel.yml` が共有するビルド本体です
（`on-tag-publish-release.yml` はこれを呼ばず、同じ入口の `make build-no-kernel` を自前のジョブで回します）。
入力に `variant` / `arch` / `build_kernel` / `upload_artifacts` を取ります。
`build_kernel` の既定は `false` です。

イメージを作ったあと、verify-image ジョブで次の2つを実行します
（どちらも失敗すればジョブが落ちます）:

1. `scripts/verify-image.sh` — イメージを起動しての検証（34 項目、minimal は 33）
2. `bash scripts/scan-image.sh` — 出荷物の秘密情報スキャン（Trivy の
   secret スキャナでイメージを見る）と CVE 照合（出荷物の版から SBOM を作り
   Grype で照合する）。SBOM は `sbom-<variant>-<arch>` の成果物として残ります

> **NVD に新しい CVE が載ると、コードを変えていない push でも落ちます。**
> 出荷物に未対応の CVE があるという信号なので、握り潰さずに
> パッチを当てるか版を上げます（`security-review` skill）。

### 4. Manual Build (`.github/workflows/manual-build-image-and-kernel.yml`)

**トリガー:** 手動のみ（workflow_dispatch）

variant と arch を選んでビルドします。**カーネルを CI でビルドする
唯一の経路**で、`build_kernel=true` を指定します。

```bash
gh workflow run manual-build-image-and-kernel.yml \
  -f variant=standard -f arch=x86_64 -f build_kernel=true
```

### 5. Security Scan (`.github/workflows/upstream-security-watch.yml`)

**トリガー:**
- 毎日 02:00 UTC
- 手動実行

**処理内容:**
1. 構成要素の版の確認（`version-check`。musl と BusyBox の新版）。
   以前は Alpine の secdb に載っているパッケージ数も数えていたが、
   Kimigayo の出荷物と関係が無い数字なので 2026-10-13 に外した
2. リポジトリのファイルシステムスキャン（Trivy、`trivy-filesystem-scan`）
3. musl か BusyBox の新版を検知したときに Issue を自動作成（脆弱性の検出では起票しない）
4. 上流のセキュリティ情報との差分（`upstream-fix-watch`）。`scripts/watch-upstream-fixes.py` が
   Debian の security-tracker・Alpine aports・上流 git・CISA KEV を見て、
   `docs/security/upstream-triage.tsv`（仕分け済みの一覧）に無いものを出す。
   修正が出たら非公開の Project に項目を足して Discord に通知し、判定できなかったときも Discord に失敗を送る

> **イメージの Trivy スキャン（`trivy-image-scan`）は 2026-10-09 に外しました。**
> Kimigayo は `scratch` 上の手組み rootfs でパッケージデータベースを
> 持たないため、Trivy は対象を 1 つも識別できません
> （`Target: -` / `Not scanned` / `Results: 0`）。
> **「脆弱性 0 件」ではなく「スキャンしていない」**という意味です。
> 出荷物の構成要素の CVE 照合は `scripts/scan-image.sh` が行い、
> 公開イメージに対しては
> [7. Dependency Review](#7-dependency-review-githubworkflowson-pr-dependency-reviewyml-と-published-image-cve-scan-githubworkflowspublished-image-cve-scanyml)
> の `published-image-scan` が毎週回します。
> ファイルシステムスキャン（`trivy-fs-scan`）はリポジトリ側の依存を
> 見るので有効です。

### 6. Base Image Update (`.github/workflows/component-update-pr.yml`)

**トリガー:** 毎週月曜 03:00 UTC、手動（`force_rebuild` を入力）

上流（musl / BusyBox / OpenRC）の更新を検知して、`versions.mk` を
書き換える PR を作成します（カーネルと Alpine は見ていません。
チェックサム表は更新しないので、マージ前に手で足します）。

- 取得した版が空・版の形でない・現在より新しくないときは、PR を作らずに失敗します
  （2026-10-12 までは後段に値が渡っておらず、`versions.mk` の版を空にした PR を作っていた）
- 変更内容は PR の本文にだけ書きます（以前のように `UPDATES.md` をコミットしない）
- PR は `GITHUB_TOKEN` で作るため、そのままでは CI が起動しません。
  **ワークフローが PR ブランチで `on-push-and-pr-build-and-verify-all-images.yml` を workflow_dispatch で起動します**
- `force_rebuild=true` で手動実行すると、更新が無くても空コミットの PR を作ります
  （ワークフロー自体の動作確認用）

**この PR は「上流が動いた」という一次情報**なので、
バージョン更新の起点として先に見てください。

### Dependabot（`.github/dependabot.yml`）

ワークフローではありませんが、毎週月曜 03:00 UTC に GitHub Actions の
更新 PR を作ります（ラベルは `依存`・`自動`、件名は `⬆️ Bump ...`）。
Dockerfile のベースイメージは見ません。`FROM alpine:${ALPINE_VERSION}` は
Dependabot が追えず、Alpine を含む構成要素の版は `versions.mk` と
`component-update-pr.yml` が扱うためです（2026-10-13 に docker のブロックを外した）。

### 7. Dependency Review (`.github/workflows/on-pr-dependency-review.yml`) と Published Image CVE Scan (`.github/workflows/published-image-cve-scan.yml`)

2026-10-16 まで `dependency-review.yml` 1 本にまとまっていたものを、性格ごとに分けた。

| ワークフロー | ジョブ | いつ | 何をするか |
| --- | --- | --- | --- |
| `on-pr-dependency-review.yml` | `dependency-review` | `main` への PR | 依存のレビュー（`fail-on-severity: high`） |
| `published-image-cve-scan.yml` | `published-image-scan` | 毎週月曜 04:00 UTC・手動 | Docker Hub の `ishinokazuki/kimigayo-os:latest`（standard / amd64）を pull し、`scripts/scan-image.sh` で CVE 照合と秘密情報スキャン。SBOM を `sbom-published-latest` として保存 |
| `published-image-cve-scan.yml` | `add-to-project` | 定期実行で `published-image-scan` が失敗したとき | 非公開の Project に項目を足す（公開の Issue は立てない） |

以前同居していた `vulnerability-scan` のうち、ビルドスクリプトの検査（コメント以外の `http://` と
`eval` があれば落ちる。`scripts/lib/versions.sh` の `eval` とループバックの `http://` だけ許可）は
`on-push-and-pr-build-and-verify-all-images.yml` の ShellCheck ジョブに移した（push ごと）。
週 1 回のリポジトリの Trivy は、push ごとと毎日の検査に重なるので外した。

`published-image-scan` が見るのは `latest` だけです。構成要素の版は
バリアント・アーキテクチャで共通なためです。新しい CVE はコードが
変わらなくても公開されるので、push ではなく定期で回します。

> 以前ここにあった「Check component versions against CVE databases」
> ステップは、CVE データベースを一切照会せず `versions.mk` の版を
> 表示するだけでした（2026-10-11 に `published-image-scan` に置き換え）。

> v3.0.1 の公開時点では既知の CVE が 5 件検出され、このジョブは失敗していました。
> v3.0.2 では 5 件すべてにパッチを当て、`/.kimigayo-build-info` の
> `PATCHED_CVES` に記録して照合から除外しています
> （→ [SECURITY_AUDIT.md](../security/SECURITY_AUDIT.md)）。
> 新しい CVE が NVD に載れば、コードを変えていなくても再び失敗します。

## ビルドプロセス

### ステップバイステップ

#### 1. リポジトリチェックアウト

```yaml
- name: Checkout repository
  uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803 # v6.1.0
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

> **QEMU は使いません。** arm64 のビルドは `ubuntu-latest`（x86_64）からの
> clang / lld によるクロスコンパイルで、**イメージの検証（と release の push）
> だけが `ubuntu-24.04-arm` ネイティブランナー**で走ります。
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

版は `meta` ジョブがタグ名（`refs/tags/v3.1.0` → `3.1.0`）から解決し、
後続のジョブへ `needs.meta.outputs.version` として渡します
（`scripts/get-version.sh` を使うのは `reusable-build-and-verify-image.yml` の方です）。

> **ここを渡し忘れると、タグ名だけ合っていて中身の版がずれます。**
> 以前 `on-tag-publish-release.yml` が版を渡さず、`os-release` が `dev` になる事故が
> ありました。下の検証（`EXPECT_VERSION`）はそれを止めるためのものです。

#### 5. Rootfsビルド

**`on-push-and-pr-build-and-verify-all-images.yml` とまったく同じ入口を使います。** 経路が分かれていると、
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
      --build-arg TARBALL_PATH="output/kimigayo-${{ matrix.variant }}-${{ needs.meta.outputs.version }}-${{ matrix.arch }}.tar.gz" \
      --build-arg VERSION="${{ needs.meta.outputs.version }}" \
      --build-arg BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
      --build-arg VCS_REF="${{ github.sha }}" \
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

**検証の実体は `scripts/verify-image.sh`**（34 項目、minimal は 33）で、`on-push-and-pr-build-and-verify-all-images.yml` と
ローカルの `make` も同じものを呼びます。`EXPECT_VERSION` を渡すと、
`LABEL version` と `/etc/os-release` の `VERSION_ID` がこの版と
一致しなければ落ちます。

> **`on-tag-publish-release.yml` に Trivy の脆弱性スキャンも pytest も統合テストもありません。**
> Trivy のイメージの脆弱性スキャンは、パッケージデータベースが無く
> 何も識別できないため 2026-10-09 に外しました。
> `on-tag-publish-release.yml` では push の前に `scripts/scan-image.sh` で秘密情報
> （Trivy の secret スキャナ）と CVE（Grype）を照合し、作った SBOM を
> GitHub Release に添付します。
> pytest は `on-push-and-pr-build-and-verify-all-images.yml` 側で回ります。
> 以前は検証に `continue-on-error` が付いており、
> tarball が小さくても `exit 0` でスキップしていました。

#### 9. 検証済みイメージを push

**タグ push のときだけ**走ります（`PUBLISH` は `github.event_name == 'push'` かつ
タグのときだけ `true`。Docker Hub へのログインも同じ条件）。

```yaml
- name: Push verified image
  if: env.PUBLISH == 'true'
  run: |
    docker push "${{ steps.tags.outputs.primary }}"
    docker push "${{ steps.tags.outputs.moving }}"
```

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

> **署名されているのは v3.0.2 以降です。** v3.0.1 以前の公開イメージは
> 署名されていません。検証には cosign v3 以上が要ります
> （v2 では `no signatures found` になります）。

## テスト戦略

### 1. 単体テスト

```bash
# ローカル実行
docker compose run --rm kimigayo-build pytest tests/unit/ -v

# CI（on-push-and-pr-build-and-verify-all-images.yml の tests ジョブ）
docker compose run --rm -w /build/kimigayo kimigayo-build \
  pytest tests/unit -q
```

`tests/unit` は 3 ファイル（`test_busybox_config_explicit.py`・
`test_check_links.py`・`test_memo_paths.py`）で 65 件（2026-10-14）。
プロパティテスト（hypothesis）と Python モジュールのテストは、検証対象の
`src/` の Python モジュールごと 2026-10-14 に削除した
（どのスクリプトからも使われていなかった）。

### 2. 統合テスト

イメージを起動して見るシェルのテストがあります（ホストで、先に
`make ci-build-local` でイメージを作っておく）。

```bash
make test-docker       # tests/integration/test_docker_startup.sh
make test-func         # tests/integration/test_functionality.sh
```

構成要素ごとの統合テストはビルドコンテナ内の `make test-musl` /
`test-busybox` / `test-openrc` です。

### 3. イメージの検証

```bash
# イメージを実際に起動して検査する（CI・release と同じスクリプト）
bash scripts/verify-image.sh kimigayo-os:standard-x86_64 standard x86_64
```

> 以前の「`/bin/sh` と `busybox --help` が動くか」だけのスモークテストは、
> OpenRC も `libc.so` も入っていないイメージでも通っていたため、
> `verify-image.sh` に置き換えました。

### 4. セキュリティテスト

```bash
# 出荷物の CVE 照合（SBOM + Grype）と秘密情報スキャン
make scan-image VARIANT=standard ARCH=x86_64

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
> 構成要素（musl / BusyBox / OpenRC）の CVE 照合は `make scan-image`
> を使います。イメージ内のバイナリを実行して読んだ版で CycloneDX の
> SBOM を作り、Grype で NVD の CPE と照合します
> （→ [DEVELOPMENT.md](../../DEVELOPMENT.md#セキュリティスキャン)）。
> カーネルはイメージに入らないので照合の対象外です。

## セキュリティスキャン

### ShellCheck（静的解析）

**外部 Action は必ずコミット SHA で固定します。** `@master` 参照は
供給網のリスクであり、再現性もありません（2026-10-09 に固定しました）。

ShellCheck は Action を使わず、版をダイジェストで固定した
`koalaman/shellcheck` のイメージを直接 `docker run` します
（`on-push-and-pr-build-and-verify-all-images.yml` と `on-tag-publish-release.yml`。ローカルの `make shellcheck-scan` と同じ対象・重大度）。

```yaml
- name: Run ShellCheck
  run: |
    set -euo pipefail
    docker run --rm -v "${PWD}:/mnt" -w /mnt \
      koalaman/shellcheck:v0.11.0@sha256:61862eba... \
      --severity=warning \
      scripts/*.sh scripts/lib/*.sh .claude/hooks/*.sh
```

`.claude/hooks` も検査対象です（Hook はこのプロジェクトの作業ルール
そのものなので、`scripts/` と同じ基準で静的解析します）。
**2026-10-12 までは検査されていませんでした。**
以前使っていた `ludeeus/action-shellcheck` は、`additional_files: '.claude/hooks'` を
`./scripts` の中での `find -name` のパターンとして扱っていたためです。

### Trivy（リポジトリのファイルシステムスキャン）

Trivy の脆弱性スキャンは**リポジトリ**に対してだけ使います（`on-push-and-pr-build-and-verify-all-images.yml`・
`upstream-security-watch.yml`）。イメージの脆弱性スキャンには
使いません（何も識別できないため）。イメージに対しては
`scripts/scan-image.sh` の中で**秘密情報スキャン（`--scanners secret`）だけ**に使います。

```yaml
- name: Run Trivy filesystem scan
  uses: aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25 # v0.36.0
  with:
    scan-type: 'fs'
    scan-ref: '.'
    format: 'sarif'
    output: 'trivy-results.sarif'
    severity: 'CRITICAL,HIGH'
```

**SARIF形式でGitHub Security tabに結果をアップロード:**

```yaml
- name: Upload Trivy results to GitHub Security tab
  uses: github/codeql-action/upload-sarif@24c54180a607b1449ed407dd24f251e4e9147c8d # v4.38.3
  with:
    sarif_file: 'trivy-results.sarif'
```

### 出荷物のスキャン（`scripts/scan-image.sh`）

イメージそのものは `scripts/scan-image.sh` で検査します。

| どこで | 何を | 失敗したら |
| --- | --- | --- |
| `reusable-build-and-verify-image.yml`（ビルドごと） | CVE 照合 + 秘密情報 | ジョブが落ちる |
| `on-tag-publish-release.yml`（Docker Hub への push 前） | CVE 照合 + 秘密情報。SBOM を Release に添付 | push しない |
| `published-image-cve-scan.yml` の `published-image-scan`（毎週月曜 04:00 UTC・手動） | Docker Hub の `latest` に CVE 照合 + 秘密情報 | ジョブが落ちる。定期実行のときだけ非公開の Project に項目を足す |

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

# 新しいバージョンでタグを作成（例。2026-10-15 時点の最新は v3.1.0）
git tag -a v3.1.1 -m "Release v3.1.1

- 新機能A
- バグ修正B
- セキュリティ強化C
"

# タグをプッシュ（**ユーザーの明示的な承認が必要**）
git push origin v3.1.1
```

#### 2. 自動ビルドとリリース

タグがプッシュされると、GitHub Actionsが自動的に:

1. 版の解決（タグ名から）
2. ShellCheck
3. 全バリアント・全アーキテクチャをビルド（6 ジョブ）
4. **イメージを起動して検証**（`scripts/verify-image.sh`、34 項目、minimal は 33）
5. 検証を通ったものだけ Docker Hub にプッシュ
6. マルチアーキテクチャマニフェスト作成
7. **Cosign のキーレス署名**（v3.0.2 から）
8. GitHub Releases を作成
9. リリースアセット（tar.gz 6 本 + SHA256SUMS + SHA512SUMS + SBOM 6 本 + 対応するソース 4 本）を添付

**Trivy の脆弱性スキャンと pytest は `on-tag-publish-release.yml` では走りません**
（pytest は `on-push-and-pr-build-and-verify-all-images.yml` 側。Trivy のイメージの脆弱性スキャンは何も識別できないため
2026-10-09 に外しました。秘密情報と CVE は `scan-image.sh` で見ます）。

**`CHANGELOG.md` は自動生成されません。** タグを打つ前に手で更新して
おいてください（→ [2. Release](#2-release-githubworkflowson-tag-publish-releaseyml)）。

#### 3. リリースノートの確認

GitHub Releasesページで以下を確認:

- リリースハイライト
- 利用可能なイメージタグ
- ビルド成果物（tar.gz）
- チェックサム（SHA256, SHA512）

### 手動実行（workflow_dispatch）

```bash
# ビルド・検証・スキャンだけ（Docker Hub には push しない）
gh workflow run on-tag-publish-release.yml -f tag=v3.1.1
```

または、GitHubのActionsタブから手動実行。

> **手動実行は Docker Hub に push しません。** タグ push と同じ経路で
> 6 本をビルドし、`verify-image.sh` と `scan-image.sh` を通して SBOM を
> 成果物に残すところまでです。`create-manifest`・`sign`・
> `create-github-release` も走りません。`tag` を省くと版は `edge` になります。
> **公開は `v*.*.*` タグの push だけ**です。公開をやり直したいときは、
> タグを打ち直すか、タグの run を Actions の Re-run で回します。
>
> 2026-10-12 までは手動実行でも `verify-and-push` が push しており、
> 既定の `tag` のままだと `latest-<variant>-<arch>` を上書きしていました
> （マニフェスト・署名・Release はタグのときしか作られないので、
> 「push されたが署名もマニフェストも無い」状態を作れた）。

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
# on-tag-publish-release.yml の実際のジョブ名は次の8つ:
#   meta / shellcheck / build / verify-and-push /
#   create-manifest / sign / create-github-release / notify
act -j build

# 環境変数を指定
act -s DOCKER_HUB_ACCESS_TOKEN=your_token
```

### Makefileでのローカルビルド

```bash
# CI相当のビルド
make ci-build-local

# CI相当のビルド + Docker Hub へのプッシュ
make ci-build-push
```

> **`ci-build-push` は Docker Hub に直接 push します**
> （`ishinokazuki/kimigayo-os:<variant>-<arch>` と
> `<VERSION>-<variant>-<arch>`。リリースのタグとは名前の形が違います）。
> 公開物を変える操作なので承認が要り、`.claude/hooks/guard-bash.sh` も止めます。

> **`make ci-build-local` は macOS ホストでは通りません。**
> ホスト側で `scripts/build-rootfs.sh` を直接叩き、その中で
> `build-musl.sh` を実際に呼ぶため、musl の `configure` が
> `unsupported long double type` で落ちます。
> `ARCH` を省略するとホストの `Makefile` の既定値 `x86_64` が渡ります
> （`build-rootfs.sh` を直接叩いたときだけ `uname -m` から自動検出します）。
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
# .github/workflows/upstream-security-watch.yml
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

      # Kimigayo をベースにしたイメージでは、Trivy はベース側の構成要素を
      # 識別できない（パッケージ DB が無い）。自分で持ち込んだものだけが対象
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
```

> **`continue-on-error: true` は付けません。** Kimigayo 自身は ShellCheck を
> 含む検査のどれにも付けていません（止められない検査は意味がないため）。

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
