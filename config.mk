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
#       used to appear only here. The artifacts did have a non-exec stack,
#       but only because lld defaults to it - not because we asked.
#       Since 2026-10-11 the three build scripts pass it explicitly.
#       Measured on the rebuilt x86_64 busybox:
#           GNU_STACK ... RW   (no E)
#           Type: DYN (Position-Independent Executable file)
#           GNU_RELRO present, BIND_NOW present
#           size unchanged at 1186 KB, 411 applets
#   REPRODUCIBLE_BUILD / SOURCE_DATE_EPOCH
#       REPRODUCIBLE_BUILD *is* set: build-system/Makefile line 51 has
#       `REPRODUCIBLE_BUILD ?= yes` and line 93 `export SOURCE_DATE_EPOCH := 0`.
#       That export does reach the build scripts (measured 2026-10-11 with
#       `make --eval='showenv: ; @echo $$SOURCE_DATE_EPOCH'` -> `0`).
#       An earlier note here, and in CLAUDE.md, wrongly said it was never set.
#   -f*-prefix-map
#       build-system/Makefile adds `-fdebug-prefix-map` to its own CFLAGS, but
#       scripts/build-{musl,busybox,openrc}.sh each do `export CFLAGS="..."`,
#       which overwrote it. As of 2026-10-11 the three scripts rebuild the
#       prefix maps themselves, gated on REPRODUCIBLE_BUILD.
#
# **Bit-for-bit reproducibility is still unverified.** Setting
# SOURCE_DATE_EPOCH and the prefix maps removes two known sources of
# nondeterminism; it does not prove there are no others. To actually claim it,
# build the same commit twice in a clean tree and compare:
#
#   for i in 1 2; do
#     rm -rf build/busybox-build-x86_64 build/busybox-install-x86_64
#     docker compose run --rm -T kimigayo-build make busybox \
#       TARGET_ARCH=x86_64 IMAGE_TYPE=standard
#     cp build/busybox-install-x86_64/bin/busybox /tmp/bb.$i
#   done
#   cmp /tmp/bb.1 /tmp/bb.2 && echo "bit-identical"
#
# Until that passes, do not advertise reproducible builds.
#
# BUSYBOX_CONFIG below is wrong: there is no src/busybox/kimigayo_defconfig.
# The real configs are src/busybox/config/{minimal,standard,extended}.config,
# selected by IMAGE_TYPE in scripts/build-busybox.sh.
#
# Wiring the *rest* of this file in would change the flags every binary is
# compiled with (note BASE_CFLAGS carries -Werror), so it needs its own change
# and its own full rebuild. Until then, do not cite config.mk as the source of
# truth for hardening flags.
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
# WRONG: this path does not exist. See the header. Kept only so that wiring
# this file in does not silently pick up a bogus default.
BUSYBOX_CONFIG := $(UTILS_SRC)/busybox/config/$(IMAGE_TYPE).config

# Build parallelism
MAKEFLAGS += -j$(shell nproc 2>/dev/null || echo 1)

# Export variables
export CC CXX LD AR AS OBJCOPY OBJDUMP STRIP RANLIB
export CFLAGS CXXFLAGS LDFLAGS INCLUDES LIBS
export ARCH CROSS_COMPILE KERNEL_ARCH
