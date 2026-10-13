# Kimigayo OS Build System
# Main Makefile

# Check if running on Linux (required for musl libc build)
UNAME_S := $(shell uname -s)
ifneq ($(UNAME_S),Linux)
    $(warning ⚠️  Warning: You are running on $(UNAME_S), not Linux)
    $(warning ⚠️  Kimigayo OS must be built in a Linux environment (Alpine Linux))
    $(warning ⚠️  Please use Docker: docker compose run --rm kimigayo-build make build)
    $(warning ⚠️  See README.md for details)
endif

# Project information
PROJECT_NAME := Kimigayo OS
# バージョンは git のリリースタグが真実の源（0.1.0 のハードコードをやめた）
VERSION := $(shell bash $(dir $(lastword $(MAKEFILE_LIST)))../scripts/get-version.sh 2>/dev/null || echo 0.0.0-unknown)
BUILD_DATE := $(shell date -u '+%Y-%m-%d %H:%M:%S UTC')

# 構成要素のバージョンの単一の真実の源
include $(dir $(lastword $(MAKEFILE_LIST)))../versions.mk

# Build configuration
#
# Legacy ARCH variable support (for backward compatibility)
#
# **アーキのマッピングより前に処理する。** 以前はマッピングの後ろで
# TARGET_ARCH := $(ARCH) としていたため、`make build ARCH=arm64` は
# info に arm64 と出しながら musl / カーネル / BusyBox を x86_64 向けに
# ビルドしていた（MUSL_ARCH などは既に x86_64 で確定済みだった）。
#
# コマンドラインで渡された ARCH だけを見る。環境変数の ARCH は
# 別の道具（カーネルの make など）向けに設定されていることがあり、
# 以前は docker-compose.yml が常に ARCH=x86_64 を入れていたため、
# 毎回この警告が出ていた。TARGET_ARCH も渡されていればそちらを優先する。
ifeq ($(origin ARCH),command line)
    $(warning Warning: ARCH variable is deprecated. Use TARGET_ARCH instead.)
    ifneq ($(origin TARGET_ARCH),command line)
        TARGET_ARCH := $(if $(filter aarch64,$(ARCH)),arm64,$(ARCH))
    endif
endif

# TARGET_ARCH: User-facing architecture name (x86_64, arm64)
TARGET_ARCH ?= x86_64

# IMAGE_TYPE: バリアント（minimal / standard / extended）。
# 既定は standard。build-busybox.sh・build-rootfs.sh の既定と揃えてある
# （以前は Makefile に既定が無く、BusyBox は standard・rootfs は minimal に
#   落ちて、standard の BusyBox を minimal として包む食い違いが起きた）。
# export して、ここから呼ぶスクリプトに同じ値が届くようにする。
IMAGE_TYPE ?= standard
export IMAGE_TYPE

# Architecture mappings for different tools
# - musl/gcc: uses aarch64 for ARM64
# - kernel: uses arm64 for ARM64
# - busybox: accepts both
ifeq ($(TARGET_ARCH),arm64)
    MUSL_ARCH := aarch64
    KERNEL_ARCH := arm64
    BUSYBOX_ARCH := arm64
    CROSS_COMPILE ?= aarch64-linux-musl-
else ifeq ($(TARGET_ARCH),x86_64)
    MUSL_ARCH := x86_64
    KERNEL_ARCH := x86_64
    BUSYBOX_ARCH := x86_64
    CROSS_COMPILE ?= x86_64-linux-musl-
else
    $(error Unsupported TARGET_ARCH: $(TARGET_ARCH). Supported: x86_64, arm64)
endif

SECURITY_HARDENING ?= full
REPRODUCIBLE_BUILD ?= yes
DEBUG ?= no
V ?= 0

# Directories
PROJECT_ROOT := $(CURDIR)/..
SRC_DIR := $(PROJECT_ROOT)/src
BUILD_DIR := $(PROJECT_ROOT)/build
OUTPUT_DIR := $(PROJECT_ROOT)/output
SCRIPTS_DIR := $(PROJECT_ROOT)/scripts
TESTS_DIR := $(PROJECT_ROOT)/tests

KERNEL_SRC := $(SRC_DIR)/kernel

# Cross-compilation settings (already defined above based on TARGET_ARCH)

# Compiler and flags
#
# ここの CC / CFLAGS / LDFLAGS は export しておらず、ビルドでは使われない
# （make info で表示するだけの参考値）。実際のフラグは
# scripts/build-{musl,busybox,openrc}.sh がそれぞれ export CFLAGS で決める。
CC := $(CROSS_COMPILE)gcc
CXX := $(CROSS_COMPILE)g++
LD := $(CROSS_COMPILE)ld
AR := $(CROSS_COMPILE)ar
STRIP := $(CROSS_COMPILE)strip

