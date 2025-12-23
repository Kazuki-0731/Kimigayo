#!/bin/bash
# Kimigayo OS - musl libc Build Script
# Builds musl libc with optimization and security hardening

set -e
set -o pipefail

# Configuration
MUSL_VERSION="${MUSL_VERSION:-1.2.4}"
ARCH="${ARCH:-x86_64}"
BUILD_TYPE="${BUILD_TYPE:-release}"
JOBS="${JOBS:-$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)}"

# Normalize arm64 to aarch64 early (musl uses aarch64 internally)
if [ "$ARCH" = "arm64" ]; then
    ARCH="aarch64"
fi

# Directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MUSL_SRC_DIR="${PROJECT_ROOT}/build/musl-src/musl-${MUSL_VERSION}"
MUSL_BUILD_DIR="${PROJECT_ROOT}/build/musl-build-${ARCH}"
MUSL_INSTALL_DIR="${PROJECT_ROOT}/build/musl-install-${ARCH}"
BUILD_LOG="${PROJECT_ROOT}/build/logs/musl-build.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions with timestamp (JST)
log_info() {
    local timestamp
    timestamp=$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S')
    echo -e "${GREEN}[INFO] ${timestamp}${NC} $*" | tee -a "$BUILD_LOG"
}

log_warn() {
    local timestamp
    timestamp=$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S')
    echo -e "${YELLOW}[WARN] ${timestamp}${NC} $*" | tee -a "$BUILD_LOG"
}

log_error() {
    local timestamp
    timestamp=$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S')
    echo -e "${RED}[ERROR] ${timestamp}${NC} $*" | tee -a "$BUILD_LOG"
}

log_build() {
    local timestamp
    timestamp=$(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M:%S')
    echo -e "${CYAN}[BUILD] ${timestamp}${NC} $*" | tee -a "$BUILD_LOG"
}

# Architecture-specific settings
setup_arch() {
    case "$ARCH" in
        x86_64)
            TARGET="x86_64-linux-musl"
            # Alpine Linuxのgccはmusl用にビルドされており、-m64は不要
            CFLAGS_ARCH=""
            # x86_64ではシステムのツールを使用（ネイティブビルド）
            export CC="${CC:-gcc}"
            export AR="${AR:-ar}"
            export RANLIB="${RANLIB:-ranlib}"
            export STRIP="${STRIP:-strip}"
            ;;
        aarch64)
            TARGET="aarch64-linux-musl"
            CFLAGS_ARCH=""
            # ARM64クロスコンパイラの検出
            if command -v aarch64-linux-musl-gcc &> /dev/null; then
                export CC="${CC:-aarch64-linux-musl-gcc}"
                export AR="${AR:-aarch64-linux-musl-ar}"
                export RANLIB="${RANLIB:-aarch64-linux-musl-ranlib}"
                export STRIP="${STRIP:-aarch64-linux-musl-strip}"
            elif command -v aarch64-alpine-linux-musl-gcc &> /dev/null; then
                export CC="${CC:-aarch64-alpine-linux-musl-gcc}"
                export AR="${AR:-aarch64-alpine-linux-musl-ar}"
                export RANLIB="${RANLIB:-aarch64-alpine-linux-musl-ranlib}"
                export STRIP="${STRIP:-aarch64-alpine-linux-musl-strip}"
            else
                log_error "ARM64 cross-compiler not found"
                log_error "Please install aarch64-linux-musl-gcc or set CC environment variable"
                log_error "For now, skipping ARM64 build (only x86_64 is supported)"
                exit 1
            fi
            ;;
        *)
            log_error "Unsupported architecture: $ARCH"
            exit 1
            ;;
    esac

    log_info "Architecture: $ARCH"
    log_info "Target: $TARGET"
}

