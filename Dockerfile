# Kimigayo OS Build Environment
# Alpine Linuxをベースとした軽量なビルド環境
#
# ALPINE_VERSION / KIMIGAYO_VERSION は versions.mk と git タグが真実の源。
# docker-compose.yml / Makefile が build arg として渡す。
# ここの既定値は compose を使わず直接 docker build したときのフォールバック。

ARG ALPINE_VERSION=3.24

FROM alpine:${ALPINE_VERSION}

# FROM をまたぐので再宣言が必要（RUN 内で使うため）
ARG ALPINE_VERSION
ARG KIMIGAYO_VERSION=dev

# メタデータ
LABEL maintainer="Kimigayo OS Development Team"
LABEL description="Build environment for Kimigayo OS"
LABEL version="${KIMIGAYO_VERSION}"

# OpenContainer Initiative (OCI) Labels
LABEL org.opencontainers.image.title="Kimigayo OS Build Environment"
LABEL org.opencontainers.image.description="Alpine Linux-based build environment for Kimigayo OS"
LABEL org.opencontainers.image.authors="Kimigayo OS Team"
LABEL org.opencontainers.image.url="https://github.com/Kazuki-0731/Kimigayo"
LABEL org.opencontainers.image.documentation="https://github.com/Kazuki-0731/Kimigayo/tree/main/docs"
LABEL org.opencontainers.image.source="https://github.com/Kazuki-0731/Kimigayo"
LABEL org.opencontainers.image.version="${KIMIGAYO_VERSION}"
LABEL org.opencontainers.image.licenses="GPL-2.0"
LABEL org.opencontainers.image.base.name="alpine:${ALPINE_VERSION}"

# 環境変数の設定
ENV KIMIGAYO_BUILD_DIR=/build
ENV KIMIGAYO_OUTPUT_DIR=/output
ENV PATH="${PATH}:/usr/local/bin"

# 必要なビルドツールと依存関係のインストール
RUN apk update && apk add --no-cache \
    # ビルドツール
    build-base \
    gcc \
    g++ \
    make \
    cmake \
    meson \
    ninja \
    autoconf \
    automake \
    libtool \
    pkgconfig \
    # musl開発ツール
    musl-dev \
    musl-utils \
    # OpenRC 0.63.2 は libcap が必須（0.52.1 の -Dcapabilities で
    # 無効化できたが、そのオプションは上流から削除された）
    libcap \
    libcap-dev \
    # カーネルビルド用
    linux-headers \
    elfutils-dev \
    ncurses-dev \
    perl \
    bison \
    flex \
    bc \
    gawk \
    diffutils \
    kmod \
    # クロスコンパイル
    binutils \
    # BusyBox
    busybox \
    # Git
    git \
    # 圧縮ツール
    gzip \
    bzip2 \
    xz \
    tar \
    cpio \
    # デバッグツール
    gdb \
    strace \
    ltrace \
    # QEMUテスト環境
    qemu-system-x86_64 \
    qemu-system-aarch64 \
    # テストフレームワーク
    python3 \
    py3-pip \
    py3-pytest \
    # セキュリティツール
    gnupg \
    openssl \
    openssl-dev \
    # ドキュメントツール
    vim \
    nano \
    curl \
    wget \
    # ファイル操作・同期ツール
    rsync \
    file \
    patch \
    # その他
    bash \
    coreutils \
    findutils \
    util-linux

# Pythonテストフレームワークのインストール
# 一覧の正本は requirements-dev.txt（Makefile / CI と同じものを入れる）
COPY requirements-dev.txt /tmp/requirements-dev.txt
RUN pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements-dev.txt && \
    rm -f /tmp/requirements-dev.txt

# ARM64 クロスコンパイラのインストール
# Clangを使用したクロスコンパイル環境のセットアップ
# cmake: compiler-rtビルド用
RUN apk add --no-cache clang llvm lld compiler-rt cmake ninja

