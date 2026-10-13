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
- RAM: 4GB 以上を推奨（arm64 のクロスビルドは 8GB 近く使う）

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
# カーネル抜き。Docker イメージにカーネルは入らない
make build-no-kernel TARGET_ARCH=x86_64 IMAGE_TYPE=standard

# テスト実行（コンテナ内）
make test
```

> **コンテナ内の `make build` はカーネルも作ります**（数十分〜数時間。
> Apple Silicon では QEMU 越しになり現実的ではありません）。
> カーネルが要るのはベアメタル／QEMU を試すときだけなので、
> 普段は `build-no-kernel` を使います。
> `IMAGE_TYPE` の既定は `standard` です。何を作るかが分かるよう明示を勧めます。

**簡単コマンド（ホストOSから）：**

```bash
# ホストOSから直接ビルド（ログは完了後に表示）
# コンテナ内で make build を実行する。カーネルを含み、変数は渡らない
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

# ビルド（簡単だがログは完了後。カーネルを含む）
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
make build-no-kernel TARGET_ARCH=x86_64 IMAGE_TYPE=standard

# クリーンアップ
make clean

# テスト実行（pytest tests/ -v）
make test
```

### ビルド成果物

コンテナ内の `make build` / `make build-no-kernel` が作るのは rootfs までです。
tarball と Docker イメージはホスト側のターゲットで作ります。

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

ホストの `make package-rootfs`（`ci-build-local` の途中でも実行される）が
配布用のtar.gzアーカイブファイルを作ります。名前の `latest` は
`Makefile` の `VERSION` の既定値です（2026-10-12 時点の手元のサイズ）。

```bash
output/
├── kimigayo-minimal-latest-x86_64.tar.gz     # Minimal版 (約1.3MB)
├── kimigayo-standard-latest-x86_64.tar.gz    # Standard版 (約1.4MB)
└── kimigayo-extended-latest-x86_64.tar.gz    # Extended版 (約1.4MB)
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
make build-no-kernel（コンテナ内）
    ↓
build/rootfs/ (ファイルシステム)
    ↓
make package-rootfs（ホスト。build-rootfs.sh をホストで実行し直すので macOS では通らない）
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
make build-no-kernel TARGET_ARCH=arm64 IMAGE_TYPE=standard

# コンテナ内で詳細ログ付きでビルド
make build-no-kernel TARGET_ARCH=x86_64 IMAGE_TYPE=standard V=1

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
make build TARGET_ARCH=x86_64 IMAGE_TYPE=standard && echo "✅ Build Success" || echo "❌ Build Failed"

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
docker compose run --rm -T kimigayo-build make build-no-kernel TARGET_ARCH=x86_64 IMAGE_TYPE=standard

# 3) 最後の手段: ビルド環境ごと作り直す（volume を消すので約150MBの再ダウンロードになる）
make clean-all
make docker-build
docker compose run --rm -T kimigayo-build make build-no-kernel TARGET_ARCH=x86_64 IMAGE_TYPE=standard
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

- **RAM**: 推奨 4GB 以上（`docker-compose.yml` のメモリ上限は `8G`、予約は `512M`。
  arm64 のクロスビルドは上限近くまで使う）
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
`make build`（コンテナ内）は次の順に作ります（`make build-no-kernel` は [2/4] を飛ばす）。

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
make status            # どこまでできているか（musl・カーネル・BusyBox・OpenRC・rootfs。カーネルは任意）
make build             # コンテナ内で make build を実行（カーネルを含む）
make test              # コンテナ内で pytest tests/ -v（tests/unit の 3 ファイル）
make test-integration  # rootfs の tarball ができたかの確認だけ
make test-docker       # イメージの起動テスト（tests/integration/test_docker_startup.sh。要イメージ）
make test-func         # イメージの機能テスト（tests/integration/test_functionality.sh。要イメージ）
make shellcheck-scan   # scripts/ と .claude/hooks/ の静的解析
make security-scan     # scan-image（成果物の CVE・秘密情報）+ Trivy FS + ShellCheck

# コンテナ内（make shell で入ってから）
make test-unit
make test-musl         # scripts/test-musl-integration.sh（test-busybox / test-openrc も）
```

> `make test-unit` と `make test-musl` / `test-busybox` / `test-openrc` はコンテナ側
> （`build-system/Makefile`）にしかありません。ホストからは
> `python3 -m pytest tests -q` でも走ります（65 件、2026-10-14）。

### バリアントとアーキテクチャ

**バリアントもアーキテクチャも、ターゲットではなく変数で選びます。**
コンテナ側とホスト側で変数名が違うので注意してください。

```bash
# コンテナ内（build-system/Makefile）: IMAGE_TYPE と TARGET_ARCH
docker compose run --rm -T kimigayo-build make build-no-kernel IMAGE_TYPE=minimal TARGET_ARCH=x86_64
docker compose run --rm -T kimigayo-build make build-no-kernel IMAGE_TYPE=extended TARGET_ARCH=arm64

