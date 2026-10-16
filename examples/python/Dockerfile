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
# python3 本体だけでなく、拡張モジュール（lib-dynload/*.so）の依存も拾う。
# 本体だけだと `import ssl` が libssl.so.3 不足で落ちる（2026-10-12 に確認）。
RUN mkdir -p /stage/usr/bin /stage/usr/lib \
    && cp -a /usr/bin/python3* /stage/usr/bin/ \
    && cp -a /usr/lib/python3* /stage/usr/lib/ \
    && for f in "$(readlink -f /usr/bin/python3)" /usr/lib/python3*/lib-dynload/*.so; do ldd "$f"; done \
       | awk '/=>/ { print $3 } /^\/lib|^\/usr\/lib/ { print $1 }' \
       | grep -v 'ld-musl' \
       | sort -u \
       | xargs -I{} cp -L {} /stage/usr/lib/

# pip は最終イメージに入らない。依存はビルドステージで入れてから COPY する
# （→ README.md「Use your own Python application」）。

# **版を固定する。** `latest` は毎リリースで中身が変わります。
FROM ishinokazuki/kimigayo-os:3.2.0

LABEL maintainer="Kimigayo OS Team"
LABEL description="Python runtime on Kimigayo OS"
LABEL version="1.0.0"

COPY --from=builder /stage/ /

WORKDIR /app

COPY app.py ./

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# BusyBox の wget は --tries を受け付けないので付けない
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -q --spider http://localhost:8000/api/health || exit 1

# **root で動かさない。** Kimigayo のイメージには nobody (65534) が居ます。
USER 65534

# `python` は無い。`python3` を使う
CMD ["python3", "app.py"]
