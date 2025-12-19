# Kimigayo OS アーキテクチャドキュメント

このドキュメントでは、Kimigayo OSの内部アーキテクチャと設計思想について説明します。

## 目次

- [全体アーキテクチャ](#全体アーキテクチャ)
- [レイヤー構造](#レイヤー構造)
- [コアコンポーネント](#コアコンポーネント)
- [パッケージ管理システム](#パッケージ管理システム)
- [セキュリティアーキテクチャ](#セキュリティアーキテクチャ)
- [ブートプロセス](#ブートプロセス)
- [設計原則](#設計原則)

## 全体アーキテクチャ

Kimigayo OSは、Alpine Linuxの設計思想を受け継ぎつつ、軽量性、セキュリティ、再現可能性を重視したアーキテクチャを採用しています。

```
┌─────────────────────────────────────────────────────────┐
│                  ユーザー空間                            │
├─────────────────────────────────────────────────────────┤
│         アプリケーション層                               │
│  - Webサーバー (nginx, apache)                          │
│  - データベース (PostgreSQL, MySQL)                     │
│  - コンテナランタイム (Docker, Podman)                  │
├─────────────────────────────────────────────────────────┤
│         パッケージ管理層 (isn)                          │
│  - Ed25519署名検証                                      │
│  - 依存関係解決                                         │
│  - アトミックインストール                               │
├─────────────────────────────────────────────────────────┤
│         システムユーティリティ層                         │
│  - BusyBox (coreutils, findutils, etc.)                │
│  - ネットワークツール (ip, ifconfig, curl)              │
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
│         Linuxカーネル (セキュリティ強化版)               │
│  - ASLR, DEP, PIE                                       │
│  - Namespace isolation                                  │
│  - Seccomp-BPF                                          │
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

**セキュリティ機能**:
```c
// カーネルパラメータ例
kernel.randomize_va_space = 2        // ASLR完全有効化
kernel.kptr_restrict = 2             // カーネルポインタ保護
kernel.dmesg_restrict = 1            // dmesgアクセス制限
kernel.yama.ptrace_scope = 1         // ptrace制限
```

**ファイルシステム**:
- **ext4**: ルートファイルシステム
- **overlay**: コンテナ用レイヤードファイルシステム
- **tmpfs**: 一時ファイル用メモリファイルシステム
- **squashfs**: 読み取り専用圧縮ファイルシステム

### 3. Cライブラリ層 (musl libc)

**目的**: POSIXシステムコールのラッパー提供

**musl libcの特徴**:
- **軽量**: glibcの約1/4のサイズ
- **高速**: 最適化されたメモリ割り当て
- **セキュア**: バッファオーバーフロー対策
- **静的リンク対応**: 独立した実行ファイル生成

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

**依存関係グラフ**:
```
networking
    ├── firewall
    │       └── sshd
    ├── ntpd
    └── nginx
            └── php-fpm
```

### 5. システムユーティリティ層 (BusyBox)

**目的**: 基本的なUnixコマンドの提供

**BusyBoxの特徴**:
- **単一バイナリ**: 数百のコマンドが1つの実行ファイル
- **省メモリ**: 共有コード、最小限の実装
- **組み込み最適**: リソース制約環境に最適

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

### 6. パッケージ管理層 (isn)

**目的**: パッケージのインストール、更新、削除

**アーキテクチャ**:
```
┌──────────────────────────────────────────┐
│          isn CLI (Python)                │
└──────────────┬───────────────────────────┘
               │
    ┌──────────┼──────────────┐
    │          │              │
┌───▼────┐ ┌──▼───────┐ ┌───▼──────┐
│ Resolve│ │ Download │ │ Install  │
│ Deps   │ │ Package  │ │ Package  │
└───┬────┘ └──┬───────┘ └───┬──────┘
    │          │             │
    └──────────┼─────────────┘
               │
    ┌──────────▼──────────┐
    │  Signature Verify   │
    │   (Ed25519/GPG)     │
    └─────────────────────┘
```

**主要機能**:
1. **依存関係解決**
2. **パッケージダウンロード**
3. **署名検証（Ed25519/GPG）**
4. **アトミックインストール**
5. **トランザクション管理**

詳細は [パッケージ管理システム](#パッケージ管理システム) を参照。

### 7. アプリケーション層

**目的**: ユーザーアプリケーションの実行環境

**サポートされるアプリケーション**:
- Webサーバー: nginx, Apache
- データベース: PostgreSQL, MySQL, SQLite
- 言語ランタイム: Python, Node.js, Ruby, Go
- コンテナ: Docker, Podman
- その他: 任意のLinuxアプリケーション

## コアコンポーネント

### カーネル設定

最小限かつセキュアなカーネル設定：

```ini
# セキュリティ機能
CONFIG_SECURITY=y
CONFIG_SECURITY_DMESG_RESTRICT=y
CONFIG_SECURITY_YAMA=y

# ASLR/DEP
CONFIG_RANDOMIZE_BASE=y
CONFIG_RANDOMIZE_MEMORY=y

# Namespace isolation
CONFIG_NAMESPACES=y
CONFIG_UTS_NS=y
CONFIG_IPC_NS=y
CONFIG_PID_NS=y
CONFIG_NET_NS=y
CONFIG_USER_NS=y

# Seccomp
CONFIG_SECCOMP=y
CONFIG_SECCOMP_FILTER=y

# ファイルシステム
CONFIG_EXT4_FS=y
CONFIG_OVERLAY_FS=y
CONFIG_TMPFS=y
CONFIG_SQUASHFS=y

# ネットワーク
CONFIG_NETFILTER=y
CONFIG_NETFILTER_XTABLES=y
CONFIG_IP_NF_IPTABLES=y
```

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

# デバッグツール（Extended）
CONFIG_STRACE=y
CONFIG_LSOF=y
CONFIG_TCPDUMP=y
```

## パッケージ管理システム

### アーキテクチャ詳細

```python
# isn パッケージマネージャの主要クラス

class PackageManager:
    """パッケージマネージャのメインクラス"""

    def __init__(self):
        self.db = PackageDatabase()
        self.resolver = DependencyResolver()
        self.downloader = PackageDownloader()
        self.verifier = SignatureVerifier()
        self.installer = PackageInstaller()

    def install(self, package_name: str) -> bool:
        # 1. パッケージ情報の取得
        pkg_info = self.db.get_package(package_name)

        # 2. 依存関係の解決
        deps = self.resolver.resolve(package_name)

        # 3. パッケージのダウンロード
        for dep in deps:
            pkg_file = self.downloader.download(dep)

            # 4. 署名検証
            if not self.verifier.verify(pkg_file):
                raise SecurityError(f"Signature verification failed: {dep}")

            # 5. インストール
            self.installer.install(pkg_file)

        return True

class SignatureVerifier:
    """Ed25519/GPG署名検証"""

    def verify_ed25519(self, package_file: str, signature: str) -> bool:
        """Ed25519署名検証（推奨）"""
        with open(package_file, 'rb') as f:
            data = f.read()

        public_key = self.load_public_key()
        return ed25519.verify(signature, data, public_key)

    def verify_gpg(self, package_file: str) -> bool:
        """GPG署名検証（レガシーサポート）"""
        result = subprocess.run(
            ['gpg', '--verify', f'{package_file}.sig', package_file],
            capture_output=True
        )
        return result.returncode == 0

class DependencyResolver:
    """依存関係解決エンジン"""

    def resolve(self, package_name: str) -> List[str]:
        """トポロジカルソートで依存関係を解決"""
        graph = self.build_dependency_graph(package_name)
        return self.topological_sort(graph)

    def build_dependency_graph(self, package: str) -> Dict:
        """依存関係グラフの構築"""
        graph = {}
        queue = [package]

        while queue:
            current = queue.pop(0)
            if current in graph:
                continue

            deps = self.db.get_dependencies(current)
            graph[current] = deps
            queue.extend(deps)

        return graph
```

### パッケージフォーマット

```
package.tar.gz
├── PKGINFO                 # パッケージメタデータ
├── .PKGINFO.ed25519        # Ed25519署名
├── .INSTALL                # インストールスクリプト
├── bin/
│   └── example
├── etc/
│   └── example.conf
└── usr/
    ├── lib/
    └── share/
```

**PKGINFOフォーマット**:
```ini
name = example-package
version = 1.0.0
architecture = x86_64
description = Example package
url = https://example.com
license = MIT
depends = musl busybox
size = 1048576
sha256 = abcdef1234567890...
```

## セキュリティアーキテクチャ

### 多層防御（Defense in Depth）

```
┌─────────────────────────────────────────┐
│  Layer 7: アプリケーション層             │
│  - Seccomp-BPF                          │
│  - Namespace isolation                  │
├─────────────────────────────────────────┤
│  Layer 6: パッケージ層                  │
│  - Ed25519署名検証                      │
│  - SHA-256ハッシュ検証                  │
├─────────────────────────────────────────┤
│  Layer 5: システム層                    │
│  - ファイアウォール (iptables)          │
│  - SELinux/AppArmor (将来)              │
├─────────────────────────────────────────┤
│  Layer 4: ランタイム層                  │
│  - ASLR, DEP                            │
│  - Stack canaries                       │
├─────────────────────────────────────────┤
│  Layer 3: コンパイル層                  │
│  - PIE, RELRO                           │
│  - FORTIFY_SOURCE                       │
├─────────────────────────────────────────┤
│  Layer 2: カーネル層                    │
│  - Kernel hardening                     │
│  - Seccomp-BPF                          │
├─────────────────────────────────────────┤
│  Layer 1: コンテナランタイム層          │
│  - Docker/Podman/Kubernetes             │
│  - ホストカーネル                       │
└─────────────────────────────────────────┘
```

### Ed25519署名検証フロー

```
┌─────────────────┐
│  パッケージ     │
│  ダウンロード   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  SHA-256        │
│  ハッシュ検証   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Ed25519        │
│  署名検証       │
└────────┬────────┘
         │
      ┌──┴──┐
      │     │
   OK │     │ NG
      ▼     ▼
  ┌─────┐ ┌─────┐
  │Install│ │Reject│
  └─────┘ └─────┘
```

## ブートプロセス

### 起動シーケンス

```
1. コンテナランタイム (Docker/Podman/Kubernetes)
   ├── コンテナ初期化
   └── rootfsマウント
       │
2. Linuxカーネル (ホストカーネル使用)
   ├── ネームスペース作成
   ├── cgroup設定
   └── /sbin/init (OpenRC) 起動
       │
3. OpenRC - sysinit
   ├── /proc, /sys, /dev マウント
   ├── ホスト名設定
   └── システムクロック設定
       │
4. OpenRC - boot
   ├── ファイルシステムチェック
   ├── ネットワーク初期化
   └── 必須サービス起動
       │
5. OpenRC - default
   ├── ユーザーサービス起動
   │   ├── アプリケーションサービス
   │   └── その他
   └── アプリケーション実行準備完了
```

### 起動時間最適化

**目標**: 10秒以下

**最適化手法**:
1. **並列サービス起動**: 依存関係のないサービスを並列起動
2. **不要サービスの無効化**: 最小限のサービスのみ起動
3. **カーネルパラメータ**: `quiet splash` で起動メッセージを抑制
4. **initrdの最小化**: 必要最小限のモジュールのみ含める

```bash
# 起動時間の測定
dmesg | grep "Freeing unused kernel"
systemd-analyze  # systemd環境の場合
```

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

- ビット同一の出力
- 決定論的ビルド
- バージョン固定

### 5. パフォーマンス

- 起動時間: <10秒
- メモリ使用量: <128MB
- イメージサイズ: Minimal <5MB

## データフロー

### パッケージインストールフロー

```
ユーザー
  │
  │ isn install vim
  │
  ▼
┌─────────────────┐
│ Package Manager │
└────────┬────────┘
         │
         │ 1. パッケージ情報取得
         ▼
┌─────────────────┐
│ Package DB      │
└────────┬────────┘
         │
         │ 2. 依存関係解決
         ▼
┌─────────────────┐
│ Dependency      │
│ Resolver        │
└────────┬────────┘
         │
         │ 3. ダウンロード
         ▼
┌─────────────────┐
│ Package         │
│ Repository      │
└────────┬────────┘
         │
         │ 4. 署名検証
         ▼
┌─────────────────┐
│ Ed25519         │
│ Verifier        │
└────────┬────────┘
         │
         │ 5. インストール
         ▼
┌─────────────────┐
│ Package         │
│ Installer       │
└────────┬────────┘
         │
         │ 6. 完了
         ▼
ファイルシステム
```

## モジュール間の依存関係

```
┌──────────────┐
│ Applications │
└──────┬───────┘
       │ depends on
       ▼
┌──────────────┐
│ isn (pkg mgr)│
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
- [design.md](../../.kiro/specs/kimigayo-os-core/design.md) - 設計書

---

**このドキュメントは、Kimigayo OSの開発に貢献する開発者のために作成されました。**
