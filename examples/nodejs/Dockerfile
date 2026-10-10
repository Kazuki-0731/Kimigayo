# Kimigayo OS + Node.js
#
# **Kimigayo にはパッケージマネージャーがありません**（設計方針）。
# `apk add` は使えないので、マルチステージビルドで Alpine 側に用意し、
# 必要なファイルだけを COPY します。
# → SPECIFICATION.md 3.5 / README.md「設計思想」

FROM alpine:3.24 AS builder

RUN apk add --no-cache nodejs

# 必要な共有ライブラリを ldd で解決して1か所に集める。
#
# **手で列挙しないこと。** node は 18 本の共有ライブラリに依存していて
# （icu・openssl・brotli・simdjson など）、列挙し忘れると実行時に
# `Error relocating ...: symbol not found` で落ちます。
# 上流の更新で依存が増えても、この書き方なら追従します。
RUN mkdir -p /stage/usr/bin /stage/usr/lib \
    && cp /usr/bin/node /stage/usr/bin/ \
    && ldd /usr/bin/node \
       | awk '/=>/ { print $3 } /^\/lib|^\/usr\/lib/ { print $1 }' \
       | grep -v 'ld-musl' \
       | sort -u \
       | xargs -I{} cp -L {} /stage/usr/lib/

# アプリの依存を入れるならここで
# COPY package*.json ./
# RUN apk add --no-cache npm && npm ci --omit=dev && cp -r node_modules /stage/app/

# **版を固定する。** `latest` は毎リリースで中身が変わります。
FROM ishinokazuki/kimigayo-os:3.0.1

LABEL maintainer="Kimigayo OS Team"
LABEL description="Node.js runtime on Kimigayo OS"
LABEL version="1.0.0"

COPY --from=builder /stage/ /

WORKDIR /app

# COPY . .

ENV NODE_ENV=production
ENV PORT=3000

EXPOSE 3000

# **root で動かさない。** Kimigayo のイメージには nobody (65534) が居ます。
USER 65534

CMD ["node", "--version"]
