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
VERSION := 0.1.0
BUILD_DATE := $(shell date -u '+%Y-%m-%d %H:%M:%S UTC')

# Build configuration
ARCH ?= x86_64
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
INIT_SRC := $(SRC_DIR)/init
PKG_SRC := $(SRC_DIR)/pkg
UTILS_SRC := $(SRC_DIR)/utils

# Cross-compilation settings
ifeq ($(ARCH),x86_64)
    CROSS_COMPILE ?= x86_64-linux-musl-
    KERNEL_ARCH := x86_64
endif
ifeq ($(ARCH),arm64)
    CROSS_COMPILE ?= aarch64-linux-musl-
    KERNEL_ARCH := arm64
endif

# Compiler and flags
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
.PHONY: all build clean help test docker-build docker-test \
        kernel musl init pkg utils rootfs iso docker-image \
        security-scan dependency-check qemu-test \
        install uninstall test-unit test-property test-integration test-musl

# Default target
all: build

help:
	@echo "Kimigayo OS Build System"
	@echo ""
	@echo "Targets:"
	@echo "  all              - Build everything (default)"
	@echo "  build            - Build OS components"
	@echo "  clean            - Remove build artifacts"
	@echo "  test             - Run all tests"
	@echo "  docker-build     - Build in Docker container"
	@echo "  iso              - Generate ISO image"
	@echo "  docker-image     - Generate Docker image"
	@echo "  security-scan    - Run security analysis"
	@echo "  qemu-test        - Test in QEMU"
	@echo ""
	@echo "Variables:"
	@echo "  ARCH             - Target architecture (x86_64, arm64)"
	@echo "  DEBUG            - Enable debug build (yes/no)"
	@echo "  V                - Verbose output (0/1)"
	@echo ""
	@echo "Examples:"
	@echo "  make build ARCH=x86_64"
	@echo "  make test V=1"
	@echo "  make iso ARCH=arm64"

# Build target
build: musl kernel busybox init pkg rootfs
	@echo ""
	@echo "=========================================="
	@echo "✅ Build completed for $(ARCH)"
	@echo "=========================================="

# musl libc build
musl:
	@echo ""
	@echo "=========================================="
	@echo "📦 [1/6] Building musl libc ($(ARCH))"
	@echo "=========================================="
	$(Q)mkdir -p $(BUILD_DIR)/musl-build-$(ARCH)
	$(Q)mkdir -p $(BUILD_DIR)/logs
	$(Q)bash $(SCRIPTS_DIR)/download-musl.sh
	$(Q)ARCH=$(ARCH) bash $(SCRIPTS_DIR)/build-musl.sh
	@echo "✅ [1/6] musl libc build completed"

# Kernel build
kernel:
	@echo ""
	@echo "=========================================="
	@echo "🐧 [2/6] Building Linux Kernel ($(ARCH))"
	@echo "=========================================="
	$(Q)mkdir -p $(BUILD_DIR)/kernel
	$(Q)mkdir -p $(BUILD_DIR)/logs
	$(Q)bash $(SCRIPTS_DIR)/download-kernel.sh
	$(Q)bash $(SCRIPTS_DIR)/apply-kernel-patches.sh
	$(Q)ARCH=$(ARCH) bash $(SCRIPTS_DIR)/build-kernel.sh
	@echo "✅ [2/6] Kernel build completed"

# BusyBox build
busybox:
	@echo ""
	@echo "=========================================="
	@echo "🔧 [3/6] Building BusyBox ($(ARCH)) - $(IMAGE_TYPE)"
	@echo "=========================================="
	$(Q)mkdir -p $(BUILD_DIR)/busybox-build-$(ARCH)
	$(Q)mkdir -p $(BUILD_DIR)/logs
	$(Q)bash $(SCRIPTS_DIR)/download-busybox.sh
	$(Q)ARCH=$(ARCH) IMAGE_TYPE=$(IMAGE_TYPE) bash $(SCRIPTS_DIR)/build-busybox.sh
	@echo "✅ [3/6] BusyBox build completed"

# Init system build (OpenRC)
init:
	@echo ""
	@echo "=========================================="
	@echo "⚙️  [4/6] Building OpenRC Init System ($(ARCH))"
	@echo "=========================================="
	$(Q)mkdir -p $(BUILD_DIR)/openrc-build-$(ARCH)
	$(Q)mkdir -p $(BUILD_DIR)/logs
	$(Q)bash $(SCRIPTS_DIR)/download-openrc.sh
	$(Q)ARCH=$(ARCH) bash $(SCRIPTS_DIR)/build-openrc.sh
	@echo "✅ [4/6] OpenRC build completed"

