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

# ARM64用compiler-rt builtinsをビルド
# ARM64の128-bit浮動小数点演算に必要なランタイムライブラリ
RUN cd /tmp && \
    wget -q https://github.com/llvm/llvm-project/releases/download/llvmorg-21.1.2/cmake-21.1.2.src.tar.xz && \
    wget -q https://github.com/llvm/llvm-project/releases/download/llvmorg-21.1.2/compiler-rt-21.1.2.src.tar.xz && \
    tar xf cmake-21.1.2.src.tar.xz && \
    tar xf compiler-rt-21.1.2.src.tar.xz && \
    cd compiler-rt-21.1.2.src && \
    mkdir build && cd build && \
    cmake -G Ninja \
        -DCMAKE_MODULE_PATH=/tmp/cmake-21.1.2.src/Modules \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_C_COMPILER=clang \
        -DCMAKE_CXX_COMPILER=clang++ \
        -DCMAKE_C_COMPILER_TARGET=aarch64-linux-musl \
        -DCMAKE_CXX_COMPILER_TARGET=aarch64-linux-musl \
        -DCMAKE_C_FLAGS="-fPIC" \
        -DCMAKE_CXX_FLAGS="-fPIC" \
        -DCOMPILER_RT_BUILD_BUILTINS=ON \
        -DCOMPILER_RT_BUILD_SANITIZERS=OFF \
        -DCOMPILER_RT_BUILD_XRAY=OFF \
        -DCOMPILER_RT_BUILD_LIBFUZZER=OFF \
        -DCOMPILER_RT_BUILD_PROFILE=OFF \
        -DCOMPILER_RT_BUILD_MEMPROF=OFF \
        -DCOMPILER_RT_BUILD_ORC=OFF \
        -DCOMPILER_RT_DEFAULT_TARGET_ONLY=ON \
        -DCOMPILER_RT_BAREMETAL_BUILD=ON \
        ../lib/builtins && \
    ninja && \
    mkdir -p /usr/local/lib/clang/21/lib/aarch64-linux-musl && \
    cp lib/linux/libclang_rt.builtins-aarch64.a /usr/local/lib/clang/21/lib/aarch64-linux-musl/ && \
    cd / && rm -rf /tmp/cmake-21.1.2.src* /tmp/compiler-rt-21.1.2.src*

# ARM64ターゲット用のGCCラッパースクリプトを作成
RUN printf '#!/bin/sh\nexec clang --target=aarch64-linux-musl -fuse-ld=lld --rtlib=compiler-rt "$@"\n' > /usr/bin/aarch64-linux-musl-gcc && \
    chmod +x /usr/bin/aarch64-linux-musl-gcc && \
    printf '#!/bin/sh\nexec clang++ --target=aarch64-linux-musl -fuse-ld=lld --rtlib=compiler-rt "$@"\n' > /usr/bin/aarch64-linux-musl-g++ && \
    chmod +x /usr/bin/aarch64-linux-musl-g++ && \
    ln -sf /usr/bin/llvm-ar /usr/bin/aarch64-linux-musl-ar && \
    ln -sf /usr/bin/llvm-ranlib /usr/bin/aarch64-linux-musl-ranlib && \
    ln -sf /usr/bin/llvm-strip /usr/bin/aarch64-linux-musl-strip && \
    ln -sf /usr/bin/llvm-nm /usr/bin/aarch64-linux-musl-nm

# ビルドディレクトリの作成
RUN mkdir -p ${KIMIGAYO_BUILD_DIR} ${KIMIGAYO_OUTPUT_DIR}

# 作業ディレクトリの設定
WORKDIR ${KIMIGAYO_BUILD_DIR}

# ビルドスクリプトのエントリポイント
CMD ["/bin/sh"]
