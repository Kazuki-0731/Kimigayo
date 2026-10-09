#!/usr/bin/env bash
#
# OpenRC Build Script for Kimigayo OS
# Builds OpenRC init system with musl libc
#

set -euo pipefail

# Save project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# バージョンは versions.mk（単一の真実の源）から読み込む
# shellcheck source=scripts/lib/versions.sh
source "${PROJECT_ROOT}/scripts/lib/versions.sh"

# ビルド済み判定（バージョンスタンプ方式）。パスを当てに行かない理由は
# scripts/lib/build-stamp.sh の冒頭コメント参照。
# shellcheck source=scripts/lib/build-stamp.sh
source "${PROJECT_ROOT}/scripts/lib/build-stamp.sh"

# Configuration
BUILD_DIR="${BUILD_DIR:-${PROJECT_ROOT}/build}"
ARCH="${ARCH:-x86_64}"

OPENRC_SRC_DIR="${BUILD_DIR}/openrc-${OPENRC_VERSION}"
OPENRC_BUILD_DIR="${BUILD_DIR}/openrc-build-${ARCH}"
# meson のクロスファイルとコンパイララッパーの置き場所。
# ビルドディレクトリの中には置かない。meson setup の直前で
# ビルドディレクトリを作り直すため、中に置くと一緒に消えて
#   ERROR: Cannot find specified cross file: .../meson-cross-aarch64-generated.txt
# になる（2026-10-09 の CI で arm64 の3バリアントが全部これで落ちた）。
# meson のビルドディレクトリは捨てる前提の出力先なので、入力を置かない。
OPENRC_CROSS_DIR="${BUILD_DIR}/openrc-cross-${ARCH}"
OPENRC_INSTALL_DIR="${BUILD_DIR}/openrc-install-${ARCH}"

# MUSL_INSTALL_DIR can be overridden by environment variable
# This allows Makefile to pass the correct path based on MUSL_ARCH
if [ -z "${MUSL_INSTALL_DIR:-}" ]; then
    MUSL_INSTALL_DIR="${BUILD_DIR}/musl-install-${ARCH}"
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions with timestamp (JST)
log_info() {
    local timestamp
    timestamp=$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S')
    echo -e "${GREEN}[INFO] ${timestamp}${NC} $*"
}

log_success() {
    local timestamp
    timestamp=$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S')
    echo -e "${GREEN}[SUCCESS] ${timestamp}${NC} $*"
}

log_warning() {
    local timestamp
    timestamp=$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S')
    echo -e "${YELLOW}[WARNING] ${timestamp}${NC} $*"
}

log_error() {
    local timestamp
    timestamp=$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S')
    echo -e "${RED}[ERROR] ${timestamp}${NC} $*"
}

# Check if OpenRC is already built at the version we want
if kimigayo_is_built "$OPENRC_INSTALL_DIR" "$OPENRC_VERSION"; then
    log_info "OpenRC ${OPENRC_VERSION} already built and installed: ${OPENRC_INSTALL_DIR}"
    log_info "Skipping build (use 'make clean-openrc' to rebuild)"
    log_success "All essential binaries verified"
    log_info "OpenRC build check completed!"
    exit 0
fi

installed_version="$(kimigayo_built_version "$OPENRC_INSTALL_DIR")"
if [ -n "$installed_version" ]; then
    log_warning "Installed OpenRC is ${installed_version}, want ${OPENRC_VERSION} -- rebuilding"
    rm -rf "${OPENRC_INSTALL_DIR}" "${OPENRC_BUILD_DIR}"
fi

# Check if source directory exists
if [ ! -d "$OPENRC_SRC_DIR" ]; then
    log_error "OpenRC source directory not found: $OPENRC_SRC_DIR"
    log_error "Please run download-openrc.sh first"
    exit 1
fi

# Check if musl is built
if [ ! -d "$MUSL_INSTALL_DIR" ]; then
    log_error "musl libc installation not found: $MUSL_INSTALL_DIR"
    log_error "Please run build-musl.sh first"
    exit 1
fi

log_info "OpenRC Build Script"
log_info "Version: ${OPENRC_VERSION}"
log_info "Architecture: ${ARCH}"
log_info "Source directory: ${OPENRC_SRC_DIR}"
log_info "Build directory: ${OPENRC_BUILD_DIR}"
log_info "Install directory: ${OPENRC_INSTALL_DIR}"

# Create build directories
mkdir -p "$OPENRC_BUILD_DIR"
mkdir -p "$OPENRC_INSTALL_DIR"

