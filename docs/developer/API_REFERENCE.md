# Kimigayo OS APIリファレンス

このドキュメントでは、Kimigayo OSの主要なAPIとインターフェースについて説明します。

## 目次

- [Initシステム API](#initシステムapi)
- [カーネルAPI](#カーネルapi)
- [ビルドシステムAPI](#ビルドシステムapi)
- [CLIツール](#cliツール)

## Initシステム API


### OpenRC サービス管理

#### rc-service

サービスの制御を行います。

**構文**:
```bash
rc-service SERVICE ACTION
```

**アクション**:
- `start`: サービスを起動
- `stop`: サービスを停止
- `restart`: サービスを再起動
- `reload`: 設定を再読み込み
- `status`: サービスの状態を確認

**例**:
```bash
# サービスの起動
rc-service nginx start

# サービスの停止
rc-service nginx stop

# サービスの再起動
rc-service nginx restart

# サービスの状態確認
rc-service nginx status
```

#### rc-update

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
- `default`: デフォルト（通常運用）
- `shutdown`: シャットダウン時

**例**:
```bash
# サービスをdefaultランレベルに追加
rc-update add nginx default

# サービスを削除
rc-update del nginx default

# すべてのサービスを表示
rc-update show

# 特定のランレベルのサービスを表示
rc-update show default
```

### サービススクリプトAPI

#### 基本構造

```bash
#!/sbin/openrc-run

name="My Service"
description="My custom service"
command="/usr/bin/myapp"
command_args="--config /etc/myapp.conf"
command_user="myapp:myapp"
pidfile="/var/run/myapp.pid"

depend() {
    need net
    use dns logger
    after firewall
    before nginx
}

start_pre() {
    # 起動前の処理
    checkpath --directory --owner ${command_user} /var/log/myapp
    return 0
}

start_post() {
    # 起動後の処理
    return 0
}

stop_pre() {
    # 停止前の処理
    return 0
}

stop_post() {
    # 停止後の処理
    return 0
}

reload() {
    # 設定再読み込み
    ebegin "Reloading ${name}"
    ${command} --reload
    eend $?
}
```

#### 依存関係の定義

```bash
depend() {
    # 必須の依存関係（起動に必要）
    need net

    # 任意の依存関係（あれば使用）
    use dns logger

    # この後に起動
    after firewall postgresql

    # この前に起動
    before nginx

    # 他のサービスを提供
    provide httpd
}
```

## カーネルAPI

### sysctl パラメータ

#### ネットワーク設定

```bash
# IPv4フォワーディング
sysctl -w net.ipv4.ip_forward=1

# TCP SYN Cookies
sysctl -w net.ipv4.tcp_syncookies=1

# ソースルーティング拒否
sysctl -w net.ipv4.conf.all.accept_source_route=0
```

#### セキュリティ設定

```bash
# カーネルポインタ保護
sysctl -w kernel.kptr_restrict=2

# dmesg制限
sysctl -w kernel.dmesg_restrict=1

# ptrace制限
sysctl -w kernel.yama.ptrace_scope=1
```

### カーネルモジュール管理

```bash
# モジュールのロード
modprobe module_name

# モジュールのアンロード
modprobe -r module_name

# ロード済みモジュールの確認
lsmod

# モジュール情報の表示
modinfo module_name
```

## ビルドシステムAPI

### Makefile ターゲット

#### 情報表示

```bash
# ビルド情報の表示
make info

# ヘルプの表示
make help

# バージョン情報
make version
```

#### ビルド

```bash
# 完全ビルド
make build

# Minimalイメージ
make build-minimal

# Standardイメージ
make build-standard

# Extendedイメージ
make build-extended

# クリーンビルド
make clean build
```

#### テスト

```bash
# すべてのテスト
make test

# 単体テスト
make test-unit

# プロパティテスト
make test-property

# 統合テスト
make test-integration

# カバレッジレポート
make coverage
```

#### 静的解析

```bash
# リント
make lint

# 静的解析
make static-analysis

# セキュリティスキャン
make security-scan
```

### ビルド設定変数

```bash
# アーキテクチャの指定
make build ARCH=x86_64
make build ARCH=arm64

# ビルドタイプ
make build BUILD_TYPE=debug
make build BUILD_TYPE=release

# 並列ビルド
make build JOBS=4

# パッケージリスト
make build PACKAGE_LIST=custom.list

# カーネル設定
make build KERNEL_CONFIG=custom.config
```

## CLIツール

### システム管理

#### システム情報

```bash
# OSバージョン
cat /etc/os-release

# カーネルバージョン
uname -a

# CPU情報
cat /proc/cpuinfo

# メモリ情報
free -m

# ディスク使用量
df -h
```

#### プロセス管理

```bash
# プロセス一覧
ps aux

# プロセスツリー
ps auxf

# リアルタイム監視
top

# プロセスの終了
kill PID
kill -9 PID  # 強制終了
```

### ネットワーク

```bash
# ネットワークインターフェース
ip addr show
ip link show

# ルーティングテーブル
ip route show

# ポート確認
netstat -tulanp
ss -tulanp

# 疎通確認
ping google.com

# DNS確認
nslookup google.com
dig google.com
```

## エラーコード

### rc-service コマンド

| コード | 説明 |
|-------|------|
| 0 | 成功 |
| 1 | サービスが起動していない |
| 2 | サービスが見つからない |
| 3 | 権限エラー |
| 4 | タイムアウト |

## システム管理

Kimigayo OSはdistroless的アプローチを採用しており、パッケージマネージャーを含みません。
必要なソフトウェアは、マルチステージビルドを使用してイメージに組み込んでください。

### マルチステージビルドの例

```dockerfile
# ビルドステージでソフトウェアを準備
FROM alpine:3.19 AS builder
RUN apk add --no-cache nginx openssl

# Kimigayo OSで最小ランタイムを構築
FROM kimigayo-os:latest
COPY --from=builder /usr/sbin/nginx /usr/sbin/nginx
COPY --from=builder /usr/lib/nginx /usr/lib/nginx
COPY --from=builder /etc/nginx /etc/nginx

CMD ["/usr/sbin/nginx", "-g", "daemon off;"]
```

## 参考リソース

- [BUILD_GUIDE.md](BUILD_GUIDE.md) - ビルド詳細
- [ARCHITECTURE.md](ARCHITECTURE.md) - アーキテクチャ
- [CONTRIBUTING.md](../../CONTRIBUTING.md) - コントリビューションガイド
- [DEVELOPMENT.md](../../DEVELOPMENT.md) - 開発ガイド

---

**APIの詳細なドキュメントは、各コンポーネントのソースコードも参照してください。**