# Security hardening flags
SECURITY_CFLAGS := -fPIE -fstack-protector-strong -D_FORTIFY_SOURCE=2
SECURITY_LDFLAGS := -Wl,-z,relro -Wl,-z,now

# Base compiler flags
CFLAGS := -Wall -Wextra -Os -std=gnu11 $(SECURITY_CFLAGS)
LDFLAGS := $(SECURITY_LDFLAGS)

ifeq ($(DEBUG),yes)
    CFLAGS += -g -O0 -DDEBUG
else
    CFLAGS += -Os -DNDEBUG
endif

# Reproducible build settings
ifeq ($(REPRODUCIBLE_BUILD),yes)
    export SOURCE_DATE_EPOCH := 0
    CFLAGS += -fdebug-prefix-map=$(PROJECT_ROOT)=.
endif

# Verbose output
ifeq ($(V),1)
    Q :=
    MAKEFLAGS += --no-print-directory
else
    Q := @
    MAKEFLAGS += --silent
endif

# Phony targets
.PHONY: all build build-no-kernel clean help info status version \
        kernel musl busybox init rootfs \
        test test-unit test-musl test-busybox test-openrc \
        clean-musl clean-kernel clean-busybox clean-openrc clean-rootfs clean-output clean-all

# Default target
all: build

help:
	@echo "Kimigayo OS Build System"
	@echo ""
	@echo "Build Targets:"
	@echo "  all              - Build everything (default)"
	@echo "  build            - Build all OS components [1/4] to [4/4] (includes kernel)"
	@echo "  build-no-kernel  - Build musl, BusyBox, OpenRC and rootfs (no kernel)"
	@echo "  musl             - Build musl libc [1/4]"
	@echo "  kernel           - Build Linux kernel [2/4]"
	@echo "  busybox          - Build BusyBox [3/4]"
	@echo "  init             - Build OpenRC init system [4/4]"
	@echo "  rootfs           - Build root filesystem"
	@echo ""
	@echo "Clean Targets:"
	@echo "  clean            - Remove all build artifacts (keeps downloads)"
	@echo "  clean-musl       - Remove only musl build artifacts"
	@echo "  clean-kernel     - Remove only kernel build artifacts"
	@echo "  clean-busybox    - Remove only BusyBox build artifacts"
	@echo "  clean-openrc     - Remove only OpenRC build artifacts"
	@echo "  clean-rootfs     - Remove only rootfs build artifacts"
	@echo "  clean-output     - Remove only output directory"
	@echo "  clean-all        - clean + build/ and output/ (downloads cache is a"
	@echo "                     separate volume and is kept; host: make clean-cache)"
	@echo ""
	@echo "Test Targets:"
	@echo "  test             - Run all tests"
	@echo "  test-unit        - Run unit tests only"
	@echo "  test-musl        - Run musl libc integration script"
	@echo "  test-busybox     - Run BusyBox integration script"
	@echo "  test-openrc      - Run OpenRC integration script"
	@echo ""
	@echo "Other Targets:"
	@echo "  info             - Show build information"
	@echo "  status           - Show build status for each component"
	@echo "  version          - Show project version (git describe)"
	@echo ""
	@echo "Variables:"
	@echo "  TARGET_ARCH      - Target architecture (x86_64, arm64)"
	@echo "  IMAGE_TYPE       - Image type (minimal, standard, extended)."
	@echo "                     Default: standard (BusyBox and rootfs alike)"
	@echo "  V                - Verbose output (0/1)"
	@echo ""
	@echo "Examples:"
	@echo "  make build-no-kernel TARGET_ARCH=x86_64 IMAGE_TYPE=standard"
	@echo "  make clean-kernel && make kernel TARGET_ARCH=x86_64"
	@echo "  make test V=1"

# Build target
build: musl kernel busybox init rootfs
	@echo ""
	@echo "=========================================="
	@echo "✅ Build completed for $(TARGET_ARCH)"
	@echo "=========================================="

# カーネルを除いたビルド。
#
# Docker イメージにカーネルは入らない（コンテナはホストのカーネルで
# 動く）。カーネルをビルドするのはベアメタル／QEMU 検証のためなので、
# musl / BusyBox / OpenRC の変更を確かめたいだけならこれで足りる。
# CI（ci.yml・release.yml）は常にこちらを使う。カーネルを CI で作るのは
# manual-build.yml を build_kernel=true で回したときだけ。
build-no-kernel: musl busybox init rootfs
	@echo ""
	@echo "=========================================="
	@echo "✅ Build completed for $(TARGET_ARCH) (kernel skipped)"
	@echo "=========================================="
	@echo "   カーネルは含まれていない。ベアメタル／QEMU 検証には"
	@echo "   make build / make kernel が必要。"