# Architecture-specific settings
case "$ARCH" in
    x86_64)
        TARGET="x86_64-linux-musl"
        export CC="${CC:-gcc}"
        export AR="${AR:-ar}"
        export RANLIB="${RANLIB:-ranlib}"
        ;;
    arm64|aarch64)
        TARGET="aarch64-linux-musl"
        export CC="aarch64-linux-musl-gcc"
        export AR="aarch64-linux-musl-ar"
        export RANLIB="aarch64-linux-musl-ranlib"
        ;;
    *)
        log_error "Unsupported architecture: $ARCH"
        exit 1
        ;;
esac

log_info "Build configuration:"
log_info "  Target: ${TARGET}"
log_info "  CC: ${CC}"

# Check for meson and ninja
if ! command -v meson &> /dev/null; then
    log_error "meson not found. Please install meson build system."
    log_info "On Alpine: apk add meson"
    exit 1
fi

if ! command -v ninja &> /dev/null; then
    log_error "ninja not found. Please install ninja build tool."
    log_info "On Alpine: apk add ninja"
    exit 1
fi

# Set compiler flags for musl
# Alpine Linux's gcc is already configured to use musl
if [ "$ARCH" = "arm64" ] || [ "$ARCH" = "aarch64" ]; then
    # For ARM64 LLVM/Clang: use musl's strlcat (no stack protector to avoid complexity)
    export CFLAGS="-Os -D_FORTIFY_SOURCE=2 -DBRANDING='\"Kimigayo\"' -DHAVE_STRLCAT -DHAVE_STRLCPY"
    # Standard linking - let musl-clang wrapper handle the details
    export LDFLAGS="-Wl,-z,relro -Wl,-z,now"
else
    # For x86_64: use standard flags with stack protector
    export CFLAGS="-Os -fstack-protector-strong -D_FORTIFY_SOURCE=2 -DBRANDING='\"Kimigayo\"'"
    export LDFLAGS="-Wl,-z,relro -Wl,-z,now"
fi

# Configure with meson
log_info "Configuring OpenRC with meson..."

# OpenRC-specific configuration options
meson_options=(
    "--prefix=/usr"
    "--sysconfdir=/etc"
    "--libdir=/usr/lib"
    "--sbindir=/usr/sbin"
    "--libexecdir=/lib/rc"
    "--buildtype=release"
    # libcap を静的リンクする。
    # OpenRC 0.63.2 では libcap が必須（無効化オプションは上流から削除）で、
    # start-stop-daemon と supervise-daemon が libcap.so.2 にリンクする。
    # 動的のままだと rootfs に Alpine の libcap.so.2 を同梱しない限り
    # 「Error loading shared library libcap.so.2」で両方起動しない（実測）。
    # BusyBox が static-pie なのと揃え、ランタイムには musl 以外の
    # 共有ライブラリを置かない方針で静的にする。
    "--prefer-static"
    # 注: -Dos / -Dcapabilities / -Drootprefix / -Dsplit-usr / -Dtermcap は
    # OpenRC 0.52.1 以降に上流から削除された。渡すと meson setup が
    # "Unknown options" で失敗する（CLAUDE.md「版上げで実際に壊れた箇所」節）。
    "-Dpam=false"
    "-Dselinux=disabled"
    "-Daudit=disabled"
    "-Dnewnet=false"
)

# Architecture-specific Meson options
if [ "$ARCH" = "arm64" ] || [ "$ARCH" = "aarch64" ]; then
    # For ARM64: Use default settings (PIE enabled)
    # Let Clang handle everything automatically with musl target

    # Generate cross-compilation file dynamically
    mkdir -p "$OPENRC_CROSS_DIR"
    CROSS_FILE="${OPENRC_CROSS_DIR}/meson-cross-aarch64-generated.txt"
    log_info "Generating Meson cross-compilation file: $CROSS_FILE"

    # Find musl lib directory for crt*.o files
    MUSL_LIB_DIR=""
    if [ -d "${MUSL_INSTALL_DIR}/usr/lib" ]; then
        MUSL_LIB_DIR="${MUSL_INSTALL_DIR}/usr/lib"
    elif [ -d "${MUSL_INSTALL_DIR}/lib" ]; then
        MUSL_LIB_DIR="${MUSL_INSTALL_DIR}/lib"
    else
        log_error "Cannot find musl lib directory in: $MUSL_INSTALL_DIR"
        exit 1
    fi

    log_info "Using musl lib directory: $MUSL_LIB_DIR"

    # compiler-rt の builtins。
    #
    # Alpine の aarch64 版 libcap.a は outline-atomics 付きでビルドされて
    # いるため、__aarch64_swp1_acq_rel のようなヘルパを参照する
    # （compiler-rt に 253 個入っている）。
    # ラッパーは -nostdlib なので clang が builtins を自動で足さず、
    #   ld.lld: error: undefined symbol: __aarch64_swp1_acq_rel
    # になる。アーカイブの解決は順序依存なので、libcap.a より後ろ、
    # つまり meson が渡す引数（"$@"）の後ろに置く必要がある。
    RT_BUILTINS_DIR="$(clang -print-resource-dir)/lib/aarch64-unknown-linux-musl"
    if [ ! -e "${RT_BUILTINS_DIR}/libclang_rt.builtins.a" ]; then
        log_error "compiler-rt builtins not found: ${RT_BUILTINS_DIR}/libclang_rt.builtins.a"
        log_error "Dockerfile の aarch64 compiler-rt 展開が失敗している可能性がある"
        exit 1
    fi
    log_info "Using compiler-rt builtins: ${RT_BUILTINS_DIR}/libclang_rt.builtins.a"

    # Create wrapper script that uses musl's crt*.o and libs
    WRAPPER_SCRIPT="${OPENRC_CROSS_DIR}/aarch64-musl-gcc-wrapper.sh"
    cat > "$WRAPPER_SCRIPT" <<EOF