# ARM64用libgccとlinux-headersをAlpineリポジトリから取得
#
# 以前は .apk の URL を「libgcc-15.2.0-r2.apk」のようにバージョンごと直打ちして
# いたため、Alpine を上げるたびに 404 になって壊れていた。
# apk fetch にパッケージ名だけ渡して、版はリポジトリに決めさせる。
WORKDIR /tmp/aarch64-libs
RUN apk fetch --no-cache --arch aarch64 \
        --keys-dir /usr/share/apk/keys/aarch64 \
        --repository "https://dl-cdn.alpinelinux.org/alpine/v${ALPINE_VERSION}/main" \
        libgcc linux-headers libcap libcap-dev && \
    mkdir -p /usr/aarch64-linux-musl/lib /usr/aarch64-linux-musl/include && \
    tar xzf libgcc-*.apk && \
    cp usr/lib/libgcc_s.so.1 /usr/aarch64-linux-musl/lib/ && \
    tar xzf linux-headers-*.apk && \
    cp -r usr/include/* /usr/aarch64-linux-musl/include/ && \
    for a in libcap-2*.apk libcap-dev-*.apk; do tar xzf "$a"; done && \
    cp -a usr/lib/libcap.so* usr/lib/libpsx.so* /usr/aarch64-linux-musl/lib/ 2>/dev/null || true && \
    mkdir -p /usr/aarch64-linux-musl/lib/pkgconfig && \
    cp -a usr/lib/pkgconfig/*.pc /usr/aarch64-linux-musl/lib/pkgconfig/ && \
    ln -sf libgcc_s.so.1 /usr/aarch64-linux-musl/lib/libgcc_s.so
WORKDIR /
RUN rm -rf /tmp/aarch64-libs

# ARM64ターゲット用のGCCラッパースクリプトとツールチェインを作成
# musl-clangアプローチ: シンプルな構成
# -fuse-ld=lld: LLVMリンカを使用
# -rtlib=compiler-rt: libgccではなくcompiler-rtを使用（-lgccを回避）
# --unwindlib=none: libgcc_sのunwind機能を使わない（muslに内包）
# Clangは--target=aarch64-linux-muslから自動的にmuslの規約を理解する
RUN printf '#!/bin/sh\nexec clang --target=aarch64-linux-musl -fuse-ld=lld -rtlib=compiler-rt --unwindlib=none -L/usr/aarch64-linux-musl/lib -I/usr/aarch64-linux-musl/include "$@"\n' > /usr/bin/aarch64-linux-musl-gcc && \
    chmod +x /usr/bin/aarch64-linux-musl-gcc && \
    printf '#!/bin/sh\nexec clang++ --target=aarch64-linux-musl -fuse-ld=lld -rtlib=compiler-rt --unwindlib=none -L/usr/aarch64-linux-musl/lib -I/usr/aarch64-linux-musl/include "$@"\n' > /usr/bin/aarch64-linux-musl-g++ && \
    chmod +x /usr/bin/aarch64-linux-musl-g++ && \
    printf '#!/bin/sh\nexec ld.lld "$@"\n' > /usr/bin/aarch64-linux-musl-ld && \
    chmod +x /usr/bin/aarch64-linux-musl-ld && \
    printf '#!/bin/sh\nexec clang --target=aarch64-linux-musl -c -I/usr/aarch64-linux-musl/include "$@"\n' > /usr/bin/aarch64-linux-musl-as && \
    chmod +x /usr/bin/aarch64-linux-musl-as && \
    ln -sf /usr/bin/llvm-ar /usr/bin/aarch64-linux-musl-ar && \
    ln -sf /usr/bin/llvm-ranlib /usr/bin/aarch64-linux-musl-ranlib && \
    ln -sf /usr/bin/llvm-strip /usr/bin/aarch64-linux-musl-strip && \
    ln -sf /usr/bin/llvm-nm /usr/bin/aarch64-linux-musl-nm && \
    ln -sf /usr/bin/llvm-objcopy /usr/bin/aarch64-linux-musl-objcopy && \
    ln -sf /usr/bin/llvm-objdump /usr/bin/aarch64-linux-musl-objdump

# Create empty GCC compatibility files that clang may still request
# Even with -rtlib=compiler-rt, clang may still look for these files
RUN cd /usr/aarch64-linux-musl/lib && \
    touch crtbeginT.o crtend.o && \
    ar crs libssp_nonshared.a && \
    echo "Created GCC compatibility files:" && \
    ls -lh crtbeginT.o crtend.o libssp_nonshared.a

# Download ARM64 compiler-rt from Alpine repository
#
# Alpine は実行アーキテクチャ向けの compiler-rt しか入れないため aarch64 版を手で取る。
# 配置先は clang 自身に聞く（-print-resource-dir）。
# 以前は /usr/lib/llvm21/lib/clang/21/... と LLVM のメジャー版を直書きしていたため、
# Alpine 3.24 で LLVM 21 → 22 に上がった時点でパスが存在しなくなっていた。
WORKDIR /tmp/compiler-rt-arm64
RUN apk fetch --no-cache --arch aarch64 \
        --keys-dir /usr/share/apk/keys/aarch64 \
        --repository "https://dl-cdn.alpinelinux.org/alpine/v${ALPINE_VERSION}/main" \
        compiler-rt && \
    tar xzf compiler-rt-*.apk && \
    RESOURCE_DIR="$(clang -print-resource-dir)" && \
    echo "clang resource dir: ${RESOURCE_DIR}" && \
    SRC_DIR="$(find usr -type d -name 'aarch64-alpine-linux-musl' | head -1)" && \
    test -n "$SRC_DIR" || { echo "aarch64 compiler-rt payload not found in apk"; exit 1; } && \
    mkdir -p "${RESOURCE_DIR}/lib/aarch64-alpine-linux-musl" && \
    cp -r "$SRC_DIR"/* "${RESOURCE_DIR}/lib/aarch64-alpine-linux-musl/" && \
    mkdir -p "${RESOURCE_DIR}/lib/aarch64-unknown-linux-musl" && \
    ln -sf ../aarch64-alpine-linux-musl/libclang_rt.builtins-aarch64.a \
           "${RESOURCE_DIR}/lib/aarch64-unknown-linux-musl/libclang_rt.builtins.a" && \
    echo "Created compiler-rt builtins symlink:" && \
    ls -lh "${RESOURCE_DIR}/lib/aarch64-unknown-linux-musl/libclang_rt.builtins.a" && \
    readlink -f "${RESOURCE_DIR}/lib/aarch64-unknown-linux-musl/libclang_rt.builtins.a"
WORKDIR /
RUN rm -rf /tmp/compiler-rt-arm64

# ビルドディレクトリの作成
RUN mkdir -p ${KIMIGAYO_BUILD_DIR} ${KIMIGAYO_OUTPUT_DIR}

# 作業ディレクトリの設定
WORKDIR ${KIMIGAYO_BUILD_DIR}

# ビルドスクリプトのエントリポイント
CMD ["/bin/sh"]
