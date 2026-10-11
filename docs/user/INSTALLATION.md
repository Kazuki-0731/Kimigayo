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

#### Minimalイメージ（2.62MB / arm64 2.98MB）

```bash
# Kimigayo OS Minimalイメージをpull
docker pull ishinokazuki/kimigayo-os:latest-minimal

# コンテナを起動
docker run -it ishinokazuki/kimigayo-os:latest-minimal
```

#### Standardイメージ（2.76MB / arm64 3.13MB、推奨）

```bash
# Kimigayo OS Standardイメージをpull
docker pull ishinokazuki/kimigayo-os:latest

# コンテナを起動
docker run -it ishinokazuki/kimigayo-os:latest
```

#### Extendedイメージ（2.78MB / arm64 3.17MB）

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
docker run -it -v kimigayo-data:/data ishinokazuki/kimigayo-os:latest
```

#### デーモンモードでの起動

```bash
# バックグラウンドで起動
docker run -d --name kimigayo-app ishinokazuki/kimigayo-os:latest

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
        image: ishinokazuki/kimigayo-os:latest
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

**Helm チャートは配布していません。** Helm で管理したい場合は、上の
Deployment マニフェストを自分のチャートに取り込んでください。

### Podman環境

Podmanを使用する場合（Dockerとほぼ同じコマンド）：

```bash
# イメージをpull
podman pull ishinokazuki/kimigayo-os:latest

# コンテナを起動
podman run -it ishinokazuki/kimigayo-os:latest

# システムdサービスとして実行
podman generate systemd --name kimigayo-app > /etc/systemd/system/kimigayo-app.service
systemctl enable --now kimigayo-app
```

## インストール後の設定

### 初回起動

コンテナ起動後、以下の設定を行います：

```bash
# ホスト名の設定（コンテナでは docker run --hostname の方が確実）
echo "kimigayo" > /etc/hostname
```

**タイムゾーンのデータベースは入っていません。** `/usr/share/zoneinfo` が
無いので `ln -sf /usr/share/zoneinfo/Asia/Tokyo /etc/localtime` は使えません。
必要な場合は、必要なゾーンだけをビルド時に持ち込みます。

```dockerfile
FROM alpine:3.24 AS tz
RUN apk add --no-cache tzdata

FROM ishinokazuki/kimigayo-os:3.0.1
COPY --from=tz /usr/share/zoneinfo/Asia/Tokyo /etc/localtime
ENV TZ=Asia/Tokyo
```

### ユーザーの作成

```bash
# 新しいユーザーを追加（BusyBox の adduser）
adduser username
```

**`sudo` と `wheel` グループはありません。** `sudo` は入っておらず、
`/etc/group` にも `wheel` がないので `adduser username wheel` は失敗します。
権限を落として実行したいときは、コンテナの外から指定してください。

```bash
docker run -it --user 1000:1000 ishinokazuki/kimigayo-os:latest
```

root へ昇格する必要がある場合は BusyBox の `su` を使います。

### 追加ソフトウェアのインストール

Kimigayo OSはdistroless設計を採用しており、パッケージマネージャは含まれていません。追加ソフトウェアが必要な場合は、マルチステージビルドを使用してください。

**実行ファイルだけを `COPY` しても動きません。** 共有ライブラリを
一緒に持ち込む必要があります。足りないと実行時に
`Error relocating ...: symbol not found` で落ちます。
**依存は手で列挙せず `ldd` で解決します**（上流の更新で依存が増えても追従できます）。

```dockerfile
FROM alpine:3.24 AS builder
RUN apk add --no-cache curl

RUN mkdir -p /stage/usr/bin /stage/usr/lib \
    && cp /usr/bin/curl /stage/usr/bin/ \
    && ldd /usr/bin/curl \
       | awk '/=>/ { print $3 } /^\/lib|^\/usr\/lib/ { print $1 }' \
       | grep -v 'ld-musl' \
       | sort -u \
       | xargs -I{} cp -L {} /stage/usr/lib/

# 版を固定する。latest は毎リリースで中身が変わります。
FROM ishinokazuki/kimigayo-os:3.0.1
COPY --from=builder /stage/ /
```

`vi`・`wget`・`awk`・`sed` は Standard と Extended に**最初から入っています**
（BusyBox のアプレット）。持ち込みが必要なのは `curl` のように
BusyBox に無いものだけです。動く例は
[examples/](../../examples/)（nginx / Node.js / Python）にあります。

### ネットワーク設定

**ネットワークはコンテナランタイムが設定します。** イメージには
`/etc/network/interfaces` が置かれていますが、**それを読む `networking`
サービスがイメージに入っていない**ので、ここを書き換えても何も起きません。

```bash
# コンテナ内から確認する
ip link show
ip addr show
```

静的 IP が必要なときは、コンテナの外から指定します。

```bash
docker network create --subnet 192.168.100.0/24 kimigayo-net
docker run -it --network kimigayo-net --ip 192.168.100.10 \
  ishinokazuki/kimigayo-os:latest
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

# DHCPクライアントの起動（BusyBox は udhcpc。dhclient は入っていません）
udhcpc -i eth0

# Dockerネットワークの確認（ホスト側で実行）
docker network ls
docker network inspect bridge
```

通常の `docker run` では**ランタイムが IP を割り当てるので `udhcpc` を
自分で叩く必要はありません。**

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
```

**配布先は Docker Hub の `ishinokazuki/kimigayo-os` だけです。**
GitHub Container Registry（`ghcr.io`）には公開していません。

## パフォーマンスチューニング

### メモリ制限の設定

```bash
# 最大メモリを512MBに制限
docker run -it --memory=512m ishinokazuki/kimigayo-os:latest

# スワップを無効化
docker run -it --memory=512m --memory-swap=512m ishinokazuki/kimigayo-os:latest
```

### CPU制限の設定

```bash
# CPU使用率を50%に制限
docker run -it --cpus=0.5 ishinokazuki/kimigayo-os:latest

# 特定のCPUコアに固定
docker run -it --cpuset-cpus=0,1 ishinokazuki/kimigayo-os:latest
```

## セキュリティ設定

### 読み取り専用ルートファイルシステム

```bash
# ルートファイルシステムを読み取り専用に
docker run -it --read-only --tmpfs /tmp ishinokazuki/kimigayo-os:latest
```

### 非rootユーザーでの実行

```bash
# 特定のユーザーIDで実行
docker run -it --user 1000:1000 ishinokazuki/kimigayo-os:latest
```

## サポート

問題が解決しない場合は、以下のリソースを参照してください：

- **GitHub リポジトリ**: https://github.com/Kazuki-0731/Kimigayo
- **Issue報告**: https://github.com/Kazuki-0731/Kimigayo/issues

## 次のステップ

インストールが完了したら、以下のドキュメントを参照してください：

- [クイックスタートガイド](QUICKSTART.md)
- [システム設定ガイド](CONFIGURATION.md)
- [セキュリティガイド](../security/SECURITY_GUIDE.md)
