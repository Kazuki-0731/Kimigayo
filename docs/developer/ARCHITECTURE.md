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
│         アプリケーション層（利用者が持ち込む）           │
│  - 例: Webサーバー、言語ランタイム、自作バイナリ        │
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
│  - 軽量な実装                                           │
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

イメージが**実際に出荷している**のは `/etc/sysctl.d/99-kimigayo-performance.conf` で、
中身は `scripts/build-rootfs.sh` の heredoc が書き出します。
セキュリティに関わるのは次の 2 つだけです。

```ini
kernel.randomize_va_space = 2        # ASLR 完全有効化
fs.suid_dumpable = 0                 # setuid プロセスのコアダンプ禁止
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
- **squashfs**: 読み取り専用圧縮ファイルシステム（自前のカーネルでは arm64 だけ
  有効。x86_64 の defconfig には入っていない。→ [カーネル設定](#カーネル設定)）

### 3. Cライブラリ層 (musl libc)

**目的**: POSIXシステムコールのラッパー提供

**musl libcの特徴**:
- **軽量**: イメージ内の `libc.so` は **954KB**（arm64, musl 1.2.6）。
  同じ arch の Debian 12 の `libc.so.6` は 1.65MB なので**約 58%**
  （2026-10-11 に `ls -l` で実測）
- **1 ファイルで済む**: `libm` / `libpthread` / `libdl` が本体に入っており、
  イメージに置く共有ライブラリが 1 つで足りる
- **全バイナリで共有**: BusyBox も OpenRC もこの `libc.so` に動的リンクする
  （v3.0.2 から。v3.0.1 までの BusyBox は static-pie で、x86_64 ではビルド環境の
  `libc.a` を取り込んでいたため、Kimigayo が musl に当てたパッチが効いていなかった）。
  静的リンクが必要なら `BUSYBOX_LINK=static` でビルドできる
- **コンパイル時の強化を有効化**: `-fPIE` /
  `-fstack-protector-strong` / `-D_FORTIFY_SOURCE=2` /
  `-Wl,-z,relro -Wl,-z,now` / `-Wl,-z,noexecstack`（`scripts/build-musl.sh`）

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
    need localmount
    use dns
    after bootmisc
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
> **自分のサービスの `depend()` に `need net` と書くと、`net` を提供する
> サービスが無いため依存が解決できず起動しません。**
> （`after` / `use` は順序と任意の依存なので、相手が無くても起動は止まりません。）
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
# ファイル操作（less は Minimal に無い）
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

**イメージに入っているアプリケーションはありません。** 利用者が
マルチステージビルドで持ち込みます（→ [CUSTOM_BUILD.md](CUSTOM_BUILD.md)、
動く例は [examples/](../../examples/) の nginx / Node.js / Python）。

- **静的リンクのバイナリ**（Go・Rust の musl ターゲットなど）はそのまま動く
- **動的リンクのバイナリ**は依存する共有ライブラリも一緒に持ち込む必要がある
  （イメージにあるのは musl の `libc.so` と OpenRC の `librc` / `libeinfo` だけ）
- glibc 向けにビルドされたバイナリは動かない

## コアコンポーネント

### カーネル設定

> **このカーネルは Docker イメージに入りません。** コンテナはホストの
> カーネルで動くので、ここに挙げた設定が効くのは、この rootfs を
> ベアメタルや VM で使う場合だけです。コンテナでは**ホストの**
> カーネル設定が効きます。

**`scripts/build-kernel.sh` が読む config は `src/kernel/config/<arch>.config`
だけです。** 手順は次のとおりです。

1. `<arch>.config` があり、プレースホルダ行（`# This is a placeholder`）を
   含まなければ、それを `.config` にして `olddefconfig` する
2. そうでなければ上流の defconfig（x86_64 は `x86_64_defconfig`、arm64 は
   `defconfig`）を使う。追跡している `<arch>.config` は今は無いので、
   **両アーキとも上流の defconfig です**。自分の config を使いたければ
   `src/kernel/config/<arch>.config` を置く
3. そのあと `apply_security_hardening` が `scripts/config` で項目を上書きし、
   もう一度 `olddefconfig` する

`apply_security_hardening` が**意図している**設定:

