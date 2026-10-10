# Kimigayo OS + Python
#
# **Kimigayo にはパッケージマネージャーがありません**（設計方針）。
# `apk add` は使えないので、マルチステージビルドで Alpine 側に用意し、
# 必要なファイルだけを COPY します。
# → SPECIFICATION.md 3.5 / README.md「設計思想」

FROM alpine:3.24 AS builder

RUN apk add --no-cache python3

# 必要な共有ライブラリを ldd で解決して1か所に集める。
# **手で列挙しないこと**（上流の更新で依存が増えると
# `Error relocating ...: symbol not found` で落ちます）。
RUN mkdir -p /stage/usr/bin /stage/usr/lib \
    && cp -a /usr/bin/python3* /stage/usr/bin/ \
    && cp -a /usr/lib/python3* /stage/usr/lib/ \
    && ldd "$(readlink -f /usr/bin/python3)" \
       | awk '/=>/ { print $3 } /^\/lib|^\/usr\/lib/ { print $1 }' \
       | grep -v 'ld-musl' \
       | sort -u \
       | xargs -I{} cp -L {} /stage/usr/lib/

# アプリの依存を入れるならここで
# COPY requirements.txt .
# RUN apk add --no-cache py3-pip && pip install --no-cache-dir --target=/stage/app/lib -r requirements.txt

# **版を固定する。** `latest` は毎リリースで中身が変わります。
FROM ishinokazuki/kimigayo-os:3.0.1

LABEL maintainer="Kimigayo OS Team"
LABEL description="Python runtime on Kimigayo OS"
LABEL version="1.0.0"

COPY --from=builder /stage/ /

WORKDIR /app

# COPY app.py .

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# **root で動かさない。** Kimigayo のイメージには nobody (65534) が居ます。
USER 65534

CMD ["python3", "--version"]
