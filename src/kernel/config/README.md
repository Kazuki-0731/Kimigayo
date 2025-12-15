# Kimigayo OS Kernel Configurations

このディレクトリには、Kimigayo OSの各イメージバリエーション用のカーネル設定ファイルが含まれています。

## 設定ファイル一覧

### Minimal Configuration (`minimal-x86_64.config`)
**ターゲット**: Docker コンテナ、最小限のVM環境
**イメージサイズ目標**: < 5MB
**特徴**:
- 最小限のカーネルモジュール（モジュールサポート無効）
- 基本的なセキュリティ強化のみ
- コンテナ実行に必要な cgroups と namespaces
- IPv6 無効
- netfilter 無効
- デバイスドライバは virtio と基本的なものに限定

**主な用途**:
- Docker コンテナ
- 軽量 VM
- 組み込みシステム

**セキュリティ機能**:
- ✅ ASLR (CONFIG_RANDOMIZE_BASE, CONFIG_RANDOMIZE_MEMORY)
- ✅ Stack Protection (CONFIG_STACKPROTECTOR_STRONG)
- ✅ Hardened Usercopy (CONFIG_HARDENED_USERCOPY)
- ✅ FORTIFY_SOURCE
- ❌ SELinux/AppArmor (サイズ削減のため無効)

---

### Standard Configuration (`standard-x86_64.config`)
**ターゲット**: 一般的なサーバー環境、VM、標準コンテナ
**イメージサイズ目標**: < 15MB
**特徴**:
- フル cgroups サポート（Kubernetes 対応）
- IPv6 完全サポート
- iptables/netfilter フルサポート
- AppArmor セキュリティモジュール
- モジュールサポート（署名検証付き）
- RAID/LVM サポート
- 仮想化サポート（KVM）

**主な用途**:
- 汎用サーバー
- VM 環境 (KVM, VirtualBox, VMware)
- Kubernetes ノード
- 開発/ステージング環境

**セキュリティ機能**:
- ✅ ASLR + Memory Randomization
- ✅ Page Table Isolation (PTI)
- ✅ Stack Protection + VMAP Stack
- ✅ Memory Protection (SLAB hardening)
- ✅ AppArmor
- ✅ Module Signature Verification
- ✅ Hardened Usercopy
- ✅ FORTIFY_SOURCE
- ✅ Zero-init stack variables

---

### Extended Configuration (`extended-x86_64.config`)
**ターゲット**: 開発環境、フル機能サーバー、デスクトップ環境
**イメージサイズ目標**: < 50MB
**特徴**:
- 全機能有効（デバッグ、プロファイリング、トレーシング）
- SELinux + AppArmor
- フル Bluetooth/Wireless サポート
- USB デバイス完全サポート
- マルチメディアデバイス (カメラ、オーディオ)
- グラフィックス (DRM, framebuffer)
- 全ファイルシステムサポート (Btrfs, XFS, NTFS, etc.)
- 全暗号化アルゴリズム
- NUMA サポート
- デバッグシンボル

**主な用途**:
- 開発マシン
- デスクトップ環境
- フル機能サーバー
- パフォーマンス分析
- カーネル開発

**セキュリティ機能**:
- ✅ 全セキュリティ機能有効
- ✅ SELinux + AppArmor 同時サポート
- ✅ 監査サブシステム (auditsyscall)
- ✅ 初期化時メモリゼロ化 (CONFIG_INIT_ON_ALLOC/FREE)
- ✅ デバッグ機能（開発用）

---

## カーネル設定の使用方法

### 1. ビルド時に設定を指定

```bash
# Minimal イメージ
export KERNEL_CONFIG=minimal
make kernel ARCH=x86_64

# Standard イメージ (デフォルト)
make kernel ARCH=x86_64

# Extended イメージ
export KERNEL_CONFIG=extended
make kernel ARCH=x86_64
```

### 2. 設定ファイルの直接使用

```bash
cd build/kernel-src/linux-6.6.11

# Minimal 設定を適用
cp /path/to/kimigayo/src/kernel/config/minimal-x86_64.config .config

# 設定を確認・調整
make menuconfig

# ビルド
make -j$(nproc)
```

## セキュリティ強化オプション比較

| セキュリティ機能 | Minimal | Standard | Extended |
|----------------|---------|----------|----------|
| ASLR | ✅ | ✅ | ✅ |
| Stack Protection | ✅ | ✅ | ✅ |
| FORTIFY_SOURCE | ✅ | ✅ | ✅ |
| Hardened Usercopy | ✅ | ✅ | ✅ |
| Page Table Isolation | ❌ | ✅ | ✅ |
| SLAB Hardening | ⚠️ Basic | ✅ Full | ✅ Full |
| AppArmor | ❌ | ✅ | ✅ |
| SELinux | ❌ | ❌ | ✅ |
| Module Signing | ❌ | ✅ | ✅ |
| Init Memory Zeroing | ❌ | ⚠️ Stack | ✅ Full |
| Audit Subsystem | ❌ | ✅ | ✅ |

## パフォーマンス vs セキュリティ

### Minimal
- **パフォーマンス**: ⭐⭐⭐⭐⭐ (最高速)
- **セキュリティ**: ⭐⭐⭐ (基本的)
- **メモリ使用量**: 最小
- **起動時間**: 最速

### Standard
- **パフォーマンス**: ⭐⭐⭐⭐ (高速)
- **セキュリティ**: ⭐⭐⭐⭐ (堅牢)
- **メモリ使用量**: 中程度
- **起動時間**: 高速

### Extended
- **パフォーマンス**: ⭐⭐⭐ (標準)
- **セキュリティ**: ⭐⭐⭐⭐⭐ (最高)
- **メモリ使用量**: 大
- **起動時間**: 標準

## カスタマイズ

既存の設定をベースにカスタマイズする場合:

```bash
# Standard 設定をベースにカスタマイズ
cp standard-x86_64.config my-custom.config

# 設定を編集
vi my-custom.config

# またはmenuconfig でGUIで編集
cd build/kernel-src/linux-6.6.11
cp /path/to/my-custom.config .config
make menuconfig

# 変更を保存
cp .config /path/to/kimigayo/src/kernel/config/my-custom.config
```

## トラブルシューティング

### Q: カーネルビルドが失敗する
**A**: 設定ファイルのバージョンがカーネルバージョンと一致しているか確認してください。
```bash
cd build/kernel-src/linux-6.6.11
make ARCH=x86_64 olddefconfig  # 古い設定を新しいカーネルに適合
```

### Q: モジュールが見つからない
**A**: Minimal 設定ではモジュールサポートが無効です。Standard または Extended を使用してください。

### Q: セキュリティ機能が有効になっているか確認したい
**A**: ビルド後にカーネル設定を確認:
```bash
cd build/kernel/output
cat config-6.6.11-x86_64 | grep -E "RANDOMIZE|STACKPROTECTOR|FORTIFY"
```

## 参考資料

- [Linux Kernel Configuration](https://www.kernel.org/doc/html/latest/admin-guide/README.html)
- [Kernel Hardening](https://kernsec.org/wiki/index.php/Kernel_Self_Protection_Project)
- [Alpine Linux Kernel Config](https://git.alpinelinux.org/aports/tree/main/linux-lts)
- [Kimigayo OS Security Policy](../../../docs/security/SECURITY_POLICY.md)