# Create build directories
init_build_dirs() {
    mkdir -p "$MUSL_BUILD_DIR"
    mkdir -p "$MUSL_INSTALL_DIR"
    mkdir -p "$(dirname "$BUILD_LOG")"

    log_info "Build directories initialized"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking build prerequisites"

    if [ ! -d "$MUSL_SRC_DIR" ]; then
        log_error "musl libc source not found: $MUSL_SRC_DIR"
        log_error "Please run download-musl.sh first"
        exit 1
    fi

    # Check for required tools
    local required_tools=("make")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "$tool not found (required for musl build)"
            exit 1
        fi
    done

    # Check if C compiler is available and working
    local compiler="${CC:-gcc}"
    log_info "Testing C compiler: $compiler"

    if ! command -v "$compiler" &> /dev/null; then
        log_error "C compiler not found: $compiler"
        log_error "Please install gcc or set CC environment variable"
        exit 1
    fi

    # Test if compiler can create executables
    # Use a temporary file for better compatibility with cross-compilers
    local test_file="/tmp/test_cc_$$.c"
    local test_out="/tmp/test_cc_$$"

    echo 'int main(){return 0;}' > "$test_file"

    if $compiler "$test_file" -o "$test_out" 2>/dev/null; then
        log_info "C compiler check: OK ($compiler)"
    else
        # For cross-compilers, just check if they can compile (not necessarily execute)
        if $compiler -c "$test_file" -o "${test_out}.o" 2>/dev/null; then
            log_info "C compiler check: OK ($compiler - cross-compile mode)"
        else
            log_error "C compiler cannot compile: $compiler"
            log_error "Please check your compiler installation"
            rm -f "$test_file" "$test_out" "${test_out}.o"
            exit 1
        fi
    fi

    rm -f "$test_file" "$test_out" "${test_out}.o"

    log_info "Prerequisites check completed"
}

# Configure musl libc
configure_musl() {
    log_build "Configuring musl libc for $ARCH"

    # Clean build directory to avoid stale configuration
    if [ -d "$MUSL_BUILD_DIR" ]; then
        log_info "Cleaning stale build directory"
        rm -rf "$MUSL_BUILD_DIR"
        mkdir -p "$MUSL_BUILD_DIR"
    fi

    # Clean source directory of any previous build artifacts
    log_info "Cleaning source directory of build artifacts"
    cd "$MUSL_SRC_DIR" || exit 1
    make clean 2>/dev/null || true
    find . -name "*.d" -delete 2>/dev/null || true
    find . -name "config.mak" -delete 2>/dev/null || true

    cd "$MUSL_BUILD_DIR" || exit 1

    # Security hardening flags
    local CFLAGS_SECURITY="-fPIE -fstack-protector-strong -D_FORTIFY_SOURCE=2"
    local LDFLAGS_SECURITY="-Wl,-z,relro -Wl,-z,now"

    # Optimization flags
    local CFLAGS_OPT="-Os"
    if [ "$BUILD_TYPE" = "debug" ]; then
        CFLAGS_OPT="-O0 -g"
    fi

    # Combined flags
    export CFLAGS="${CFLAGS_ARCH} ${CFLAGS_OPT} ${CFLAGS_SECURITY}"
    export LDFLAGS="${LDFLAGS_SECURITY}"

    log_info "CFLAGS: $CFLAGS"
    log_info "LDFLAGS: $LDFLAGS"

    # Unset ARCH to prevent configure from using it
    # muslのconfigureはARCH環境変数を見る可能性があるため
    local SAVED_ARCH="$ARCH"
    unset ARCH

    # Configure
    "${MUSL_SRC_DIR}/configure" \
        --prefix=/usr \
        --syslibdir=/lib \
        --target="${TARGET}" \
        --enable-static \
        --enable-shared \
        --enable-wrapper=all \
        2>&1 | tee -a "$BUILD_LOG" || {
        log_error "musl libc configuration failed"
        export ARCH="$SAVED_ARCH"
        exit 1
    }

    # Restore ARCH
    export ARCH="$SAVED_ARCH"

    log_info "musl libc configuration completed"
}

