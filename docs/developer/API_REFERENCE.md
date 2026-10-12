# Kimigayo OS リファレンス

このドキュメントは、Kimigayo OS を使う・作るときに参照する
**OpenRC のサービス定義・ビルド変数とターゲット・運用コマンド**の一覧です。

> **Python の API はここに載っていません。** `src/` 配下の Python
> モジュールはビルドとテストの補助で、利用者向けの公開 API ではありません。
> 詳細は各モジュールのソースを参照してください。

## 目次

- [OpenRC（サービス管理）](#openrcサービス管理)
- [カーネルパラメータ](#カーネルパラメータ)
- [ビルドシステム](#ビルドシステム)
- [運用コマンド](#運用コマンド)
- [ソフトウェアの追加](#ソフトウェアの追加)

## OpenRC（サービス管理）

> **既定では OpenRC は動いていません。** 既定の PID 1 は `/bin/sh` です
> （`Dockerfile.runtime` の `CMD`）。この状態で `rc-service` を叩くと
> `openrc did not boot` の警告が出て終了コード 1 になります。
> OpenRC を使うときは `/sbin/init` を PID 1 にします
> （→ [ARCHITECTURE.md](ARCHITECTURE.md#ブートプロセス)、
> [システム設定ガイド](../user/CONFIGURATION.md#サービス管理)）。

### rc-service

サービスの制御を行います。

**構文**:
```bash
rc-service SERVICE ACTION
```

**アクション**:
- `start`: サービスを起動
- `stop`: サービスを停止
- `restart`: サービスを再起動
- `reload`: 設定を再読み込み（サービスが `reload()` を定義している場合）
- `status`: サービスの状態を確認

**例**:
```bash
rc-service myapp start
rc-service myapp stop
rc-service myapp restart
rc-service myapp status
```

存在しないサービスを指定すると ``service `xxx' does not exist`` と出て
終了コード 1 になります。

### rc-update

サービスの自動起動設定を管理します。

**構文**:
```bash
rc-update ACTION SERVICE [RUNLEVEL]
```

**アクション**:
- `add`: サービスを追加
- `del`: サービスを削除
- `show`: 登録されているサービスを表示

**ランレベル**:
- `sysinit`: システム初期化
- `boot`: ブート時
- `default`: デフォルト（通常運用。既定で登録されているのは `local` と `netmount`）
- `shutdown`: シャットダウン時

**例**:
```bash
rc-update add myapp default
rc-update del myapp default
rc-update show
rc-update show default
```

### サービススクリプト

#### 基本構造

```bash
#!/sbin/openrc-run

name="My Service"
description="My custom service"
command="/usr/local/bin/myapp"
command_args="--config /etc/myapp.conf"
command_user="myapp:myapp"
pidfile="/run/myapp.pid"
command_background="yes"

depend() {
    need localmount
    use dns logger
    after bootmisc
}

start_pre() {
    # 起動前の処理
    checkpath --directory --owner ${command_user} /var/log/myapp
}

reload() {
    ebegin "Reloading ${name}"
    start-stop-daemon --signal HUP --pidfile "${pidfile}"
    eend $?
}
```

#### 依存関係の定義

```bash
depend() {
    # 必須の依存関係（無ければ起動しない）
    need localmount

    # 任意の依存関係（あれば使用）
    use dns logger

    # 順序の指定（存在しなければ無視される）
    after bootmisc
    before local

    # 他のサービスを提供
    provide myservice
}
```

> **`need net` は書かないでください。** Kimigayo には `net` を提供する
> サービス（`networking` など）が入っていないので、依存が解決できず
> 起動しません。コンテナのネットワークはランタイムが用意します。
> 同梱しているサービスは `ls /etc/init.d` で確認できます。

## カーネルパラメータ

**コンテナからはカーネルパラメータを変えられません。** `/proc/sys` は
読み取り専用で、カーネルはホストのものです。名前空間ごとの値
（`net.*` の多く）はランタイム側で指定します。

```bash
docker run --sysctl net.ipv4.ip_forward=1 ishinokazuki/kimigayo-os:3.0.2
```

イメージには `/etc/sysctl.d/99-kimigayo-performance.conf` が入っていますが、
コンテナでは適用されません（`sysctl` サービスが「ホストが管理」と報告して
スキップします）。効くのはこの rootfs をベアメタルや VM で使う場合だけです。

**カーネルモジュールも扱えません**（`modprobe` / `lsmod` のアプレットは
ありますが、カーネルもモジュールもイメージに入っていません）。
モジュールが要るならホスト側でロードします。

## ビルドシステム

### Makefile ターゲット

ターゲットは**ホストの `Makefile`** と**コンテナ内の `build-system/Makefile`**
に分かれています。片方にしか無いものを反対側で叩くと `No rule to make target`
になります。全量は `make help`（ホスト）で確認できます。

#### 情報表示（ホスト）

```bash
make help              # ヘルプ
make info              # ビルド設定（コンテナ内で make info を実行）
make version           # プロジェクトの版（git describe）
make print-versions    # 構成要素の版（versions.mk）
```

#### ビルド

**バリアントはターゲットではなく変数で選びます。コンテナ側では
`IMAGE_TYPE` を常に明示してください**（省くと BusyBox と rootfs の既定が
ずれ、minimal になることがあります）。

```bash
# コンテナ内（build-system/Makefile）。カーネル抜き（Docker イメージにはカーネルは入らない）
docker compose run --rm -T kimigayo-build make build-no-kernel TARGET_ARCH=x86_64 IMAGE_TYPE=standard
docker compose run --rm -T kimigayo-build make build-no-kernel TARGET_ARCH=x86_64 IMAGE_TYPE=minimal

# カーネルも含めて作る（数十分〜数時間。ベアメタル／QEMU 検証用）
docker compose run --rm -T kimigayo-build make build TARGET_ARCH=x86_64 IMAGE_TYPE=standard

# ホスト側（rootfs → イメージ → 検証。Linux ホストのみ。macOS では通らない）
make ci-build-local VARIANT=minimal ARCH=x86_64
make ci-build-all ARCH=x86_64        # 3バリアントを順に

# 成果物を消してから作り直す
docker compose run --rm -T kimigayo-build make clean
```

> `make build-minimal` / `build-standard` / `build-extended` は存在しません。

#### テスト

```bash
# ホスト: コンテナ内で pytest tests/ -v（unit・property・integration すべて）
make test

# ホスト: 統合テスト（test_phase1_integration.py と tarball の存在確認）
make test-integration

# コンテナ内（build-system/Makefile）にだけあるターゲット
docker compose run --rm -T kimigayo-build make test-unit
docker compose run --rm -T kimigayo-build make test-property
```

カバレッジは make ターゲットではありません（設定は `.coveragerc`）。

```bash
python3 -m pytest tests/unit tests/property --cov --cov-report=term-missing
```

#### 静的解析・スキャン（ホスト）

```bash
# ShellCheck（scripts/ と .claude/hooks/）
make shellcheck-scan

# scan-image + Trivy（ファイルシステム）+ ShellCheck
make security-scan

# 出荷物（kimigayo-os:$(VARIANT)-$(ARCH)）の CVE 照合と秘密情報スキャン
make scan-image

# リポジトリ側の依存だけを見る
make trivy-fs-scan
```

> `make lint` / `make static-analysis` は存在しません。
> **`make trivy-scan`（イメージスキャン）は何も検査できません。**
> パッケージデータベースを持たないため Trivy が対象を識別できません。
> そのため `security-scan` には含めず、脆弱性の検査は `scan-image`
> （出荷物の版から SBOM を作り Grype で照合）で行います。
> `scan-image` の環境変数（`SCANS` / `SBOM_OUT` / `FAIL_ON`）は
> [DEVELOPMENT.md](../../DEVELOPMENT.md#セキュリティスキャン) を参照。

### ビルド設定変数

**実在する変数だけを挙げます。**

| 変数 | 置き場 | 既定 | 用途 |
| --- | --- | --- | --- |
| `TARGET_ARCH` | `build-system/Makefile` | `x86_64` | `x86_64` / `arm64` |
| `IMAGE_TYPE` | `build-system/Makefile` | **無し（明示する）** | `minimal` / `standard` / `extended` |
| `VARIANT` | `Makefile`（ホスト側） | `standard` | 同上。ホストのターゲットはこちらを使う |
| `ARCH` | `Makefile`（ホスト側） | `x86_64` | ホスト側のアーキテクチャ。`build-system` では非推奨（`TARGET_ARCH` に読み替えられ警告が出る。compose が `ARCH=x86_64` を渡すので警告は毎回出る） |
| `KIMIGAYO_VERSION` | `Makefile`（ホスト側） | `scripts/get-version.sh`（`git describe`）の結果。失敗時 `dev` | `/etc/os-release` などに入る版 |
| `VERSION` | `Makefile`（ホスト側） | `latest` | tarball 名・ローカルのタグに入る文字列 |
| `V` | `build-system/Makefile` | `0` | `1` で詳細出力 |

```bash
docker compose run --rm -T kimigayo-build make build-no-kernel TARGET_ARCH=arm64 IMAGE_TYPE=minimal
make ci-build-local VARIANT=minimal ARCH=x86_64
```

> **定義されていても効かない変数があります。**
> `BUILD_JOBS`（ホスト）はどこからも使われていません（並列度はスクリプトが
> `nproc` で決める）。`SECURITY_HARDENING`（コンテナ）は `make info` が
> 表示するだけです。`DEBUG` はホスト側では未使用で、コンテナ側の `CFLAGS` も
> `scripts/build-*.sh` が上書きするため効きません。
>
> `BUILD_TYPE` / `PACKAGE_LIST` / `KERNEL_CONFIG` はどちらの Makefile にも
> 存在しません。カーネル設定は `src/kernel/config/<arch>.config` で
> 切り替えます（→ [ARCHITECTURE.md](ARCHITECTURE.md#カーネル設定)）。

## 運用コマンド

コマンドは BusyBox のアプレットです。GNU 版や procps 版のオプションは
使えないものがあります。

### システム情報

```bash
cat /etc/os-release        # OS の版（VERSION_ID / VERSION_CODENAME）
cat /.kimigayo-build-info  # ビルド情報（バリアント・アーキ・パッチ済み CVE）
uname -a                   # カーネルの版（コンテナではホストのカーネル）
free -m                    # メモリ
df -h                      # ディスク使用量
```

### プロセス管理

```bash
ps                         # プロセス一覧（`ps aux` は使えない）
ps -o pid,user,comm        # 列を選ぶ（Extended のみ。Minimal / Standard の ps はオプションを受け付けない）
top -b -n1                 # 1 回だけ表示
kill PID
kill -9 PID                # 強制終了
```

### ネットワーク

```bash
ip addr show
ip link show
ip route show
netstat -tulnp             # 待ち受けポート（ss は無い）
ping -c 3 example.com
nslookup example.com       # DNS の確認（dig は無い）
```

## ソフトウェアの追加

Kimigayo OS はパッケージマネージャーを含みません。必要なソフトウェアは
マルチステージビルドでイメージに持ち込みます。

**静的リンクのバイナリはそのまま `COPY` で動きます。** 動的リンクの
実行ファイルは、依存する共有ライブラリも一緒に持ち込む必要があります
（イメージにあるのは musl の `libc.so` と OpenRC の `librc` / `libeinfo` だけ）。
`ldd` で依存を集める方法は
[CUSTOM_BUILD.md](CUSTOM_BUILD.md#1-動的リンクの実行ファイルは共有ライブラリも要る)、
動く例（nginx / Node.js / Python）は [examples/](../../examples/) にあります。

```dockerfile
# 静的リンクの例
FROM golang:1-alpine AS builder
WORKDIR /build
COPY . .
RUN CGO_ENABLED=0 go build -ldflags '-s -w' -o app .

FROM ishinokazuki/kimigayo-os:3.0.2
COPY --from=builder /build/app /usr/local/bin/app
CMD ["/usr/local/bin/app"]
```

## 参考リソース

- [BUILD_GUIDE.md](BUILD_GUIDE.md) - ビルド詳細
- [ARCHITECTURE.md](ARCHITECTURE.md) - アーキテクチャ
- [CUSTOM_BUILD.md](CUSTOM_BUILD.md) - 公開イメージをベースにしたカスタマイズ
- [CONTRIBUTING.md](../../CONTRIBUTING.md) - コントリビューションガイド
- [DEVELOPMENT.md](../../DEVELOPMENT.md) - 開発ガイド