# musl libc build
musl:
	@echo ""
	@echo "=========================================="
	@echo "📦 [1/4] Building musl libc ($(TARGET_ARCH))"
	@echo "=========================================="
	$(Q)mkdir -p $(BUILD_DIR)/musl-build-$(MUSL_ARCH)
	$(Q)mkdir -p $(BUILD_DIR)/logs
	$(Q)bash $(SCRIPTS_DIR)/download-musl.sh
	$(Q)ARCH=$(MUSL_ARCH) bash $(SCRIPTS_DIR)/build-musl.sh
	@echo "✅ [1/4] musl libc build completed"

# Kernel build
kernel:
	@echo ""
	@echo "=========================================="
	@echo "🐧 [2/4] Building Linux Kernel ($(TARGET_ARCH))"
	@echo "=========================================="
	$(Q)mkdir -p $(BUILD_DIR)/kernel
	$(Q)mkdir -p $(BUILD_DIR)/logs
	$(Q)bash $(SCRIPTS_DIR)/download-kernel.sh
	$(Q)bash $(SCRIPTS_DIR)/apply-kernel-patches.sh
	$(Q)ARCH=$(KERNEL_ARCH) bash $(SCRIPTS_DIR)/build-kernel.sh
	@echo "✅ [2/4] Kernel build completed"

# BusyBox build
busybox:
	@echo ""
	@echo "=========================================="
	@echo "🔧 [3/4] Building BusyBox ($(TARGET_ARCH)) - $(IMAGE_TYPE)"
	@echo "=========================================="
	$(Q)mkdir -p $(BUILD_DIR)/busybox-build-$(BUSYBOX_ARCH)
	$(Q)mkdir -p $(BUILD_DIR)/logs
	$(Q)bash $(SCRIPTS_DIR)/download-busybox.sh
	$(Q)ARCH=$(BUSYBOX_ARCH) MUSL_INSTALL_DIR=$(BUILD_DIR)/musl-install-$(MUSL_ARCH) IMAGE_TYPE=$(IMAGE_TYPE) bash $(SCRIPTS_DIR)/build-busybox.sh
	@echo "✅ [3/4] BusyBox build completed"

# Init system build (OpenRC)
init:
	@echo ""
	@echo "=========================================="
	@echo "⚙️  [4/4] Building OpenRC Init System ($(TARGET_ARCH))"
	@echo "=========================================="
	$(Q)mkdir -p $(BUILD_DIR)/openrc-build-$(TARGET_ARCH)
	$(Q)mkdir -p $(BUILD_DIR)/logs
	$(Q)bash $(SCRIPTS_DIR)/download-openrc.sh
	$(Q)ARCH=$(TARGET_ARCH) MUSL_INSTALL_DIR=$(BUILD_DIR)/musl-install-$(MUSL_ARCH) bash $(SCRIPTS_DIR)/build-openrc.sh
	@echo "✅ [4/4] OpenRC build completed"

# Root filesystem
rootfs:
	@echo ""
	@echo "=========================================="
	@echo "📁 Building Root Filesystem"
	@echo "=========================================="
	$(Q)mkdir -p $(BUILD_DIR)/rootfs
	$(Q)mkdir -p $(BUILD_DIR)/logs
	$(Q)ARCH=$(TARGET_ARCH) IMAGE_TYPE=$(IMAGE_TYPE) bash $(SCRIPTS_DIR)/build-rootfs.sh
	@echo "✅ Root filesystem build completed"

# Testing
test:
	@echo "[TEST] Running tests"
	$(Q)pytest $(TESTS_DIR)/ -v

test-unit:
	@echo "[TEST] Unit tests"
	$(Q)pytest $(TESTS_DIR)/unit/ -v

# 統合スクリプトは ARCH でインストール先を決める（musl は aarch64、
# BusyBox / OpenRC は arm64 という名前）。以前は docker-compose.yml の
# ARCH=x86_64 に頼っていたので、TARGET_ARCH=arm64 でも x86_64 を見ていた。
test-musl:
	@echo "[TEST] musl libc integration tests"
	$(Q)ARCH=$(MUSL_ARCH) bash $(SCRIPTS_DIR)/test-musl-integration.sh

test-busybox:
	@echo "[TEST] BusyBox integration tests"
	$(Q)ARCH=$(BUSYBOX_ARCH) bash $(SCRIPTS_DIR)/test-busybox-integration.sh

