# Kimigayo OS アーキテクチャドキュメント

このドキュメントでは、Kimigayo OSの内部アーキテクチャと設計思想について説明します。

## 目次

- [全体アーキテクチャ](#全体アーキテクチャ)
- [レイヤー構造](#レイヤー構造)
- [コアコンポーネント](#コアコンポーネント)
- [セキュリティアーキテクチャ](#セキュリティアーキテクチャ)
- [ブートプロセス](#ブートプロセス)
- [設計原則](#設計原則)
- [データフロー](#データフロー)
- [モジュール間の依存関係](#モジュール間の依存関係)
- [参考リソース](#参考リソース)

> **パッケージ管理システムの節はありません。** Kimigayo OS は
> パッケージマネージャーを**意図的に持ちません**（→
> [全体アーキテクチャ](#全体アーキテクチャ)）。ソフトウェアの追加は
> ビルド時のマルチステージビルドで行います。

## 全体アーキテクチャ

Kimigayo OSは、Googleのdistrolessと同様の設計思想を採用し、不変性、最小攻撃面、軽量性を重視したアーキテクチャを実現しています。

```
┌─────────────────────────────────────────────────────────┐
│                  ユーザー空間                            │
├─────────────────────────────────────────────────────────┤
│         アプリケーション層                               │
│  - Webサーバー (nginx, apache)                          │
│  - データベース (PostgreSQL, MySQL)                     │
│  - コンテナランタイム (Docker, Podman)                  │
├─────────────────────────────────────────────────────────┤
│         システムユーティリティ層                         │
│  - BusyBox (coreutils, findutils, etc.)                │
│  - ネットワークツール (ip, ifconfig, wget)              │
│  - システム管理ツール (ps, top, free)                   │
├─────────────────────────────────────────────────────────┤
│         Init システム層 (OpenRC)                        │
│  - サービス管理 (rc-service, rc-update)                │
│  - ランレベル管理                                       │
│  - 依存関係管理                                         │
├─────────────────────────────────────────────────────────┤
│         Cライブラリ層 (musl libc)                       │
│  - POSIX準拠API                                         │
│  - 軽量・高速な実装                                     │
│  - UTF-8サポート                                        │
├═════════════════════════════════════════════════════════┤
│                  カーネル空間                            │
├─────────────────────────────────────────────────────────┤
│         Linuxカーネル                                   │
│  - Namespace isolation                                  │
│  - cgroup                                               │
│  - カーネルモジュール                                   │
├─────────────────────────────────────────────────────────┤
│         ハードウェア抽象化層                             │
│  - デバイスドライバ                                     │
│  - ファイルシステム (ext4, overlay, tmpfs)              │
│  - ネットワークスタック                                 │
├─────────────────────────────────────────────────────────┤
│         ハードウェア                                     │
│  - x86_64, ARM64, RISC-V (将来)                        │
└─────────────────────────────────────────────────────────┘
```

> **この図はレイヤーの全体像で、Kimigayo が配布するものの範囲ではありません。**
> **成果物は `Cライブラリ層` から `システムユーティリティ層` までです。**
> カーネル空間とハードウェア抽象化層はホストが提供し、
> **カーネルは Docker イメージに入りません。** 想定する使い方は
> VPS 上の Docker コンテナで、ベアメタル起動は対象外です
> （カーネルのビルド手段は QEMU やベアメタルを試すために残してありますが、
> `ci.yml` ではビルドしません）。
>
> **ルートファイルシステムも、コンテナでは `overlay` です**
> （`ext4` はこの rootfs をベアメタルや VM で使う場合の話）。
> 下記の各層は、ベアメタルで動かした場合も含めた説明です。

## レイヤー構造

### 1. ハードウェア層

**目的**: ハードウェアリソースの提供

**サポートアーキテクチャ**:
- x86_64 (AMD64): 現在サポート
- ARM64 (AArch64): 現在サポート
- RISC-V: 将来サポート予定

**主要コンポーネント**:
- CPU、メモリ、ストレージ
- ネットワークインターフェース
- 入出力デバイス

### 2. Linuxカーネル層

**目的**: ハードウェア抽象化とリソース管理

**主要機能**:
- プロセススケジューリング
- メモリ管理
- ファイルシステム管理
- ネットワークスタック
- デバイスドライバ管理

**セキュリティ関連のカーネルパラメータ**:

イメージが**実際に出荷している**のは
`configs/sysctl/99-kimigayo-performance.conf` の内容で、
セキュリティに関わるのは次の 3 つだけです。

```ini
kernel.randomize_va_space = 2        # ASLR 完全有効化
fs.suid_dumpable = 0                 # setuid プロセスのコアダンプ禁止
kernel.core_uses_pid = 1
```

> **`kernel.kptr_restrict` / `kernel.dmesg_restrict` /
> `kernel.yama.ptrace_scope` は出荷していません。**
> 以前ここに「セキュリティ機能」として並んでいましたが、
> 出荷ファイルには入っていません（2026-10-11 に突合）。
>
> **そもそもコンテナでは `/proc/sys` が読み取り専用で、
> この sysctl ファイルは適用されません**（`sysctl` サービスが
> `kernel parameters are managed by the host` と報告してスキップします）。
> 効くのはこの rootfs をベアメタルや VM で使う場合だけです。

**ファイルシステム**:
- **overlay**: コンテナのルートファイルシステム（通常はこれ）
- **tmpfs**: 一時ファイル用メモリファイルシステム
- **ext4**: ベアメタル／VM でルートに使う場合
- **squashfs**: 読み取り専用圧縮ファイルシステム（カーネル config では
  `=m`。minimal / standard の defconfig のみ）

### 3. Cライブラリ層 (musl libc)

**目的**: POSIXシステムコールのラッパー提供

**musl libcの特徴**:
- **軽量**: イメージ内の `libc.so` は **954KB**（arm64, musl 1.2.6）。
  同じ arch の Debian 12 の `libc.so.6` は 1.65MB なので**約 58%**
  （2026-10-11 に `ls -l` で実測）
- **1 ファイルで済む**: `libm` / `libpthread` / `libdl` が本体に入っており、
  イメージに置く共有ライブラリが 1 つで足りる
- **静的リンク対応**: BusyBox は static-pie でビルドしている
- **コンパイル時の強化を有効化**: `-fPIE` /
  `-fstack-protector-strong` / `-D_FORTIFY_SOURCE=2` /
  `-Wl,-z,relro -Wl,-z,now`（`scripts/build-musl.sh`）

> **「glibc より高速」とは書きません。** musl の malloc は実装が単純で、
> **マルチスレッドで競合する場面では glibc より遅いことが知られています。**
> 採用理由はサイズと依存の少なさで、速度ではありません。
>
> **ロケールはほぼ実装されていません**（`C` / `C.UTF-8` 相当のみ）。
> 照合順序や月名の翻訳を libc に期待するアプリには向きません。
>
> **GNU 拡張がありません。** BusyBox の `vi` が glibc の GNU 正規表現
> 拡張を使っているため、POSIX `regcomp`/`regexec` に書き換える
> パッチを当てています（`src/busybox/patches/`）。

**主要API**:
```c
// メモリ管理
void* malloc(size_t size);
void free(void* ptr);

// ファイルI/O
int open(const char* path, int flags);
ssize_t read(int fd, void* buf, size_t count);
ssize_t write(int fd, const void* buf, size_t count);

// プロセス管理
pid_t fork(void);
int execve(const char* pathname, char* const argv[], char* const envp[]);

// ネットワーク
int socket(int domain, int type, int protocol);
int bind(int sockfd, const struct sockaddr* addr, socklen_t addrlen);
```

### 4. Initシステム層 (OpenRC)

**目的**: システム初期化とサービス管理

**OpenRCの特徴**:
- **軽量**: systemdより小さいフットプリント
- **並列起動**: 依存関係に基づく並列サービス起動
- **依存関係管理**: 明示的なサービス依存関係
- **ランレベル**: 柔軟なランレベルシステム

**主要ランレベル**:
```
sysinit  → boot → default → shutdown
```

**サービススクリプト例**:
```bash
#!/sbin/openrc-run

name="Nginx Web Server"
command="/usr/sbin/nginx"
command_args="-c /etc/nginx/nginx.conf"
pidfile="/var/run/nginx.pid"

depend() {
    need net
    use dns
    after firewall
}

start_pre() {
    checkpath --directory --owner nginx:nginx /var/log/nginx
}

reload() {
    ebegin "Reloading ${name}"
    ${command} -s reload
    eend $?
}
```

**依存関係グラフ**（OpenRC の `depend()` の書き方の例）:
```
networking
    ├── firewall
    │       └── sshd
    ├── ntpd
    └── nginx
            └── php-fpm
```

> **これは OpenRC 一般の例で、Kimigayo が同梱しているサービスでは
> ありません。** `networking` / `firewall` / `sshd` / `ntpd` / `nginx` /
> `php-fpm` はどれもイメージに入っていません。
> **自分のサービスの `depend()` に `need net` や `after firewall` と
> 書くと、依存が解決できず起動しません。**
> 同梱しているのは `/etc/init.d/` の 28 個（`localmount`・`netmount`・
> `sysctl`・`bootmisc`・`local` など）で、`default` ランレベルに
> 登録されているのは `local` と `netmount` だけです。

### 5. システムユーティリティ層 (BusyBox)

**目的**: 基本的なUnixコマンドの提供

**BusyBoxの特徴**:
- **単一バイナリ**: 数百のコマンドが1つの実行ファイル
- **省メモリ**: 共有コード、最小限の実装
- **コンテナ最適**: 最小限のリソースで動作

**提供コマンド（一部）**:
```bash
# ファイル操作
ls, cp, mv, rm, mkdir, cat, less, grep, find, tar

# システム管理
ps, top, free, df, mount, umount, kill

# ネットワーク
ping, wget, ifconfig, route, netstat

# テキスト処理
sed, awk, cut, sort, uniq, head, tail
```

**アーキテクチャ**:
```
┌──────────────────────────────┐
│   Symlinks (ls, cp, mv...)   │
└──────────────┬───────────────┘
               │
         ┌─────▼──────┐
         │  BusyBox   │ (単一バイナリ)
         │   main()   │
         └─────┬──────┘
               │
    ┌──────────┼──────────┐
    │          │          │
┌───▼───┐  ┌──▼──┐  ┌───▼───┐
│ ls.c  │  │cp.c │  │ mv.c  │
└───────┘  └─────┘  └───────┘
```

### 6. アプリケーション層

**目的**: ユーザーアプリケーションの実行環境

**サポートされるアプリケーション**:
- Webサーバー: nginx, Apache
- データベース: PostgreSQL, MySQL, SQLite
- 言語ランタイム: Python, Node.js, Ruby, Go
- コンテナ: Docker, Podman
- その他: 任意のLinuxアプリケーション

## コアコンポーネント

### カーネル設定

> **このカーネルは Docker イメージに入りません。** コンテナはホストの
> カーネルで動くので、ここに挙げた設定が効くのは、この rootfs を
> ベアメタルや VM で使う場合だけです。コンテナでは**ホストの**
> カーネル設定が効きます。

`src/kernel/config/` の config 断片で**明示している**もの:

```ini
# セキュリティ機能
CONFIG_SECURITY=y
CONFIG_SECURITY_YAMA=y

# ASLR
CONFIG_RANDOMIZE_BASE=y
CONFIG_RANDOMIZE_MEMORY=y

# Namespace isolation
CONFIG_NAMESPACES=y
CONFIG_PID_NS=y
CONFIG_NET_NS=y
CONFIG_USER_NS=y

# ファイルシステム
CONFIG_EXT4_FS=y
CONFIG_OVERLAY_FS=y
CONFIG_TMPFS=y
CONFIG_SQUASHFS=y        # minimal / standard のみ

# ネットワーク
CONFIG_NETFILTER=y
CONFIG_IP_NF_IPTABLES=y
```

**`defconfig` の既定で有効になっているもの**（こちらの config 断片には
書いていないが、ビルド結果の `.config` では `y`。カーネル 6.18.55 で確認）:

```ini
CONFIG_SECCOMP=y
CONFIG_SECCOMP_FILTER=y
CONFIG_UTS_NS=y
CONFIG_IPC_NS=y
CONFIG_NETFILTER_XTABLES=y
```

> **BusyBox と同じで、カーネル config も「書かないと既定値が入る」。**
> 上の 5 つは意図して選んだものではなく、既定で付いてきています。
> 上流が既定を変えれば黙って消えるので、**保証として引かないこと。**

**`CONFIG_SECURITY_DMESG_RESTRICT` は無効です**
（ビルド結果は `# CONFIG_SECURITY_DMESG_RESTRICT is not set`）。
`kernel.dmesg_restrict` を sysctl で設定する方針のためです。

> **seccomp はカーネルが対応しているだけで、Kimigayo は
> seccomp プロファイルを配布していません。**
> コンテナで絞るならランタイム側で指定してください
> （`docker run --security-opt seccomp=profile.json`）。

### BusyBoxアプレット選択

```ini
# 必須アプレット（Minimal）
CONFIG_LS=y
CONFIG_CP=y
CONFIG_MV=y
CONFIG_RM=y
CONFIG_CAT=y
CONFIG_ECHO=y
CONFIG_GREP=y
CONFIG_SED=y
CONFIG_AWK=y

# ネットワークアプレット（Standard）
CONFIG_PING=y
CONFIG_WGET=y
CONFIG_IFCONFIG=y
CONFIG_ROUTE=y

# Extended が追加するもの（11 個）
CONFIG_AR=y
CONFIG_ED=y
CONFIG_FBSET=y
CONFIG_FDFORMAT=y
CONFIG_FLASH_ERASEALL=y
CONFIG_FLASH_LOCK=y
CONFIG_FLASH_UNLOCK=y
CONFIG_FLASHCP=y
CONFIG_INOTIFYD=y
CONFIG_RFKILL=y
CONFIG_UNLZOP=y
```

> **`strace` と `tcpdump` はどのバリアントにも入っていません。**
> BusyBox にそのアプレット自体がなく、`CONFIG_STRACE` /
> `CONFIG_TCPDUMP` は `src/busybox/config/` のどこにもありません
> （2026-10-11 に突合）。以前ここに「デバッグツール（Extended）」として
> 並んでいましたが、存在しないものでした。
>
> **`lsof` は Extended 専用ではありません。** `CONFIG_LSOF=y` は
> `extended.config` にしか書かれていませんが、**実測では 3 バリアント
> すべてに `lsof` があります**（書かなくても既定で入る）。
>
> **Extended と Standard の差は上の 11 個だけで、MTD/flash と
> framebuffer 系が主です。** デバッガが必要なら、ビルド時に
> マルチステージで持ち込んでください。

> **BusyBox の config は「書かないと既定値が入る」。**
> ここに並べたものは意図して選んだ分で、**実際のバイナリには
> 書いていないアプレットも入ります。** 何が入っているかは
> イメージ側で確認してください（`busybox --list`）。
> 過去に `dpkg` と `rpm` がこの経路で入っていました。


## セキュリティアーキテクチャ

### 多層防御（Defense in Depth）

```
┌─────────────────────────────────────────┐
│  Layer 5: パッケージマネージャー不在     │★ Kimigayo が担保
│  - 追加インストール手段が無い            │
│  - 侵入後に道具を持ち込めない            │
├─────────────────────────────────────────┤
│  Layer 4: コンパイル層                  │★ Kimigayo が担保
│  - PIE, RELRO (-Wl,-z,relro -Wl,-z,now) │
│  - FORTIFY_SOURCE                       │
│  - Stack canaries                       │
├─────────────────────────────────────────┤
│  Layer 3: 最小の実行面                  │★ Kimigayo が担保
│  - 第三者の共有ライブラリ無し            │
│  - sshd / sudo / iptables 無し           │
├─────────────────────────────────────────┤
│  Layer 2: カーネル層                    │ ホスト（コンテナの場合）
│  - Namespace / cgroup                   │
│  - ASLR                                 │
├─────────────────────────────────────────┤
│  Layer 1: コンテナランタイム層          │ 利用者が設定
│  - --cap-drop / --read-only / --user    │
│  - seccomp プロファイル                  │
│  - NetworkPolicy / ポート公開            │
└─────────────────────────────────────────┘
```

**★ の 3 層が Kimigayo 自身が担保している部分です。**
Layer 1 と 2 はホストと利用者の設定によります
（→ [システム設定ガイド](../user/CONFIGURATION.md#セキュリティ設定)）。

**配布していないもの**: seccomp プロファイル、SELinux / AppArmor の
ポリシー、`iptables`、Cosign による署名。
**ファイアウォールはイメージに入っていません**（`iptables` 無し）。


## ブートプロセス

### 起動シーケンス

**既定では OpenRC は動きません。** `Dockerfile.runtime` は `ENTRYPOINT` を
持たず `CMD ["/bin/sh"]` なので、`docker run` した場合の PID 1 は
`/bin/sh` です。

```
1. コンテナランタイム (Docker/Podman/Kubernetes)
   ├── コンテナ初期化（namespace / cgroup）
   ├── rootfs マウント（overlay）
   ├── ネットワーク・/etc/hosts・/etc/resolv.conf を用意
   └── CMD / ENTRYPOINT を PID 1 として起動
       │
2. 既定: /bin/sh が PID 1
   └── OpenRC は起動しない（rc-service は
       "openrc did not boot" で失敗する）
```

**OpenRC を使う場合は `/sbin/init` を PID 1 にします**
（`--entrypoint /sbin/init`）。`/etc/inittab` が次を順に実行します。

```
2'. /sbin/init (BusyBox init) が PID 1
       │
3. openrc sysinit
   ├── /proc, /sys, /dev の確認
   └── （/run の tmpfs マウントは権限不足で失敗する。
        --tmpfs /run を渡せば解消）
       │
4. openrc boot
   ├── sysctl（コンテナでは「ホストが管理」と報告してスキップ）
   ├── loopback（ランタイムが済ませているため RTNETLINK で拒否される）
   ├── mtab / bootmisc / hostname / localmount など
   └── dmesg は CAP_SYSLOG が無く失敗する
       │
5. openrc default
   ├── local
   └── netmount
       （既定で登録されているのはこの 2 つだけ）
```

**上記の失敗はいずれも無害で、起動は続行します。**
実測では `openrc default` が終了コード 0 で完走します。
詳細と対処は[システム設定ガイド](../user/CONFIGURATION.md#サービス管理)。

### 起動時間

**目標**: 10秒以下 / **実測**: 0.61秒（v3.0.1、arm64 ネイティブ、10回の中央値）

> **これは「Kimigayo が速い」という意味ではありません。**
> 同じ条件で測ると Alpine 0.62 秒・Ubuntu 24.04 0.59 秒で、
> **100MB の Ubuntu がいちばん速い**という結果です。
> 測っている時間のほとんどがコンテナランタイム自身の処理なので、
> **イメージの中身はほとんど効きません。**
> 差が出るのは常駐メモリ（Kimigayo 232KB / Alpine 276KB /
> Ubuntu 312KB）とサイズの方です。
>
> **OpenRC が default ランレベルを完走するまでは 0.77 秒**で、
> `/bin/true` の 0.61 秒との差が Init の分です。

**コンテナでは `quiet splash` や initrd の調整は効きません**
（ブートローダーも initrd も作っていません）。効くのは OpenRC に
起動させるサービスの数です。

```bash
# 起動時間の測定（ホスト側から）
scripts/benchmark-startup.sh

# default ランレベルまで含めて測る
docker run --rm <image> /sbin/openrc default
```

**`dmesg` はコンテナからは使えません**（`CAP_SYSLOG` が必要）。
`systemd-analyze` はこのプロジェクトでは使いません（Init は OpenRC）。

測定条件は [docs/benchmarks/lifecycle.md](../benchmarks/lifecycle.md) に
記録しています。

## 設計原則

### 1. KISS原則（Keep It Simple, Stupid）

- シンプルな実装
- 明確なインターフェース
- 最小限のコンポーネント

### 2. Unix哲学

- 1つのことをうまくやる
- プログラム同士の連携
- テキストストリームの利用

### 3. セキュアバイデフォルト

- デフォルトで安全な設定
- 最小権限の原則
- 多層防御

### 4. 再現可能性

- バージョン固定（`versions.mk` + チェックサム検証）

**再現可能ビルドは未達**（2026-10-11 に確認）。[config.mk](../../config.mk) に
`SOURCE_DATE_EPOCH` と prefix-map を入れる仕組みはあるが、
`REPRODUCIBLE_BUILD=yes` のときだけ有効で、この変数をどこも設定して
いない。そもそも [config.mk](../../config.mk) 自体がどの Makefile からも include されて
いないため、ビット同一性は検証も保証もされていない。

**「ビット同一の出力」「決定論的ビルド」は 2026-10-11 に削除した。**
一度も検証していない主張だった。

### 5. パフォーマンス

目標値は [SPECIFICATION.md](../../SPECIFICATION.md) §8.3 の定義。
実測は v3.0.1（2026-10-11）。

| 指標 | 目標 | 実測 |
|------|------|------|
| 起動時間 | < 10秒 | 0.61秒 |
| 常駐メモリ | < 128MB | 232KB |
| イメージサイズ (Minimal) | < 5MB | 2.62MB / arm64 2.98MB |
| イメージサイズ (Standard) | < 15MB | 2.76MB / arm64 3.13MB |
| イメージサイズ (Extended) | < 50MB | 2.78MB / arm64 3.17MB |

**3 バリアントとも、いちばん厳しい Minimal の目標 5MB を下回っています。**
起動時間の解釈は[起動時間](#起動時間)の注記を参照してください。

## データフロー

### ビルド時

バージョンの単一の真実の源は [versions.mk](../../versions.mk) です。
各スクリプトはここだけを読みます（`scripts/lib/versions.sh` 経由）。

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
                    Dockerfile.runtime → Docker イメージ → 検証
```

**カーネル（[2/4]）の成果物は Docker イメージに入りません。**
`build/kernel/output/vmlinuz-<version>-<arch>` に置かれ、
ベアメタル／QEMU 検証でだけ使います。`ci.yml` ではビルドしません。

プロジェクト自身の版は `scripts/get-version.sh`（`git describe --tags`）が
決め、`build-rootfs.sh` の `resolve_project_version()` が 1 箇所で
`/etc/os-release`・`/etc/motd`・`/.kimigayo-build-info` に流します。
`verify_rootfs` がビルド中の版と `os-release` の
`VERSION_ID` / `VERSION_CODENAME` を突合します。

### 実行時

```
docker run
    ↓
コンテナランタイム（namespace / cgroup / overlay / ネットワーク）
    ↓
PID 1（既定は /bin/sh、または /sbin/init、またはアプリ本体）
    ↓
BusyBox アプレット ─→ musl libc（/usr/lib/libc.so）─→ ホストのカーネル
    ↑
OpenRC（librc / libeinfo）※ /sbin/init を PID 1 にした場合のみ
```

**イメージ内の共有ライブラリは musl の `libc.so` と OpenRC 自身の
`librc` / `libeinfo` だけです**（第三者の共有ライブラリを持ちません）。
`libcap` は OpenRC に静的リンクしてあります。

## モジュール間の依存関係

```
┌──────────────┐
│ Applications │
└──────┬───────┘
       │ uses
       ▼
┌──────────────┐     ┌──────────────┐
│ BusyBox      │────▶│ musl libc    │
└──────┬───────┘     └──────┬───────┘
       │ managed by         │ wraps
       ▼                    ▼
┌──────────────┐     ┌──────────────┐
│ OpenRC       │     │ Linux Kernel │
└──────┬───────┘     └──────────────┘
       │ starts
       ▼
┌──────────────┐
│ Services     │
└──────────────┘
```

## 参考リソース

- [BUILD_GUIDE.md](BUILD_GUIDE.md) - ビルド詳細
- [API_REFERENCE.md](API_REFERENCE.md) - API仕様
- [SPECIFICATION.md](../../SPECIFICATION.md) - プロジェクト仕様

---

**このドキュメントは、Kimigayo OSの開発に貢献する開発者のために作成されました。**