# ホスト側（rootfs → イメージ → smoke まで。Linux ホストのみ）: VARIANT と ARCH
make ci-build-local VARIANT=minimal ARCH=x86_64
make ci-build-all ARCH=x86_64          # 3 バリアントを順に
```

- ホスト側の既定は `VARIANT=standard` / `ARCH=x86_64`。
  コンテナ側の `IMAGE_TYPE` の既定は `standard`（`build-system/Makefile` が
  export し、BusyBox と rootfs に同じ値が届く）
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
（`scripts/build-kernel.sh` が選びます）。無いとき、または
プレースホルダ行（`# This is a placeholder`）を含むときは上流の defconfig を使います
（無いときに `src/kernel/config/` へ何かを書き出すことはありません）。
**追跡している `<arch>.config` は今は無いので、両アーキとも上流の defconfig です。**
自分の config を使うなら、その行を含まない完全な `.config` を置きます。

どちらの場合も、そのあと `apply_security_hardening` が `scripts/config` で
項目を上書きします（→ [ARCHITECTURE.md](ARCHITECTURE.md#カーネル設定)）。
バリアント別の config と `kimigayo_*_defconfig` は 2026-10-14 に削除しました
（ビルドで使われていませんでした）。

```bash
cp my-kernel.config src/kernel/config/x86_64.config   # プレースホルダ行を含まないもの
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
docker compose run --rm -T kimigayo-build make build-no-kernel TARGET_ARCH=arm64 IMAGE_TYPE=standard
```

**両アーキテクチャを一度に作るターゲットはありません。**
`TARGET_ARCH` を変えて 2 回回すか、GitHub Actions に任せます。
**RISC-V は未対応**です（`SPECIFICATION.md` 8.2 の「将来的に」）。

> arm64 のクロスビルドはメモリを多く使います。compose のメモリ上限は
> `8G` で、以前の `2G` では `meson setup` が OOM で落ちていました。

## ビルド出力

### 生成されるファイル

```
build/rootfs/                                  # rootfs（イメージの中身）
output/kimigayo-<variant>-<version>-<arch>.tar.gz
```

`<version>` にはホストの `Makefile` の `VERSION` が入ります（既定は `latest`）。
`git describe` 由来の版（`KIMIGAYO_VERSION`）が入るのは `/etc/os-release` などの
中身で、tarball 名ではありません。リリースでは `release.yml` がタグの版で名前を付けます。

- **ISO イメージは生成されません。** ベアメタル起動は対象外です
  （→ [SPECIFICATION.md](../../SPECIFICATION.md) 6.2・9.2）
- リリースでは、tarball に加えて `SHA256SUMS`・`SHA512SUMS`・
  SBOM（CycloneDX）・対応するソース（上流の tarball とリポジトリの archive）が GitHub Release に添付され、Docker イメージは Cosign で署名されます

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
PATCHED_CVES=musl:CVE-2026-40200 musl:CVE-2026-6042 busybox:CVE-2026-38754 ...
```

`PATCHED_CVES` は `src/*/patches/` のファイル名から作られ、
`scripts/scan-image.sh` がパッチ済みの CVE を照合結果から除外するのに使います。

### 成果物の検査

```bash
bash scripts/verify-image.sh <image> <variant> <arch>
```

版の突合・全 ELF の PIE / RELRO / BIND_NOW / 非実行スタック / スタック保護・OpenRC の起動などを
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
make log-openrc        # build/logs/openrc-build.log

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
| `make clean-all` | コンテナ・volume・ビルド環境のイメージ。**約 150MB の再ダウンロードになる**ので最後の手段（`build/` は残るので、版が同じならビルド済みの構成要素は飛ばされる） |
| `make clean-all`（コンテナ内） | `build/`（`downloads/` を除く）と `output/`。ダウンロードキャッシュは volume なので残る |

## CI/CD との統合

GitHub Actions のワークフローは `.github/workflows/` にあります。

| ワークフロー | いつ | 何をするか |
|------------|------|-----------|
| `ci.yml` | `main` への push・PR、手動 | ShellCheck・リンク検査・pytest・3 バリアント × 2 アーキのビルドとイメージ検証（カーネルは作らない） |
| `release.yml` | `v*.*.*` タグ、手動 | Docker Hub への公開・Cosign 署名・GitHub Release（**公開はタグのときだけ**。手動実行はビルド・検証・スキャンまでで push しない） |
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
