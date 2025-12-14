# Kimigayo OS APIリファレンス

このドキュメントでは、Kimigayo OSの主要なAPIとインターフェースについて説明します。

## 目次

- [パッケージマネージャAPI](#パッケージマネージャapi)
- [Initシステ API](#initシステムapi)
- [カーネルAPI](#カーネルapi)
- [ビルドシステムAPI](#ビルドシステムapi)
- [CLIツール](#cliツール)

## パッケージマネージャAPI

### isn CLI

#### 基本コマンド

##### isn install

パッケージをインストールします。

**構文**:
```bash
isn install [OPTIONS] PACKAGE...
```

**オプション**:
- `-y, --yes`: 確認なしでインストール
- `--no-verify`: 署名検証をスキップ（非推奨）
- `--simulate`: シミュレーションのみ（実際にはインストールしない）
- `-v, --verbose`: 詳細ログを表示

**例**:
```bash
# 単一パッケージのインストール
isn install vim

# 複数パッケージのインストール
isn install vim git curl

# 確認なしでインストール
isn install -y nginx

# シミュレーション
isn install --simulate python3
```

**戻り値**:
- `0`: 成功
- `1`: 一般的なエラー
- `2`: パッケージが見つからない
- `3`: 依存関係エラー
- `4`: 署名検証失敗

##### isn remove

パッケージを削除します。

**構文**:
```bash
isn remove [OPTIONS] PACKAGE...
```

**オプション**:
- `-y, --yes`: 確認なしで削除
- `--purge`: 設定ファイルも削除
- `--recursive`: 依存パッケージも削除

**例**:
```bash
# パッケージの削除
isn remove vim

# 設定ファイルも削除
isn remove --purge nginx

# 依存パッケージも削除
isn remove --recursive mysql
```

##### isn update

パッケージリポジトリのインデックスを更新します。

**構文**:
```bash
isn update [OPTIONS]
```

**オプション**:
- `--force`: 強制的に更新
- `--repository REPO`: 特定のリポジトリのみ更新

**例**:
```bash
# リポジトリの更新
isn update

# 強制更新
isn update --force
```

##### isn upgrade

インストール済みパッケージをアップグレードします。

**構文**:
```bash
isn upgrade [OPTIONS] [PACKAGE...]
```

**オプション**:
- `-y, --yes`: 確認なしでアップグレード
- `--security-only`: セキュリティアップデートのみ
- `--check`: アップデート可能なパッケージを表示のみ

**例**:
```bash
# すべてのパッケージをアップグレード
isn upgrade

# セキュリティアップデートのみ
isn upgrade --security-only

# 特定のパッケージをアップグレード
isn upgrade vim git
```

##### isn search

パッケージを検索します。

**構文**:
```bash
isn search [OPTIONS] PATTERN
```

**オプション**:
- `--description`: 説明文も検索対象に含める
- `--exact`: 完全一致のみ

**例**:
```bash
# パッケージ名で検索
isn search vim

# 説明文も含めて検索
isn search --description editor
```

##### isn info

パッケージ情報を表示します。

**構文**:
```bash
isn info [OPTIONS] PACKAGE
```

**オプション**:
- `-v, --verbose`: 詳細情報を表示
- `--depends`: 依存関係を表示
- `--files`: パッケージに含まれるファイルを表示

**例**:
```bash
# パッケージ情報の表示
isn info vim

# 依存関係の表示
isn info --depends nginx

# ファイルリストの表示
isn info --files busybox
```

### Python API

#### PackageManager クラス

```python
from kimigayo.pkg import PackageManager

class PackageManager:
    """パッケージマネージャのメインクラス"""

    def __init__(self, config_path: str = "/etc/isn/isn.conf"):
        """
        パッケージマネージャの初期化

        Args:
            config_path: 設定ファイルのパス

        Raises:
            ConfigError: 設定ファイルの読み込みエラー
        """
        pass

    def install(self, package_name: str, verify: bool = True) -> bool:
        """
        パッケージをインストール

        Args:
            package_name: インストールするパッケージ名
            verify: 署名検証を実行するか（デフォルト: True）

        Returns:
            bool: インストール成功時True

        Raises:
            PackageNotFoundError: パッケージが見つからない
            DependencyError: 依存関係エラー
            SecurityError: 署名検証失敗

        Example:
            >>> pm = PackageManager()
            >>> pm.install("vim")
            True
        """
        pass

    def remove(self, package_name: str, purge: bool = False) -> bool:
        """
        パッケージを削除

        Args:
            package_name: 削除するパッケージ名
            purge: 設定ファイルも削除するか

        Returns:
            bool: 削除成功時True

        Raises:
            PackageNotFoundError: パッケージがインストールされていない

        Example:
            >>> pm = PackageManager()
            >>> pm.remove("vim", purge=True)
            True
        """
        pass

    def upgrade(self, package_name: str = None, security_only: bool = False) -> List[str]:
        """
        パッケージをアップグレード

        Args:
            package_name: 特定のパッケージ名（Noneで全パッケージ）
            security_only: セキュリティアップデートのみ

        Returns:
            List[str]: アップグレードされたパッケージのリスト

        Example:
            >>> pm = PackageManager()
            >>> upgraded = pm.upgrade(security_only=True)
            >>> print(upgraded)
            ['openssl', 'openssh']
        """
        pass

    def search(self, pattern: str, description: bool = False) -> List[Package]:
        """
        パッケージを検索

        Args:
            pattern: 検索パターン
            description: 説明文も検索するか

        Returns:
            List[Package]: 検索結果のパッケージリスト

        Example:
            >>> pm = PackageManager()
            >>> results = pm.search("vim")
            >>> for pkg in results:
            ...     print(f"{pkg.name}: {pkg.description}")
        """
        pass

    def list_installed(self) -> List[Package]:
        """
        インストール済みパッケージの一覧を取得

        Returns:
            List[Package]: インストール済みパッケージのリスト

        Example:
            >>> pm = PackageManager()
            >>> for pkg in pm.list_installed():
            ...     print(f"{pkg.name} {pkg.version}")
        """
        pass
```

#### Package クラス

```python
from dataclasses import dataclass
from typing import List

@dataclass
class Package:
    """パッケージ情報"""

    name: str
    version: str
    architecture: str
    description: str
    url: str
    license: str
    depends: List[str]
    size: int
    sha256: str
    signature: str

    def __str__(self) -> str:
        return f"{self.name}-{self.version} ({self.architecture})"

    def to_dict(self) -> dict:
        """辞書形式で返す"""
        return {
            'name': self.name,
            'version': self.version,
            'architecture': self.architecture,
            'description': self.description,
            'url': self.url,
            'license': self.license,
            'depends': self.depends,
            'size': self.size,
            'sha256': self.sha256,
        }
```

#### DependencyResolver クラス

```python
class DependencyResolver:
    """依存関係解決エンジン"""

    def resolve(self, package_name: str) -> List[str]:
        """
        依存関係を解決し、インストール順序を返す

        Args:
            package_name: パッケージ名

        Returns:
            List[str]: インストール順序のパッケージリスト

        Raises:
            DependencyError: 依存関係が解決できない
            CyclicDependencyError: 循環依存

        Example:
            >>> resolver = DependencyResolver()
            >>> order = resolver.resolve("nginx")
            >>> print(order)
            ['musl', 'openssl', 'pcre', 'nginx']
        """
        pass

    def check_conflicts(self, package_name: str) -> List[str]:
        """
        競合するパッケージを確認

        Args:
            package_name: パッケージ名

        Returns:
            List[str]: 競合するパッケージのリスト

        Example:
            >>> resolver = DependencyResolver()
            >>> conflicts = resolver.check_conflicts("apache")
            >>> print(conflicts)
            ['nginx']
        """
        pass
```

#### SignatureVerifier クラス

```python
class SignatureVerifier:
    """署名検証クラス"""

    def __init__(self, public_key_path: str):
        """
        署名検証器の初期化

        Args:
            public_key_path: 公開鍵ファイルのパス
        """
        pass

    def verify_ed25519(self, file_path: str, signature: str) -> bool:
        """
        Ed25519署名を検証

        Args:
            file_path: 検証対象ファイル
            signature: Ed25519署名（hex文字列）

        Returns:
            bool: 検証成功時True

        Raises:
            SecurityError: 署名検証失敗

        Example:
            >>> verifier = SignatureVerifier("/etc/isn/public.key")
            >>> is_valid = verifier.verify_ed25519("/tmp/package.tar.gz", signature)
            >>> print(is_valid)
            True
        """
        pass

    def verify_gpg(self, file_path: str) -> bool:
        """
        GPG署名を検証（レガシーサポート）

        Args:
            file_path: 検証対象ファイル

        Returns:
            bool: 検証成功時True

        Example:
            >>> verifier = SignatureVerifier("/etc/isn/public.key")
            >>> is_valid = verifier.verify_gpg("/tmp/package.tar.gz")
            >>> print(is_valid)
            True
        """
        pass
```

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

### isn コマンド

| コード | 説明 |
|-------|------|
| 0 | 成功 |
| 1 | 一般的なエラー |
| 2 | パッケージが見つからない |
| 3 | 依存関係エラー |
| 4 | 署名検証失敗 |
| 5 | ネットワークエラー |
| 6 | ディスク容量不足 |
| 7 | 権限エラー |

### rc-service コマンド

| コード | 説明 |
|-------|------|
| 0 | 成功 |
| 1 | サービスが起動していない |
| 2 | サービスが見つからない |
| 3 | 権限エラー |
| 4 | タイムアウト |

## 参考リソース

- [BUILD_GUIDE.md](BUILD_GUIDE.md) - ビルド詳細
- [ARCHITECTURE.md](ARCHITECTURE.md) - アーキテクチャ
- [CONTRIBUTING.md](../../CONTRIBUTING.md) - コントリビューションガイド
- [DEVELOPMENT.md](../../DEVELOPMENT.md) - 開発ガイド

---

**APIの詳細なドキュメントは、各コンポーネントのソースコードも参照してください。**
