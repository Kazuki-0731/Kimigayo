# Kimigayo OS セキュリティ強化ガイド

このガイドでは、Kimigayo OSのセキュリティを最大限に強化するための設定と手順を説明します。

## 目次

- [レベル別強化設定](#レベル別強化設定)
- [カーネル強化](#カーネル強化)
- [ネットワーク強化](#ネットワーク強化)
- [ファイルシステム強化](#ファイルシステム強化)
- [アプリケーション強化](#アプリケーション強化)
- [コンテナセキュリティ](#コンテナセキュリティ)
- [監査とコンプライアンス](#監査とコンプライアンス)

## レベル別強化設定

Kimigayo OSでは、セキュリティ要件に応じて3つの強化レベルを提供します。

### レベル1: 基本強化（すべての環境に推奨）

最小限の設定で最大の効果を得る基本的な強化設定です。

```bash
# 自動強化スクリプトを実行
/usr/share/kimigayo/security/harden-level1.sh
```

または手動で設定：

```bash
# 1. 不要なサービスの無効化
rc-update del telnet default
rc-update del ftp default

# 2. ファイアウォールの有効化
rc-update add iptables default
rc-service iptables start

# 3. SSH強化
sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
rc-service sshd restart
```

### レベル2: 中程度の強化（サーバー環境推奨）

より厳格なセキュリティ設定を適用します。

```bash
# 自動強化スクリプトを実行
/usr/share/kimigayo/security/harden-level2.sh
```

レベル1の設定に加えて：

```bash
# カーネルパラメータの強化
cat >> /etc/sysctl.conf << EOF
kernel.dmesg_restrict = 1
kernel.kptr_restrict = 2
kernel.yama.ptrace_scope = 1
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.tcp_syncookies = 1
EOF
sysctl -p

# ファイルシステムの強化
echo "tmpfs /tmp tmpfs defaults,nodev,nosuid,noexec 0 0" >> /etc/fstab
echo "tmpfs /var/tmp tmpfs defaults,nodev,nosuid,noexec 0 0" >> /etc/fstab
```

### レベル3: 最大強化（高セキュリティ環境）

最高レベルのセキュリティ設定です。パフォーマンスに影響する可能性があります。

```bash
# 自動強化スクリプトを実行
/usr/share/kimigayo/security/harden-level3.sh
```

レベル2の設定に加えて：

```bash
# 完全なカーネル強化
cat >> /etc/sysctl.conf << EOF
kernel.kexec_load_disabled = 1
kernel.unprivileged_bpf_disabled = 1
kernel.unprivileged_userns_clone = 0
fs.protected_fifos = 2
fs.protected_regular = 2
EOF
sysctl -p

```

## カーネル強化

### カーネルパラメータの最適化

```bash
# /etc/sysctl.d/99-security.conf を作成
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
kernel.unprivileged_userns_clone = 0         # 非特権user namespaceの無効化

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
net.ipv4.icmp_echo_ignore_all = 0            # ping応答（0=有効, 1=無効）
net.ipv4.icmp_echo_ignore_broadcasts = 1     # ブロードキャストping無視
net.ipv4.icmp_ignore_bogus_error_responses = 1
net.ipv4.tcp_syncookies = 1                  # SYN Flood対策
net.ipv4.tcp_timestamps = 0                  # TCPタイムスタンプ無効化
net.ipv4.conf.all.log_martians = 1           # 異常パケットのログ

# ネットワーク保護（IPv6）
net.ipv6.conf.all.accept_redirects = 0
net.ipv6.conf.default.accept_redirects = 0
net.ipv6.conf.all.accept_source_route = 0
net.ipv6.conf.default.accept_source_route = 0
net.ipv6.conf.all.accept_ra = 0              # Router Advertisement拒否
net.ipv6.conf.default.accept_ra = 0

# IPv6を使用しない場合は完全無効化
net.ipv6.conf.all.disable_ipv6 = 1
net.ipv6.conf.default.disable_ipv6 = 1
net.ipv6.conf.lo.disable_ipv6 = 1
```

```bash
# 設定を反映
sysctl -p /etc/sysctl.d/99-security.conf
```

### カーネルモジュールの制限

```bash
# /etc/modprobe.d/security.conf を作成
vi /etc/modprobe.d/security.conf
```

```ini
# 使用しないファイルシステム
install cramfs /bin/true
install freevxfs /bin/true
install jffs2 /bin/true
install hfs /bin/true
install hfsplus /bin/true
install squashfs /bin/true
install udf /bin/true

# 使用しないネットワークプロトコル
install dccp /bin/true
install sctp /bin/true
install rds /bin/true
install tipc /bin/true

# Bluetooth（使用しない場合）
install bluetooth /bin/true

# Firewire（DMA攻撃対策）
install firewire-core /bin/true

# Thunderbolt（DMA攻撃対策）
install thunderbolt /bin/true

# USB Storage（使用しない場合）
# install usb-storage /bin/true
```

### ブートローダーの保護

```bash
# GRUBパスワードの設定
grub-mkpasswd-pbkdf2
# パスワードを入力し、生成されたハッシュをコピー

# /etc/grub.d/40_custom を編集
vi /etc/grub.d/40_custom
```

```bash
cat << EOF
set superusers="admin"
password_pbkdf2 admin grub.pbkdf2.sha512.10000.[生成されたハッシュ]
EOF
```

```bash
# GRUB設定を更新
grub-mkconfig -o /boot/grub/grub.cfg

# GRUB設定ファイルのパーミッション
chmod 600 /boot/grub/grub.cfg
```

## ネットワーク強化

### ファイアウォール（iptables）詳細設定

```bash
# ファイアウォールスクリプトを作成
vi /etc/iptables/rules.v4
```

```bash
#!/sbin/iptables-restore
*filter
:INPUT DROP [0:0]
:FORWARD DROP [0:0]
:OUTPUT ACCEPT [0:0]
:LOG_DROP - [0:0]

# ループバック許可
-A INPUT -i lo -j ACCEPT
-A OUTPUT -o lo -j ACCEPT

# 確立された接続を許可
-A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# 無効なパケットをドロップ
-A INPUT -m state --state INVALID -j DROP

# SSH（ブルートフォース対策付き）
-A INPUT -p tcp --dport 22 -m state --state NEW -m recent --set --name SSH
-A INPUT -p tcp --dport 22 -m state --state NEW -m recent --update --seconds 60 --hitcount 4 --name SSH -j LOG_DROP

# SSH接続許可（カスタムポートの場合は変更）
-A INPUT -p tcp --dport 22 -j ACCEPT

# HTTP/HTTPS（Webサーバーの場合）
# -A INPUT -p tcp --dport 80 -j ACCEPT
# -A INPUT -p tcp --dport 443 -j ACCEPT

# ICMP（制限付き）
-A INPUT -p icmp --icmp-type echo-request -m limit --limit 1/s --limit-burst 2 -j ACCEPT
-A INPUT -p icmp --icmp-type echo-reply -j ACCEPT
-A INPUT -p icmp --icmp-type destination-unreachable -j ACCEPT
-A INPUT -p icmp --icmp-type time-exceeded -j ACCEPT

# ログとドロップ
-A LOG_DROP -m limit --limit 5/min -j LOG --log-prefix "iptables DROP: " --log-level 7
-A LOG_DROP -j DROP

# デフォルトでドロップ
-A INPUT -j LOG_DROP

COMMIT
```

```bash
# ファイアウォールルールをロード
iptables-restore < /etc/iptables/rules.v4

# 永続化
rc-service iptables save
```

### ポートスキャン対策

```bash
# /etc/iptables/antiscan.rules を作成
vi /etc/iptables/antiscan.rules
```

```bash
# Null scan
iptables -A INPUT -p tcp --tcp-flags ALL NONE -j DROP

# FIN scan
iptables -A INPUT -p tcp --tcp-flags FIN,ACK FIN -j DROP

# Xmas scan
iptables -A INPUT -p tcp --tcp-flags FIN,PSH,URG FIN,PSH,URG -j DROP

# SYN/FIN scan
iptables -A INPUT -p tcp --tcp-flags SYN,FIN SYN,FIN -j DROP

# SYN/RST scan
iptables -A INPUT -p tcp --tcp-flags SYN,RST SYN,RST -j DROP
```

## ファイルシステム強化

### パーティションのマウントオプション

```bash
# /etc/fstab を編集
vi /etc/fstab
```

推奨マウントオプション：

```fstab
# <device>  <mount point>  <type>  <options>  <dump>  <pass>

# ルートパーティション
/dev/sda1  /  ext4  defaults,noatime,errors=remount-ro  0  1

# /tmpの強化
tmpfs  /tmp  tmpfs  defaults,nodev,nosuid,noexec,size=1G  0  0

# /var/tmpの強化
tmpfs  /var/tmp  tmpfs  defaults,nodev,nosuid,noexec,size=512M  0  0

# /homeの強化
/dev/sda2  /home  ext4  defaults,nodev,nosuid,noatime  0  2

# /varの強化（別パーティションの場合）
/dev/sda3  /var  ext4  defaults,nodev,noatime  0  2

# /var/logの強化（別パーティションの場合）
/dev/sda4  /var/log  ext4  defaults,nodev,nosuid,noexec,noatime  0  2

# リムーバブルメディア
/dev/sdb1  /mnt/usb  vfat  noauto,nodev,nosuid,noexec,user  0  0
```

マウントオプションの説明：
- `nodev`: デバイスファイルの無効化
- `nosuid`: SUID/SGIDビットの無効化
- `noexec`: 実行ファイルの無効化
- `noatime`: アクセス時刻の更新無効化（パフォーマンス向上）

```bash
# 設定を適用（再起動後に有効）
mount -a
```

### ファイルパーミッションの監査

```bash
# SUID/SGIDビットが設定されたファイルを検索
find / -perm -4000 -type f -exec ls -la {} \; > /var/log/suid-files.log
find / -perm -2000 -type f -exec ls -la {} \; > /var/log/sgid-files.log

# World-writableファイルを検索
find / -xdev -type f -perm -0002 -exec ls -la {} \; > /var/log/world-writable-files.log

# Owner不明のファイルを検索
find / -xdev -nouser -o -nogroup > /var/log/orphan-files.log

# 不要なSUID/SGIDビットを削除
chmod u-s /path/to/file
chmod g-s /path/to/file
```

### 重要ファイルの保護

```bash
# システムファイルのパーミッション設定
chmod 644 /etc/passwd
chmod 600 /etc/shadow
chmod 644 /etc/group
chmod 600 /etc/gshadow
chmod 600 /etc/ssh/sshd_config
chmod 600 /boot/grub/grub.cfg

# ログファイルの保護
chmod 640 /var/log/messages
chmod 640 /var/log/auth.log
```

## アプリケーション強化

### Seccomp-BPFの使用

システムコールをフィルタリングして、アプリケーションのセキュリティを強化します。

```bash
# Seccompプロファイルの作成例
vi /etc/seccomp/httpd.json
```

```json
{
  "defaultAction": "SCMP_ACT_ERRNO",
  "architectures": ["SCMP_ARCH_X86_64"],
  "syscalls": [
    {
      "names": ["read", "write", "open", "close", "stat", "fstat"],
      "action": "SCMP_ACT_ALLOW"
    },
    {
      "names": ["socket", "bind", "listen", "accept"],
      "action": "SCMP_ACT_ALLOW"
    }
  ]
}
```

## コンテナセキュリティ

### Dockerの強化

```bash
# Dockerデーモンの設定
vi /etc/docker/daemon.json
```

```json
{
  "icc": false,
  "userns-remap": "default",
  "no-new-privileges": true,
  "seccomp-profile": "/etc/docker/seccomp.json",
  "live-restore": true,
  "userland-proxy": false,
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

### コンテナ実行時のセキュリティ

```bash
# セキュアなコンテナ起動例
docker run -d \
  --read-only \
  --tmpfs /tmp:noexec,nosuid,nodev \
  --security-opt=no-new-privileges \
  --cap-drop=ALL \
  --cap-add=NET_BIND_SERVICE \
  --pids-limit 100 \
  --memory 512m \
  --cpus 0.5 \
  kimigayo/app:latest
```

## 監査とコンプライアンス

### 監査ログの設定

監査機能が必要な場合は、マルチステージビルドで組み込んでください。

```bash
# 監査ルールの設定
vi /etc/audit/rules.d/audit.rules
```

```bash
# 監査システムの削除を監視
-w /var/log/audit/ -k audit-log

# 認証イベント
-w /var/log/auth.log -p wa -k auth
-w /etc/passwd -p wa -k passwd_changes
-w /etc/shadow -p wa -k shadow_changes
-w /etc/group -p wa -k group_changes

# ネットワーク設定の変更
-w /etc/network/ -p wa -k network_changes
-w /etc/ssh/sshd_config -p wa -k sshd_config

# カーネルモジュールのロード
-w /sbin/insmod -p x -k module_insertion
-w /sbin/rmmod -p x -k module_removal
-w /sbin/modprobe -p x -k module_load

# SUID/SGID実行の監視
-a always,exit -F arch=b64 -S execve -F euid=0 -F uid!=0 -k suid_execution
```

```bash
# 監査サービスの起動
rc-service auditd start
rc-update add auditd default
```

### CIS Benchmark準拠

CIS (Center for Internet Security) Benchmarkに準拠するための確認：

```bash
# CIS Benchmarkスクリプトのダウンロード
wget https://downloads.cisecurity.org/alpine-linux-benchmark.sh

# ベンチマークの実行
bash alpine-linux-benchmark.sh --level 1

# レポートの確認
cat /var/log/cis-benchmark-report.txt
```

## セキュリティ検証

### 設定の検証

```bash
# カーネルパラメータの確認
sysctl -a | grep -E "kernel\.|net\.|fs\."

# ファイアウォールルールの確認
iptables -L -n -v

# サービスの確認
rc-status

# ポートリスニングの確認
netstat -tulanp

# SUIDファイルの確認
find / -perm -4000 -type f -ls
```

### 脆弱性スキャン

```bash
# ポートスキャン（外部から）
# nmap -sS -O <your-ip>

# システムの脆弱性確認
cat /etc/os-release
```

## 参考リソース

- [CIS Benchmarks](https://www.cisecurity.org/benchmark/alpine_linux)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [セキュリティポリシー](SECURITY_POLICY.md)
- [セキュリティガイド](SECURITY_GUIDE.md)

---

**注意**: すべてのセキュリティ設定は、本番環境に適用する前にテスト環境で十分に検証してください。
