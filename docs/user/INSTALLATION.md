# Kimigayo OS インストールガイド

Kimigayo OSへようこそ！このガイドでは、Kimigayo OSのインストール方法を説明します。

## 目次

- [システム要件](#システム要件)
- [インストール方法](#インストール方法)
  - [Docker環境](#docker環境)
  - [Kubernetes環境](#kubernetes環境)
  - [Podman環境](#podman環境)
- [インストール後の設定](#インストール後の設定)
- [トラブルシューティング](#トラブルシューティング)

## システム要件

### 最小要件
- **CPU**: x86_64 または ARM64
- **RAM**: 128MB
- **ストレージ**: 512MB
- **コンテナランタイム**: Docker 20.10以降、Podman 3.0以降、またはKubernetes 1.20以降

### 推奨要件
- **CPU**: x86_64 または ARM64（2コア以上）
- **RAM**: 512MB以上
- **ストレージ**: 2GB以上

### サポートアーキテクチャ
- x86_64 (AMD64)
- ARM64 (AArch64)
- 将来的に: RISC-V

## インストール方法

Kimigayo OSはコンテナイメージとして提供されており、以下の環境で実行できます：

### Docker環境

Dockerを使用したインストールが最も簡単です。

#### 前提条件
- Docker 20.10以降がインストールされていること

#### Minimalイメージ（5MB以下）

```bash
# Kimigayo OS Minimalイメージをpull
docker pull ishinokazuki/kimigayo-os:latest-minimal

# コンテナを起動
docker run -it ishinokazuki/kimigayo-os:latest-minimal
```

#### Standardイメージ（推奨）

```bash
# Kimigayo OS Standardイメージをpull
docker pull ishinokazuki/kimigayo-os:latest

# コンテナを起動
docker run -it ishinokazuki/kimigayo-os:latest
```

#### Extendedイメージ

```bash
# Kimigayo OS Extendedイメージをpull
docker pull ishinokazuki/kimigayo-os:latest-extended

# コンテナを起動
docker run -it ishinokazuki/kimigayo-os:latest-extended
```

**注意:** Docker Hubのリポジトリは `ishinokazuki/kimigayo-os` です。

#### 永続的なデータボリュームを使用

```bash
# データボリュームを作成
docker volume create kimigayo-data

# ボリュームをマウントして起動
docker run -it -v kimigayo-data:/data kimigayo/kimigayo-os:standard
```

#### デーモンモードでの起動

```bash
# バックグラウンドで起動
docker run -d --name kimigayo-app kimigayo/kimigayo-os:standard

# コンテナに接続
docker exec -it kimigayo-app /bin/sh
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
  replicas: 3
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

# ログの確認
kubectl logs -l app=kimigayo-os
```

#### Helmチャートの使用

```bash
# Helmリポジトリの追加
helm repo add kimigayo https://charts.kimigayo-os.org
helm repo update

# Kimigayo OSのインストール
helm install my-kimigayo kimigayo/kimigayo-os

# カスタム設定でインストール
helm install my-kimigayo kimigayo/kimigayo-os \
  --set image.tag=standard \
  --set replicaCount=3 \
  --set resources.requests.memory=128Mi
```

### Podman環境

Podmanを使用する場合（Dockerとほぼ同じコマンド）：

```bash
# イメージをpull
podman pull kimigayo/kimigayo-os:standard

# コンテナを起動
podman run -it kimigayo/kimigayo-os:standard

# システムdサービスとして実行
podman generate systemd --name kimigayo-app > /etc/systemd/system/kimigayo-app.service
systemctl enable --now kimigayo-app
```

## インストール後の設定

### 初回起動

コンテナ起動後、以下の設定を行います：

```bash
# ホスト名の設定
echo "kimigayo" > /etc/hostname

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

### 追加ソフトウェアのインストール

Kimigayo OSはdistroless設計を採用しており、パッケージマネージャは含まれていません。追加ソフトウェアが必要な場合は、マルチステージビルドを使用してください。

```bash
# マルチステージビルドの例
FROM alpine:3.19 AS builder
RUN apk add --no-cache vim curl wget

FROM ishinokazuki/kimigayo-os:latest
COPY --from=builder /usr/bin/vim /usr/bin/vim
COPY --from=builder /usr/bin/curl /usr/bin/curl
COPY --from=builder /usr/bin/wget /usr/bin/wget
```

### ネットワーク設定

```bash
# ネットワークインターフェースの確認
ip link show

# 静的IPの設定（必要に応じて）
cat > /etc/network/interfaces << EOF
auto eth0
iface eth0 inet static
    address 192.168.1.100
    netmask 255.255.255.0
    gateway 192.168.1.1
EOF
```

## トラブルシューティング

### コンテナが起動しない

- **メモリ不足**: 最低128MBのRAMが必要です
- **ストレージ不足**: 最低512MBのストレージが必要です
- **アーキテクチャ不一致**: x86_64またはARM64アーキテクチャを確認してください

```bash
# コンテナのログを確認
docker logs <container-id>

# リソース使用状況を確認
docker stats
```

### ネットワークに接続できない

```bash
# ネットワークインターフェースの確認
ip link show

# DHCPクライアントの起動
dhclient eth0

# Dockerネットワークの確認
docker network ls
docker network inspect bridge
```

### ソフトウェアのインストール方法

Kimigayo OSはdistroless設計のため、パッケージマネージャは含まれていません。

```bash
# 必要なソフトウェアはマルチステージビルドで追加
# Dockerfileを参照してください
```

### イメージのpullが失敗する

```bash
# Dockerデーモンの再起動
sudo systemctl restart docker

# プロキシ設定の確認（必要に応じて）
docker info | grep -i proxy

# 別のレジストリを試す
docker pull ghcr.io/kimigayo/kimigayo-os:standard
```

## パフォーマンスチューニング

### メモリ制限の設定

```bash
# 最大メモリを512MBに制限
docker run -it --memory=512m kimigayo/kimigayo-os:standard

# スワップを無効化
docker run -it --memory=512m --memory-swap=512m kimigayo/kimigayo-os:standard
```

### CPU制限の設定

```bash
# CPU使用率を50%に制限
docker run -it --cpus=0.5 kimigayo/kimigayo-os:standard

# 特定のCPUコアに固定
docker run -it --cpuset-cpus=0,1 kimigayo/kimigayo-os:standard
```

## セキュリティ設定

### 読み取り専用ルートファイルシステム

```bash
# ルートファイルシステムを読み取り専用に
docker run -it --read-only --tmpfs /tmp kimigayo/kimigayo-os:standard
```

### 非rootユーザーでの実行

```bash
# 特定のユーザーIDで実行
docker run -it --user 1000:1000 kimigayo/kimigayo-os:standard
```

## サポート

問題が解決しない場合は、以下のリソースを参照してください：

- **GitHub リポジトリ**: https://github.com/Kazuki-0731/Kimigayo
- **Issue報告**: https://github.com/Kazuki-0731/Kimigayo/issues
- **GitHub Discussions**: https://github.com/Kazuki-0731/Kimigayo/discussions

## 次のステップ

インストールが完了したら、以下のドキュメントを参照してください：

- [クイックスタートガイド](QUICKSTART.md)
- [システム設定ガイド](CONFIGURATION.md)
- [セキュリティガイド](../security/SECURITY_GUIDE.md)
