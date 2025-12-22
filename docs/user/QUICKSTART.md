# Kimigayo OS クイックスタートガイド

このガイドでは、Kimigayo OSを使い始めるための基本的な操作を説明します。

## 目次

- [初めてのログイン](#初めてのログイン)
- [基本コマンド](#基本コマンド)
- [パッケージの管理](#パッケージの管理)
- [システムの設定](#システムの設定)
- [よく使う操作](#よく使う操作)

## 初めてのログイン

### Dockerコンテナの場合

```bash
# コンテナを起動
docker run -it kimigayo/kimigayo-os:standard

# シェルプロンプトが表示されます
/ #
```

### 実機またはVMの場合

1. ブート後、ログインプロンプトが表示されます
2. デフォルトユーザー名とパスワードでログイン（初回セットアップ時に設定）

```
kimigayo login: root
Password:

Welcome to Kimigayo OS!
~ #
```

## 基本コマンド

Kimigayo OSはBusyBoxベースのため、標準的なUnixコマンドが使用できます。

### ファイル操作

```bash
# ディレクトリの内容を表示
ls -la

# ディレクトリの移動
cd /etc

# ファイルの表示
cat /etc/os-release

# ファイルの編集
vi /etc/config.conf

# ファイルのコピー
cp source.txt destination.txt

# ファイルの移動
mv oldname.txt newname.txt

# ファイルの削除
rm file.txt
```

### システム情報

```bash
# OSバージョンの確認
cat /etc/os-release

# カーネルバージョンの確認
uname -a

# CPU情報
cat /proc/cpuinfo

# メモリ情報
free -m

# ディスク使用状況
df -h

# 起動時間
uptime
```

### プロセス管理

```bash
# 実行中のプロセスを表示
ps aux

# プロセスのリアルタイム監視
top

# プロセスの終了
kill <PID>

# プロセスの強制終了
kill -9 <PID>
```

### ネットワーク

```bash
# ネットワークインターフェースの確認
ip addr show

# 疎通確認
ping google.com

# ポートのリスニング確認
netstat -tuln

# HTTPリクエスト
wget https://example.com
curl https://example.com
```

## ソフトウェアの追加

Kimigayo OSはdistroless的アプローチを採用しており、パッケージマネージャーを含みません。
必要なソフトウェアは、マルチステージビルドを使用してイメージに組み込んでください。

### マルチステージビルドの例

```dockerfile
# ビルドステージで必要なソフトウェアを準備
FROM alpine:3.19 AS builder
RUN apk add --no-cache vim curl wget

# Kimigayo OSで最小ランタイムを構築
FROM kimigayo-os:latest
COPY --from=builder /usr/bin/vim /usr/bin/vim
COPY --from=builder /usr/bin/curl /usr/bin/curl
COPY --from=builder /usr/bin/wget /usr/bin/wget

CMD ["/bin/sh"]
```

## システムの設定

### ホスト名の変更

```bash
# ホスト名の設定
echo "my-kimigayo" > /etc/hostname

# 即座に反映
hostname my-kimigayo
```

### ネットワークの設定

```bash
# DHCPを使用する場合
vi /etc/network/interfaces
```

以下の内容を追加：

```
auto eth0
iface eth0 inet dhcp
```

静的IPの場合：

```
auto eth0
iface eth0 inet static
    address 192.168.1.100
    netmask 255.255.255.0
    gateway 192.168.1.1
```

```bash
# ネットワークサービスの再起動
rc-service networking restart
```

### タイムゾーンの設定

```bash
# 利用可能なタイムゾーンの確認
ls /usr/share/zoneinfo/

# タイムゾーンの設定（日本の場合）
ln -sf /usr/share/zoneinfo/Asia/Tokyo /etc/localtime
```

### サービスの管理

Kimigayo OSはOpenRCを使用します。

```bash
# サービスの起動
rc-service <service-name> start

# サービスの停止
rc-service <service-name> stop

# サービスの再起動
rc-service <service-name> restart

# サービスの状態確認
rc-service <service-name> status

# 起動時にサービスを自動起動
rc-update add <service-name> default

# 自動起動の解除
rc-update del <service-name> default

# 登録されているサービスの確認
rc-update show
```

## よく使う操作

### システムのシャットダウンと再起動

```bash
# シャットダウン
poweroff

# 再起動
reboot

# 1分後にシャットダウン
shutdown -h +1
```

### ログの確認

```bash
# システムログの表示
dmesg

# 最近のログを表示
dmesg | tail -50

# ログファイルの確認
tail -f /var/log/messages
```

### ディスク管理

```bash
# パーティションの確認
fdisk -l

# ファイルシステムのマウント
mount /dev/sda1 /mnt

# アンマウント
umount /mnt

# ディスク使用量の確認
du -sh /var/log
```

### ユーザー管理

```bash
# 新しいユーザーの作成
adduser username

# パスワードの変更
passwd username

# ユーザーの削除
deluser username

# グループの確認
groups username
```

### アーカイブとアップロード

```bash
# tarアーカイブの作成
tar -czf archive.tar.gz /path/to/directory

# tarアーカイブの展開
tar -xzf archive.tar.gz

# ファイルの圧縮
gzip file.txt

# ファイルの解凍
gunzip file.txt.gz
```

## パフォーマンス目標

Kimigayo OSは以下のパフォーマンス目標を達成しています：

- **起動時間**: 10秒以下
- **メモリ使用量**: 128MB未満
- **イメージサイズ**:
  - Minimal: 5MB以下
  - Standard: 15MB以下
  - Extended: 50MB以下

## セキュリティのベストプラクティス

```bash
# rootでの直接ログインを無効化
vi /etc/ssh/sshd_config
# PermitRootLogin no を設定

# ファイアウォールの設定
iptables -A INPUT -p tcp --dport 22 -j ACCEPT
iptables -A INPUT -j DROP
```

## トラブルシューティング

### コマンドが見つからない

必要なコマンドは、マルチステージビルドでイメージに組み込んでください。

### ディスク容量不足

```bash
# ディスク使用量の確認
df -h

# 大きなファイルの検索
find / -type f -size +10M -exec ls -lh {} \;
```

### ネットワーク接続の問題

```bash
# ネットワークインターフェースの確認
ip link show

# DHCPで再度IPを取得
dhclient eth0

# DNSの確認
cat /etc/resolv.conf
```

## 次のステップ

基本的な操作に慣れたら、以下のドキュメントも参照してください：

- [システム設定ガイド](CONFIGURATION.md)
- [セキュリティガイド](../security/SECURITY_GUIDE.md)

## ヘルプとサポート

- **公式ドキュメント**: https://docs.kimigayo-os.org
- **コミュニティフォーラム**: https://forum.kimigayo-os.org
- **Issue報告**: https://github.com/kimigayo/kimigayo-os/issues
