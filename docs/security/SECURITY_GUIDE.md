# Kimigayo OS セキュリティガイド

このガイドでは、Kimigayo OSのセキュリティ機能と、システムをより安全に運用するための設定方法を説明します。

## 前提: この文書のどこが効くか

**Kimigayo OS の成果物は rootfs だけを詰めた Docker イメージです。**
カーネルはイメージに入らず、コンテナはホストのカーネルで動きます。
**このため、以下の章の多くはコンテナでは直接使えません。**

| 章 | コンテナ | ホスト（ベアメタル／VM）|
| --- | --- | --- |
| カーネルセキュリティ（sysctl・モジュール）| **効かない**（`/proc/sys` は読み取り専用。ホスト側で設定）| ホストの OS で設定する |
| ネットワークセキュリティ（`iptables`）| **使えない**（`iptables` は未収録。ホストかオーケストレータで）| ホストの OS で設定する |
| SSH 強化 | **使えない**（`sshd` は未収録。`docker exec` を使う）| ホストの OS で設定する |
| アクセス制御（`sudo`）| **使えない**（`sudo` も `wheel` も無い。`--user` を使う）| ホストの OS で設定する |
| ログとモニタリング | syslog は動いていない。`docker logs` を使う | ホストの OS で設定する |
| インシデント対応 | 下記の「コンテナの場合」を使う | ホストの OS の手順で |

**ホスト側の作業は、Kimigayo ではなくホストの OS（Ubuntu など）で行います。**
Kimigayo はパッケージマネージャーを持たず、`iptables`・`sshd`・`sudo`・
`logrotate`・`auditd` を追加する仕組みもありません。

