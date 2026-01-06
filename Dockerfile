# Kimigayo OS Build Environment
# Alpine Linuxをベースとした軽量なビルド環境

FROM alpine:3.23

# メタデータ
LABEL maintainer="Kimigayo OS Development Team"
LABEL description="Build environment for Kimigayo OS"
LABEL version="0.1.0"

# OpenContainer Initiative (OCI) Labels
LABEL org.opencontainers.image.title="Kimigayo OS Build Environment"
LABEL org.opencontainers.image.description="Alpine Linux-based build environment for Kimigayo OS"
LABEL org.opencontainers.image.authors="Kimigayo OS Team"
LABEL org.opencontainers.image.url="https://github.com/Kazuki-0731/Kimigayo"
LABEL org.opencontainers.image.documentation="https://github.com/Kazuki-0731/Kimigayo/tree/main/docs"
LABEL org.opencontainers.image.source="https://github.com/Kazuki-0731/Kimigayo"
LABEL org.opencontainers.image.version="0.1.0"
LABEL org.opencontainers.image.licenses="GPL-2.0"
LABEL org.opencontainers.image.base.name="alpine:3.19"

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
RUN pip3 install --no-cache-dir --break-system-packages \
    hypothesis \
    pytest-cov \
    pytest-xdist \
    pyyaml

# Rustツールチェインのインストール (isn package manager用)
# Alpine 3.19のRust (1.76) は古すぎるため、rustupで最新版をインストール
RUN apk add --no-cache curl && \
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable --profile minimal && \
    . "$HOME/.cargo/env" && \
    rustup target add x86_64-unknown-linux-musl

# Rustのパスを追加
ENV PATH="/root/.cargo/bin:${PATH}"

# ARM64 クロスコンパイラのインストール
# Clangを使用したクロスコンパイル環境のセットアップ
# cmake: compiler-rtビルド用
RUN apk add --no-cache clang llvm lld compiler-rt cmake ninja

# ARM64用libgccとlinux-headersをAlpineリポジトリからダウンロード
# Alpine Linux aarch64リポジトリのlibgccとlinux-headersパッケージを取得
RUN mkdir -p /tmp/aarch64-libs
WORKDIR /tmp/aarch64-libs
RUN wget -q https://dl-cdn.alpinelinux.org/alpine/v3.23/main/aarch64/libgcc-15.2.0-r2.apk && \
    wget -q https://dl-cdn.alpinelinux.org/alpine/v3.23/main/aarch64/linux-headers-6.16.12-r0.apk && \
    tar xzf libgcc-15.2.0-r2.apk && \
    mkdir -p /usr/aarch64-linux-musl/lib && \
    cp usr/lib/libgcc_s.so.1 /usr/aarch64-linux-musl/lib/ && \
    tar xzf linux-headers-6.16.12-r0.apk && \
    mkdir -p /usr/aarch64-linux-musl/include && \
    cp -r usr/include/* /usr/aarch64-linux-musl/include/
WORKDIR /usr/aarch64-linux-musl/lib
RUN ln -s libgcc_s.so.1 libgcc_s.so
WORKDIR /
RUN rm -rf /tmp/aarch64-libs

# ARM64ターゲット用のGCCラッパースクリプトとツールチェインを作成
# musl-clangアプローチ: シンプルにターゲットとリンカのみ指定
# -fuse-ld=lld: LLVMリンカを使用
# -rtlib=compiler-rt: GCC libgccの代わりにLLVM compiler-rtを使用
# --unwindlib=none: GCC libgcc_ehの代わりにunwindライブラリなし（muslが提供）
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

# ビルドディレクトリの作成
RUN mkdir -p ${KIMIGAYO_BUILD_DIR} ${KIMIGAYO_OUTPUT_DIR}

# 作業ディレクトリの設定
WORKDIR ${KIMIGAYO_BUILD_DIR}

# ビルドスクリプトのエントリポイント
CMD ["/bin/sh"]
