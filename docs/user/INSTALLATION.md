# Kimigayo OS インストールガイド

Kimigayo OSへようこそ！このガイドでは、Kimigayo OSのインストール方法を説明します。

## 目次

- [システム要件](#システム要件)
- [インストール方法](#インストール方法)
  - [Docker環境](#docker環境)
  - [仮想化環境](#仮想化環境)
  - [ベアメタル（実機）](#ベアメタル実機)
- [インストール後の設定](#インストール後の設定)
- [トラブルシューティング](#トラブルシューティング)

## システム要件

### 最小要件
- **CPU**: x86_64 または ARM64
- **RAM**: 128MB
- **ストレージ**: 512MB

### 推奨要件
- **CPU**: x86_64 または ARM64（2コア以上）
- **RAM**: 512MB以上
- **ストレージ**: 2GB以上

### サポートアーキテクチャ
- x86_64 (AMD64)
- ARM64 (AArch64)
- 将来的に: RISC-V, ARM32

## インストール方法

Kimigayo OSは以下の環境にインストールできます：

### Docker環境

Dockerを使用したインストールが最も簡単です。

#### 前提条件
- Docker 20.10以降がインストールされていること

#### Minimalイメージ（5MB以下）

```bash
# Kimigayo OS Minimalイメージをpull
docker pull kimigayo/kimigayo-os:minimal

# コンテナを起動
docker run -it kimigayo/kimigayo-os:minimal
```

#### Standardイメージ（15MB以下）

```bash
# Kimigayo OS Standardイメージをpull
docker pull kimigayo/kimigayo-os:standard

# コンテナを起動
docker run -it kimigayo/kimigayo-os:standard
```

#### Extendedイメージ（50MB以下）

```bash
# Kimigayo OS Extendedイメージをpull
docker pull kimigayo/kimigayo-os:extended

# コンテナを起動
docker run -it kimigayo/kimigayo-os:extended
```

#### 永続的なデータボリュームを使用

```bash
# データボリュームを作成
docker volume create kimigayo-data

# ボリュームをマウントして起動
docker run -it -v kimigayo-data:/data kimigayo/kimigayo-os:standard
```

### Kubernetes環境

Kubernetesクラスタにデプロイする場合：

```yaml
# kimigayo-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kimigayo-os
spec:
  replicas: 1
  selector:
    matchLabels:
      app: kimigayo-os
  template:
    metadata:
      labels:
        app: kimigayo-os
    spec:
      containers:
      - name: kimigayo-os
        image: kimigayo/kimigayo-os:standard
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

```bash
# デプロイ
kubectl apply -f kimigayo-deployment.yaml

# Podの確認
kubectl get pods
```

### 仮想化環境

#### QEMU/KVM

```bash
# ディスクイメージを作成
qemu-img create -f qcow2 kimigayo-os.qcow2 2G

# ISOイメージから起動
qemu-system-x86_64 \
  -m 512 \
  -cdrom kimigayo-os.iso \
  -hda kimigayo-os.qcow2 \
  -boot d

# インストール後の起動
qemu-system-x86_64 \
  -m 512 \
  -hda kimigayo-os.qcow2 \
  -enable-kvm  # KVMが利用可能な場合
```

#### VirtualBox

1. VirtualBoxを起動
2. 「新規」をクリック
3. 以下の設定を入力：
   - **名前**: Kimigayo OS
   - **タイプ**: Linux
   - **バージョン**: Other Linux (64-bit)
   - **メモリサイズ**: 512MB以上
   - **ハードディスク**: 仮想ハードディスクを作成する（2GB以上）
4. 設定 → ストレージ → 光学ドライブにKimigayo OSのISOイメージを追加
5. 起動してインストールを実行

### ベアメタル（実機）

#### x86_64実機へのインストール

1. **USBブートメディアの作成**

```bash
# LinuxまたはmacOSの場合
sudo dd if=kimigayo-os.iso of=/dev/sdX bs=4M status=progress
sync
```

2. **BIOSからUSBブート**
   - コンピュータを再起動
   - BIOS/UEFIに入る（通常F2, F12, DELキー）
   - USBデバイスから起動するように設定

3. **インストール実行**
   - インストーラーの指示に従う
   - パーティション設定
   - ブートローダーのインストール

#### ARM64デバイスへのインストール

```bash
# SDカードにイメージを書き込み（Raspberry Piなど）
sudo dd if=kimigayo-os-arm64.img of=/dev/sdX bs=4M status=progress
sync

# SDカードをデバイスに挿入して起動
```

## インストール後の設定

### 初回起動

インストール後、初回起動時に以下の設定を行います：

```bash
# ホスト名の設定
echo "kimigayo" > /etc/hostname

# ネットワークの設定
vi /etc/network/interfaces

# タイムゾーンの設定
ln -sf /usr/share/zoneinfo/Asia/Tokyo /etc/localtime
```

### ユーザーの作成

```bash
# 新しいユーザーを追加
adduser username

# sudoグループに追加（必要に応じて）
adduser username wheel
```

### パッケージマネージャ（isn）の初期化

```bash
# パッケージリポジトリの更新
isn update

# 基本パッケージのインストール
isn install vim curl wget
```

## トラブルシューティング

### 起動しない

- **メモリ不足**: 最低128MBのRAMが必要です
- **ストレージ不足**: 最低512MBのストレージが必要です
- **アーキテクチャ不一致**: x86_64またはARM64アーキテクチャを確認してください

### ネットワークに接続できない

```bash
# ネットワークインターフェースの確認
ip link show

# DHCPクライアントの起動
dhclient eth0
```

### パッケージマネージャが動作しない

```bash
# リポジトリの確認
cat /etc/isn/repositories.conf

# キャッシュのクリア
isn cache clean

# リポジトリの再同期
isn update --force
```

## サポート

問題が解決しない場合は、以下のリソースを参照してください：

- **公式ドキュメント**: https://docs.kimigayo-os.org
- **GitHubリポジトリ**: https://github.com/kimigayo/kimigayo-os
- **コミュニティフォーラム**: https://forum.kimigayo-os.org
- **Issue報告**: https://github.com/kimigayo/kimigayo-os/issues

## 次のステップ

インストールが完了したら、以下のドキュメントを参照してください：

- [クイックスタートガイド](QUICKSTART.md)
- [パッケージマネージャ使用方法](PACKAGE_MANAGER.md)
- [システム設定ガイド](CONFIGURATION.md)
