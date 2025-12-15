#!/bin/bash
# Kimigayo OS - musl libc Build Script
# Builds musl libc with optimization and security hardening

set -e

# Configuration
MUSL_VERSION="${MUSL_VERSION:-1.2.4}"
ARCH="${ARCH:-x86_64}"
BUILD_TYPE="${BUILD_TYPE:-release}"
JOBS="${JOBS:-$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)}"

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
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $*" | tee -a "$BUILD_LOG"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*" | tee -a "$BUILD_LOG"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" | tee -a "$BUILD_LOG"
}

log_build() {
    echo -e "${CYAN}[BUILD]${NC} $*" | tee -a "$BUILD_LOG"
}

# Architecture-specific settings
setup_arch() {
    case "$ARCH" in
        x86_64)
            TARGET="x86_64-linux-musl"
            CFLAGS_ARCH="-m64"
            ;;
        arm64|aarch64)
            TARGET="aarch64-linux-musl"
            CFLAGS_ARCH=""
            # ARM64クロスコンパイラの検出
            if command -v aarch64-linux-musl-gcc &> /dev/null; then
                export CC="${CC:-aarch64-linux-musl-gcc}"
            elif command -v aarch64-alpine-linux-musl-gcc &> /dev/null; then
                export CC="${CC:-aarch64-alpine-linux-musl-gcc}"
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
    local required_tools=("make" "gcc")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_warn "$tool not found (may be required for musl build)"
        fi
    done

    log_info "Prerequisites check completed"
}

# Configure musl libc
configure_musl() {
    log_build "Configuring musl libc for $ARCH"

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
        exit 1
    }

    log_info "musl libc configuration completed"
}

# Build musl libc
build_musl() {
    log_build "Building musl libc ${MUSL_VERSION} for ${ARCH}"
    log_info "Using ${JOBS} parallel jobs"

    cd "$MUSL_BUILD_DIR" || exit 1

    # Build
    log_info "Starting musl libc compilation..."
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

    local libc_path="${MUSL_INSTALL_DIR}/lib/libc.so"

    # Check for libc.so
    if [ -f "$libc_path" ]; then
        log_info "✓ libc.so found: $libc_path"
    else
        log_error "✗ libc.so not found: $libc_path"
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
        local size=$(stat -f%z "$libc_path" 2>/dev/null || stat -c%s "$libc_path" 2>/dev/null || echo 0)
        local size_kb=$((size / 1024))
        log_info "libc.so size: ${size_kb}KB"
    fi

    # List installed files
    log_info "Installed files summary:"
    find "$MUSL_INSTALL_DIR" -type f | head -10 | while read -r file; do
        log_info "  - ${file#$MUSL_INSTALL_DIR}"
    done

    local file_count=$(find "$MUSL_INSTALL_DIR" -type f | wc -l | tr -d ' ')
    log_info "Total files installed: $file_count"

    return 0
}

# Create musl-gcc wrapper
create_musl_gcc_wrapper() {
    log_info "Creating musl-gcc wrapper"

    local wrapper_dir="${PROJECT_ROOT}/build/musl-tools-${ARCH}/bin"
    mkdir -p "$wrapper_dir"

    local musl_gcc="${wrapper_dir}/musl-gcc"

    cat > "$musl_gcc" << EOF
#!/bin/sh
exec gcc \\
    -specs "${MUSL_INSTALL_DIR}/usr/lib/musl-gcc.specs" \\
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

    if [ -f "${MUSL_INSTALL_DIR}/lib/libc.so" ]; then
        local size=$(stat -f%z "${MUSL_INSTALL_DIR}/lib/libc.so" 2>/dev/null || \
                     stat -c%s "${MUSL_INSTALL_DIR}/lib/libc.so" 2>/dev/null || echo 0)
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
    echo "" | tee -a "$BUILD_LOG"

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
}

main "$@"