# Build musl libc
build_musl() {
    log_build "Building musl libc ${MUSL_VERSION} for ${ARCH}"
    log_info "Using ${JOBS} parallel jobs"

    cd "$MUSL_BUILD_DIR" || exit 1

    # Build
    log_info "Starting musl libc compilation..."

    # Debug: Check generated config.mak
    log_info "Debug: Content of config.mak:"
    if [ -f config.mak ]; then
        cat config.mak 2>/dev/null || echo "Cannot read config.mak"
    else
        log_warn "config.mak not found!"
    fi

    # Debug: Check generated Makefile for ARCH references
    log_info "Debug: Checking Makefile for arch/ paths..."
    if [ -f Makefile ]; then
        grep -n "arch/" Makefile 2>/dev/null | head -10 || echo "No arch/ references in Makefile"
    else
        log_warn "Makefile not found!"
    fi

    # Debug: Check what arch directory actually exists in source
    log_info "Debug: Available arch directories in source:"
    ls -la "$MUSL_SRC_DIR/arch/" 2>/dev/null | grep "^d" | awk '{print $NF}' | grep -v "^\." || echo "Cannot list arch directories"

    # Debug: Check for stale dependency files in source directory
    log_info "Debug: Checking source directory for stale files..."
    if find "$MUSL_SRC_DIR" -name "*.d" -o -name "config.mak" 2>/dev/null | grep -q .; then
        log_warn "⚠️ Found stale build files in source directory!"
        find "$MUSL_SRC_DIR" -name "*.d" -o -name "config.mak" 2>/dev/null | head -5 || true
    fi

    # Debug: Show current environment
    log_info "Debug: ARCH environment variable: ${ARCH:-<not set>}"
    log_info "Debug: Current directory: $(pwd)"

    make -j"$JOBS" 2>&1 | tee -a "$BUILD_LOG" || {
        log_error "musl libc build failed"
        exit 1
    }

    log_info "musl libc build completed successfully"
}

# Install musl libc
install_musl() {
    log_build "Installing musl libc to ${MUSL_INSTALL_DIR}"

    cd "$MUSL_BUILD_DIR" || exit 1

    # Install to custom directory
    make install DESTDIR="$MUSL_INSTALL_DIR" 2>&1 | tee -a "$BUILD_LOG" || {
        log_error "musl libc installation failed"
        exit 1
    }

    log_info "musl libc installed successfully"
}

# Verify installation
verify_installation() {
    log_info "Verifying musl libc installation"

    # muslは複数の場所にlibc.soを配置する可能性がある
    local libc_paths=(
        "${MUSL_INSTALL_DIR}/lib/libc.so"
        "${MUSL_INSTALL_DIR}/usr/lib/libc.so"
    )

    local libc_path=""
    for path in "${libc_paths[@]}"; do
        if [ -f "$path" ]; then
            libc_path="$path"
            break
        fi
    done

    # Check for libc.so
    if [ -n "$libc_path" ]; then
        log_info "✓ libc.so found: $libc_path"
    else
        log_error "✗ libc.so not found in expected locations"
        log_error "Searched paths:"
        for path in "${libc_paths[@]}"; do
            log_error "  - $path"
        done
        log_info "Installed files:"
        find "$MUSL_INSTALL_DIR" -type f | head -20
        return 1
    fi

    # Check for header files
    local include_dir="${MUSL_INSTALL_DIR}/usr/include"
    if [ -d "$include_dir" ] && [ -f "${include_dir}/stdio.h" ]; then
        log_info "✓ Header files found: $include_dir"
    else
        log_error "✗ Header files not found: $include_dir"
        return 1
    fi

    # Check library size
    if [ -f "$libc_path" ]; then
        local size
        size=$(stat -f%z "$libc_path" 2>/dev/null || stat -c%s "$libc_path" 2>/dev/null || echo 0)
        local size_kb=$((size / 1024))
        log_info "libc.so size: ${size_kb}KB"
    fi

    # List installed files
    log_info "Installed files summary:"
    # Disable pipefail temporarily to avoid SIGPIPE errors with head
    set +o pipefail
    find "$MUSL_INSTALL_DIR" -type f 2>/dev/null | head -10 | while read -r file; do
        log_info "  - ${file#$MUSL_INSTALL_DIR}"
    done

    local file_count
    file_count=$(find "$MUSL_INSTALL_DIR" -type f 2>/dev/null | wc -l | tr -d ' ')
    log_info "Total files installed: $file_count"
    set -o pipefail

    return 0
}

