# Kimigayo OS セキュリティガイド

このガイドでは、Kimigayo OSのセキュリティ機能と、システムをより安全に運用するための設定方法を説明します。

## 目次

- [セキュリティアーキテクチャ](#セキュリティアーキテクチャ)
- [カーネルセキュリティ](#カーネルセキュリティ)
- [ネットワークセキュリティ](#ネットワークセキュリティ)
- [アクセス制御](#アクセス制御)
- [パッケージセキュリティ](#パッケージセキュリティ)
- [ログとモニタリング](#ログとモニタリング)
- [インシデント対応](#インシデント対応)

## セキュリティアーキテクチャ

Kimigayo OSは多層防御（Defense in Depth）の原則に基づいて設計されています。

```
┌─────────────────────────────────────────────┐
│         アプリケーション層                    │
│         - Seccomp-BPF                       │
│         - Namespace isolation               │
├─────────────────────────────────────────────┤
│         システム層                           │
│         - ファイアウォール（iptables）        │
│         - SSHアクセス制御                    │
├─────────────────────────────────────────────┤
│         カーネル層                           │
│         - ASLR, DEP, PIE                    │
│         - カーネルパラメータ強化              │
├─────────────────────────────────────────────┤
│         コンパイル層                         │
│         - Stack protector, FORTIFY_SOURCE   │
│         - RELRO, PIE                        │
└─────────────────────────────────────────────┘
```

## カーネルセキュリティ

### カーネルパラメータの強化

セキュリティを強化するカーネルパラメータの設定：

```bash
# /etc/sysctl.conf を編集
vi /etc/sysctl.conf
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
# 設定を反映
sysctl -p
```

### カーネルモジュールのブラックリスト

不要なカーネルモジュールを無効化：

```bash
# /etc/modprobe.d/blacklist.conf を作成
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

### ファイアウォール設定（iptables）

基本的なファイアウォールルールの設定：

```bash
# デフォルトポリシー（すべて拒否）
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT

# ループバックを許可
iptables -A INPUT -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT

# 確立された接続を許可
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# SSH接続を許可（ポート22）
iptables -A INPUT -p tcp --dport 22 -m state --state NEW -m recent --set
iptables -A INPUT -p tcp --dport 22 -m state --state NEW -m recent --update --seconds 60 --hitcount 4 -j DROP
iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# HTTP/HTTPSを許可（Webサーバーの場合）
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# ICMPを制限的に許可
iptables -A INPUT -p icmp --icmp-type echo-request -m limit --limit 1/s -j ACCEPT
iptables -A INPUT -p icmp --icmp-type echo-reply -j ACCEPT

# 無効なパケットをドロップ
iptables -A INPUT -m state --state INVALID -j DROP

# ログ記録（オプション）
iptables -A INPUT -m limit --limit 5/min -j LOG --log-prefix "iptables denied: " --log-level 7

# ルールを保存
rc-service iptables save

# 自動起動を有効化
rc-update add iptables default
```

### SSH強化

SSHサーバーのセキュリティ強化：

```bash
# SSH設定ファイルを編集
vi /etc/ssh/sshd_config
```

推奨設定：

```ini
# プロトコルバージョン
Protocol 2

# rootログインを無効化
PermitRootLogin no

# パスワード認証を無効化
PasswordAuthentication no
PermitEmptyPasswords no

# 公開鍵認証のみ許可
PubkeyAuthentication yes

# ホストベース認証を無効化
HostbasedAuthentication no
IgnoreRhosts yes

# X11フォワーディングを無効化（不要な場合）
X11Forwarding no

# 最大認証試行回数
MaxAuthTries 3
MaxSessions 2

# ログイン時間制限
LoginGraceTime 30

# 特定のユーザーのみ許可
AllowUsers user1 user2

# または特定のグループのみ許可
AllowGroups ssh-users

# 強力な暗号化方式のみ使用
Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com,aes128-gcm@openssh.com
MACs hmac-sha2-512-etm@openssh.com,hmac-sha2-256-etm@openssh.com
KexAlgorithms curve25519-sha256,curve25519-sha256@libssh.org,diffie-hellman-group-exchange-sha256

# ポート番号の変更（オプション）
Port 2222
```

```bash
# SSHサービスを再起動
rc-service sshd restart
```

### 公開鍵認証の設定

```bash
# クライアント側でSSHキーペアを生成（Ed25519推奨）
ssh-keygen -t ed25519 -C "user@kimigayo"

# または RSA（4096ビット）
ssh-keygen -t rsa -b 4096 -C "user@kimigayo"

# 公開鍵をサーバーにコピー
ssh-copy-id -i ~/.ssh/id_ed25519.pub user@server-ip

# サーバー側でパーミッションを確認
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

## アクセス制御

### ユーザー管理

```bash
# 新しいユーザーの作成
adduser newuser

# sudoグループに追加（管理者権限）
adduser newuser wheel

# ユーザーのロック（無効化）
passwd -l username

# ユーザーのアンロック
passwd -u username

# パスワードポリシーの設定
vi /etc/login.defs
```

```ini
# パスワードの最小長
PASS_MIN_LEN 12

# パスワードの有効期限
PASS_MAX_DAYS 90
PASS_MIN_DAYS 1
PASS_WARN_AGE 7
```

### sudoの設定

```bash
# sudoの設定を編集（visudoを使用）
visudo
```

推奨設定：

```ini
# デフォルト設定
Defaults env_reset
Defaults secure_path="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Defaults timestamp_timeout=5
Defaults use_pty

# ログ記録
Defaults logfile="/var/log/sudo.log"
Defaults log_input,log_output

# wheelグループにsudo権限を付与
%wheel ALL=(ALL) ALL

# パスワードなしsudoを許可（慎重に使用）
# %wheel ALL=(ALL) NOPASSWD: ALL

# 特定のコマンドのみ許可
user1 ALL=(ALL) /usr/bin/systemctl, /usr/bin/journalctl
```

### ファイルとディレクトリのパーミッション

重要なファイルのパーミッション設定：

```bash
# システムファイルの保護
chmod 644 /etc/passwd
chmod 600 /etc/shadow
chmod 644 /etc/group
chmod 600 /etc/gshadow
chmod 600 /boot/grub/grub.cfg

# ログファイルの保護
chmod 640 /var/log/messages
chmod 640 /var/log/secure

# 実行ファイルのSUID/SGIDビットを確認
find / -perm -4000 -type f -exec ls -la {} \;  # SUID
find / -perm -2000 -type f -exec ls -la {} \;  # SGID

# 不要なSUID/SGIDビットを削除
chmod u-s /path/to/file
```

## ログとモニタリング

### システムログの設定

```bash
# ログローテーションの設定
vi /etc/logrotate.conf
```

```ini
# ログを週次でローテーション
weekly

# 4週間分保持
rotate 4

# 古いログを圧縮
compress

# ローテーション後に新しいログファイルを作成
create
```

### ログの監視

```bash
# システムログのリアルタイム監視
tail -f /var/log/messages

# 認証ログの監視
tail -f /var/log/auth.log

# カーネルログの確認
dmesg | tail -50

# 特定のパターンを検索
grep "Failed password" /var/log/auth.log

# SSH接続失敗を確認
grep "Failed password" /var/log/auth.log | awk '{print $11}' | sort | uniq -c | sort -nr
```

### セキュリティイベントのモニタリング

```bash
# 失敗したログイン試行を監視
grep "Failed password" /var/log/auth.log

# sudoの使用を監視
tail -f /var/log/sudo.log

# ファイアウォールログを確認
grep "iptables denied" /var/log/messages

# 不審なプロセスを確認
ps aux | grep -v "^root" | grep -E "nc|ncat|netcat|/tmp"
```

## インシデント対応

### 侵害の兆候

以下の兆候が見られた場合は、システムが侵害されている可能性があります：

- 不審なプロセスの実行
- 予期しないネットワーク接続
- ファイルシステムの改ざん
- 異常なCPU/メモリ使用量
- 不正なユーザーアカウント

### 初動対応

```bash
# 1. ネットワークを遮断
iptables -P INPUT DROP
iptables -P OUTPUT DROP
iptables -P FORWARD DROP

# 2. 実行中のプロセスを確認
ps auxf

# 3. ネットワーク接続を確認
netstat -tulanp

# 4. 最近ログインしたユーザーを確認
last -a

# 5. システムのスナップショットを作成
tar -czf /backup/incident-$(date +%Y%m%d-%H%M%S).tar.gz \
    /var/log \
    /etc \
    /home

# 5. メモリダンプを取得（フォレンジック用）
dd if=/dev/mem of=/backup/memory-dump-$(date +%Y%m%d-%H%M%S).img
```

### フォレンジック調査

```bash
# ファイルのタイムスタンプを確認
stat /path/to/suspicious/file

# 最近変更されたファイルを検索
find /etc -mtime -1 -type f

# ハッシュ値の比較
sha256sum /bin/bash

# 隠しファイルを検索
find / -name ".*" -type f

# SUID/SGIDビットが設定されたファイルを検索
find / -perm -4000 -o -perm -2000
```

## セキュリティチェックリスト

### 初期セットアップ時

- [ ] 最新のセキュリティアップデートを適用
- [ ] ファイアウォールを設定
- [ ] SSH強化（鍵認証、rootログイン無効化）
- [ ] 不要なサービスを無効化
- [ ] カーネルパラメータの強化
- [ ] ユーザーアカウントの設定
- [ ] sudoの設定
- [ ] ログローテーションの設定

### 定期的なメンテナンス（週次）

- [ ] セキュリティアップデートの確認と適用
- [ ] ログの確認
- [ ] パッケージ監査の実施
- [ ] ディスク使用量の確認
- [ ] バックアップの確認

### 定期的なメンテナンス（月次）

- [ ] パスワードポリシーの見直し
- [ ] ユーザーアカウントの監査
- [ ] ファイアウォールルールの見直し
- [ ] 不要なパッケージの削除
- [ ] カーネルアップデートの適用

## 参考リソース

- [セキュリティポリシー](SECURITY_POLICY.md)
- [脆弱性報告手順](VULNERABILITY_REPORTING.md)
- [セキュリティ強化設定](HARDENING_GUIDE.md)
- [CIS Benchmarks](https://www.cisecurity.org/benchmark/alpine_linux)

## 緊急連絡先

セキュリティインシデント発生時：
- **緊急メール**: emergency@kimigayo-os.org
- **セキュリティチーム**: security@kimigayo-os.org
