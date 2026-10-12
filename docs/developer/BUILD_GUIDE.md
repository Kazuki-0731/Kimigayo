# Kimigayo OS ビルドガイド

このガイドでは、Kimigayo OSのビルド方法とカスタマイズについて詳しく説明します。

## 目次

- [ソースからビルドする](#ソースからビルドする)
- [ビルド環境のセットアップ](#ビルド環境のセットアップ)
- [ビルドの流れ](#ビルドの流れ)
- [カスタマイズ](#カスタマイズ)
- [クロスコンパイル](#クロスコンパイル)
- [ビルド出力](#ビルド出力)
- [再現可能ビルド](#再現可能ビルド)
- [ビルドのデバッグ](#ビルドのデバッグ)
- [トラブルシューティング](#トラブルシューティング)
- [CI/CD との統合](#cicd-との統合)

## ソースからビルドする

### 前提条件

- Docker & Docker Compose
- Git
- 最低 2GB RAM（推奨 4GB）

### ビルド手順

**推奨方法（リアルタイム出力）：**

```bash
# リポジトリをクローン
git clone https://github.com/Kazuki-0731/Kimigayo.git
cd Kimigayo

# Docker環境を構築
make docker-build

# Dockerビルド環境に入る
make shell

# コンテナ内でビルド実行（リアルタイム出力で確認できる）
make build

# テスト実行（コンテナ内）
make test
```

**簡単コマンド（ホストOSから）：**

```bash
# ホストOSから直接ビルド（ログは完了後に表示）
make build

# ホストOSから直接テスト実行
make test
```

### よく使うコマンド

**ホストOSから実行：**

```bash
# ヘルプ表示
make help

# Dockerビルド環境にログイン
make shell

# ビルド（簡単だがログは完了後）
make build

# クリーンアップ
make clean

# すべてクリーンアップ（コンテナ+volume。約150MBの再ダウンロードになる）
make clean-all

# ビルドログを確認（最新100行）
make log-kernel
make log-musl
make log-openrc
```

**コンテナ内で実行（リアルタイム出力）：**

```bash
# まずコンテナに入る
make shell

# ビルド（リアルタイムで出力確認可能）
make build

# クリーンアップ
make clean

# テスト実行
make test
```

### ビルド成果物

`make build` を実行すると、以下の場所にビルド成果物が生成されます：

#### 1. **rootfs（ルートファイルシステム）**

OSの実体となるファイルシステム構造が生成されます。

```bash
build/rootfs/
├── bin/          # 実行可能ファイル (sh, busybox, etc.)
├── etc/          # 設定ファイル
├── lib/          # 共有ライブラリ
├── sbin/         # システム管理コマンド
├── usr/          # ユーザープログラム
└── var/          # 可変データ
```

**確認方法:**
```bash
ls -la build/rootfs/
```

#### 2. **tarballイメージ**

配布用のtar.gzアーカイブファイルが生成されます。

```bash
output/
├── kimigayo-minimal-latest-x86_64.tar.gz     # Minimal版 (約1.3MB)
├── kimigayo-standard-latest-x86_64.tar.gz    # Standard版 (約1.4MB)
└── kimigayo-extended-latest-x86_64.tar.gz    # Extended版 (約1.5MB)
```

リリース時は `SHA256SUMS` と `SHA512SUMS` が GitHub Release に添付されます。

**使用方法:**
```bash
# tarballからDockerイメージを作成
docker import output/kimigayo-standard-latest-x86_64.tar.gz kimigayo:test

# 起動
docker run -it kimigayo:test /bin/sh
```

#### 3. **Dockerイメージ**

完全なCI/CDビルド (`make ci-build-local`) を実行するとDockerイメージが生成されます。

```bash
# 完全ビルド（rootfs + tarball + Dockerイメージ）
make ci-build-local

# 全バリアントビルド
make ci-build-all
```

**生成されるイメージ:**
```bash
# イメージ一覧表示
docker images | grep kimigayo

# 主要イメージ
kimigayo-os:standard-x86_64    # Standard版 (2.60MB / 2026-10-12 実測)
kimigayo-os:minimal-x86_64     # Minimal版 (2.46MB)
kimigayo-os:extended-x86_64    # Extended版 (2.62MB)
```

**使用方法:**
```bash
# ローカルビルドイメージを起動
docker run -it kimigayo-os:standard-x86_64 /bin/sh
```

#### ビルド成果物の関係

```
make build
    ↓
build/rootfs/ (ファイルシステム)
    ↓
make package-rootfs
    ↓
output/*.tar.gz (配布用アーカイブ)
    ↓
make build-image
    ↓
Dockerイメージ (コンテナ実行用)
```

### 詳細なビルドオプション

Dockerビルド環境内で実行することで、リアルタイムなビルド出力が確認できます：

```bash
# Dockerビルド環境に入る
make shell

# コンテナ内で特定のアーキテクチャでビルド
make build TARGET_ARCH=arm64

# コンテナ内で詳細ログ付きでビルド
make build V=1

# コンテナ内でプロパティテストのみ実行
pytest tests/property/ -v

# コンテナ内で単体テストのみ実行
pytest tests/unit/ -v
```

**ダウンロードキャッシュについて：**

ローカルビルドでは、ダウンロードしたソースコード（カーネル、musl、BusyBox、OpenRC）がDocker Volumeにキャッシュされます。2回目以降のビルドは大幅に高速化されます。

```bash
# ホストOSから実行
make clean-cache  # キャッシュをクリア
make clean-all    # すべてクリア
```

**ビルドログの確認：**

Dockerビルド環境内でビルドを実行すると、リアルタイムでビルド出力を確認できます：

```bash
# Dockerビルド環境に入る
make shell

# コンテナ内でビルドログをリアルタイム確認
tail -f /build/kimigayo/build/logs/kernel-build.log   # カーネルビルドログ
tail -f /build/kimigayo/build/logs/musl-build.log     # musl libcビルドログ
tail -f /build/kimigayo/build/logs/openrc-build.log   # OpenRCビルドログ

# コンテナ内で過去のログを確認
tail -n 100 /build/kimigayo/build/logs/kernel-build.log
cat /build/kimigayo/build/logs/musl-build.log
```

**バックグラウンドビルド（tmux使用）：**

カーネルビルドなど時間のかかるビルドをバックグラウンドで実行し、完了時に通知を受け取れます：

```bash
# Dockerビルド環境に入る
make shell

# tmuxセッションを開始
tmux new -s build

# ビルド実行（完了したら通知メッセージを表示）
make build && echo "✅ Build Success" || echo "❌ Build Failed"

# Ctrl+B を押してから D を押してデタッチ（バックグラウンド実行）
# ビルドはバックグラウンドで継続される

# 後で状態を確認する場合
tmux attach -t build

# tmuxセッション一覧を確認
tmux ls

# セッションを終了する場合
tmux kill-session -t build
```

### ビルドが失敗する・止まるとき

ビルドが失敗する場合や、途中で止まる場合は、**軽いものから**試してください：

```bash
# 1) 構成要素ごとに作り直す（コンテナ側のターゲット）
docker compose run --rm kimigayo-build make clean-busybox   # clean-musl / clean-kernel / clean-openrc も

# 2) ビルド成果物をすべて消す（ダウンロード済みのソースは残る）
make clean
make build

# 3) 最後の手段: ビルド環境ごと作り直す（約150MBの再ダウンロードとフルビルドになる）
make clean-all
make docker-build
make build
```

**注意:** カーネルビルド中に "The source tree is not clean" エラーが出る場合、ビルドスクリプトが自動的に`make mrproper`を実行してクリーニングします。

## ビルド環境のセットアップ

### 必要なソフトウェア

| ソフトウェア | 目的 |
|------------|------|
| Docker（Compose v2 の `docker compose`） | ビルド環境の提供。ビルドはすべてコンテナ内で走る |
| Git | ソースの取得。ビルドが版（`git describe`）とコミット時刻を読む |
| Make | 入口（`Makefile`） |

### システム要件

- **RAM**: 最低 2GB、推奨 4GB 以上（`docker-compose.yml` の `memory: 2G`）
- **ディスク**: 10GB 以上の空き
- **ホスト OS**: Linux / macOS / Windows（WSL2）

> **`docker-compose.yml` は `platform: linux/amd64` を固定しています。**
> Apple Silicon の Mac では x86_64 が QEMU のエミュレーションになり、
> musl・BusyBox・OpenRC は通りますが、**カーネルのフルビルドは現実的ではありません**。
> フルビルドは GitHub Actions に任せる方針です
> （→ [CLAUDE.md](../../CLAUDE.md)「フルビルドは x86_64 / arm64 とも GitHub Actions で回す」）。

### 初期セットアップ

```bash
git clone https://github.com/Kazuki-0731/Kimigayo.git
cd Kimigayo

make docker-build      # ビルド環境のイメージ（Alpine ベース）
make info              # ビルド設定の確認
make print-versions    # 構成要素の版（versions.mk）
```

## ビルドの流れ

構成要素の版は [versions.mk](../../versions.mk) だけに書かれています。
`make build`（コンテナ内）は次の順に作ります。

```
versions.mk ─┬→ download-musl    → build-musl     [1/4]
             ├→ download-kernel  → apply-kernel-patches → build-kernel  [2/4]
             ├→ download-busybox → apply-busybox-patches → build-busybox [3/4]
             └→ download-openrc  → build-openrc   [4/4]
                                        ↓
                              build-rootfs.sh（build/rootfs/）
                                        ↓
                        package-rootfs（output/*.tar.gz）
                                        ↓
                    Dockerfile.runtime → Docker イメージ → smoke test
```

**カーネルは Docker イメージに入りません**（コンテナはホストのカーネルで動きます）。
CI でもカーネルは作りません。ベアメタル／QEMU を試すときだけ作ります
（→ [CLAUDE.md](../../CLAUDE.md)「カーネルは CI で作らない」）。

### ビルドコマンド

```bash
# ホスト側
make help              # 全ターゲット
make info              # ビルド設定
make status            # どこまでできているか
make build             # コンテナ内で make build を実行
make test              # コンテナ内で pytest（unit + property）
make test-integration  # 統合テスト
make shellcheck-scan   # scripts/ と .claude/hooks/ の静的解析
make security-scan     # scan-image（成果物の CVE・秘密情報）+ Trivy FS + ShellCheck

# コンテナ内（make shell で入ってから）
make test-unit
make test-property
```

> `make test-unit` / `make test-property` はコンテナ側（`build-system/Makefile`）
> にしかありません。ホストからは `python3 -m pytest tests/unit -q` でも走ります。

### バリアントとアーキテクチャ

**バリアントもアーキテクチャも、ターゲットではなく変数で選びます。**
コンテナ側とホスト側で変数名が違うので注意してください。

```bash
# コンテナ内（build-system/Makefile）: IMAGE_TYPE と TARGET_ARCH
docker compose run --rm -T kimigayo-build make build IMAGE_TYPE=minimal TARGET_ARCH=x86_64
docker compose run --rm -T kimigayo-build make build IMAGE_TYPE=extended TARGET_ARCH=arm64

# ホスト側（rootfs → イメージ → smoke まで。Linux ホストのみ）: VARIANT と ARCH
make ci-build-local VARIANT=minimal ARCH=x86_64
make ci-build-all ARCH=x86_64          # 3 バリアントを順に
```

- 既定は `standard` / `x86_64`
- **ホストの `make build ARCH=arm64` はアーキテクチャを変えません**
  （ホストの `build` はコンテナへ変数を渡さない）。上のようにコンテナ側で
  `TARGET_ARCH` を渡してください
- `docker compose run` の出力をパイプやファイルに繋ぐときは **`-T` を付けます**。
  付けないと出力が消え、スクリプトが走らないまま成功扱いになることがあります
- **ホストの `make ci-build-local` は macOS では通りません**
  （musl の `configure` が `unsupported long double type` で落ちる）

| バリアント | 目標（SPECIFICATION.md §8.3） | 実測（v3.0.2、x86_64 / arm64） | BusyBox アプレット |
|-----------|------|------|------|
| **Minimal** | < 5MB | 2.46MB / 2.83MB | 367（`vi`・`wget`・`du`・`less` が無い） |
| **Standard** | < 15MB | 2.60MB / 2.98MB | 400 |
| **Extended** | < 50MB | 2.62MB / 3.01MB | 411 |

**3 バリアントの違いは BusyBox の config（`src/busybox/config/<variant>.config`）だけ**です。
musl・OpenRC はどのバリアントにも同じものが入り、カーネルはどれにも入りません。

## カスタマイズ

### アプリを載せたイメージを作る

**Kimigayo のビルドに手を入れる必要はありません。** 公開イメージを
ベースにして、マルチステージビルドで持ち込みます
（→ [CUSTOM_BUILD.md](CUSTOM_BUILD.md)、動く例は [examples/](../../examples/)）。

### BusyBox のアプレットを変える

`src/busybox/config/{minimal,standard,extended}.config` を編集します。

- **書いていない項目は Kconfig の既定値になります。** 外したいものは
  `# CONFIG_XXX is not set` と明示してください。書かなかったために
  `dpkg`・`rpm` が入っていた、`wget` の HTTPS が落ちていた、という前例があります
  （`tests/unit/test_busybox_config_explicit.py` が主要な項目を見ています）
- **config を変えただけでは再ビルドされません。** ビルド済みかどうかは
  版・バリアント・リンク方法で判定するので、成果物を消してから作ります

```bash
rm -rf build/busybox-build-x86_64 build/busybox-install-x86_64
docker compose run --rm -T kimigayo-build make busybox \
  TARGET_ARCH=x86_64 IMAGE_TYPE=extended
```

### カーネル設定

**使われるのは `src/kernel/config/<arch>.config` だけです**
（`scripts/build-kernel.sh` が選びます）。無ければ上流の defconfig を使い、
プレースホルダの `<arch>.config` を書き出します。

```bash
vi src/kernel/config/x86_64.config
docker compose run --rm -T kimigayo-build make kernel TARGET_ARCH=x86_64
```

> `make kernel-menuconfig` は存在せず、`make kernel KERNEL_CONFIG=...` も
> 効きません。`menuconfig` を使いたいときはカーネルのソースツリー
> （`build/kernel-src/linux-<version>/`）で直接叩きます。

### コンパイルフラグ

**強化フラグは `scripts/build-{musl,busybox,openrc}.sh` に直書きされています**
（`-fPIE`・`-fstack-protector-strong`・`-D_FORTIFY_SOURCE=2`・
`-Wl,-z,relro -Wl,-z,now`・`-Wl,-z,noexecstack`）。
`make build CFLAGS=...` で渡しても、スクリプトが `CFLAGS` を上書きするので効きません。

> `config.mk` にもフラグが書かれていますが、**どこからも読まれていません。**
> パッケージリスト（`build/packages/*.list`）やビルド設定ファイル
> （`custom-image.yaml`）による構成の変更も、**仕組みとして存在しません**。

## クロスコンパイル

**クロスツールチェーンのセットアップは不要です。** ビルド環境の
イメージ（`make docker-build`）に入っています。arm64 は clang / lld で
クロスコンパイルします。

```bash
docker compose run --rm -T kimigayo-build make build TARGET_ARCH=arm64
```

**両アーキテクチャを一度に作るターゲットはありません。**
`TARGET_ARCH` を変えて 2 回回すか、GitHub Actions に任せます。
**RISC-V は未対応**です（`SPECIFICATION.md` 8.2 の「将来的に」）。

> arm64 を手元でクロスビルドするなら、compose ではなく
> `docker run --memory 8g` で直接叩きます（compose の `memory: 2G` では
> `meson setup` が OOM で落ちる）。

## ビルド出力

### 生成されるファイル

```
build/rootfs/                                  # rootfs（イメージの中身）
output/kimigayo-<variant>-<version>-<arch>.tar.gz
```

`<version>` には `git describe` から取ったプロジェクトの版が入ります
（`KIMIGAYO_VERSION` 未指定なら `latest`）。

- **ISO イメージは生成されません。** ベアメタル起動は対象外です
  （→ [SPECIFICATION.md](../../SPECIFICATION.md) 6.2・9.2）
- リリースでは、tarball に加えて `SHA256SUMS`・`SHA512SUMS`・
  SBOM（CycloneDX）が GitHub Release に添付され、Docker イメージは Cosign で署名されます

### ビルド情報

イメージの `/.kimigayo-build-info` に記録されます（値は例）。

```
# Kimigayo OS Build Information
BUILD_DATE=<コミット時刻>   # ビルドした時刻ではない
BUILD_ARCH=x86_64
IMAGE_TYPE=standard
VERSION=3.0.2
CODENAME=Himawari
BUILDER=root
PATCHED_CVES=CVE-2026-38753 CVE-2026-38754 ...
```

`PATCHED_CVES` は `src/*/patches/` のファイル名から作られ、
`scripts/scan-image.sh` がパッチ済みの CVE を照合結果から除外するのに使います。

### 成果物の検査

```bash
bash scripts/verify-image.sh <image> <variant> <arch>
```

版の突合・全 ELF の PIE / RELRO / BIND_NOW / 非実行スタック・OpenRC の起動などを
検査します（34 項目、Minimal は 33）。**「イメージが起動した」は検証ではありません。**

## 再現可能ビルド

**rootfs の tarball はビット同一になりました**（2026-10-12）。
同じコミット（46b05da）を CI と Manual Build で別々にビルドし、
standard / x86_64 の tarball の SHA-256 が一致しました。

そのためにしていること:

- `build-system/Makefile` が `SOURCE_DATE_EPOCH=0` を export し、
  `scripts/build-{musl,busybox,openrc}.sh` がビルドディレクトリのパスを
  `-fdebug-prefix-map` などで消す
- `/.kimigayo-build-info` の `BUILD_DATE` をコミット時刻にし、ホスト名を入れない
- tarball を `--sort=name --mtime=@<コミット時刻> --owner=0 --group=0 --numeric-owner`
  で作り、`gzip -n` で圧縮する（CI と release で同じ）

**確かめたのは 1 組・1 バリアントだけで、Docker イメージの digest は見ていません。**
名乗る範囲は「rootfs の tarball」までです。

### 自分で確かめるには

同じコミットで `manual-build.yml` を回し、CI の `rootfs-<variant>-<arch>`
成果物と `shasum -a 256` を比べます。手元で作った tarball は、
上の tar のオプションを付けない限り一致しません。

## ビルドのデバッグ

### ログ

各構成要素のログは `build/logs/` と `build/*.log` に出ます。

```bash
make log-kernel        # build/logs/kernel-build.log の最新100行
make log-musl
make log-openrc

# パッチが黙ってスキップされていないか
grep -iE 'skipped: [1-9]|not applicable' build/kernel-patches.log build/busybox-patches.log
```

`build-system/Makefile` には `V=1`（詳細出力）があります。

### 実際にビルドされた版を確かめる

ビルド済みかどうかは `.kimigayo-build-version` と `versions.mk` を突合して決めます。
**版を上げたのに古いものが残っていないか**はこう見ます。

```bash
make print-versions
find build -maxdepth 2 -name '.kimigayo-build-version' -exec sh -c 'echo "$1: $(cat "$1")"' _ {} \;
```

### ステップ実行

個別ターゲットは**ビルドコンテナ内**の `build-system/Makefile` にあります。
ホストの `Makefile` には無いので、ホストで叩くと
`No rule to make target` になります。

```bash
docker compose run --rm -T kimigayo-build make musl      # [1/4]
docker compose run --rm -T kimigayo-build make kernel    # [2/4] 成果物には入らない
docker compose run --rm -T kimigayo-build make busybox   # [3/4]
docker compose run --rm -T kimigayo-build make init      # [4/4]
docker compose run --rm -T kimigayo-build make rootfs
```

イメージ化はホスト側の `make package-rootfs` → `make build-image` です。

## トラブルシューティング

### よくあるビルドエラー

#### エラー: "Cannot connect to the Docker daemon"

Docker Desktop（macOS / Windows）か Docker デーモン（Linux）を起動します。

#### エラー: "No space left on device"

```bash
docker system prune        # 停止中のコンテナ・宙に浮いたイメージ・ビルドキャッシュ
make clean                 # ビルド成果物だけ
```

#### ビルドは通ったのに、実行すると落ちる（Segmentation fault など）

**musl を作り直したのに、BusyBox と OpenRC が古い musl にリンクされたまま**
のことがあります。成果物の日時を比べ、古ければ消して作り直します
（→ [CLAUDE.md](../../CLAUDE.md)「musl を作り直したら、それにリンクしているものも作り直す」）。

```bash
ls -l build/rootfs/sbin/openrc build/rootfs/usr/lib/libc.so
```

#### 版を上げたあと、ビルドが妙な挙動をする

前の版の残骸を疑い、構成要素ごとに消します（コンテナ側のターゲット）。

```bash
docker compose run --rm kimigayo-build make clean-busybox   # clean-musl / clean-kernel / clean-openrc も
```

### クリーンの使い分け

| コマンド | 消えるもの |
|---------|-----------|
| `make clean` | ビルド成果物だけ |
| `make clean-cache` | ダウンロードキャッシュ（volume） |
| `make clean-all` | コンテナ・volume・ビルド環境のイメージ。**約 150MB の再ダウンロードとフルビルドになる**ので最後の手段 |

## CI/CD との統合

GitHub Actions のワークフローは `.github/workflows/` にあります。

| ワークフロー | いつ | 何をするか |
|------------|------|-----------|
| `ci.yml` | `main` への push・PR | ShellCheck・リンク検査・pytest・3 バリアント × 2 アーキのビルドとイメージ検証（カーネルは作らない） |
| `release.yml` | `v*.*.*` タグ | Docker Hub への公開・Cosign 署名・GitHub Release |
| `manual-build.yml` | 手動 | バリアント・アーキを選んでビルド。**カーネルを CI で作る唯一の経路**（`build_kernel=true`） |

詳しくは [CICD_GUIDE.md](CICD_GUIDE.md)。

## 参考リソース

- [DEVELOPMENT.md](../../DEVELOPMENT.md) - 開発環境の詳細
- [CONTRIBUTING.md](../../CONTRIBUTING.md) - コントリビューションガイドライン
- [CUSTOM_BUILD.md](CUSTOM_BUILD.md) - 公開イメージをベースにしたカスタマイズ
- [docs/troubleshooting/](../troubleshooting/) - 実際に踏んだ罠の記録
- [Makefile](../../Makefile) / [build-system/Makefile](../../build-system/Makefile)

---

**質問やサポートが必要な場合**:
- GitHub Issues: https://github.com/Kazuki-0731/Kimigayo/issues
- Discussions: https://github.com/Kazuki-0731/Kimigayo/discussions