```ini
# 有効にする
CONFIG_RANDOMIZE_BASE=y
CONFIG_RANDOMIZE_MEMORY=y
CONFIG_SECURITY=y
CONFIG_SECURITY_DMESG_RESTRICT=y
CONFIG_HARDENED_USERCOPY=y
CONFIG_FORTIFY_SOURCE=y
CONFIG_STACKPROTECTOR=y
CONFIG_STACKPROTECTOR_STRONG=y
CONFIG_PANIC_ON_OOPS=y         # PANIC_TIMEOUT=10

# 無効にする
# CONFIG_NETFILTER / NETFILTER_ADVANCED / NETFILTER_XTABLES
# CONFIG_IP_NF_IPTABLES / IP6_NF_IPTABLES / BRIDGE_NETFILTER
```

2026-10-13 までは x86_64 で `scripts/config --disable RETPOLINE` も呼んでいましたが、
6.18 ではシンボル名が `MITIGATION_RETPOLINE` に変わっていて何もしていなかったので
外しました（Spectre v2 の緩和は無効にしません）。また、`<arch>.config` が無いときに
プレースホルダを `src/kernel/config/` へ書き出す処理もやめました。
モジュールの `modules_install` は、モジュールがビルドされたとき
（`modules.order` があるとき）だけ実行し、失敗したらビルドを止めます。

**実際にビルドされた `.config` で、上の意図はすべて効いています**
（2026-10-13、6.18.55、`manual-build.yml` を `build_kernel=true` で両アーキに
回した run 38287999391 / 38288004527 の artifact `kernel-config-<arch>`）。
以前ここで「手元の `.config` は `CONFIG_NETFILTER=y`」と書いていたのは、
途中で止まった実行の残骸でした。

| 項目 | x86_64 | arm64 | 出どころ |
| --- | --- | --- | --- |
| `RANDOMIZE_BASE`（KASLR） | y | y | 上書き |
| `RANDOMIZE_MEMORY` | y | （x86 専用） | 上書き |
| `SECURITY`・`SECURITY_DMESG_RESTRICT` | y | y | 上書き |
| `HARDENED_USERCOPY`・`FORTIFY_SOURCE` | y | y | 上書き |
| `STACKPROTECTOR_STRONG` | y | y | 上書き |
| `PANIC_ON_OOPS`（`PANIC_TIMEOUT=10`） | y | y | 上書き |
| `NETFILTER` | 無効 | 無効 | 上書き |
| `STRICT_KERNEL_RWX`・`SECCOMP_FILTER` | y | y | defconfig |
| `MITIGATION_RETPOLINE`・`MITIGATION_PAGE_TABLE_ISOLATION` | y | （x86 専用） | defconfig |
| `UNMAP_KERNEL_AT_EL0`・`ARM64_PTR_AUTH` | （arm64 専用） | y | defconfig |
| `MODULES` | y | y | defconfig |
| `SECURITY_YAMA` | 無効 | 無効 | defconfig |
| `INIT_ON_ALLOC_DEFAULT_ON` | 無効 | 無効 | defconfig |
| `USER_NS` | 無効 | y | defconfig |
| `OVERLAY_FS` | 無効 | m | defconfig |
| `SQUASHFS` | 無効 | y | defconfig |

**アーキで差があるのは上流の defconfig の違いです**（arm64 の `defconfig` は
x86_64 の `x86_64_defconfig` よりずっと多くを有効にしている）。
NETFILTER を無効にしているので、このカーネルでは iptables も、iptables に
頼る Docker の既定のブリッジネットワークも使えません。x86_64 は `OVERLAY_FS` も無いので、
このカーネルの上で Docker を動かす用途には向きません。

確かめ直すには `manual-build.yml` を `build_kernel=true` で回します。
主な強化項目がジョブのサマリーに出て、`.config` が artifact
`kernel-config-<arch>` に残ります（手元なら `build/kernel/output/config-<version>-<arch>`）。

> **バリアント別の config と `kimigayo_*_defconfig` は 2026-10-14 に削除しました**
> （どのスクリプトからも参照されていなかった）。過去の資料や古いコミットに出てくる
> `CONFIG_SECURITY_YAMA=y`・`CONFIG_USER_NS=y`・`CONFIG_OVERLAY_FS=y`・
> `CONFIG_SQUASHFS` などは、ビルド結果の設定ではありません。

