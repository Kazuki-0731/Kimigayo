# Kimigayo OS + Nginx
#
# **Kimigayo にはパッケージマネージャーがありません**（設計方針）。
# `apk add` は使えないので、マルチステージビルドで Alpine 側に用意し、
# 必要なファイルだけを COPY します。
# → SPECIFICATION.md 3.5 / README.md「設計思想」

FROM alpine:3.24 AS builder

RUN apk add --no-cache nginx

# nginx 本体・モジュール・mime.types と、必要な共有ライブラリを集める。
# **ライブラリを手で列挙しないこと**（上流の更新で依存が増えると
# 実行時に `Error relocating ...: symbol not found` で落ちます）。
RUN mkdir -p /stage/usr/sbin /stage/usr/lib /stage/etc/nginx \
    && cp /usr/sbin/nginx /stage/usr/sbin/ \
    && cp -a /usr/lib/nginx /stage/usr/lib/ 2>/dev/null || true \
    && cp /etc/nginx/mime.types /stage/etc/nginx/ \
    && ldd /usr/sbin/nginx \
       | awk '/=>/ { print $3 } /^\/lib|^\/usr\/lib/ { print $1 }' \
       | grep -v 'ld-musl' \
       | sort -u \
       | xargs -I{} cp -L {} /stage/usr/lib/

# **版を固定する。** `latest` は毎リリースで中身が変わります。
FROM ishinokazuki/kimigayo-os:3.0.1

LABEL maintainer="Kimigayo OS Team"
LABEL description="Nginx web server on Kimigayo OS"
LABEL version="1.0.0"

COPY --from=builder /stage/ /

# **非 root で動かすため、nginx が書き込む場所を用意して渡す。**
# `/var/lib/nginx/logs` は nginx のコンパイル時既定の error_log の場所。
# 設定を読む前に開こうとするので、無いと起動時に alert が出る。
RUN mkdir -p /var/log/nginx /var/lib/nginx/tmp /var/lib/nginx/logs \
             /var/www/html /etc/nginx/conf.d \
    && printf '<html><body><h1>Kimigayo OS + Nginx</h1></body></html>\n' \
       > /var/www/html/index.html \
    && chown -R 65534:65534 /var/log/nginx /var/lib/nginx

COPY nginx.conf /etc/nginx/nginx.conf
COPY default.conf /etc/nginx/conf.d/default.conf

# **1024 未満のポートは非 root では bind できない**ので 8080 を使う
# （default.conf も 8080 を listen している）。
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost:8080/ || exit 1

# **root で動かさない。** Kimigayo のイメージには nobody (65534) が居ます。
USER 65534

CMD ["nginx", "-g", "daemon off;"]
