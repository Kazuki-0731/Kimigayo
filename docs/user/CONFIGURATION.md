# Kimigayo OS システム設定ガイド

このガイドでは、Kimigayo OSの各種設定方法について説明します。

## 目次

- [基本設定](#基本設定)
- [ネットワーク設定](#ネットワーク設定)
- [サービス管理](#サービス管理)
- [セキュリティ設定](#セキュリティ設定)
- [システム最適化](#システム最適化)
- [カーネル設定](#カーネル設定)

## 基本設定

### ホスト名の設定

```bash
# ホスト名の確認
hostname

# ホスト名の変更
echo "my-server" > /etc/hostname

# 即座に反映
hostname my-server

# /etc/hostsファイルの更新
vi /etc/hosts
```

`/etc/hosts`に以下を追加：
```
127.0.0.1   localhost
127.0.1.1   my-server
```

### タイムゾーンの設定

```bash
# 現在のタイムゾーンの確認
date +%Z

# 利用可能なタイムゾーンの確認
ls /usr/share/zoneinfo/

# タイムゾーンの設定（日本の場合）
ln -sf /usr/share/zoneinfo/Asia/Tokyo /etc/localtime

# 時刻の確認
date
```

### ロケールの設定

```bash
# ロケールの設定
vi /etc/locale.conf
```

以下を追加：
```
LANG=ja_JP.UTF-8
LC_ALL=ja_JP.UTF-8
```

```bash
# ロケールの反映
export LANG=ja_JP.UTF-8
export LC_ALL=ja_JP.UTF-8
```

### キーボード配列の設定

```bash
# キーボード配列の設定
vi /etc/conf.d/keymaps
```

以下を設定：
```
keymap="jp106"
```

## ネットワーク設定

### 静的IPアドレスの設定

```bash
# ネットワーク設定ファイルの編集
vi /etc/network/interfaces
```

以下の内容を追加：
```
auto eth0
iface eth0 inet static
    address 192.168.1.100
    netmask 255.255.255.0
    gateway 192.168.1.1
    dns-nameservers 8.8.8.8 8.8.4.4
```

```bash
# ネットワークサービスの再起動
rc-service networking restart

# IPアドレスの確認
ip addr show eth0
```

### DHCP設定

```bash
# DHCPクライアントの設定
vi /etc/network/interfaces
```

以下の内容を追加：
```
auto eth0
iface eth0 inet dhcp
```

```bash
# ネットワークサービスの再起動
rc-service networking restart
```

### DNS設定

```bash
# DNS設定ファイルの編集
vi /etc/resolv.conf
```

以下を追加：
```
nameserver 8.8.8.8
nameserver 8.8.4.4
nameserver 1.1.1.1
```

### 無線LAN設定

```bash
# 無線LANツールのインストール
isn install wireless-tools wpa_supplicant

# 無線インターフェースの確認
iwconfig

# WPA設定ファイルの作成
wpa_passphrase "SSID" "password" > /etc/wpa_supplicant/wpa_supplicant.conf

# ネットワーク設定
vi /etc/network/interfaces
```

以下を追加：
```
auto wlan0
iface wlan0 inet dhcp
    pre-up wpa_supplicant -B -i wlan0 -c /etc/wpa_supplicant/wpa_supplicant.conf
    post-down killall -q wpa_supplicant
```

## サービス管理

Kimigayo OSはOpenRCを使用してサービスを管理します。

### サービスの基本操作

```bash
# サービスの起動
rc-service <service-name> start

# サービスの停止
rc-service <service-name> stop

# サービスの再起動
rc-service <service-name> restart

# サービスの状態確認
rc-service <service-name> status

# すべてのサービスの状態確認
rc-status
```

### サービスの自動起動設定

```bash
# サービスを自動起動に追加
rc-update add <service-name> default

# サービスを自動起動から削除
rc-update del <service-name> default

# 起動時に実行されるサービスの確認
rc-update show default

# すべてのランレベルのサービスを表示
rc-update show
```

### ランレベルの管理

Kimigayo OSの主なランレベル：
- **sysinit**: システム初期化
- **boot**: ブート時
- **default**: デフォルトランレベル
- **shutdown**: シャットダウン時

```bash
# 現在のランレベルの確認
rc-status --runlevel

# 特定のランレベルのサービス確認
rc-update show boot
```

### カスタムサービスの作成

```bash
# サービススクリプトの作成
vi /etc/init.d/myservice
```

以下の内容を追加：
```bash
#!/sbin/openrc-run

name="My Service"
command="/usr/bin/myapp"
pidfile="/var/run/myservice.pid"

depend() {
    need net
    after firewall
}
```

```bash
# 実行権限を付与
chmod +x /etc/init.d/myservice

# サービスを有効化
rc-update add myservice default

# サービスを起動
rc-service myservice start
```

## セキュリティ設定

### ファイアウォールの設定

```bash
# iptablesのインストール
isn install iptables

# 基本的なファイアウォールルール
# すべてをブロック
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT

# ループバックを許可
iptables -A INPUT -i lo -j ACCEPT

# 確立された接続を許可
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# SSHを許可
iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# HTTPとHTTPSを許可
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# ルールの保存
rc-service iptables save

# iptablesを自動起動に追加
rc-update add iptables default
```

### SSH設定

```bash
# SSHサーバーのインストール
isn install openssh

# SSH設定ファイルの編集
vi /etc/ssh/sshd_config
```

推奨設定：
```
# rootログインを無効化
PermitRootLogin no

# パスワード認証を無効化（公開鍵認証のみ）
PasswordAuthentication no

# 公開鍵認証を有効化
PubkeyAuthentication yes

# ポート番号の変更（オプション）
Port 2222
```

```bash
# SSHサービスの再起動
rc-service sshd restart

# SSHを自動起動に追加
rc-update add sshd default
```

### ユーザーとパーミッション

```bash
# 新しいユーザーの作成
adduser username

# sudoグループに追加
adduser username wheel

# sudoの設定
vi /etc/sudoers
```

以下の行のコメントを解除：
```
%wheel ALL=(ALL) ALL
```

### セキュリティアップデートの自動適用

```bash
# セキュリティアップデートの自動適用を有効化
isn config set auto-security-updates true

# cronジョブで定期的にチェック
crontab -e
```

以下を追加：
```
0 2 * * * isn update && isn upgrade --security-only -y
```

## システム最適化

### メモリ最適化

Kimigayo OSは128MB未満でのメモリ使用を目標としています。

```bash
# メモリ使用量の確認
free -m

# プロセスのメモリ使用量を確認
ps aux --sort=-%mem | head -10

# 不要なサービスを無効化
rc-update del <service-name> default

# スワップの設定（必要に応じて）
dd if=/dev/zero of=/swapfile bs=1M count=512
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile

# 起動時にスワップを有効化
echo "/swapfile none swap sw 0 0" >> /etc/fstab
```

### ディスク最適化

```bash
# ディスク使用量の確認
df -h

# 大きなファイルの検索
find / -type f -size +10M -exec ls -lh {} \;

# ログローテーションの設定
vi /etc/logrotate.conf

# パッケージキャッシュのクリア
isn cache clean --all

# tmpfsを使用して一時ファイルをRAMに保存
echo "tmpfs /tmp tmpfs defaults,noatime,mode=1777 0 0" >> /etc/fstab
```

### 起動時間の最適化

Kimigayo OSは10秒以下の起動時間を目標としています。

```bash
# 起動時間の確認
dmesg | grep "Freeing unused kernel"

# 不要なサービスを無効化
rc-update show default

# サービスを削除
rc-update del <unnecessary-service> default

# カーネルパラメータの最適化
vi /etc/default/grub
```

以下を追加：
```
GRUB_CMDLINE_LINUX="quiet splash"
```

## カーネル設定

### カーネルパラメータの変更

```bash
# 現在のカーネルパラメータの確認
cat /proc/cmdline

# ブートローダー設定の編集
vi /boot/grub/grub.cfg

# または
vi /etc/default/grub

# 設定を反映
grub-mkconfig -o /boot/grub/grub.cfg
```

### カーネルモジュールの管理

```bash
# ロード済みモジュールの確認
lsmod

# モジュールのロード
modprobe <module-name>

# モジュールのアンロード
modprobe -r <module-name>

# 起動時に自動ロードするモジュールの設定
vi /etc/modules-load.d/modules.conf
```

### sysctl設定

```bash
# 現在のsysctl設定の確認
sysctl -a

# 設定の変更（一時的）
sysctl -w net.ipv4.ip_forward=1

# 永続的な設定
vi /etc/sysctl.conf
```

推奨設定：
```
# IPv4フォワーディング
net.ipv4.ip_forward = 1

# TCP設定の最適化
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_keepalive_time = 1800

# セキュリティ設定
kernel.dmesg_restrict = 1
kernel.kptr_restrict = 2
```

```bash
# 設定の反映
sysctl -p
```

## システムモニタリング

### ログの確認

```bash
# システムログの確認
tail -f /var/log/messages

# カーネルログの確認
dmesg | tail -50

# 特定のサービスのログ
tail -f /var/log/<service-name>.log
```

### リソース監視

```bash
# システムリソースのリアルタイム監視
top

# または
htop  # 要インストール: isn install htop

# ディスクI/Oの監視
iostat  # 要インストール: isn install sysstat

# ネットワーク監視
iftop  # 要インストール: isn install iftop
```

## バックアップと復元

### システムのバックアップ

```bash
# 重要な設定ファイルのバックアップ
tar -czf config-backup.tar.gz /etc

# 完全なシステムバックアップ
tar -czf system-backup.tar.gz \
    --exclude=/proc \
    --exclude=/sys \
    --exclude=/dev \
    --exclude=/tmp \
    /
```

### 復元

```bash
# 設定ファイルの復元
tar -xzf config-backup.tar.gz -C /

# サービスの再起動
rc-service <service-name> restart
```

## トラブルシューティング

### 起動しない場合

1. ブートローダー（GRUB）のリカバリモードで起動
2. ルートファイルシステムを読み書きモードでマウント
3. 設定ファイルを確認・修正

```bash
# 読み書きモードで再マウント
mount -o remount,rw /
```

### ネットワークが接続できない場合

```bash
# ネットワークインターフェースの確認
ip link show

# インターフェースを有効化
ip link set eth0 up

# DHCPで再度取得
dhclient eth0
```

## 参考リソース

- **公式ドキュメント**: https://docs.kimigayo-os.org
- **OpenRCドキュメント**: https://wiki.gentoo.org/wiki/OpenRC
- **コミュニティフォーラム**: https://forum.kimigayo-os.org
