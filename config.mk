# Kimigayo OS Build Configuration
# This file contains cross-compilation and build settings
#
# ============================================================================
# WARNING: nothing includes this file (verified 2026-10-11).
# ============================================================================
# Neither Makefile nor build-system/Makefile has `include config.mk`, and no
# script sources it. Every variable below is therefore inert. Treat it as the
# *intended* flag set, not as what the build uses.
#
# Where the flags actually come from:
#
#   musl     scripts/build-musl.sh    CFLAGS_SECURITY / LDFLAGS_SECURITY
#   BusyBox  scripts/build-busybox.sh CONFIG_EXTRA_CFLAGS + exported CFLAGS
#   OpenRC   scripts/build-openrc.sh  exported CFLAGS / LDFLAGS
#   kernel   scripts/build-kernel.sh  KCFLAGS + src/kernel/config/*.config
#
# Consequences, measured rather than assumed:
#
#   -fPIE / -fstack-protector-strong / -D_FORTIFY_SOURCE=2
#       applied - the three build scripts set them directly.
#       scripts/verify-image.sh checks the ELF type of every executable.
#   -Wl,-z,noexecstack
#       appears only here, yet the artifacts do have a non-exec stack
#       (GNU_STACK=RW on busybox, openrc and libc.so) because lld defaults
#       to it. Not guaranteed by us.
#   REPRODUCIBLE_BUILD / SOURCE_DATE_EPOCH / -f*-prefix-map
#       never applied. REPRODUCIBLE_BUILD is not set anywhere either, so the
#       block below could not fire even if this file were included.
#
# Wiring this file into the build scripts changes the flags every binary is
# compiled with, so it needs its own change and its own full rebuild. Until
# then, do not cite config.mk as the source of truth for hardening flags.
# ============================================================================

# Architecture-specific settings
ifeq ($(ARCH),x86_64)
    CROSS_COMPILE ?= x86_64-linux-musl-
    KERNEL_ARCH := x86_64
    KERNEL_TARGET := bzImage
    QEMU_SYSTEM := qemu-system-x86_64
    QEMU_MACHINE := pc
    QEMU_CPU := qemu64
endif

ifeq ($(ARCH),arm64)
    CROSS_COMPILE ?= aarch64-linux-musl-
    KERNEL_ARCH := arm64
    KERNEL_TARGET := Image
    QEMU_SYSTEM := qemu-system-aarch64
    QEMU_MACHINE := virt
    QEMU_CPU := cortex-a57
endif

# Toolchain
CC := $(CROSS_COMPILE)gcc
CXX := $(CROSS_COMPILE)g++
LD := $(CROSS_COMPILE)ld
AR := $(CROSS_COMPILE)ar
AS := $(CROSS_COMPILE)as
OBJCOPY := $(CROSS_COMPILE)objcopy
OBJDUMP := $(CROSS_COMPILE)objdump
STRIP := $(CROSS_COMPILE)strip
RANLIB := $(CROSS_COMPILE)ranlib

# musl libc paths
MUSL_PREFIX := /usr
MUSL_INCLUDE := $(MUSL_PREFIX)/include
MUSL_LIB := $(MUSL_PREFIX)/lib

# Build flags
BASE_CFLAGS := -Wall -Wextra -Werror -std=gnu11
BASE_CXXFLAGS := -Wall -Wextra -Werror -std=gnu++17

# Optimization flags
ifeq ($(DEBUG),yes)
    OPT_FLAGS := -O0 -g -DDEBUG
else
    OPT_FLAGS := -Os -DNDEBUG
endif

# Security hardening flags
SECURITY_CFLAGS := \
    -fPIE \
    -fstack-protector-strong \
    -D_FORTIFY_SOURCE=2 \
    -fno-strict-overflow \
    -fno-delete-null-pointer-checks

SECURITY_LDFLAGS := \
    -Wl,-z,relro \
    -Wl,-z,now \
    -Wl,-z,noexecstack \
    -pie

# Reproducible build flags
ifeq ($(REPRODUCIBLE_BUILD),yes)
    REPRODUCIBLE_FLAGS := \
        -fdebug-prefix-map=$(CURDIR)=. \
        -fmacro-prefix-map=$(CURDIR)=.
    export SOURCE_DATE_EPOCH := 0
else
    REPRODUCIBLE_FLAGS :=
endif

# Combined flags
CFLAGS := $(BASE_CFLAGS) $(OPT_FLAGS) $(SECURITY_CFLAGS) $(REPRODUCIBLE_FLAGS)
CXXFLAGS := $(BASE_CXXFLAGS) $(OPT_FLAGS) $(SECURITY_CFLAGS) $(REPRODUCIBLE_FLAGS)
LDFLAGS := $(SECURITY_LDFLAGS)

# Include paths
INCLUDES := -I$(MUSL_INCLUDE) -I$(SRC_DIR)/include

# Library paths
LIBS := -L$(MUSL_LIB)

# 構成要素のバージョンは versions.mk（単一の真実の源）で定義する。
# ここに数字を書かないこと（CLAUDE.md「バージョンの単一の真実の源」節）。
include $(dir $(lastword $(MAKEFILE_LIST)))versions.mk

# Kernel configuration
KERNEL_CONFIG := $(KERNEL_SRC)/config/kimigayo_$(ARCH)_defconfig

# BusyBox configuration
BUSYBOX_CONFIG := $(UTILS_SRC)/busybox/kimigayo_defconfig

# Build parallelism
MAKEFLAGS += -j$(shell nproc 2>/dev/null || echo 1)

# Export variables
export CC CXX LD AR AS OBJCOPY OBJDUMP STRIP RANLIB
export CFLAGS CXXFLAGS LDFLAGS INCLUDES LIBS
export ARCH CROSS_COMPILE KERNEL_ARCH