#!/bin/sh
# Wrapper to use musl's startup files instead of GCC's
# -B: Search directory for startup files (crt*.o)
# -nostdlib: Don't use standard system startup/libraries
# -lc: Explicitly link musl libc
#
# リンク時だけ compiler-rt の builtins を末尾に足す。
# -c のコンパイルにも渡すと "argument unused during compilation" が
# 出続けるので、コンパイルかリンクかを見て分ける。
for arg in "\$@"; do
    if [ "\$arg" = "-c" ]; then
        exec clang --target=aarch64-linux-musl -fuse-ld=lld \\
            -B"${MUSL_LIB_DIR}" \\
            -L"${MUSL_LIB_DIR}" \\
            -nostdlib -lc \\
            -I/usr/aarch64-linux-musl/include \\
            "\$@"
    fi
done

exec clang --target=aarch64-linux-musl -fuse-ld=lld \\
    -B"${MUSL_LIB_DIR}" \\
    -L"${MUSL_LIB_DIR}" \\
    -nostdlib -lc \\
    -I/usr/aarch64-linux-musl/include \\
    "\$@" \\
    -L"${RT_BUILTINS_DIR}" -lclang_rt.builtins
EOF
    chmod +x "$WRAPPER_SCRIPT"

    # Create cross-compilation file pointing to our wrapper
    cat > "$CROSS_FILE" <<EOF
[binaries]
c = '${WRAPPER_SCRIPT}'
cpp = '${WRAPPER_SCRIPT}'
ar = 'aarch64-linux-musl-ar'
strip = 'aarch64-linux-musl-strip'
ranlib = 'aarch64-linux-musl-ranlib'
pkgconfig = 'pkg-config'

[properties]
needs_exe_wrapper = true
# OpenRC 0.63.2 は libcap を必須で要求する。pkg-config がホスト(x86_64)の
# libcap.pc を拾わないよう、sysroot 側だけを見るようにする。
sys_root = '/usr/aarch64-linux-musl'
pkg_config_libdir = ['/usr/aarch64-linux-musl/lib/pkgconfig']

[host_machine]
system = 'linux'
cpu_family = 'aarch64'
cpu = 'aarch64'
endian = 'little'
EOF

    meson_options+=("--cross-file=$CROSS_FILE")
    log_info "Using dynamically generated cross-compilation file"
else
    # For x86_64: enable PIE and staticpic for better security
    meson_options+=("-Db_pie=true")
    meson_options+=("-Db_staticpic=true")
fi

log_info "Meson options:"
for opt in "${meson_options[@]}"; do
    log_info "  $opt"
done

# ここに来るのは「ビルドする」と決めたときだけなので、古い meson の
# ビルドディレクトリは使い回さず作り直す。
#
# 残骸を使い回すと meson が次のように拒否して止まる:
#   ERROR: Build data file '.../meson-private/build.dat' references
#   functions or classes that don't exist. This probably means that it
#   was generated with an old version of meson.
# Alpine を上げて meson のバージョンが変わると必ず踏む（実際に踏んだ）。
if [ -d "$OPENRC_BUILD_DIR" ]; then
    log_info "Removing stale meson build directory: $OPENRC_BUILD_DIR"
    rm -rf "$OPENRC_BUILD_DIR"
fi

# Setup meson build
if ! meson setup "${meson_options[@]}" "$OPENRC_BUILD_DIR" "$OPENRC_SRC_DIR"; then
    log_error "Meson configuration failed"
    exit 1
fi

log_success "OpenRC configured successfully"

# Build OpenRC
log_info "Building OpenRC..."
log_info "This may take a few minutes..."

if ! ninja -C "$OPENRC_BUILD_DIR"; then
    log_error "OpenRC build failed"
    exit 1