test-openrc:
	@echo "[TEST] OpenRC integration tests"
	$(Q)ARCH=$(TARGET_ARCH) bash $(SCRIPTS_DIR)/test-openrc-integration.sh

# 注: 以前ここにあった docker-build / docker-test は docker-compose を
# 呼んでいたが、このファイルはビルドコンテナの中で使うもので、
# コンテナには docker CLI も docker-compose も無い。ホストの Makefile の
# make docker-build / make test を使う。

# Clean targets (individual components)
clean-musl:
	@echo "[CLEAN] Removing musl build artifacts..."
	$(Q)rm -rf $(BUILD_DIR)/musl-build-* $(BUILD_DIR)/musl-install-* $(BUILD_DIR)/musl-tools-* 2>/dev/null || true
	@echo "[SUCCESS] musl clean completed"

# カーネルはソースツリーの中でビルドする（O= を使っていない）ので、
# オブジェクトは build/kernel-src/linux-<ver>/ に溜まる。展開済みの
# ソースごと消す（tarball は build/downloads/ にあり、次回は展開し直すだけ）。
# 以前は実在しない build/kernel-build-* を消していて、ソースツリーの
# .config とオブジェクトが残っていた。
clean-kernel:
	@echo "[CLEAN] Removing kernel build artifacts..."
	$(Q)rm -rf $(BUILD_DIR)/kernel-src $(BUILD_DIR)/kernel
	@echo "[SUCCESS] Kernel clean completed"

clean-busybox:
	@echo "[CLEAN] Removing BusyBox build artifacts..."
	$(Q)rm -rf $(BUILD_DIR)/busybox-build-* $(BUILD_DIR)/busybox-install-* 2>/dev/null || true
	@echo "[SUCCESS] BusyBox clean completed"

clean-openrc:
	@echo "[CLEAN] Removing OpenRC build artifacts..."
	$(Q)rm -rf $(BUILD_DIR)/openrc-build-* $(BUILD_DIR)/openrc-install-* $(BUILD_DIR)/openrc-cross-* 2>/dev/null || true
	@echo "[SUCCESS] OpenRC clean completed"

clean-rootfs:
	@echo "[CLEAN] Removing root filesystem artifacts..."
	$(Q)rm -rf $(BUILD_DIR)/rootfs 2>/dev/null || true
	@echo "[SUCCESS] Root filesystem clean completed"

clean-output:
	@echo "[CLEAN] Removing output directory..."
	$(Q)rm -rf $(OUTPUT_DIR)/* 2>/dev/null || true
	@echo "[SUCCESS] Output clean completed"

# Clean all build artifacts (keeps downloads cache)
clean: clean-musl clean-kernel clean-busybox clean-openrc clean-rootfs clean-output
	@echo "[SUCCESS] All build artifacts cleaned"

# build/ と output/ を丸ごと消す（コンテナ内用）。
#
# ダウンロードキャッシュ（build/downloads/）は docker-compose.yml で
# named volume をマウントしているので消えない（マウントポイント自体は
# rm できない）。キャッシュとビルド環境イメージを消すのはホストの
# make clean-cache / make clean-all。以前はここで docker-compose down -v を
# 呼んでいたが、コンテナに docker-compose は無く必ず失敗していた。
clean-all: clean
	@echo "[CLEAN] Removing build/ and output/ (downloads volume is kept)"
	$(Q)if [ -d $(BUILD_DIR) ]; then find $(BUILD_DIR) -mindepth 1 -maxdepth 1 ! -name downloads -exec rm -rf {} +; fi
	$(Q)rm -rf $(OUTPUT_DIR)

# Build information
info:
	@echo "Project: $(PROJECT_NAME)"
	@echo "Version: $(VERSION)"
	@echo "Build Date: $(BUILD_DATE)"
	@echo "Architecture: $(TARGET_ARCH)"
	@echo "  - musl: $(MUSL_ARCH)"
	@echo "  - kernel: $(KERNEL_ARCH)"
	@echo "  - busybox: $(BUSYBOX_ARCH)"
	@echo "Cross Compiler: $(CROSS_COMPILE)"
	@echo "Security Hardening: $(SECURITY_HARDENING)"
	@echo "Reproducible Build: $(REPRODUCIBLE_BUILD)"
	@echo "Debug: $(DEBUG)"
	@echo "CFLAGS: $(CFLAGS)"
	@echo "LDFLAGS: $(LDFLAGS)"

# Build status
status:
	@bash $(SCRIPTS_DIR)/build-status.sh show

# Version
version:
	@echo "$(VERSION)"
