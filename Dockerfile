# Kimigayo OS Build Environment
# Alpine Linuxをベースとした軽量なビルド環境

FROM alpine:3.19

# メタデータ
LABEL maintainer="Kimigayo OS Development Team"
LABEL description="Build environment for Kimigayo OS"
LABEL version="0.1.0"

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
    autoconf \
    automake \
    libtool \
    pkgconfig \
    # musl開発ツール
    musl-dev \
    musl-utils \
    # カーネルビルド用
    linux-headers \
    perl \
    bison \
    flex \
    bc \
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
    # デバッグツール
    gdb \
    strace \
    ltrace \
    # テストフレームワーク
    python3 \
    py3-pip \
    py3-pytest \
    # セキュリティツール
    gnupg \
    openssl \
    # ドキュメントツール
    vim \
    nano \
    curl \
    wget \
    # その他
    bash \
    coreutils \
    findutils

# Pythonテストフレームワークのインストール
RUN pip3 install --no-cache-dir --break-system-packages \
    hypothesis \
    pytest-cov \
    pytest-xdist \
    pyyaml

# ARM64 クロスコンパイラのインストール
# Clangを使用したクロスコンパイル環境のセットアップ
RUN apk add --no-cache clang llvm lld

# ARM64ターゲット用のGCCラッパースクリプトを作成
RUN printf '#!/bin/sh\nexec clang --target=aarch64-linux-musl -fuse-ld=lld "$@"\n' > /usr/bin/aarch64-linux-musl-gcc && \
    chmod +x /usr/bin/aarch64-linux-musl-gcc && \
    printf '#!/bin/sh\nexec clang++ --target=aarch64-linux-musl -fuse-ld=lld "$@"\n' > /usr/bin/aarch64-linux-musl-g++ && \
    chmod +x /usr/bin/aarch64-linux-musl-g++ && \
    ln -sf /usr/bin/llvm-ar /usr/bin/aarch64-linux-musl-ar && \
    ln -sf /usr/bin/llvm-ranlib /usr/bin/aarch64-linux-musl-ranlib && \
    ln -sf /usr/bin/llvm-strip /usr/bin/aarch64-linux-musl-strip

# ビルドディレクトリの作成
RUN mkdir -p ${KIMIGAYO_BUILD_DIR} ${KIMIGAYO_OUTPUT_DIR}

# 作業ディレクトリの設定
WORKDIR ${KIMIGAYO_BUILD_DIR}

# ビルドスクリプトのエントリポイント
CMD ["/bin/sh"]
