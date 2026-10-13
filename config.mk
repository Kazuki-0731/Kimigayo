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
#   kernel   scripts/build-kernel.sh  KCFLAGS + upstream defconfig hardened by
#            apply_security_hardening (scripts/config). It only reads
#            src/kernel/config/<arch>.config if it exists. No <arch>.config is
#            tracked now (the variant configs, kimigayo_*_defconfig and the
#            placeholder x86_64.config were deleted 2026-10-14), so both
#            architectures use the upstream defconfig.
#
# Consequences, measured rather than assumed:
#
#   -fPIE / -fstack-protector-strong / -D_FORTIFY_SOURCE=2
#       set directly by the three build scripts. Until 2026-10-13 the arm64
#       OpenRC build (scripts/build-openrc.sh) did not pass
#       -fstack-protector-strong, so openrc / librc / libeinfo in the published
#       v3.0.2 arm64 image have no stack protector (fixed on main).
#       -D_FORTIFY_SOURCE=2 is implemented by Alpine's fortify-headers, not
#       by musl. x86_64 gets it from the host headers; arm64 only sees our
#       own musl headers, so it had no effect there until 2026-10-14, when
#       the arm64 builds started putting /usr/include/fortify first
#       (the published v3.0.2 arm64 image is not fortified).
#       scripts/verify-image.sh checks PIE, RELRO, BIND_NOW, a non-exec
#       stack and the stack protector on every ELF in the image.
#   -Wl,-z,noexecstack
#       used to appear only here. The artifacts did have a non-exec stack,
#       but only because the linker defaulted to it - not because we asked.
#       Since 2026-10-11 the three build scripts pass it explicitly.
#       Measured 2026-10-11 on the rebuilt x86_64 busybox (static at the time;
#       BusyBox has been dynamically linked since v3.0.2, so the size differs):
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
# **Verified 2026-10-12 for the rootfs tarball only:** the same commit
# (46b05da) built independently by ci.yml and manual-build.yml produced
# standard/x86_64 tarballs with identical SHA-256. Getting there also needed
# a deterministic /.kimigayo-build-info (commit time, no hostname) and a
# normalized tar (--sort=name, --mtime, gzip -n) in the workflows.
# Docker image digests and the other variants/arches are not verified.
# To re-check a single component locally, build the same commit twice
# in a clean tree and compare:
#
#   for i in 1 2; do
#     rm -rf build/busybox-build-x86_64 build/busybox-install-x86_64
#     docker compose run --rm -T kimigayo-build make busybox \
#       TARGET_ARCH=x86_64 IMAGE_TYPE=standard
#     cp build/busybox-install-x86_64/bin/busybox /tmp/bb.$i
#   done
#   cmp /tmp/bb.1 /tmp/bb.2 && echo "bit-identical"
#
# Do not advertise more than what has been checked this way.
#
# BUSYBOX_CONFIG below is wrong: it points at src/utils/busybox/config/,
# which does not exist. The real configs are
# src/busybox/config/{minimal,standard,extended}.config, selected by
# IMAGE_TYPE in scripts/build-busybox.sh.
#
# KERNEL_CONFIG below points at src/kernel/config/kimigayo_<arch>_defconfig.
# The file was deleted (2026-10-14) and the build does not use it (see
# "kernel" above).
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
# WRONG: the defconfig file no longer exists. See the header.
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
