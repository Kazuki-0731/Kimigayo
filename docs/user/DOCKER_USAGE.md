# Kimigayo OS - Docker使用ガイド

Kimigayo OSのDockerイメージの使い方を説明します。

## 📋 目次

- [イメージの種類](#イメージの種類)
- [基本的な使い方](#基本的な使い方)
- [ユースケース別サンプル](#ユースケース別サンプル)
- [トラブルシューティング](#トラブルシューティング)
- [よくある質問](#よくある質問)

## イメージの種類

Kimigayo OSは3つのバリアントを提供しています:

| バリアント | イメージ名 | サイズ | 用途 |
|-----------|-----------|--------|------|
| **Minimal** | `ishinokazuki/kimigayo-os:latest-minimal` | ~5MB | 最小限の環境、組み込み、マイクロサービス |
| **Standard** (推奨) | `ishinokazuki/kimigayo-os:latest` | ~10MB | 一般的な用途、開発、本番環境 |
| **Extended** | `ishinokazuki/kimigayo-os:latest-extended` | ~20MB | 開発ツール付き、デバッグ、フル機能 |

### アーキテクチャ対応

- **x86_64 (amd64)**: 完全サポート
- **ARM64 (aarch64)**: 完全サポート

マルチアーキテクチャ対応のため、Dockerが自動的に適切なイメージを選択します。

## 基本的な使い方

### イメージの取得

```bash
# Standardバリアント（推奨）
docker pull ishinokazuki/kimigayo-os:latest

# Minimalバリアント
docker pull ishinokazuki/kimigayo-os:latest-minimal

# Extendedバリアント
docker pull ishinokazuki/kimigayo-os:latest-extended

# 特定バージョンを指定
docker pull ishinokazuki/kimigayo-os:0.1.0
```

### 基本的な起動

```bash
# インタラクティブシェルで起動
docker run -it ishinokazuki/kimigayo-os:latest

# コンテナ内でコマンド実行
docker run --rm ishinokazuki/kimigayo-os:latest /bin/sh -c "echo 'Hello from Kimigayo OS'"

# バックグラウンドで起動（デーモンモード）
docker run -d --name my-kimigayo ishinokazuki/kimigayo-os:latest sleep infinity
```

### コンテナへのアクセス

```bash
# 実行中のコンテナに接続
docker exec -it my-kimigayo /bin/sh

# コンテナのログを確認
docker logs my-kimigayo

# コンテナの停止
docker stop my-kimigayo

# コンテナの削除
docker rm my-kimigayo
```

## ユースケース別サンプル

### 1. 軽量Webサーバー

BusyBox httpdを使用した簡易Webサーバー:

```bash
# ホスト側にコンテンツディレクトリを作成
mkdir -p ~/www
echo "<h1>Hello from Kimigayo OS!</h1>" > ~/www/index.html

# Webサーバーを起動
docker run -d \
  --name kimigayo-web \
  -p 8080:80 \
  -v ~/www:/var/www/html:ro \
  ishinokazuki/kimigayo-os:latest \
  httpd -f -p 80 -h /var/www/html

# ブラウザで http://localhost:8080 にアクセス
```

### 2. マイクロサービス基盤

最小限のフットプリントでマイクロサービスを実行:

```dockerfile
# Dockerfile
FROM ishinokazuki/kimigayo-os:latest-minimal

# アプリケーションバイナリをコピー
COPY myapp /usr/local/bin/myapp
RUN chmod +x /usr/local/bin/myapp

# ポート公開
EXPOSE 8080

# アプリケーション起動
CMD ["/usr/local/bin/myapp"]
```

```bash
# ビルドと実行
docker build -t my-microservice .
docker run -d -p 8080:8080 my-microservice
```

### 3. 開発環境

永続的な開発コンテナ:

```bash
# 開発用コンテナを起動
docker run -it \
  --name dev-env \
  -v $(pwd):/workspace \
  -w /workspace \
  ishinokazuki/kimigayo-os:latest-extended \
  /bin/sh

# コンテナ内で開発作業
# ファイルはホストと同期される
```

### 4. CIパイプライン

GitHub ActionsやGitLab CIでのテスト環境:

```yaml
# .github/workflows/test.yml
name: Test

on: [push]

jobs:
  test:
    runs-on: ubuntu-latest
    container:
      image: ishinokazuki/kimigayo-os:latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: |
          echo "Testing in Kimigayo OS"
          /bin/sh test.sh
```

### 5. セキュアな実行環境

読み取り専用ルートファイルシステムでの実行:

```bash
# セキュリティ強化設定で起動
docker run -it \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  --security-opt=no-new-privileges:true \
  --cap-drop=ALL \
  --cap-add=NET_BIND_SERVICE \
  ishinokazuki/kimigayo-os:latest \
  /bin/sh
```

### 6. バッチ処理

定期的なバッチジョブ実行:

```bash
# バッチスクリプトを作成
cat > batch.sh <<'EOF'
#!/bin/sh
echo "Batch job started at $(date)"
# バッチ処理の内容
echo "Processing..."
sleep 5
echo "Batch job completed at $(date)"
EOF

# バッチジョブを実行
docker run --rm \
  -v $(pwd)/batch.sh:/batch.sh:ro \
  ishinokazuki/kimigayo-os:latest \
  /bin/sh /batch.sh
```

### 7. Docker Composeでのサービス構成

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    image: ishinokazuki/kimigayo-os:latest
    command: /app/server
    volumes:
      - ./app:/app:ro
    ports:
      - "8080:8080"
    restart: unless-stopped

  worker:
    image: ishinokazuki/kimigayo-os:latest-minimal
    command: /app/worker
    volumes:
      - ./app:/app:ro
    restart: unless-stopped

  monitoring:
    image: ishinokazuki/kimigayo-os:latest-extended
    command: /bin/sh -c "while true; do ps aux; sleep 60; done"
```

```bash
# サービス起動
docker compose up -d

# ログ確認
docker compose logs -f

# サービス停止
docker compose down
```

### 8. マルチステージビルド

効率的なイメージビルド:

```dockerfile
# ビルドステージ
FROM alpine:3.19 AS builder
RUN apk add --no-cache gcc musl-dev
COPY src/ /src
WORKDIR /src
RUN gcc -static -o myapp main.c

# 実行ステージ
FROM ishinokazuki/kimigayo-os:latest-minimal
COPY --from=builder /src/myapp /usr/local/bin/myapp
CMD ["/usr/local/bin/myapp"]
```

## トラブルシューティング

### イメージが見つからない

**症状:**
```
Error response from daemon: manifest for ishinokazuki/kimigayo-os:latest not found
```

**解決策:**
1. イメージ名のスペルを確認
2. タグが存在するか確認:
```bash
docker pull ishinokazuki/kimigayo-os:0.1.0
```
3. ネットワーク接続を確認

---

### コンテナが即座に終了する

**症状:**
```bash
$ docker run ishinokazuki/kimigayo-os:latest
$ docker ps
CONTAINER ID   IMAGE     COMMAND   CREATED   STATUS    PORTS     NAMES
```

**解決策:**

デフォルトコマンドが`/bin/sh`のため、インタラクティブモード(`-it`)が必要:

```bash
# ✅ 正しい
docker run -it ishinokazuki/kimigayo-os:latest

# または長時間実行コマンドを指定
docker run -d ishinokazuki/kimigayo-os:latest sleep infinity
```

---

### Permission denied エラー

**症状:**
```
permission denied while trying to connect to the Docker daemon socket
```

**解決策:**

```bash
# ユーザーをdockerグループに追加
sudo usermod -aG docker $USER

# ログアウト/ログインして反映
# または
newgrp docker

# Dockerサービスを再起動
sudo systemctl restart docker
```

---

### メモリ不足エラー

**症状:**
```
Cannot allocate memory
```

**解決策:**

メモリ制限を調整:

```bash
# メモリ制限を128MBに設定
docker run -it --memory=128m ishinokazuki/kimigayo-os:latest

# メモリ制限を確認
docker stats
```

---

### ボリュームマウントが機能しない

**症状:**
コンテナ内でホストのファイルが見えない

**解決策:**

1. 絶対パスを使用:
```bash
# ❌ 間違い
docker run -v ./data:/data ishinokazuki/kimigayo-os:latest

# ✅ 正しい
docker run -v $(pwd)/data:/data ishinokazuki/kimigayo-os:latest
```

2. SELinuxの場合は`:z`フラグを追加:
```bash
docker run -v $(pwd)/data:/data:z ishinokazuki/kimigayo-os:latest
```

---

### ネットワーク接続できない

**症状:**
コンテナから外部ネットワークにアクセスできない

**解決策:**

```bash
# DNSを明示的に指定
docker run --dns=8.8.8.8 ishinokazuki/kimigayo-os:latest

# ホストネットワークモードを使用（セキュリティリスクあり）
docker run --network=host ishinokazuki/kimigayo-os:latest
```

---

### イメージサイズが大きい

**症状:**
期待よりイメージサイズが大きい

**解決策:**

適切なバリアントを選択:

```bash
# Minimalバリアント（最小）
docker pull ishinokazuki/kimigayo-os:latest-minimal

# イメージサイズを確認
docker images | grep kimigayo-os
```

## よくある質問

### Q1: Alpineとの違いは何ですか？

**A:** Kimigayo OSはGoogleのdistrolessと同様の設計思想を採用し、以下の特徴があります:

- パッケージマネージャを意図的に排除（不変インフラの徹底）
- より強力なセキュリティ強化（最小攻撃面、デフォルト設定）
- デバッグ可能性（BusyBoxによるシェル・ツール提供）
- 再現可能ビルドの徹底
- 日本語ドキュメントの充実

---

### Q2: パッケージを追加できますか？

**A:** Kimigayo OSはdistroless設計を採用しており、パッケージマネージャは含まれていません。必要なソフトウェアは、マルチステージビルドでコンパイルしてから、Kimigayo OSイメージにコピーすることを推奨します。

```bash
# マルチステージビルドの例
FROM alpine:3.19 AS builder
RUN apk add --no-cache curl

FROM ishinokazuki/kimigayo-os:latest
COPY --from=builder /usr/bin/curl /usr/bin/curl
```

---

### Q3: 本番環境で使用できますか？

**A:** Kimigayo OSは現在**開発段階**です。本番環境での使用は推奨しません。

安定版リリース（v1.0.0）まではテスト・開発環境での使用を推奨します。

---

### Q4: どのバリアントを選ぶべきですか？

**A:**

- **Minimal**: マイクロサービス、最小限のフットプリントが必要な場合
- **Standard**: 一般的な用途（推奨）
- **Extended**: 開発・デバッグ、フル機能が必要な場合

迷ったら**Standard**を選択してください。

---

### Q5: アーキテクチャを指定できますか？

**A:** はい、プラットフォームフラグで指定できます:

```bash
# ARM64を明示的に指定
docker pull --platform=linux/arm64 ishinokazuki/kimigayo-os:latest

# x86_64を明示的に指定
docker pull --platform=linux/amd64 ishinokazuki/kimigayo-os:latest
```

---

### Q6: ログはどこに保存されますか？

**A:** デフォルトではログは保存されません。永続化する場合:

```bash
# ボリュームをマウント
docker run -it \
  -v kimigayo-logs:/var/log \
  ishinokazuki/kimigayo-os:latest
```

---

### Q7: セキュリティアップデートはどうなりますか？

**A:** 定期的に脆弱性スキャンを実施し、セキュリティアドバイザリを公開します:

- [セキュリティポリシー](https://github.com/Kazuki-0731/Kimigayo/blob/main/docs/security/SECURITY_POLICY.md)
- [脆弱性報告](https://github.com/Kazuki-0731/Kimigayo/blob/main/docs/security/VULNERABILITY_REPORTING.md)

## サポート

### ドキュメント

- [インストールガイド](INSTALLATION.md)
- [クイックスタート](QUICKSTART.md)
- [設定ガイド](CONFIGURATION.md)

### コミュニティ

- [GitHub Issues](https://github.com/Kazuki-0731/Kimigayo/issues) - バグ報告・機能リクエスト
- [GitHub Discussions](https://github.com/Kazuki-0731/Kimigayo/discussions) - 質問・アイデア
- [Wiki](https://github.com/Kazuki-0731/Kimigayo/wiki) - 詳細な技術情報

### 貢献

Kimigayo OSへの貢献を歓迎します！

- [貢献ガイド](../../CONTRIBUTING.md)
- [コミットメッセージガイド](../developer/COMMIT_GUIDE.md)

---

**Kimigayo OSを使っていただきありがとうございます！🎉**