fi

log_success "OpenRC build completed"

# Install to staging directory
log_info "Installing OpenRC to ${OPENRC_INSTALL_DIR}..."

# Use meson install with DESTDIR (absolute path required)
OPENRC_INSTALL_DIR_ABS="$(cd "$(dirname "$OPENRC_INSTALL_DIR")" && pwd)/$(basename "$OPENRC_INSTALL_DIR")"
log_info "Absolute install path: ${OPENRC_INSTALL_DIR_ABS}"

if ! DESTDIR="$OPENRC_INSTALL_DIR_ABS" meson install -C "$OPENRC_BUILD_DIR"; then
    log_error "OpenRC installation failed"
    log_info "Trying to check meson install output..."
    meson install -C "$OPENRC_BUILD_DIR" --dry-run || true
    exit 1
fi

log_success "OpenRC installed successfully"

# Verify installation
log_info "Verifying OpenRC installation..."

# Check possible locations (bin, sbin, usr/bin, usr/sbin)
# Note: 'rc' is not a standalone binary, it's a directory (lib/rc/rc/)
essential_binaries=(
    "rc-status"
    "rc-service"
    "rc-update"
    "openrc"
    "openrc-init"
    "openrc-run"
    "openrc-shutdown"
)

all_found=true
for binary in "${essential_binaries[@]}"; do
    found=false
    location=""

    # Check multiple possible locations for binaries
    for dir in "bin" "sbin" "usr/bin" "usr/sbin"; do
        if [ -f "${OPENRC_INSTALL_DIR}/${dir}/${binary}" ]; then
            location="${dir}/${binary}"
            log_success "  ✓ ${location}"
            found=true
            break
        fi
    done

    if [ "$found" = false ]; then
        log_error "  ✗ ${binary} not found"
        all_found=false
    fi
done

if [ "$all_found" = false ]; then
    log_error "Some essential files are missing"
    log_info "Checking actual installation contents:"
    log_info "Searching for OpenRC binaries in ${OPENRC_INSTALL_DIR}..."
    find "${OPENRC_INSTALL_DIR}" -type f -name "openrc*" -o -name "rc-*" -o -name "rc" 2>/dev/null | while read -r file; do
        log_info "  Found: ${file#${OPENRC_INSTALL_DIR}/}"
    done
    log_info "Directory structure:"
    ls -la "${OPENRC_INSTALL_DIR}/" 2>/dev/null || true

    # Check all possible binary directories
    for dir in "bin" "sbin" "usr/bin" "usr/sbin"; do
        if [ -d "${OPENRC_INSTALL_DIR}/${dir}" ]; then
            log_info "Contents of ${dir}/:"
            ls -la "${OPENRC_INSTALL_DIR}/${dir}/" 2>/dev/null || true
        else
            log_info "${dir}/ does not exist"
        fi
    done

    exit 1
fi

log_success "All essential binaries verified"

# Check for init scripts directory
if [ -d "${OPENRC_INSTALL_DIR}/etc/init.d" ]; then
    init_count=$(find "${OPENRC_INSTALL_DIR}/etc/init.d" -type f 2>/dev/null | wc -l)
    log_info "Init scripts directory created with ${init_count} scripts"
else
    log_warning "Init scripts directory not created"
fi

# Check for runlevel directories
runlevels=("boot" "default" "shutdown" "sysinit")
for level in "${runlevels[@]}"; do
    if [ -d "${OPENRC_INSTALL_DIR}/etc/runlevels/${level}" ]; then
        log_success "  ✓ Runlevel: ${level}"
    else
        log_warning "  ✗ Runlevel directory missing: ${level}"
    fi
done

# Display final summary
log_success "OpenRC build completed successfully"
log_info "Build summary:"
log_info "  Version: ${OPENRC_VERSION}"
log_info "  Architecture: ${ARCH}"
log_info "  Installation directory: ${OPENRC_INSTALL_DIR}"

# List installed binaries
log_info "Installed OpenRC binaries:"
set +o pipefail
for dir in "${OPENRC_INSTALL_DIR}/sbin" "${OPENRC_INSTALL_DIR}/usr/sbin"; do
    if [ -d "$dir" ]; then
        find "$dir" -type f -o -type l 2>/dev/null | while read -r binary; do
            log_info "  - ${binary#${OPENRC_INSTALL_DIR}/}"
        done
    fi
done
set -o pipefail

# どの版をインストールしたかを残す（次回のビルド済み判定に使う）
kimigayo_write_build_stamp "$OPENRC_INSTALL_DIR" "$OPENRC_VERSION"

log_success "OpenRC is ready for integration"

# Record build success
"${PROJECT_ROOT}/scripts/build-status.sh" record openrc 2>/dev/null || true