> **seccomp はカーネルが対応しているだけで、Kimigayo は
> seccomp プロファイルを配布していません。**
> コンテナで絞るならランタイム側で指定してください
> （`docker run --security-opt seccomp=profile.json`）。

### BusyBoxアプレット選択

```ini
# 主なアプレット（全バリアント。SED / AWK は minimal.config には
# 書いておらず、既定値で入っている）
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
│  - PIE / Full RELRO / 非実行スタック    │
│    （verify-image.sh が全 ELF を検査）  │
│  - Stack canaries（arm64 の OpenRC 除く）│
│  - FORTIFY_SOURCE（下記）                │
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
ただし Layer 4 のうち、Stack Protector は v3.0.2 の arm64 の OpenRC
（`openrc`・`openrc-run`・`librc`・`libeinfo` など）には付いていません
（`scripts/build-openrc.sh` が arm64 だけ外していた。v3.1.0 で修正しました。`scripts/verify-image.sh` が検査します）。
`-D_FORTIFY_SOURCE=2` は musl ではなく Alpine の `fortify-headers` が実装します。
x86_64 はビルド環境のヘッダを使うので自動で入りますが、arm64 は自前の musl の
ヘッダだけを見るため、**v3.0.2 の arm64 には効いていません**。2026-10-14 から
arm64 のビルドも `fortify-headers` を musl より前に置き、`scripts/verify-image.sh` が
BusyBox のトラップの数で効いているかを検査します（v3.1.0 から）。
Layer 1 と 2 はホストと利用者の設定によります
（→ [システム設定ガイド](../user/CONFIGURATION.md#セキュリティ設定)）。

**配布していないもの**: seccomp プロファイル、SELinux / AppArmor の
ポリシー、`iptables`。
（イメージの署名は v3.0.2 から `release.yml` の `sign` ジョブで
Cosign のキーレス署名をしています。検証には cosign v3 以上が要ります。）
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

**目標**: 10秒以下 / **実測**: 0.60秒（v3.0.2、arm64 ネイティブ、10回の中央値）

> **これは「Kimigayo が速い」という意味ではありません。**
> 同じ条件で測ると Alpine・Ubuntu 24.04 とも 0.59 秒で、差は出ません。
> 測っている時間のほとんどがコンテナランタイム自身の処理なので、
> **イメージの中身はほとんど効きません。**
> 常駐メモリも同程度（Kimigayo 288KB / Alpine 272KB / Ubuntu 312KB）で、
> 差が出るのはサイズの方です。
>
> **OpenRC が default ランレベルを完走するまでは 0.72 秒**
> （Standard、v3.0.2 の公開イメージ、2026-10-12、arm64 ネイティブ、10 回の中央値）で、
> `/bin/true` の 0.60 秒との差が Init の分です。

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

**rootfs の tarball はビット同一になった**（2026-10-12）。
同じコミット（46b05da）を CI と Manual Build で別々にビルドし、
standard / x86_64 の tarball の SHA-256 が一致した。
`build-system/Makefile` が `REPRODUCIBLE_BUILD ?= yes` と
`SOURCE_DATE_EPOCH` を設定し、tarball は並び順・mtime・gzip ヘッダを
固定して作っている（→ [BUILD_GUIDE.md](BUILD_GUIDE.md#再現可能ビルド)）。

**確かめたのは 1 組・1 バリアントだけで、Docker イメージの digest は
見ていない。** 名乗る範囲は「rootfs の tarball」に留める。
（[config.mk](../../config.mk) はどこからも include されていないので、
そこにある設定は効いていない。）

### 5. パフォーマンス

目標値は [SPECIFICATION.md](../../SPECIFICATION.md) §8.3 の定義。
実測は v3.0.2 の公開イメージ（2026-10-12）。

| 指標 | 目標 | 実測 |
|------|------|------|
| 起動時間 | < 10秒 | 0.60秒 |
| 常駐メモリ | < 128MB | 288KB |
| イメージサイズ (Minimal) | < 5MB | 2.46MB / arm64 2.83MB |
| イメージサイズ (Standard) | < 15MB | 2.60MB / arm64 2.98MB |
| イメージサイズ (Extended) | < 50MB | 2.62MB / arm64 3.01MB |

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
