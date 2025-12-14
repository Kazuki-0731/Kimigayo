# Kimigayo OS Build Configuration
# This file contains cross-compilation and build settings

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

# Kernel configuration
KERNEL_VERSION ?= 6.6
KERNEL_CONFIG := $(KERNEL_SRC)/config/kimigayo_$(ARCH)_defconfig

# BusyBox configuration
BUSYBOX_VERSION ?= 1.36.1
BUSYBOX_CONFIG := $(UTILS_SRC)/busybox/kimigayo_defconfig

# OpenRC configuration
OPENRC_VERSION ?= 0.52

# Package manager configuration
ISN_VERSION := $(VERSION)

# Build parallelism
MAKEFLAGS += -j$(shell nproc 2>/dev/null || echo 1)

# Export variables
export CC CXX LD AR AS OBJCOPY OBJDUMP STRIP RANLIB
export CFLAGS CXXFLAGS LDFLAGS INCLUDES LIBS
export ARCH CROSS_COMPILE KERNEL_ARCH
