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

# ARM64 クロスコンパイラのインストール (musl.cc)
RUN cd /tmp && \
    echo "Downloading aarch64-linux-musl-cross toolchain..." && \
    wget --timeout=30 --tries=3 -O aarch64-linux-musl-cross.tgz https://musl.cc/aarch64-linux-musl-cross.tgz && \
    echo "Extracting toolchain..." && \
    tar -xzf aarch64-linux-musl-cross.tgz -C /opt && \
    echo "Cleaning up..." && \
    rm aarch64-linux-musl-cross.tgz && \
    echo "ARM64 cross-compiler installed successfully"

# クロスコンパイラをPATHに追加
ENV PATH="/opt/aarch64-linux-musl-cross/bin:${PATH}"

# ビルドディレクトリの作成
RUN mkdir -p ${KIMIGAYO_BUILD_DIR} ${KIMIGAYO_OUTPUT_DIR}

# 作業ディレクトリの設定
WORKDIR ${KIMIGAYO_BUILD_DIR}

# ビルドスクリプトのエントリポイント
CMD ["/bin/sh"]
