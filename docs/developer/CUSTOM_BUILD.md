# カスタムイメージのビルドガイド

このガイドでは、Kimigayo OSをベースにしたカスタムDockerイメージの作成方法を説明します。

## 📋 目次

- [基本的なカスタマイズ](#基本的なカスタマイズ)
- [マルチステージビルド](#マルチステージビルド)
- [イメージバリアントの作成](#イメージバリアントの作成)
- [セキュリティ強化](#セキュリティ強化)
- [サイズ最適化](#サイズ最適化)
- [ベストプラクティス](#ベストプラクティス)

## 基本的なカスタマイズ

### 1. シンプルなアプリケーションコンテナ

静的バイナリをKimigayo OSに追加する最もシンプルな方法:

```dockerfile
FROM ishinokazuki/kimigayo-os:latest

# アプリケーションバイナリをコピー
COPY myapp /usr/local/bin/myapp
RUN chmod +x /usr/local/bin/myapp

# ポート公開
EXPOSE 8080

# エントリーポイント設定
ENTRYPOINT ["/usr/local/bin/myapp"]
```

ビルドと実行:

```bash
docker build -t my-custom-app .
docker run -p 8080:8080 my-custom-app
```

### 2. 設定ファイルの追加

```dockerfile
FROM ishinokazuki/kimigayo-os:latest

# アプリケーションと設定をコピー
COPY myapp /usr/local/bin/myapp
COPY config.yaml /etc/myapp/config.yaml

RUN chmod +x /usr/local/bin/myapp

# 作業ディレクトリ設定
WORKDIR /app

# 起動コマンド
CMD ["/usr/local/bin/myapp", "--config", "/etc/myapp/config.yaml"]
```

### 3. 環境変数の使用

```dockerfile
FROM ishinokazuki/kimigayo-os:latest

COPY myapp /usr/local/bin/myapp
RUN chmod +x /usr/local/bin/myapp

# 環境変数設定
ENV APP_ENV=production
ENV APP_PORT=8080
ENV LOG_LEVEL=info

EXPOSE ${APP_PORT}

CMD ["/usr/local/bin/myapp"]
```

## マルチステージビルド

### Go言語アプリケーション

```dockerfile
# ビルドステージ
FROM golang:1.21-alpine AS builder

WORKDIR /build

# 依存関係をコピー
COPY go.mod go.sum ./
RUN go mod download

# ソースコードをコピー
COPY . .

# 静的リンクでビルド
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -a -installsuffix cgo \
    -ldflags '-extldflags "-static" -w -s' \
    -o app .

# 実行ステージ
FROM ishinokazuki/kimigayo-os:latest-minimal

# ビルドステージからバイナリをコピー
COPY --from=builder /build/app /usr/local/bin/app

# 非rootユーザーで実行
USER nobody

EXPOSE 8080

ENTRYPOINT ["/usr/local/bin/app"]
```

### Rustアプリケーション

```dockerfile
# ビルドステージ
FROM rust:1.75-alpine AS builder

RUN apk add --no-cache musl-dev

WORKDIR /build

# 依存関係のみ先にビルド（キャッシュ効率化）
COPY Cargo.toml Cargo.lock ./
RUN mkdir src && \
    echo "fn main() {}" > src/main.rs && \
    cargo build --release && \
    rm -rf src

# 実際のソースコードをコピーしてビルド
COPY . .
RUN touch src/main.rs && \
    cargo build --release --target x86_64-unknown-linux-musl

# 実行ステージ
FROM ishinokazuki/kimigayo-os:latest-minimal

COPY --from=builder /build/target/x86_64-unknown-linux-musl/release/myapp /usr/local/bin/myapp

USER nobody

EXPOSE 8080

CMD ["/usr/local/bin/myapp"]
```

### C/C++アプリケーション

```dockerfile
# ビルドステージ
FROM alpine:3.19 AS builder

RUN apk add --no-cache gcc g++ musl-dev make

WORKDIR /build

COPY . .

# 静的リンクでビルド
RUN make LDFLAGS="-static"

# 実行ステージ
FROM ishinokazuki/kimigayo-os:latest-minimal

COPY --from=builder /build/myapp /usr/local/bin/myapp

USER nobody

EXPOSE 8080

CMD ["/usr/local/bin/myapp"]
```

## イメージバリアントの作成

### プロジェクト専用のMinimal/Standard/Extendedバリアント

```dockerfile
# Minimal: 最小限の実行環境
FROM ishinokazuki/kimigayo-os:latest-minimal AS minimal

COPY myapp /usr/local/bin/myapp
RUN chmod +x /usr/local/bin/myapp

USER nobody
ENTRYPOINT ["/usr/local/bin/myapp"]

# ----------------------------------------

# Standard: 開発ツール付き
FROM ishinokazuki/kimigayo-os:latest AS standard

COPY myapp /usr/local/bin/myapp
COPY scripts/ /usr/local/bin/scripts/

RUN chmod +x /usr/local/bin/myapp && \
    chmod +x /usr/local/bin/scripts/*

EXPOSE 8080

CMD ["/usr/local/bin/myapp"]

# ----------------------------------------

# Extended: デバッグツール付き
FROM ishinokazuki/kimigayo-os:latest-extended AS extended

COPY myapp /usr/local/bin/myapp
COPY debug-scripts/ /usr/local/bin/debug/

RUN chmod +x /usr/local/bin/myapp

# デバッグポート公開
EXPOSE 8080 9090

CMD ["/usr/local/bin/myapp", "--debug"]
```

ビルド時にターゲットを指定:

```bash
# Minimalバリアント
docker build --target minimal -t myapp:minimal .

# Standardバリアント
docker build --target standard -t myapp:standard .

# Extendedバリアント
docker build --target extended -t myapp:extended .
```

## セキュリティ強化

### 1. 非rootユーザーの使用

```dockerfile
FROM ishinokazuki/kimigayo-os:latest

# アプリケーションユーザーを作成
RUN addgroup -g 1000 appuser && \
    adduser -D -u 1000 -G appuser appuser

COPY --chown=appuser:appuser myapp /usr/local/bin/myapp
RUN chmod +x /usr/local/bin/myapp

# 非rootユーザーに切り替え
USER appuser

EXPOSE 8080

CMD ["/usr/local/bin/myapp"]
```

### 2. 読み取り専用ルートファイルシステム

```dockerfile
FROM ishinokazuki/kimigayo-os:latest

COPY myapp /usr/local/bin/myapp
RUN chmod +x /usr/local/bin/myapp

# 書き込み可能なディレクトリを作成
RUN mkdir -p /tmp /var/log/app && \
    chmod 1777 /tmp

USER nobody

# 読み取り専用で実行（docker runで --read-only オプション使用）
CMD ["/usr/local/bin/myapp"]
```

実行時:

```bash
docker run --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  --tmpfs /var/log/app:rw,noexec,nosuid,size=16m \
  myapp:latest
```

### 3. Capability制限

```dockerfile
FROM ishinokazuki/kimigayo-os:latest

COPY myapp /usr/local/bin/myapp
RUN chmod +x /usr/local/bin/myapp

USER nobody

# Capabilityのメタデータ（実行時に適用）
LABEL security.capabilities="NET_BIND_SERVICE"

CMD ["/usr/local/bin/myapp"]
```

実行時:

```bash
docker run \
  --cap-drop=ALL \
  --cap-add=NET_BIND_SERVICE \
  --security-opt=no-new-privileges:true \
  myapp:latest
```

### 4. ヘルスチェックの追加

```dockerfile
FROM ishinokazuki/kimigayo-os:latest

COPY myapp /usr/local/bin/myapp
RUN chmod +x /usr/local/bin/myapp

USER nobody

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD ["/bin/sh", "-c", "wget -q --spider http://localhost:8080/health || exit 1"]

CMD ["/usr/local/bin/myapp"]
```

## サイズ最適化

### 1. 不要なファイルの削除

```dockerfile
FROM ishinokazuki/kimigayo-os:latest-minimal

# マルチステージビルドで最小限のファイルのみコピー
COPY --from=builder /build/app /usr/local/bin/app

# .dockerignoreファイルを活用
# 以下を.dockerignoreに記載:
# *.md
# .git
# tests/
# docs/
```

### 2. レイヤー最適化

```dockerfile
FROM ishinokazuki/kimigayo-os:latest-minimal

# ❌ 悪い例（3レイヤー）
# COPY file1 /app/
# COPY file2 /app/
# COPY file3 /app/

# ✅ 良い例（1レイヤー）
COPY file1 file2 file3 /app/

# または
COPY . /app/
```

### 3. キャッシュ戦略

```dockerfile
FROM ishinokazuki/kimigayo-os:latest

# 1. 変更頻度の低いものを先にコピー（依存関係など）
COPY requirements.txt /app/
RUN install-dependencies

# 2. 変更頻度の高いものを後にコピー（ソースコードなど）
COPY src/ /app/src/

CMD ["/app/src/main"]
```

## ベストプラクティス

### 1. .dockerignoreの活用

```.dockerignore
# Git関連
.git
.gitignore
.gitattributes

# ビルド成果物
build/
dist/
*.tar.gz

# ドキュメント
README.md
docs/
*.md

# テスト
tests/
test/
*.test

# IDE設定
.vscode/
.idea/
*.swp

# ログ
*.log

# 環境変数（本番用は別途注入）
.env
.env.local
```

### 2. バージョンタグ戦略

```bash
# バージョンタグを複数付与
docker build -t myapp:0.1.0 .
docker tag myapp:0.1.0 myapp:0.1
docker tag myapp:0.1.0 myapp:latest

# セマンティックバージョニング
# major.minor.patch
# 例: 1.2.3
```

### 3. Makefileでのビルド自動化

```makefile
# Makefile
IMAGE_NAME := myapp
VERSION := $(shell git describe --tags --always)
REGISTRY := docker.io/username

.PHONY: build
build:
	docker build -t $(IMAGE_NAME):$(VERSION) .
	docker tag $(IMAGE_NAME):$(VERSION) $(IMAGE_NAME):latest

.PHONY: push
push:
	docker push $(IMAGE_NAME):$(VERSION)
	docker push $(IMAGE_NAME):latest

.PHONY: test
test:
	docker run --rm $(IMAGE_NAME):$(VERSION) /bin/sh -c "test-command"

.PHONY: clean
clean:
	docker rmi $(IMAGE_NAME):$(VERSION) $(IMAGE_NAME):latest
```

### 4. マルチアーキテクチャビルド

```bash
# Docker Buildxを使用
docker buildx create --name multiarch --use

# マルチアーキテクチャビルド
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t myapp:latest \
  --push \
  .
```

Dockerfileの例:

```dockerfile
FROM --platform=$BUILDPLATFORM ishinokazuki/kimigayo-os:latest AS base

ARG TARGETARCH
ARG TARGETOS

FROM base AS builder

# アーキテクチャに応じたビルド
COPY build-${TARGETARCH}.sh /tmp/
RUN sh /tmp/build-${TARGETARCH}.sh

FROM base

COPY --from=builder /build/output /usr/local/bin/app

CMD ["/usr/local/bin/app"]
```

### 5. Lintとセキュリティスキャン

```bash
# Dockerfile Lint
docker run --rm -i hadolint/hadolint < Dockerfile

# イメージスキャン
docker scan myapp:latest

# Trivyスキャン
trivy image myapp:latest
```

### 6. ドキュメント化

Dockerfileにコメントを追加:

```dockerfile
FROM ishinokazuki/kimigayo-os:latest

# アプリケーション情報
LABEL maintainer="your-email@example.com"
LABEL description="My custom application"
LABEL version="1.0.0"

# ビルド引数（オプション）
ARG BUILD_DATE
ARG VCS_REF

LABEL org.opencontainers.image.created="${BUILD_DATE}"
LABEL org.opencontainers.image.revision="${VCS_REF}"

# アプリケーションのインストール
COPY myapp /usr/local/bin/myapp
RUN chmod +x /usr/local/bin/myapp

# 非rootユーザーで実行（セキュリティ向上）
USER nobody

# ポート公開
EXPOSE 8080

# ヘルスチェック
HEALTHCHECK CMD wget -q --spider http://localhost:8080/health || exit 1

# 起動コマンド
CMD ["/usr/local/bin/myapp"]
```

## サンプルプロジェクト構成

```
my-custom-app/
├── Dockerfile
├── .dockerignore
├── Makefile
├── README.md
├── src/
│   ├── main.go
│   └── ...
├── config/
│   └── app.yaml
└── scripts/
    ├── build.sh
    └── test.sh
```

## トラブルシューティング

### イメージサイズが大きい

**原因:** 不要なファイルが含まれている

**解決策:**
1. .dockerignoreを活用
2. マルチステージビルドを使用
3. Minimalバリアントをベースにする

### ビルドが遅い

**原因:** キャッシュが効いていない

**解決策:**
1. 変更頻度の低いレイヤーを先に配置
2. BuildKitを有効化: `DOCKER_BUILDKIT=1 docker build .`

### 実行時にPermission denied

**原因:** ファイルに実行権限がない

**解決策:**
```dockerfile
COPY myapp /usr/local/bin/myapp
RUN chmod +x /usr/local/bin/myapp
```

## 関連ドキュメント

- [ビルドガイド](BUILD_GUIDE.md)
- [CI/CDガイド](CICD_GUIDE.md)
- [Docker使用ガイド](../user/DOCKER_USAGE.md)
- [セキュリティガイド](../security/SECURITY_GUIDE.md)

---

**カスタムイメージの作成を楽しんでください！🚀**
