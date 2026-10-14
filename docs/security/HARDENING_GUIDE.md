# Kimigayo OS セキュリティ強化ガイド

このガイドでは、Kimigayo OSを動かすときのセキュリティ強化の設定と手順を説明します。

## 前提: この文書のどこが効くか

**Kimigayo OS の成果物は rootfs だけの Docker イメージです。**
カーネルはイメージに入らず、コンテナはホストのカーネルで動きます。

| 章 | コンテナ | ホスト（ベアメタル／VM）|
| --- | --- | --- |
| [コンテナセキュリティ](#コンテナセキュリティ) | **ここを読む** | — |
| カーネル強化（sysctl・モジュール）| **効かない**（ホスト側で設定）| ホストの OS で設定する |
| ネットワーク強化 | `-p` / `--network` で制御（`iptables` は未収録）| ホストの OS で設定する |
| ファイルシステム強化 | `--read-only` / `--tmpfs` を使う | ホストの OS で設定する |
| アプリケーション強化（seccomp）| ランタイム側で指定 | — |
| 監査 | `docker logs` / `docker diff` | ホストの `auditd` などで |

**「ホスト」の作業は、Kimigayo ではなくホストの OS（Ubuntu など）で行います。**
Kimigayo はパッケージマネージャーを持たず、`iptables`・`sshd`・`auditd` を
イメージに追加する仕組みもありません。ベアメタル起動は対象外です。

**コンテナで実際に効く設定は[システム設定ガイド](../user/CONFIGURATION.md#セキュリティ設定)に
まとめてあります。** 迷ったらそちらを先に読んでください。

> **自動強化スクリプトは配布していません。**
> 以前この文書は `/usr/share/kimigayo/security/harden-level{1,2,3}.sh` の
> 実行を案内していましたが、**3 本とも存在しません**
> （リポジトリにもイメージにも無い。2026-10-11 に確認）。
> 下記は手で設定する内容です。

## 目次

- [レベル別強化設定](#レベル別強化設定)
- [カーネル強化](#カーネル強化)
- [ネットワーク強化](#ネットワーク強化)
- [ファイルシステム強化](#ファイルシステム強化)
- [アプリケーション強化](#アプリケーション強化)
- [コンテナセキュリティ](#コンテナセキュリティ)
- [監査とコンプライアンス](#監査とコンプライアンス)
- [Trivy の既知の指摘と、その判断](#trivy-の既知の指摘とその判断2026-10-11)
- [セキュリティ検証](#セキュリティ検証)

## レベル別強化設定

セキュリティ要件に応じた 3 段階の目安です（スクリプトは配布していません）。

### レベル1: 基本強化（すべての環境に推奨）

**コンテナの場合** — ここが基本です。既定の CMD は `/bin/sh` なので、
`-d` で動かすのは自分のアプリのイメージ（`<your-app-image>`）です。

```bash
docker run -d \
  --read-only --tmpfs /tmp:rw,noexec,nosuid --tmpfs /run \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --user 65534:65534 \
  -p 127.0.0.1:8080:8080 \
  <your-app-image>
```

| オプション | 何を防ぐか |
| --- | --- |
| `--read-only` | `/etc` などへの書き込み（`Read-only file system` で拒否）|
| `--tmpfs /tmp:rw,noexec,nosuid` | 持ち込んだファイルの実行 |
| `--cap-drop ALL` | 不要なケーパビリティの利用 |
| `--security-opt no-new-privileges` | setuid などによる特権昇格 |
| `--user 65534:65534` | root での実行 |
| `-p 127.0.0.1:...` | 外部への意図しない公開 |

**`sshd`・`iptables`・`sudo` はイメージに入っていません。**
一方で `telnetd`・`ftpd`・`httpd`・`crond` の BusyBox アプレットは
全バリアントに、`nc`・`telnet`（クライアント）は standard 以上に入っています。
**既定ではどれも起動していません**（PID 1 は `/bin/sh`）。
使わないなら、自分のイメージで該当するリンク（`/sbin/telnetd` など）を
消しておくと確実です。

**ホスト側** — ホストの OS で、ファイアウォールを有効にし、
SSH の root ログインとパスワード認証を無効にします
（→ [SECURITY_GUIDE.md](SECURITY_GUIDE.md#ssh)）。

### レベル2: 中程度の強化（サーバー環境推奨）

レベル1の設定に加えて、次を設定します。

**コンテナの場合**:

```bash
docker run -d \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=64m \
  --tmpfs /run:rw,noexec,nosuid,nodev \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --user 65534:65534 \
  --pids-limit 100 --memory 512m --cpus 0.5 \
  <your-app-image>
```

**ホスト側**（ホストの `/etc/sysctl.d/99-security.conf` に置き、
`sysctl -p /etc/sysctl.d/99-security.conf` で反映）:

```ini
kernel.dmesg_restrict = 1
kernel.kptr_restrict = 2
kernel.yama.ptrace_scope = 1
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.tcp_syncookies = 1
```

### レベル3: 最大強化（高セキュリティ環境）

パフォーマンスや互換性に影響する可能性があります。

**コンテナの場合** — seccomp プロファイルで使えるシステムコールを絞り
（→ [Seccomp-BPFの使用](#seccomp-bpfの使用)）、Docker デーモンの
`userns-remap` を有効にします（→ [Dockerの強化](#dockerの強化)）。

**ホスト側** — レベル2に加えて:

```ini
kernel.kexec_load_disabled = 1
kernel.unprivileged_bpf_disabled = 1
fs.protected_fifos = 2
fs.protected_regular = 2
# Debian / Ubuntu の独自パッチのカーネルにだけある項目（素のカーネルには無い）
# kernel.unprivileged_userns_clone = 0
```

## カーネル強化

### カーネルパラメータの最適化

> **コンテナからは設定できません**（`/proc/sys` が読み取り専用で
> `sysctl -w` は `Read-only file system`）。名前空間化されたものだけ
> `docker run --sysctl` で渡せます。**以下はホスト側の作業です。**

```bash
# ホストで /etc/sysctl.d/99-security.conf を作成
vi /etc/sysctl.d/99-security.conf
```

推奨設定：

```ini
# カーネル強化
kernel.dmesg_restrict = 1                    # dmesgへのアクセス制限
kernel.kptr_restrict = 2                     # カーネルポインタの非表示
kernel.yama.ptrace_scope = 1                 # ptraceの制限
kernel.kexec_load_disabled = 1               # kexecの無効化
kernel.unprivileged_bpf_disabled = 1         # 非特権BPFの無効化
# kernel.unprivileged_userns_clone = 0       # Debian/Ubuntu 独自。素のカーネルには無い。
#                                            # 無効にすると rootless コンテナが動かない

# メモリ保護
vm.mmap_min_addr = 65536                     # NULL pointer dereference対策
kernel.randomize_va_space = 2                # ASLR完全有効化

# ファイルシステム保護
fs.protected_hardlinks = 1                   # ハードリンク保護
fs.protected_symlinks = 1                    # シンボリックリンク保護
fs.protected_fifos = 2                       # FIFO保護
fs.protected_regular = 2                     # 通常ファイル保護
fs.suid_dumpable = 0                         # SUID dumpの無効化

# ネットワーク保護（IPv4）
net.ipv4.conf.all.rp_filter = 1              # リバースパスフィルタリング
net.ipv4.conf.default.rp_filter = 1
net.ipv4.conf.all.accept_source_route = 0    # ソースルーティング拒否
net.ipv4.conf.default.accept_source_route = 0
net.ipv4.conf.all.accept_redirects = 0       # ICMPリダイレクト拒否
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.secure_redirects = 0       # 安全なICMPリダイレクトも拒否
net.ipv4.conf.default.secure_redirects = 0
net.ipv4.conf.all.send_redirects = 0         # ICMPリダイレクト送信無効
net.ipv4.conf.default.send_redirects = 0
net.ipv4.icmp_echo_ignore_broadcasts = 1     # ブロードキャストping無視
net.ipv4.icmp_ignore_bogus_error_responses = 1
net.ipv4.tcp_syncookies = 1                  # SYN Flood対策
net.ipv4.conf.all.log_martians = 1           # 異常パケットのログ

# ネットワーク保護（IPv6）
net.ipv6.conf.all.accept_redirects = 0
net.ipv6.conf.default.accept_redirects = 0
net.ipv6.conf.all.accept_source_route = 0
net.ipv6.conf.default.accept_source_route = 0
```

> Docker ホストでは `net.ipv4.ip_forward` を 0 にしたり、IPv6 を
> 丸ごと無効にしたりするとコンテナの通信が壊れることがあります。

```bash
# ホストで設定を反映
sysctl -p /etc/sysctl.d/99-security.conf
```

### カーネルモジュールの制限

> **コンテナからは操作できません**（`/lib/modules` が無く `modprobe` は
> 失敗。`lsmod` が見せるのは**ホストの**モジュール）。**ホスト側の作業です。**

```bash
# ホストで /etc/modprobe.d/security.conf を作成
vi /etc/modprobe.d/security.conf
```

```ini
# 使用しないファイルシステム
install cramfs /bin/true
install freevxfs /bin/true
install jffs2 /bin/true
install hfs /bin/true
install hfsplus /bin/true
install udf /bin/true

# 使用しないネットワークプロトコル
install dccp /bin/true
install sctp /bin/true
install rds /bin/true
install tipc /bin/true
```

## ネットワーク強化

**コンテナの場合** — `iptables` はイメージに入っていません。

- 公開するポートは `-p 127.0.0.1:8080:8080` のようにアドレスを絞る
- 外と通信しないなら `--network none`
- コンテナ同士は用途ごとに `docker network create` で分ける
- Kubernetes なら `NetworkPolicy`

**ホスト側** — ホストのファイアウォールで制御します。Docker が公開した
ポートはホストの `INPUT` チェインを通らないので、絞るなら
`DOCKER-USER` チェインにルールを書きます（ホストの OS と Docker の
ドキュメントに従ってください）。

## ファイルシステム強化

### マウントオプション

**コンテナでは `/etc/fstab` は読まれません。** 同じことは
`docker run` 側で指定します。

```bash
docker run --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=64m \
  --tmpfs /var/tmp:rw,noexec,nosuid,nodev,size=16m \
  --tmpfs /run:rw,noexec,nosuid,nodev \
  ishinokazuki/kimigayo-os:3.0.2 <command>
```

- `nodev`: デバイスファイルの無効化
- `nosuid`: SUID/SGIDビットの無効化
- `noexec`: 実行ファイルの無効化

### ファイルパーミッションの監査

公開イメージには setuid / setgid のファイルも world-writable のファイルも
ありません（3.0.2 実測。前者は `verify-image.sh` が検査）。
自分のイメージで確かめるには（BusyBox の `find` は `-nouser` と `-ls` に
対応していません）：

```bash
# SUID/SGIDビットが設定されたファイル
docker run --rm <image> find / -xdev -perm /6000 -type f

# World-writableファイル
docker run --rm <image> find / -xdev -type f -perm -0002

# root・nobody 以外が所有するファイル（-nouser の代わり。公開イメージのユーザーはこの 2 つだけ）
docker run --rm <image> sh -c \
  'find / -xdev ! -user root ! -user nobody -exec ls -ln {} \;'

# 見つけた SUID/SGID ビットを外す（Dockerfile の RUN で）
chmod u-s,g-s /path/to/file
```

### 重要ファイルの権限

イメージの既定値は `/etc/passwd` 644・`/etc/shadow` 600・`/etc/group` 644・
`/root` 700 です（`/etc/shadow` は `verify-image.sh` が検査）。
`/etc/gshadow`・`/etc/ssh`・`/boot` はありません。

## アプリケーション強化

### Seccomp-BPFの使用

システムコールをフィルタリングして、アプリケーションのセキュリティを強化します。

**プロファイルはホスト側に置きます。** Kimigayo のイメージには
seccomp プロファイルは入っておらず（rootfs だけでカーネルも持たない）、
適用するのは `docker run --security-opt` です。
**Docker は既定のプロファイルを適用している**ので、何も指定しなくても
危険なシステムコールの多くは塞がれています。

さらに絞るときは、**Docker の既定プロファイルを出発点にして**、
アプリが使わないものを削ります。ゼロから最小のリストを書くと、
`execve`・`mmap`・`exit_group` などが漏れてコンテナが起動しなくなります。

```bash
# 1) Docker の既定プロファイルを取得（使っている Docker の版に合わせる）
curl -fsSLO https://raw.githubusercontent.com/moby/profiles/main/seccomp/default.json

# 2) アプリが使わないシステムコールを削ったものを用意する
cp default.json /etc/docker/seccomp/myapp.json   # ← 編集する

# 3) 適用して動作確認する
docker run --rm --security-opt seccomp=/etc/docker/seccomp/myapp.json <your-app-image>
```

## コンテナセキュリティ

### Dockerの強化

ホストの Docker デーモンの設定（`/etc/docker/daemon.json`）。
**ホスト側の作業です。**

```json
{
  "icc": false,
  "userns-remap": "default",
  "no-new-privileges": true,
  "live-restore": true,
  "userland-proxy": false,
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

独自の seccomp プロファイルを既定にしたい場合は `"seccomp-profile"` に
そのパスを足します（→ [Seccomp-BPFの使用](#seccomp-bpfの使用)）。

### コンテナ実行時のセキュリティ

```bash
# セキュアなコンテナ起動例（<your-app-image> は Kimigayo をベースにした自分のイメージ）
docker run -d \
  --read-only \
  --tmpfs /tmp:noexec,nosuid,nodev \
  --security-opt=no-new-privileges \
  --cap-drop=ALL \
  --cap-add=NET_BIND_SERVICE \
  --user 65534:65534 \
  --pids-limit 100 \
  --memory 512m \
  --cpus 0.5 \
  <your-app-image>
```

### イメージの署名と SBOM

v3.0.2 から公開イメージには Cosign のキーレス署名があり、SBOM（CycloneDX）は
GitHub Release に添付しています。検証手順は
[セキュリティポリシー](SECURITY_POLICY.md#イメージの署名)にあります
（cosign v3 以上が必要）。

## 監査とコンプライアンス

**コンテナの場合** — `auditd` はイメージに入っていません（コンテナの中で
動かすものでもありません）。コンテナの監査は次で行います。

```bash
# イメージからの変更点（--read-only なら何も出ない）
docker diff <container>

# 出力されたログ
docker logs <container>
```

**ホスト側** — ホストの OS で `auditd` や `falco` を設定します。
Docker 関連の監査ルールの例（ホストの `/etc/audit/rules.d/docker.rules`）:

```bash
-w /usr/bin/dockerd -k docker
-w /var/lib/docker -k docker
-w /etc/docker -k docker
-w /etc/docker/daemon.json -k docker
```

> 以前ここに「CIS Benchmark スクリプト（`alpine-linux-benchmark.sh`）を
> 取得して実行する」手順があったが、**その URL は 404 で、イメージに
> `bash` も無い**（2026-10-12 に確認して削除）。Kimigayo は CIS
> Benchmark への準拠を謳っていない。

## Trivy の既知の指摘と、その判断（2026-10-11）

**`make security-scan` が毎回出す指摘のうち、意図的に直していないものを
記録する。** 次に走らせた人が同じ triage をやり直さないため。

| 指摘 | 対象 | 判断 |
| --- | --- | --- |
| **DS-0002 (HIGH)** イメージのユーザーが root | `Dockerfile` | **直さない。** これはビルド環境のイメージで、`apk` やクロスコンパイル、`/build` への書き込みに root が必要。公開物ではない |
| **DS-0002 (HIGH)** イメージのユーザーが root | `Dockerfile.runtime` | **直さない（要判断として保留）。** 公開イメージの既定ユーザーを変えると、`openrc` が動かなくなり、既存の利用者全員に影響する破壊的変更になる。**利用者側で `docker run --user 65534` か Dockerfile の `USER` を使う**ことを案内する（→ `examples/` の3つはすべて `USER 65534` にしてある） |
| `make trivy-scan`（イメージスキャン）が何も検出しない | 公開イメージ | **仕様。** パッケージデータベースを持たないため Trivy が対象を1つも識別できない。「脆弱性 0 件」ではなく「スキャンしていない」。2026-10-11 に `security-scan` から外し、出荷物の CVE 照合は `make scan-image`（イメージ内のバイナリから読んだ版で SBOM を作り Grype で照合）に置き換えた |

> **`make scan-image` の CVE 照合は、v3.0.1 の公開イメージで 5 件を検出している**
> （BusyBox 1.38.0 に 3 件・musl 1.2.6 に 2 件、2026-10-11）。
> **v3.0.2 で 5 件すべてにパッチを当て、v3.0.2 の公開イメージは 0 件**（2026-10-12）。
> 一覧と対応は [SECURITY_AUDIT.md](SECURITY_AUDIT.md#検出された-cve-と対応2026-10-11) にある。

### BusyBox の cpio はディレクトリを脱出できた（v3.0.1 まで。修正済み）

**v3.0.1 までの `busybox cpio -i` は、エントリ名の `../` を剥がさなかった**
（2026-10-11 実測）。**2026-10-11 に
`CONFIG_FEATURE_PATH_TRAVERSAL_PROTECTION=y` を 3 バリアントすべてで
有効にして修正した。v3.0.2 から有効。**

修正を実際の脱出で検証した結果:

| BusyBox | 警告 | 展開先 |
| --- | --- | --- |
| **新 Kimigayo 1.38.0（保護有効）** | `cpio: removing leading '../' from member names` | **展開先ディレクトリ内**（阻止）|
| Alpine 3.24 の 1.37.0（保護無効・比較）| なし | **展開先の外**（脱出成功）|

再現手順（`../escaped` を含む cpio を作り、`dest/` から展開する）:

```bash
# 悪意あるアーカイブを作る
mkdir -p /work/mk/sub /work/target/dest
echo PWNED > /work/mk/escaped          # /work/mk/sub から見て ../escaped
cd /work/mk/sub && printf '../escaped\n' | cpio -o -H newc > /work/evil.cpio

# 展開してどこに出るか見る
cd /work/target/dest && busybox cpio -iv -F /work/evil.cpio
# 保護あり: /work/target/dest/escaped（内側）
# 保護なし: /work/target/escaped（外側 = 脱出）
```

> **検証するときは、BusyBox を `busybox` という名前で置くこと。**
> BusyBox は `argv[0]` でアプレットを決めるので、
> `/opt/bb/new-busybox cpio ...` のように別名で置くと
> `applet not found`（rc=127）になり、**「何も展開されなかった」のを
> 「保護が効いた」と読み違える。** 2026-10-11 に実際にこれで
> 誤った結論を出しかけた。

- **`tar` と `unzip` はエントリ名の `../` を常に剥がす**
  （`archival/tar.c` の `skip_unsafe_prefix`、`archival/unzip.c` の
  `strip_unsafe_prefix`）。ただし `tar` のシンボリックリンク／ハードリンク
  経由の脱出は下記の CVE-2026-108119 があり、安全とは言い切れない
- **`cpio` / `ar` / `rpm` が `CONFIG_FEATURE_PATH_TRAVERSAL_PROTECTION`
  に依存する。** BusyBox の既定は `n`
- 影響範囲: `cpio` は 3 バリアントすべてに入っている（minimal にも
  既定で入っていた）。`ar` は extended のみ。`rpm` は v3.0.1 で削除済み
- **アプレット数は変わらない**（extended: 411 のまま。BusyBox のサイズは
  v3.0.2 の動的リンク化で変わったので、ここでは比べられない）

**v3.0.1 以前のイメージを使っているあいだは、信頼できないアーカイブを
特権で展開しないこと。**

**回帰テストは `scripts/verify-image.sh` に入っている。** イメージ内で
`../escape` を含む cpio を実際に作って展開し、展開先の外にファイルが
できたら `ESCAPED` で失敗する。v3.0.1 の公開イメージは `ESCAPED`、
現在の `main` からビルドしたイメージは `CONTAINED` になる。
config の行が消えると既定値（`n`）に黙って戻るため、config ではなく
挙動を見ている。

関連して、2026-10-09 に **CVE-2026-108119**（BusyBox の `tar` の遅延リンク
生成が展開先の外を検証しない、CVSS 6.3 MEDIUM）が公表された。
**Kimigayo の BusyBox 1.38.0 も影響を受ける**（2026-10-13 に公開イメージ
3.0.2 の 3 バリアントで実測。Alpine 3.24 の busybox 1.37.0-r31 と edge の 1.38.0-r7 も同じ）。

- 1 本の tar に `esc -> ..` と `esc/escaped.txt` を入れる形は止まる
  （`esc/` が先に実ディレクトリとして作られ、シンボリックリンクの作成が失敗する）
- **2 本に分けると抜ける。** 1 本目で `esc -> ..` だけを作り、2 本目で
  ハードリンク `esc/escaped.txt` を同じディレクトリに展開すると、
  展開先の外に `escaped.txt` ができる
- 原因は `archival/libarchive/unsafe_symlink_target.c` の
  `create_links_from_list` が、遅延して作るリンクの解決先が展開先の中に
  収まるかを確かめないこと

**上流 BusyBox に修正コミットがある**（`382008b3f07d` tar: protect against
Symlink+Hardlink attack、2026-10-09。関連 `5da20102b5db`）。リリース・Alpine・
Debian にはまだ入っていない（2026-10-14 時点）。
NVD にまだ BusyBox の CPE が載っていないため、
**`make scan-image`（Grype による CPE 照合）では検出されない。**
発動条件は「信頼できない tar を、同じ展開先に続けて特権で展開する」こと
（CVSS は `AV:L/AC:H/UI:R`）。**それまでは、信頼できない tar を同じ
ディレクトリに続けて展開しないこと。** 取り込むときは
`src/busybox/patches/` に CVE ID 入りの名前で置く。上流との差分は
`security.yml` が毎日確かめ、出たら Issue と Discord で知らせる
（追跡: [#121](https://github.com/Kazuki-0731/Kimigayo/issues/121)）。

---

## セキュリティ検証

### 設定の検証

コンテナに対して確かめるもの:

```bash
# 付けたオプションが効いているか（ReadonlyRootfs・CapDrop・SecurityOpt・User）
docker inspect --format '{{.HostConfig.ReadonlyRootfs}} {{.HostConfig.CapDrop}} {{.HostConfig.SecurityOpt}} {{.Config.User}}' <container>

# 待ち受けているポート
docker exec <container> netstat -tuln

# SUIDファイル（BusyBox の find は -ls に対応しない）
docker exec <container> find / -xdev -perm -4000 -type f
```

カーネルパラメータとファイアウォールの確認はホスト側で行います。

### 脆弱性スキャン

```bash
# ポートスキャン（外部から）
# nmap -sS <your-ip>

# 出荷物の既知の CVE 照合（SBOM + Grype。リポジトリで実行し、
# kimigayo-os:<variant>-<arch> のイメージが要る）
make scan-image VARIANT=standard ARCH=x86_64
```

公開イメージなら、GitHub Release に添付した SBOM（`*.cdx.json`）を
自分の照合器（Grype など）にかけても確かめられます。
`cat /etc/os-release` で分かるのは版だけで、脆弱性の確認にはなりません。

## 参考リソース

- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [セキュリティポリシー](SECURITY_POLICY.md)
- [セキュリティガイド](SECURITY_GUIDE.md)

---

**注意**: すべてのセキュリティ設定は、本番環境に適用する前にテスト環境で十分に検証してください。