# Package manager build
pkg:
	@echo ""
	@echo "=========================================="
	@echo "📦 [5/6] Building Package Manager (isn)"
	@echo "=========================================="
	$(Q)mkdir -p $(BUILD_DIR)/pkg
	@echo "  Package manager build will be implemented in Phase 6"
	@echo "✅ [5/6] Package manager build completed"

# Root filesystem
rootfs:
	@echo ""
	@echo "=========================================="
	@echo "📁 [6/6] Building Root Filesystem"
	@echo "=========================================="
	$(Q)mkdir -p $(BUILD_DIR)/rootfs
	@echo "  Root filesystem creation will be implemented in Phase 3"
	@echo "✅ [6/6] Root filesystem build completed"

# ISO image generation
iso: build
	@echo "[BUILD] ISO Image"
	$(Q)mkdir -p $(OUTPUT_DIR)
	@echo "  ISO generation will be implemented in Phase 8"

# Docker image generation
docker-image: build
	@echo "[BUILD] Docker Image"
	$(Q)mkdir -p $(OUTPUT_DIR)
	@echo "  Docker image generation will be implemented in Phase 8"

# Testing
test:
	@echo "[TEST] Running tests"
	$(Q)pytest $(TESTS_DIR)/ -v

test-unit:
	@echo "[TEST] Unit tests"
	$(Q)pytest $(TESTS_DIR)/unit/ -v

test-property:
	@echo "[TEST] Property tests"
	$(Q)pytest $(TESTS_DIR)/property/ -v --hypothesis-show-statistics

test-integration:
	@echo "[TEST] Integration tests"
	$(Q)pytest $(TESTS_DIR)/integration/ -v

test-musl:
	@echo "[TEST] musl libc integration tests"
	$(Q)bash $(SCRIPTS_DIR)/test-musl-integration.sh

test-busybox:
	@echo "[TEST] BusyBox integration tests"
	$(Q)bash $(SCRIPTS_DIR)/test-busybox-integration.sh

test-openrc:
	@echo "[TEST] OpenRC integration tests"
	$(Q)bash $(SCRIPTS_DIR)/test-openrc-integration.sh

# Security
security-scan:
	@echo "[SECURITY] Running security scan"
	@echo "  Security scanning will be implemented in Phase 10"

dependency-check:
	@echo "[SECURITY] Checking dependencies"
	@echo "  Dependency check will be implemented in Phase 6"

# QEMU testing
qemu-test:
	@echo "[QEMU] Starting QEMU test"
	@echo "  QEMU testing will be implemented in Phase 4"

qemu-debug:
	@echo "[QEMU] Starting QEMU with debug options"
	@echo "  QEMU debugging will be implemented in Phase 4"

# Docker build
docker-build:
	docker-compose build

docker-test:
	docker-compose run --rm kimigayo-build make test

# Clean
clean:
	@echo "[CLEAN] Removing build artifacts"
	@echo "[INFO] Keeping downloads cache (use 'make clean-cache' to remove)"
	@echo "[CLEAN] Removing kernel build artifacts..."
	$(Q)rm -rf $(BUILD_DIR)/kernel-build-* 2>/dev/null || true
	@echo "[CLEAN] Removing musl build artifacts..."
	$(Q)rm -rf $(BUILD_DIR)/musl-build-* $(BUILD_DIR)/musl-install-* $(BUILD_DIR)/musl-tools-* 2>/dev/null || true
	@echo "[CLEAN] Removing BusyBox build artifacts..."
	$(Q)rm -rf $(BUILD_DIR)/busybox-build-* $(BUILD_DIR)/busybox-install-* 2>/dev/null || true
	@echo "[CLEAN] Removing OpenRC build artifacts..."
	$(Q)rm -rf $(BUILD_DIR)/openrc-build-* $(BUILD_DIR)/openrc-install-* 2>/dev/null || true
	@echo "[CLEAN] Removing output directory..."
	$(Q)rm -rf $(OUTPUT_DIR)/* 2>/dev/null || true
	@echo "[SUCCESS] Clean completed"

clean-all: clean
	@echo "[CLEAN] Removing all generated files"
	$(Q)docker-compose down -v
	$(Q)rm -rf $(BUILD_DIR) $(OUTPUT_DIR)

# Build information
info:
	@echo "Project: $(PROJECT_NAME)"
	@echo "Version: $(VERSION)"
	@echo "Build Date: $(BUILD_DATE)"
	@echo "Architecture: $(ARCH)"
	@echo "Cross Compiler: $(CROSS_COMPILE)"
	@echo "Security Hardening: $(SECURITY_HARDENING)"
	@echo "Reproducible Build: $(REPRODUCIBLE_BUILD)"
	@echo "Debug: $(DEBUG)"
	@echo "CFLAGS: $(CFLAGS)"
	@echo "LDFLAGS: $(LDFLAGS)"

# Version
version:
	@echo "$(VERSION)"