# Create musl-gcc wrapper
create_musl_gcc_wrapper() {
    log_info "Creating musl-gcc wrapper"

    # Check if musl-gcc.specs exists
    local specs_file="${MUSL_INSTALL_DIR}/usr/lib/musl-gcc.specs"
    if [ ! -f "$specs_file" ]; then
        log_warn "musl-gcc.specs not found at $specs_file"
        log_warn "Skipping musl-gcc wrapper creation"
        return 0
    fi

    local wrapper_dir="${PROJECT_ROOT}/build/musl-tools-${ARCH}/bin"
    mkdir -p "$wrapper_dir"

    local musl_gcc="${wrapper_dir}/musl-gcc"

    cat > "$musl_gcc" << EOF
#!/bin/sh
exec gcc \\
    -specs "${specs_file}" \\
    "\$@"
EOF

    chmod +x "$musl_gcc"

    log_info "musl-gcc wrapper created: $musl_gcc"
}

# Show build summary
show_summary() {
    log_info "Build Summary"
    log_info "============================================"
    log_info "musl libc Version: $MUSL_VERSION"
    log_info "Architecture: $ARCH"
    log_info "Build Type: $BUILD_TYPE"
    log_info "Build Jobs: $JOBS"
    log_info "============================================"
    log_info "Installation Directory: $MUSL_INSTALL_DIR"

    # Find libc.so in possible locations
    local libc_so_path=""
    for path in "${MUSL_INSTALL_DIR}/lib/libc.so" "${MUSL_INSTALL_DIR}/usr/lib/libc.so"; do
        if [ -f "$path" ]; then
            libc_so_path="$path"
            break
        fi
    done

    if [ -n "$libc_so_path" ]; then
        local size
        size=$(stat -f%z "$libc_so_path" 2>/dev/null || \
               stat -c%s "$libc_so_path" 2>/dev/null || echo 0)
        local size_kb=$((size / 1024))
        log_info "libc.so Size: ${size_kb}KB"
    fi

    log_info "Build Log: $BUILD_LOG"
    log_info "============================================"
}

# Main
main() {
    log_info "Kimigayo OS - musl libc Build Script"
    log_info "musl libc Version: ${MUSL_VERSION}"
    log_info "Target Architecture: ${ARCH}"
    log_info "Build Type: ${BUILD_TYPE}"
    log_info ""

    # Check if musl is already built and installed
    if [ -f "${MUSL_INSTALL_DIR}/lib/libc.so" ] && [ -f "${MUSL_INSTALL_DIR}/bin/musl-gcc" ]; then
        log_info "musl libc already built and installed: ${MUSL_INSTALL_DIR}"
        log_info "Skipping build (use 'make clean' to rebuild)"
        show_summary
        log_info "musl libc build check completed!"
        exit 0
    fi

    setup_arch
    init_build_dirs
    check_prerequisites
    configure_musl
    build_musl
    install_musl
    verify_installation
    create_musl_gcc_wrapper
    show_summary

    log_info "musl libc build completed successfully!"

    # Record build success
    "${PROJECT_ROOT}/scripts/build-status.sh" record musl 2>/dev/null || true
}

main "$@"