**コンテナでの設定は[システム設定ガイド](../user/CONFIGURATION.md#セキュリティ設定)に
まとめてあります。** こちらを先に読んでください。

## 目次

- [セキュリティアーキテクチャ](#セキュリティアーキテクチャ)
- [カーネルセキュリティ](#カーネルセキュリティ)
- [ネットワークセキュリティ](#ネットワークセキュリティ)
- [アクセス制御](#アクセス制御)
- [ログとモニタリング](#ログとモニタリング)
- [インシデント対応](#インシデント対応)
- [セキュリティチェックリスト](#セキュリティチェックリスト)

> **「パッケージセキュリティ」の章はありません。**
> Kimigayo はパッケージマネージャーを**意図的に持ちません**。
> 侵入されてもパッケージ経由で道具を入れることはできません。
> ただし `wget`（standard 以上）・`nc`（standard 以上）・`ftpget` などで
> ファイルを取得することはでき、`/tmp` も既定では書き込み・実行が可能です。
> 持ち込みを防ぐには `--read-only` と `--tmpfs /tmp:rw,noexec,nosuid` を併用します。

## セキュリティアーキテクチャ

Kimigayo OSは多層防御（Defense in Depth）の原則に基づいて設計されています。

```
┌─────────────────────────────────────────────┐
│ パッケージマネージャー不在                   │★ Kimigayo
│   - パッケージ経由の追加インストール手段が無い│
├─────────────────────────────────────────────┤
│ コンパイル層                                 │★ Kimigayo
│   - PIE, RELRO (-z relro -z now), 非実行スタック│
│   - Stack protector（v3.0.2 の arm64 OpenRC 以外）│
├─────────────────────────────────────────────┤
│ 小さな実行面                                 │★ Kimigayo
│   - 共有ライブラリは musl と OpenRC のものだけ│
│   - sshd / sudo / iptables / curl 無し       │
├─────────────────────────────────────────────┤
│ カーネル層                                   │ ホストが提供
│   - Namespace / cgroup, ASLR, seccomp        │
├─────────────────────────────────────────────┤
│ コンテナランタイム層                         │ 利用者が設定
│   - --cap-drop / --read-only / --user        │
│   - seccomp プロファイル                     │
└─────────────────────────────────────────────┘
```

**★ の 3 層が Kimigayo 自身が担保する部分です。**
強化フラグの詳細（どれを検査しているか、効果が確認できていないもの）は
[セキュリティポリシー](SECURITY_POLICY.md#コンパイル時のセキュリティ強化)を見てください。

> **実行面について正直に書くと**: `telnetd`・`ftpd`・`httpd`・`crond`・`nc` などの
> BusyBox アプレットはイメージに入っています（`nc` は standard 以上、
> ほかは全バリアント）。**既定では起動していません**（PID 1 は `/bin/sh`）。
> 不要なら利用者のイメージで該当するリンクを消してください。

> **Kimigayo は seccomp プロファイルを配布していません。**
> seccomp を効かせるのは**ホストのカーネルとコンテナランタイム**です
> （Docker は既定のプロファイルを適用します）。さらに絞るなら
> `docker run --security-opt seccomp=profile.json` のように
> ランタイム側で指定してください（→ [HARDENING_GUIDE.md](HARDENING_GUIDE.md#seccomp-bpfの使用)）。
> SELinux / AppArmor のポリシーも配布していません。

## カーネルセキュリティ

### カーネルパラメータの強化

> **コンテナからは設定できません。** `/proc/sys` が読み取り専用で、
> `sysctl -w` は `Read-only file system` で失敗します。
> 名前空間化されたものだけ `docker run --sysctl ...` で渡せます
> （`kernel.kptr_restrict` などは whitelist 外で拒否されます）。
> **以下はホスト側の作業です。**
>
> イメージが出荷している `/etc/sysctl.d/99-kimigayo-performance.conf` で
> セキュリティに関わるのは `kernel.randomize_va_space = 2` /
> `fs.suid_dumpable = 0` / `net.ipv4.tcp_syncookies = 1` の 3 つです
> （コンテナでは適用されません）。

ホストで、セキュリティを強化するカーネルパラメータを設定します：

```bash
# ホストで /etc/sysctl.d/99-security.conf を作成
vi /etc/sysctl.d/99-security.conf
```

以下の設定を追加：

```ini
# カーネル強化
kernel.dmesg_restrict = 1
kernel.kptr_restrict = 2
kernel.yama.ptrace_scope = 1
kernel.kexec_load_disabled = 1

# ASLRの強化
kernel.randomize_va_space = 2

# ネットワーク保護
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.secure_redirects = 0
net.ipv4.conf.default.secure_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.icmp_ignore_bogus_error_responses = 1
net.ipv4.tcp_syncookies = 1

# IPv6保護
net.ipv6.conf.all.accept_redirects = 0
net.ipv6.conf.default.accept_redirects = 0
net.ipv6.conf.all.accept_source_route = 0
net.ipv6.conf.default.accept_source_route = 0

# ファイルシステム保護
fs.protected_hardlinks = 1
fs.protected_symlinks = 1
fs.suid_dumpable = 0
```

```bash
# ホストで設定を反映
sysctl -p /etc/sysctl.d/99-security.conf
```

### カーネルモジュールのブラックリスト

> **コンテナからは操作できません**（`/lib/modules` が無く `modprobe` は
> 失敗します。`lsmod` が見せるのは**ホストの**モジュールです）。
> **以下はホスト側の作業です。**

ホストで不要なカーネルモジュールを無効化：

```bash
# ホストで /etc/modprobe.d/blacklist.conf を作成
vi /etc/modprobe.d/blacklist.conf
```

```ini
# 使用しないファイルシステム
blacklist cramfs
blacklist freevxfs
blacklist jffs2
blacklist hfs
blacklist hfsplus
blacklist udf

# 使用しないネットワークプロトコル
blacklist dccp
blacklist sctp
blacklist rds
blacklist tipc

# 使用しないUSBストレージ（必要に応じて）
# blacklist usb-storage
```

## ネットワークセキュリティ

### 通信の制御

**コンテナの場合** — `iptables` はイメージに入っていません。
通信制御は `docker run` のオプションか、ホスト／オーケストレータで行います。

```bash
# 公開するポートをループバックに限る
docker run -d -p 127.0.0.1:8080:8080 <your-app-image>

# ネットワークを持たせない
docker run --rm --network none ishinokazuki/kimigayo-os:3.0.2 <command>
```

Kubernetes なら `NetworkPolicy` を使います。

**ホスト側** — ホストのファイアウォール（`iptables` / `nftables` / `ufw` など）を
ホストの OS の手順で設定します。Docker が公開したポートは
ホストの `INPUT` チェインではなく `DOCKER-USER` チェインで制御する点に
注意してください。

### SSH

> **`sshd` と `/etc/ssh` はイメージに入っていません。** コンテナへの
> 接続は `docker exec -it <container> /bin/sh` を使います。
> **`sshd` を入れることは推奨しません**（攻撃面が増え、不変インフラの
> 前提も崩れます）。

ホスト（VPS）の SSH は、ホストの OS で強化します。最低限の推奨設定
（ホストの `/etc/ssh/sshd_config`）：

```ini
PermitRootLogin no
PasswordAuthentication no
PermitEmptyPasswords no
PubkeyAuthentication yes
X11Forwarding no
MaxAuthTries 3
LoginGraceTime 30
```

公開鍵はクライアント側で `ssh-keygen -t ed25519` で作り、
`ssh-copy-id` でホストに登録します。

## アクセス制御

### ユーザーと権限

> **`sudo` も `/etc/sudoers` も `wheel` グループも `/etc/login.defs` もありません**
> （`su` のアプレットはあります）。イメージの既定ユーザーは root です。

**コンテナの場合** — 権限は `docker run` で落とします。

```bash
docker run --rm \
  --user 65534:65534 \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  ishinokazuki/kimigayo-os:3.0.2 id
# → uid=65534(nobody) gid=65534(nogroup)
```

自分のアプリのイメージでは `USER` を指定します
（`examples/` の 3 つはすべて `USER 65534`）。

ユーザーを追加したい場合は、イメージのビルド時に BusyBox の `adduser` を使います
（`adduser -D -H -s /sbin/nologin app` のように）。BusyBox の `adduser` /
`passwd` は `/etc/login.defs` を読まないので、パスワードの有効期限などの
ポリシーは設定できません。

### ファイルとディレクトリのパーミッション

イメージの既定値（3.0.2 実測）:

| ファイル | 権限 |
| --- | --- |
| `/etc/passwd` | 644 |
| `/etc/shadow` | 600（`verify-image.sh` が検査） |
| `/etc/group` | 644 |
| `/root` | 700 |
| `/tmp`・`/var/tmp` | 1777 |

`/etc/gshadow`・`/boot` はありません。setuid / setgid のファイルは 0 個です
（`verify-image.sh` が検査）。確認するには：

```bash
docker run --rm ishinokazuki/kimigayo-os:3.0.2 \
  find / -xdev -perm /6000 -type f
# 何も出なければ setuid / setgid は無い
```

## ログとモニタリング

### システムログ

> **コンテナでは syslog は動いておらず、`/var/log` は空です。**
> 標準出力・標準エラーに出したものを `docker logs` で読みます。
> `dmesg` も `CAP_SYSLOG` が無いため使えません。
> `logrotate` もイメージに入っていません。

```bash
# コンテナのログ
docker logs -f <container>

# ログの肥大化はランタイム側で抑える
docker run --log-opt max-size=10m --log-opt max-file=3 ...
```

認証ログやカーネルログ（`/var/log/auth.log`・`dmesg`）を見るのは
ホスト側の作業です。

### プロセスとネットワークの確認（コンテナ内）

BusyBox の `ps` は `aux` を受け付けません。`ps -o` は extended だけで使えます
（minimal / standard の `ps` はオプションを持たない）。

```bash
docker exec <container> ps
docker exec <container> top -b -n1
docker exec <container> netstat -tulanp
```

## インシデント対応

### 侵害の兆候

以下の兆候が見られた場合は、システムが侵害されている可能性があります：

- 不審なプロセスの実行
- 予期しないネットワーク接続
- ファイルシステムの改ざん
- 異常なCPU/メモリ使用量
- 不正なユーザーアカウント

### 初動対応（コンテナの場合）

コンテナは作り直せるので、**調べる前に証拠を残し、作り直す**のが基本です。

```bash
# 1. ネットワークから切り離す（コンテナは止めない）
docker network disconnect <network> <container>

# 2. 実行中のプロセスとネットワーク接続を確認
docker exec <container> ps
docker exec <container> netstat -tulanp

# 3. イメージからの変更点を確認（--read-only なら何も出ないはず）
docker diff <container>

# 4. ファイルシステムのスナップショットを取る
docker export <container> > incident-$(date +%Y%m%d-%H%M%S).tar
docker logs <container> > incident-$(date +%Y%m%d-%H%M%S).log 2>&1

# 5. 停止して、信頼できるイメージから作り直す
docker stop <container>
```

ホストが侵害された疑いがある場合は、ホストの OS の手順で対応します。

### フォレンジック調査

```bash
# 取得したスナップショットを展開して調べる（ホスト側）
mkdir snapshot && tar -xf incident-*.tar -C snapshot

# 公開イメージと実行ファイルのハッシュを比べる
docker run --rm ishinokazuki/kimigayo-os:3.0.2 sha256sum /bin/busybox
sha256sum snapshot/bin/busybox

# 最近変更されたファイル
find snapshot/etc -mtime -1 -type f

# 隠しファイル
find snapshot -name ".*" -type f

# setuid / setgid（公開イメージには 0 個）
find snapshot -perm -4000 -o -perm -2000
```

## セキュリティチェックリスト

### 初期セットアップ時

- [ ] 使うタグを固定する（例: `3.0.2-standard`）。必要なら `cosign verify` で署名を確認（→ [セキュリティポリシー](SECURITY_POLICY.md#イメージの署名)）
- [ ] `--read-only`・`--cap-drop ALL`・`--security-opt no-new-privileges`・`--user` を付ける
- [ ] 公開するポートを絞る（`-p 127.0.0.1:...`、`--network none`）
- [ ] ホストの OS 側でファイアウォール・SSH・カーネルパラメータを設定する

### 定期的なメンテナンス（週次）

- [ ] 新しいリリース（[GitHub Releases](https://github.com/Kazuki-0731/Kimigayo/releases)）とセキュリティアドバイザリを確認する
- [ ] 新しい版が出ていたら、イメージを pull してコンテナを作り直す（コンテナ内で更新する手段はありません）
- [ ] `docker logs` を確認する

### 定期的なメンテナンス（月次）

- [ ] 使っている `docker run` のオプションと公開ポートを見直す
- [ ] ホストの OS とカーネルを更新する

## 参考資料

- [セキュリティポリシー](SECURITY_POLICY.md)
- [脆弱性報告手順](VULNERABILITY_REPORTING.md)
- [セキュリティ強化設定](HARDENING_GUIDE.md)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)

## 緊急連絡先

セキュリティインシデント・脆弱性の報告は
[GitHub Security Advisories](https://github.com/Kazuki-0731/Kimigayo/security/advisories/new)
（非公開）だけで受け付けます。メールの窓口はありません。
