#!/bin/bash
# Kimigayo OS - Root Filesystem Builder
# Creates FHS-compliant directory structure and essential device nodes

set -e  # Exit on error
set -u  # Exit on undefined variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
# log_info が BLUE を使うのに定義が無く、set -u で
# "BLUE: unbound variable" になっていた（他の scripts/*.sh と同じ値を定義する）
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# バージョンとビルド済み判定（CLAUDE.md「バージョンの単一の真実の源」節）
# shellcheck source=scripts/lib/versions.sh
source "${PROJECT_ROOT}/scripts/lib/versions.sh"
# shellcheck source=scripts/lib/build-stamp.sh
source "${PROJECT_ROOT}/scripts/lib/build-stamp.sh"

# Architecture detection
detect_arch() {
    if [ -n "${ARCH:-}" ]; then
        echo "$ARCH"
        return
    fi

    local host_arch
    host_arch=$(uname -m)

    case "$host_arch" in
        x86_64|amd64)
            echo "x86_64"
            ;;
        aarch64|arm64)
            echo "arm64"
            ;;
        *)
            echo "x86_64"  # Default to x86_64
            ;;
    esac
}

# Build configuration
BUILD_DIR="${PROJECT_ROOT}/build"
ROOTFS_DIR="${BUILD_DIR}/rootfs"
ARCH="${ARCH:-$(detect_arch)}"
IMAGE_TYPE="${IMAGE_TYPE:-minimal}"

# Install directories for built components
MUSL_INSTALL_DIR="${BUILD_DIR}/musl-install-${ARCH}"
KERNEL_OUTPUT_DIR="${BUILD_DIR}/kernel/output"
BUSYBOX_INSTALL_DIR="${BUILD_DIR}/busybox-install-${ARCH}"
OPENRC_INSTALL_DIR="${BUILD_DIR}/openrc-install-${ARCH}"

# Log file
LOG_DIR="${BUILD_DIR}/logs"
LOG_FILE="${LOG_DIR}/rootfs-build.log"
mkdir -p "$LOG_DIR"

# Logging functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $*" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $*" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $*" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO:${NC} $*" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] SUCCESS:${NC} $*" | tee -a "$LOG_FILE"
}

# Create FHS-compliant directory structure
create_directory_structure() {
    log "Creating FHS-compliant directory structure..."

    # Remove old rootfs if exists
    if [ -d "$ROOTFS_DIR" ]; then
        log_warn "Removing existing rootfs directory..."
        rm -rf "$ROOTFS_DIR"
    fi

    mkdir -p "$ROOTFS_DIR"

    # Create standard FHS directories
    local dirs=(
        # Essential directories
        "bin"           # Essential command binaries
        "sbin"          # Essential system binaries
        "lib"           # Essential shared libraries
        "lib64"         # 64-bit libraries (symlink for x86_64)

        # Device and virtual filesystems
        "dev"           # Device files
        "proc"          # Process information
        "sys"           # System information
        "run"           # Runtime data

        # Configuration and variable data
        "etc"           # System configuration
        "etc/init.d"    # Init scripts
        "etc/runlevels" # OpenRC runlevels
        "etc/runlevels/boot"
        "etc/runlevels/default"
        "etc/runlevels/shutdown"
        "etc/runlevels/sysinit"
        "etc/conf.d"    # Service configuration
        "etc/network"   # Network configuration
        "var"           # Variable data
        "var/log"       # Log files
        "var/run"       # Runtime data (usually symlink to /run)
        "var/tmp"       # Temporary files
        "var/cache"     # Cache files
        "var/lib"       # State information

        # User directories
        "home"          # User home directories
        "root"          # Root user home

        # Temporary and mount points
        "tmp"           # Temporary files
        "mnt"           # Temporary mount point
        "media"         # Removable media

        # Optional directories
        "opt"           # Optional software
        "srv"           # Service data

        # User programs
        "usr"           # User hierarchy
        "usr/bin"       # User binaries
        "usr/sbin"      # System administration binaries
        "usr/lib"       # User libraries
        "usr/local"     # Local hierarchy
        "usr/local/bin"
        "usr/local/sbin"
        "usr/local/lib"
        "usr/share"     # Architecture-independent data
        "usr/share/man" # Manual pages
        "usr/include"   # C header files
    )

    for dir in "${dirs[@]}"; do
        mkdir -p "$ROOTFS_DIR/$dir"
        log_info "  Created: /$dir"
    done

    # Create symbolic links
    log "Creating symbolic links..."

    # /lib64 -> /lib (for x86_64 compatibility)
    if [ "$ARCH" = "x86_64" ]; then
        ln -sf lib "$ROOTFS_DIR/lib64"
        log_info "  Created symlink: /lib64 -> /lib"
    fi

    # /var/run -> /run
    rm -rf "$ROOTFS_DIR/var/run"
    ln -sf ../run "$ROOTFS_DIR/var/run"
    log_info "  Created symlink: /var/run -> /run"

    # /var/lock -> /run/lock
    mkdir -p "$ROOTFS_DIR/run/lock"
    ln -sf ../run/lock "$ROOTFS_DIR/var/lock"
    log_info "  Created symlink: /var/lock -> /run/lock"

    log "✅ Directory structure created successfully"
}

# Create essential device nodes
create_device_nodes() {
    log "Creating essential device nodes..."

    local dev_dir="$ROOTFS_DIR/dev"

    # Check if we have permission to create device nodes
    # In Docker or non-root environments, this might fail
    if ! touch "$dev_dir/.test" 2>/dev/null; then
        log_error "Cannot write to $dev_dir"
        return 1
    fi
    rm -f "$dev_dir/.test"

    # Note: mknod requires root privileges
    # In a Docker build environment, these will be created at runtime
    # or by the container runtime

    # Create device node creation script for later use
    cat > "$ROOTFS_DIR/sbin/create-devices" << 'EOF'
#!/bin/sh
# Create essential device nodes
# This script should be run with root privileges

# Character devices
mknod -m 666 /dev/null c 1 3 2>/dev/null || true
mknod -m 666 /dev/zero c 1 5 2>/dev/null || true
mknod -m 666 /dev/full c 1 7 2>/dev/null || true
mknod -m 666 /dev/random c 1 8 2>/dev/null || true
mknod -m 666 /dev/urandom c 1 9 2>/dev/null || true
mknod -m 666 /dev/tty c 5 0 2>/dev/null || true
mknod -m 600 /dev/console c 5 1 2>/dev/null || true

# TTY devices
for i in 0 1 2 3 4 5 6; do
    mknod -m 660 /dev/tty$i c 4 $i 2>/dev/null || true
done

# PTY master
mkdir -p /dev/pts
mknod -m 666 /dev/ptmx c 5 2 2>/dev/null || true

# Standard file descriptors
ln -sf /proc/self/fd /dev/fd 2>/dev/null || true
ln -sf /proc/self/fd/0 /dev/stdin 2>/dev/null || true
ln -sf /proc/self/fd/1 /dev/stdout 2>/dev/null || true
ln -sf /proc/self/fd/2 /dev/stderr 2>/dev/null || true

echo "Device nodes created successfully"
EOF

    chmod +x "$ROOTFS_DIR/sbin/create-devices"
    log_info "  Created device node creation script: /sbin/create-devices"

    # Create symbolic links that don't require root
    ln -sf /proc/self/fd "$dev_dir/fd" 2>/dev/null || true
    ln -sf /proc/self/fd/0 "$dev_dir/stdin" 2>/dev/null || true
    ln -sf /proc/self/fd/1 "$dev_dir/stdout" 2>/dev/null || true
    ln -sf /proc/self/fd/2 "$dev_dir/stderr" 2>/dev/null || true

    # Create pts directory for pseudo-terminals
    mkdir -p "$dev_dir/pts"
    mkdir -p "$dev_dir/shm"

    log "✅ Device node preparation completed"
}

# Set proper permissions
set_permissions() {
    log "Setting proper file permissions..."

    # Set standard directory permissions
    chmod 755 "$ROOTFS_DIR"
    chmod 755 "$ROOTFS_DIR/bin"
    chmod 755 "$ROOTFS_DIR/sbin"
    chmod 755 "$ROOTFS_DIR/usr"
    chmod 755 "$ROOTFS_DIR/usr/bin"
    chmod 755 "$ROOTFS_DIR/usr/sbin"
    chmod 755 "$ROOTFS_DIR/etc"

    # Secure directories
    chmod 700 "$ROOTFS_DIR/root"  # Root home directory
    chmod 1777 "$ROOTFS_DIR/tmp"  # Sticky bit for tmp
    chmod 755 "$ROOTFS_DIR/var"
    chmod 1777 "$ROOTFS_DIR/var/tmp"  # Sticky bit for tmp

    # Runtime and device directories
    chmod 755 "$ROOTFS_DIR/dev"
    chmod 755 "$ROOTFS_DIR/run"

    log "✅ Permissions set successfully"
}

# Optimize rootfs size
optimize_rootfs() {
    log ""
    log "=========================================="
    log "🔧 Optimizing rootfs size..."
    log "=========================================="

    local size_before
    size_before=$(du -sh "$ROOTFS_DIR" | awk '{print $1}')
    log_info "Size before optimization: $size_before"

    # 1. Strip all binaries and shared libraries
    log_info "Step 1: Stripping binaries and libraries..."
    local stripped_count=0

    # Temporarily disable exit on error for strip commands
    set +e

    # Strip all ELF binaries
    while IFS= read -r file; do
        if file "$file" 2>/dev/null | grep -q "not stripped"; then
            if strip --strip-all "$file" 2>/dev/null; then
                stripped_count=$((stripped_count + 1))
            fi
        fi
    done < <(find "$ROOTFS_DIR" -type f -executable 2>/dev/null)

    # Strip shared libraries
    while IFS= read -r file; do
        if file "$file" 2>/dev/null | grep -q "not stripped"; then
            if strip --strip-unneeded "$file" 2>/dev/null; then
                stripped_count=$((stripped_count + 1))
            fi
        fi
    done < <(find "$ROOTFS_DIR" -type f -name "*.so*" 2>/dev/null)

    # Re-enable exit on error
    set -e

    log_success "  ✓ Stripped binaries and libraries"

    # 2. Remove unnecessary files
    log_info "Step 2: Removing unnecessary files..."
    local removed_count=0

    # Remove man pages (documentation not needed in minimal OS)
    if [ -d "$ROOTFS_DIR/usr/share/man" ]; then
        rm -rf "$ROOTFS_DIR/usr/share/man"
        log_success "  ✓ Removed man pages"
        removed_count=$((removed_count + 1))
    fi

    # Remove example init scripts (not needed in production)
    if [ -d "$ROOTFS_DIR/usr/share/openrc/support/init.d.examples" ]; then
        rm -rf "$ROOTFS_DIR/usr/share/openrc/support/init.d.examples"
        log_success "  ✓ Removed example init scripts"
        removed_count=$((removed_count + 1))
    fi

    # Remove static libraries (.a files) if any
    local a_files
    a_files=$(find "$ROOTFS_DIR" -type f -name "*.a" 2>/dev/null | wc -l)
    if [ "$a_files" -gt 0 ]; then
        find "$ROOTFS_DIR" -type f -name "*.a" -delete 2>/dev/null || true
        removed_count=$((removed_count + a_files))
    fi

    # Remove libtool archives (.la files) if any
    local la_files
    la_files=$(find "$ROOTFS_DIR" -type f -name "*.la" 2>/dev/null | wc -l)
    if [ "$la_files" -gt 0 ]; then
        find "$ROOTFS_DIR" -type f -name "*.la" -delete 2>/dev/null || true
        removed_count=$((removed_count + la_files))
    fi

    if [ $removed_count -gt 0 ]; then
        log_success "  ✓ Removed $removed_count unnecessary files/directories"
    else
        log_info "  ✓ No unnecessary files found"
    fi

    # 3. Create symbolic links for duplicate OpenRC binaries
    log_info "Step 3: Creating symbolic links for duplicate binaries..."
    local symlink_count=0

    # Many einfo-related binaries are hardlinks to the same binary
    # Convert them to symlinks to save space
    if [ -d "$ROOTFS_DIR/lib/rc/rc/bin" ]; then
        local einfo_bins=(ebegin eend eerror eerrorn eindent einfo einfon eoutdent ewarn ewarnn ewend)
        local base_bin="$ROOTFS_DIR/lib/rc/rc/bin/einfo"

        if [ -f "$base_bin" ]; then
            for bin in "${einfo_bins[@]}"; do
                local target="$ROOTFS_DIR/lib/rc/rc/bin/$bin"
                if [ -f "$target" ] && [ "$target" != "$base_bin" ]; then
                    # Check if they are identical
                    if cmp -s "$base_bin" "$target"; then
                        rm -f "$target"
                        ln -s "einfo" "$target"
                        symlink_count=$((symlink_count + 1))
                    fi
                fi
            done
        fi
    fi

    if [ $symlink_count -gt 0 ]; then
        log_success "  ✓ Created $symlink_count symbolic links"
    else
        log_info "  ✓ No duplicate binaries found"
    fi

    # 4. Compress compressible files
    log_info "Step 4: Compressing configuration files..."
    local compressed_count=0

    # Temporarily disable exit on error for compression
    set +e

    # Compress large text files (> 1KB) in /usr/share
    if [ -d "$ROOTFS_DIR/usr/share" ]; then
        while IFS= read -r file; do
            if file "$file" 2>/dev/null | grep -q "text"; then
                if gzip -9 "$file" 2>/dev/null; then
                    compressed_count=$((compressed_count + 1))
                fi
            fi
        done < <(find "$ROOTFS_DIR/usr/share" -type f -size +1k 2>/dev/null)
    fi

    # Re-enable exit on error
    set -e

    if [ -d "$ROOTFS_DIR/usr/share" ]; then
        local gz_files
        gz_files=$(find "$ROOTFS_DIR/usr/share" -type f -name "*.gz" 2>/dev/null | wc -l)
        if [ "$gz_files" -gt 0 ]; then
            log_success "  ✓ Compressed $gz_files files"
        else
            log_info "  ✓ No large text files to compress"
        fi
    else
        log_info "  ✓ No large text files to compress"
    fi

    # Clean up empty directories
    # ただし FHS の骨格は「空であることが正しい」ので消してはいけない。
    # 2026-10-09 までこの find が無条件だったため、
    # create_directory_structure が作った /tmp・/run・/var/log などが
    # 全リリースイメージ（v0.1.0〜v2.0.1）から欠落していた。
    # /run が無いと OpenRC が state を書けず、/var/lock -> ../run/lock も
    # 宛先の無いリンクになる。/tmp が無いと多くのソフトウェアが動かない。
    # 空ディレクトリは tar/イメージのサイズをほぼ増やさないので残して問題ない。
    local keep_dirs=(
        "tmp" "var/tmp" "var/log" "var/cache" "var/lib"
        "run" "run/lock"
        "dev" "proc" "sys"
        "home" "root" "mnt" "media" "opt" "srv"
        "usr/local/bin" "usr/local/sbin" "usr/local/lib"
    )
    local find_args=( "$ROOTFS_DIR" -mindepth 1 -type d -empty )
    local keep
    for keep in "${keep_dirs[@]}"; do
        find_args+=( ! -path "$ROOTFS_DIR/$keep" )
    done
    find "${find_args[@]}" -delete 2>/dev/null || true

    local size_after
    size_after=$(du -sh "$ROOTFS_DIR" | awk '{print $1}')
    log_info "Size after optimization: $size_after"

    log ""
    log "=========================================="
    log "✅ Rootfs optimization completed!"
    log "=========================================="
    log_success "Summary:"
    log_success "  - Stripped binaries/libraries: $stripped_count"
    log_success "  - Removed files: $removed_count"
    log_success "  - Created symlinks: $symlink_count"
    log_success "  - Compressed files: $compressed_count"
    log_success "  - Size: $size_before → $size_after"
    log ""
}

# シンボリックリンクを張り替えてコピーする
#
# BusyBox のアプレットは先に /bin/busybox への相対シンボリックリンクとして
# 置かれる。そこへ同名の実バイナリを cp すると、cp はリンクを張り替えずに
# **リンク先へ書き込む**ため /bin/busybox 本体が壊れる。
# 実測（2026-10-09）: OpenRC の usr/sbin をコピーしただけで
# /sbin/start-stop-daemon -> ../bin/busybox 経由で 1.1MB の busybox が
# 57.8KB の start-stop-daemon に化け、全アプレットが死んだ。
# GNU の cp --remove-destination は BusyBox cp に無いので使わない。
copy_over() {
    local src_dir="$1" dest_dir="$2"
    [ -d "$src_dir" ] || return 0
    mkdir -p "$dest_dir"

    local src name
    for src in "$src_dir"/*; do
        [ -e "$src" ] || [ -L "$src" ] || continue
        name="$(basename "$src")"
        if [ -d "$src" ] && [ ! -L "$src" ]; then
            copy_over "$src" "$dest_dir/$name"
        else
            rm -f "$dest_dir/$name"
            cp -a "$src" "$dest_dir/$name"
        fi
    done
}

# Copy built components to rootfs
copy_components() {
    log "Copying built components to rootfs..."

    # Copy musl libc
    if [ -d "$MUSL_INSTALL_DIR" ]; then
        log_info "Copying musl libc..."

        # Copy libraries
        if [ -d "$MUSL_INSTALL_DIR/lib" ]; then
            cp -a "$MUSL_INSTALL_DIR/lib"/* "$ROOTFS_DIR/lib/" 2>/dev/null || true
            log_info "  ✓ musl libraries copied"
        fi

        # 共有ライブラリ本体は usr/lib に入る。
        # musl 自身が作る /lib/ld-musl-<arch>.so.1 は /usr/lib/libc.so を指す
        # 絶対シンボリックリンクなので、これを入れないとリンク切れになり、
        # 動的リンクされたバイナリが一切起動しない（README の
        # 「自分のアプリを COPY する」使い方と OpenRC が壊れる）。
        # BusyBox は static-pie なので、入れ忘れても smoke テストは通ってしまう。
        if [ -f "$MUSL_INSTALL_DIR/usr/lib/libc.so" ]; then
            mkdir -p "$ROOTFS_DIR/usr/lib"
            cp -a "$MUSL_INSTALL_DIR/usr/lib/libc.so" "$ROOTFS_DIR/usr/lib/"
            log_info "  ✓ musl libc.so copied"
        else
            log_warn "  musl libc.so not found: $MUSL_INSTALL_DIR/usr/lib/libc.so"
        fi

        # 静的ライブラリ（libc.a 2.5MB）・CRT オブジェクト・musl-gcc・
        # ヘッダ（usr/include）はビルド時にだけ必要なので入れない。
        # ここには以前 "$MUSL_INSTALL_DIR/include" を見るヘッダのコピーが
        # あったが、musl は usr/include に入れるため条件が常に偽で、
        # v0.1.0 以降どの版でもヘッダは入っていなかった。
    else
        log_warn "musl installation directory not found: $MUSL_INSTALL_DIR"
    fi

    # カーネルとモジュール（ビルドされていれば）
    #
    # **Docker イメージにカーネルは入らない。** コンテナはホストの
    # カーネルで動くので、ここでコピーするのはベアメタル／QEMU 検証用の
    # rootfs を作るときのためだけ。カーネルが無くても警告で済ませる。
    #
    # パスは build-kernel.sh の出力に合わせる。
    # 2026-10-09 まで boot/vmlinuz と lib/modules を探していたが、
    # build-kernel.sh が実際に置くのは
    #   $KERNEL_OUTPUT_DIR/vmlinuz-<version>-<arch>
    #   $KERNEL_OUTPUT_DIR/modules/lib/modules/<version>/
    # で、**一度も噛み合っていなかった**（コンテナ向けには無害だが、
    # ベアメタル用の rootfs を作ると静かにカーネル無しになる）。
    # **カーネルとモジュールは必ず arch と版で絞る。**
    # build/kernel/output/ には前のビルドの成果物が残る。絞らないと
    # 別アーキ・別版のものが入る。2026-10-09 に実際に踏んで、
    # arm64 の rootfs に x86_64 / 6.6.11 のモジュール 232KB が
    # 入っていた（minimal のイメージが standard より大きいという
    # 不自然さから気づいた）。
    #
    # モジュールのコピーはカーネル本体が見つかったときだけ行う。
    # コンテナ向けの成果物にモジュールだけ入っても意味がなく、
    # 「カーネルは無いのにモジュールはある」状態は紛らわしい。
    local kernel_image="${KERNEL_OUTPUT_DIR}/vmlinuz-${KERNEL_VERSION}-${ARCH}"
    if [ -f "$kernel_image" ]; then
        mkdir -p "$ROOTFS_DIR/boot"
        cp -a "$kernel_image" "$ROOTFS_DIR/boot/"
        ln -sf "vmlinuz-${KERNEL_VERSION}-${ARCH}" "$ROOTFS_DIR/boot/vmlinuz"
        log_info "  ✓ Kernel copied: boot/$(basename "$kernel_image")"

        # modules_install は INSTALL_MOD_PATH=$KERNEL_OUTPUT_DIR/modules なので
        # 実体は modules/lib/modules/<version>/ に入る。
        # ディレクトリ名は KERNEL_VERSION そのままなので一致で絞れる。
        local mod_src="${KERNEL_OUTPUT_DIR}/modules/lib/modules/${KERNEL_VERSION}"
        if [ -d "$mod_src" ]; then
            mkdir -p "$ROOTFS_DIR/lib/modules"
            cp -a "$mod_src" "$ROOTFS_DIR/lib/modules/"
            log_info "  ✓ Kernel modules copied: lib/modules/${KERNEL_VERSION}"
        else
            log_info "  カーネルモジュールなし: $mod_src"
        fi
    else
        log_info "  カーネルは未ビルド（コンテナ向けには不要）: $(basename "$kernel_image")"
    fi

    # Copy BusyBox
    if [ -d "$BUSYBOX_INSTALL_DIR" ]; then
        log_info "Copying BusyBox..."

        # Copy all BusyBox files
        if [ -d "$BUSYBOX_INSTALL_DIR/bin" ]; then
            cp -a "$BUSYBOX_INSTALL_DIR/bin"/* "$ROOTFS_DIR/bin/" 2>/dev/null || true
        fi
        if [ -d "$BUSYBOX_INSTALL_DIR/sbin" ]; then
            cp -a "$BUSYBOX_INSTALL_DIR/sbin"/* "$ROOTFS_DIR/sbin/" 2>/dev/null || true
        fi
        if [ -d "$BUSYBOX_INSTALL_DIR/usr/bin" ]; then
            cp -a "$BUSYBOX_INSTALL_DIR/usr/bin"/* "$ROOTFS_DIR/usr/bin/" 2>/dev/null || true
        fi
        if [ -d "$BUSYBOX_INSTALL_DIR/usr/sbin" ]; then
            cp -a "$BUSYBOX_INSTALL_DIR/usr/sbin"/* "$ROOTFS_DIR/usr/sbin/" 2>/dev/null || true
        fi

        log_info "  ✓ BusyBox copied"
    else
        log_warn "BusyBox installation directory not found: $BUSYBOX_INSTALL_DIR"
    fi

    # Copy OpenRC
    if [ -d "$OPENRC_INSTALL_DIR" ]; then
        log_info "Copying OpenRC init system..."

        # Copy binaries
        # BusyBox のアプレットと同名のものがあるため copy_over を使う
        # （start-stop-daemon が衝突する。OpenRC の実装を優先する）
        copy_over "$OPENRC_INSTALL_DIR/bin" "$ROOTFS_DIR/bin"
        copy_over "$OPENRC_INSTALL_DIR/sbin" "$ROOTFS_DIR/sbin"

        # 実行ファイル本体（openrc / openrc-run / rc-update / start-stop-daemon 等
        # 9 個）は usr/sbin に入る。prefix が /usr なので sbin/ には何も無く、
        # ここを漏らしていたため OpenRC のバイナリが 1 つもイメージに入らないまま
        # 「✓ OpenRC copied」と報告していた。
        # create_config_files が作る inittab と configs/openrc/ は /sbin/openrc を
        # 参照しているので、Alpine と同じく /sbin に置く。
        copy_over "$OPENRC_INSTALL_DIR/usr/sbin" "$ROOTFS_DIR/sbin"

        # **/usr/sbin にも同じ名前で引けるようにする。**
        #
        # OpenRC の prefix は /usr なので、install される init スクリプトの
        # shebang は #!/usr/sbin/openrc-run になっている。/sbin に移すだけだと
        # 37 本のうち 36 本が
        #   unable to exec `/etc/init.d/sysctl': No such file or directory
        # で**1つも起動できない**（ファイルはあるので存在チェックでは通る。
        # ENOENT は shebang の指す先が無いことを意味する）。
        #
        # 2026-10-09 に実測。`openrc default` を走らせて初めて分かった。
        # rc-update show も verify-image.sh も init スクリプトを exec しない
        # ので、それまで気づけなかった。
        #
        # シンボリックリンクなのでサイズはほぼ増えない。
        if [ -d "$OPENRC_INSTALL_DIR/usr/sbin" ]; then
            mkdir -p "$ROOTFS_DIR/usr/sbin"
            local orc_bin
            for orc_bin in "$OPENRC_INSTALL_DIR/usr/sbin"/*; do
                [ -e "$orc_bin" ] || continue
                orc_bin="$(basename "$orc_bin")"
                ln -sfn "../../sbin/${orc_bin}" "$ROOTFS_DIR/usr/sbin/${orc_bin}"
            done
            log_info "  ✓ OpenRC binaries linked into /usr/sbin (init スクリプトの shebang 用)"
        fi

        # Copy libraries
        copy_over "$OPENRC_INSTALL_DIR/lib" "$ROOTFS_DIR/lib"

        # 共有ライブラリ（librc.so.1 / libeinfo.so.1）も usr/lib に入る。
        # musl の既定探索パスは /lib:/usr/local/lib:/usr/lib なので /lib で解決する。
        # pkgconfig と usr/include はビルド時専用なので入れない。
        if [ -d "$OPENRC_INSTALL_DIR/usr/lib" ]; then
            find "$OPENRC_INSTALL_DIR/usr/lib" -maxdepth 1 -name 'lib*.so*' \
                -exec cp -a {} "$ROOTFS_DIR/lib/" \; 2>/dev/null || true
        fi

        # Copy init scripts and configuration
        copy_over "$OPENRC_INSTALL_DIR/etc" "$ROOTFS_DIR/etc"

        # Copy shared data
        copy_over "$OPENRC_INSTALL_DIR/usr/share" "$ROOTFS_DIR/usr/share"

        log_info "  ✓ OpenRC copied"

        patch_openrc_for_busybox || return 1
    else
        log_warn "OpenRC installation directory not found: $OPENRC_INSTALL_DIR"
    fi

    # Package manager removed - Kimigayo OS follows distroless approach

    log "✅ Components copied successfully"
}

# Create essential configuration files
# ---------------------------------------------------------------------------
# OpenRC の init スクリプトを BusyBox の userland に合わせる
#
# なぜ必要か（2026-10-10 に `openrc boot` を実走させて発覚）:
#   OpenRC の上流 init スクリプトは GNU procps / coreutils / kmod を前提に
#   長オプションを使う。Kimigayo の userland は BusyBox だけなので、
#   対応していないオプションはその場で usage を吐いて失敗する。
#   実測では `sysctl` が毎回 ERROR になっていた:
#       /sbin/sysctl: unrecognized option: system
#       * ERROR: sysctl failed to start
#   rc-update show も `<script> describe` も start() を呼ばないので、
#   既存の検査では一切検知できなかった。
#
# 直す対象は「Docker で実際に走るもの」だけに絞る。
# root / fsck / hwclock / modules / localmount / swap / procfs は
# depend() に `keyword -docker` が付いており**コンテナでは実行されない**
# （実測で確認）。Kimigayo はコンテナ向け OS なので触らない。
#
# 置換前の文字列が消えていたら**ビルドを止める**。OpenRC を上げて上流が
# 書き換えたときに「当てたつもり」で進まないため。
# ---------------------------------------------------------------------------
replace_line_in_file() {
    local file="$1" needle="$2" replacement="$3" n

    if [ ! -f "$file" ]; then
        log_error "Not found: $file"
        return 1
    fi
    n="$(grep -cF -- "$needle" "$file" || true)"
    if [ "$n" != "1" ]; then
        log_error "Expected exactly 1 occurrence of the following in ${file}, got ${n}:"
        log_error "    $needle"
        log_error "  OpenRC ${OPENRC_VERSION} の上流が書き換えた可能性があります。"
        log_error "  該当スクリプトを読み直して、この置換を作り直してください。"
        return 1
    fi
    # **置換は index()/substr() で行う。`sub()` は使えない。**
    # awk の sub() は第1引数を**正規表現**として解釈するため、
    # `sysctl ${quiet} --system` のような `$` `{` `}` を含む文字列は
    # マッチしない。sub() で書いたときは置換が1件も起きないのに
    # 「✓ 置き換えた」と報告していた（2026-10-10）。
    #
    # **`mv` ではなく `cat >` で書き戻す。**
    # mv は awk が作った新ファイル（0644）で元を置き換えるため、
    # init スクリプトの実行権限が落ちる。実際に sysctl と bootmisc が
    # 0644 になり、OpenRC から起動されなくなった（同日）。
    awk -v needle="$needle" -v repl="$replacement" '
        {
            i = index($0, needle)
            if (i > 0) {
                print substr($0, 1, i - 1) repl substr($0, i + length(needle))
                next
            }
            print
        }
    ' "$file" > "${file}.new" || return 1
    cat "${file}.new" > "$file" && rm -f "${file}.new"

    # **置換後に消えたことを確かめる。** 「当てたつもり」で進まないため。
    if grep -qF -- "$needle" "$file"; then
        log_error "Replacement did not take effect in ${file}:"
        log_error "    $needle"
        return 1
    fi
}

patch_openrc_for_busybox() {
    local initd="$ROOTFS_DIR/etc/init.d"
    [ -d "$initd" ] || return 0

    log_info "Adapting OpenRC init scripts to the BusyBox userland..."

    # --- sysctl: BusyBox には --system が無い ---------------------------------
    #
    # procps の `sysctl --system` は複数のディレクトリから *.conf を読む。
    # BusyBox の `-p` は複数ファイルを取れるので、読む場所を自分で並べて渡す。
    # （同名ファイルのディレクトリ間シャドウイングまでは再現しない。
    #   Kimigayo が置くのは /etc/sysctl.d/99-kimigayo-performance.conf だけ）
    if [ -f "$initd/sysctl" ]; then
        replace_line_in_file "$initd/sysctl" \
            'sysctl ${quiet} --system' \
            'kimigayo_sysctl ${quiet}' || return 1

        # BusyBox 版の本体を関数として足す（上流の構造は崩さない）
        cat >> "$initd/sysctl" << 'SYSCTL_EOF'

# ---------------------------------------------------------------------------
# Kimigayo: BusyBox の sysctl に --system が無いための置き換え。
# 上流の Linux_sysctl() は procps の長オプションを前提にしていた。
# ---------------------------------------------------------------------------
kimigayo_sysctl()
{
	local quiet="$1" conf= files= out=

	# コンテナではカーネルは**ホストのもの**。非特権コンテナは
	# /proc/sys を read-only で渡されるので、どのキーも書けない。
	# これは「設定に失敗した」ではなく「ここの担当ではない」ので、
	# エラーにせず対象外として抜ける（設定するならホスト側で
	# docker run --sysctl、または --privileged）。
	#
	# 判定に `[ -w /proc/sys/kernel ]` は使えない。read-only mount でも
	# root には writable と返る（実測）。/proc/mounts を見る。
	if grep -q " /proc/sys proc ro[, ]" /proc/mounts 2>/dev/null; then
		einfo "kernel parameters are managed by the host (/proc/sys is read-only)"
		return 0
	fi

	for conf in /run/sysctl.d/*.conf /etc/sysctl.d/*.conf \
		/usr/local/lib/sysctl.d/*.conf /usr/lib/sysctl.d/*.conf \
		/lib/sysctl.d/*.conf /etc/sysctl.conf; do
		[ -r "$conf" ] && files="${files} ${conf}"
	done
	[ -n "$files" ] || return 0

	# -e: このカーネルに存在しないキーを警告にしない
	#     （コンテナでは見えない net.* がある。実測で rmem_default 等）
	# shellcheck disable=SC2086
	out="$(sysctl ${quiet} -e -p ${files} 2>&1)"
	[ -n "$out" ] && printf "%s\n" "$out"

	# **BusyBox の sysctl は書き込みに失敗しても終了コード 0 を返す**（実測）。
	# そのままだと全キー失敗でも [ ok ] になるので、出力で判定する。
	case "$out" in
	*"error setting key"*) return 1 ;;
	esac
	return 0
}
SYSCTL_EOF
        log_info "  ✓ sysctl: --system -> BusyBox の -p に置き換え"
    fi

    # --- bootmisc: BusyBox の mount には --bind が無い ------------------------
    #
    # clean_run() が /run の下敷きを掃除するために bind mount する。
    # BusyBox の mount は長オプションを持たないが `-o bind` で同じことができる。
    # keyword に -docker が無いので**コンテナでも実行される**。
    if [ -f "$initd/bootmisc" ]; then
        replace_line_in_file "$initd/bootmisc" \
            'mount --bind / $dir' \
            'mount -o bind / $dir' || return 1
        log_info "  ✓ bootmisc: mount --bind -> mount -o bind"
    fi
}

create_config_files() {
    log "Creating essential configuration files..."

    # /etc/passwd
    cat > "$ROOTFS_DIR/etc/passwd" << 'EOF'
root:x:0:0:root:/root:/bin/sh
nobody:x:65534:65534:nobody:/:/sbin/nologin
EOF
    chmod 644 "$ROOTFS_DIR/etc/passwd"
    log_info "  Created: /etc/passwd"

    # /etc/group
    cat > "$ROOTFS_DIR/etc/group" << 'EOF'
root:x:0:
tty:x:5:
kmem:x:15:
input:x:24:
video:x:27:
audio:x:28:
disk:x:6:
cdrom:x:11:
usb:x:85:
users:x:100:
nogroup:x:65534:
EOF
    chmod 644 "$ROOTFS_DIR/etc/group"
    log_info "  Created: /etc/group"

    # /etc/shadow (minimal)
    cat > "$ROOTFS_DIR/etc/shadow" << 'EOF'
root:*:19000:0:99999:7:::
nobody:*:19000:0:99999:7:::
EOF
    chmod 600 "$ROOTFS_DIR/etc/shadow"
    log_info "  Created: /etc/shadow"

    # /etc/hosts
    cat > "$ROOTFS_DIR/etc/hosts" << 'EOF'
127.0.0.1   localhost localhost.localdomain
::1         localhost localhost.localdomain
EOF
    chmod 644 "$ROOTFS_DIR/etc/hosts"
    log_info "  Created: /etc/hosts"

    # /etc/hostname
    echo "kimigayo" > "$ROOTFS_DIR/etc/hostname"
    chmod 644 "$ROOTFS_DIR/etc/hostname"
    log_info "  Created: /etc/hostname"

    # /etc/fstab
    cat > "$ROOTFS_DIR/etc/fstab" << 'EOF'
# <file system> <mount point>   <type>  <options>               <dump>  <pass>
proc            /proc           proc    defaults                0       0
sysfs           /sys            sysfs   defaults                0       0
devpts          /dev/pts        devpts  gid=5,mode=620          0       0
tmpfs           /run            tmpfs   defaults                0       0
tmpfs           /tmp            tmpfs   defaults                0       0
EOF
    chmod 644 "$ROOTFS_DIR/etc/fstab"
    log_info "  Created: /etc/fstab"

    # /etc/inittab (for init system) - Optimized for containers
    cat > "$ROOTFS_DIR/etc/inittab" << 'EOF'
# /etc/inittab - Kimigayo OS init configuration (Optimized)

# System initialization (simplified for containers)
::sysinit:/sbin/openrc sysinit
::sysinit:/sbin/openrc boot

# Main system
::wait:/sbin/openrc default

# Console (single getty to save resources)
::respawn:/sbin/getty 38400 console

# Shutdown
::shutdown:/sbin/openrc shutdown
EOF
    chmod 644 "$ROOTFS_DIR/etc/inittab"
    log_info "  Created: /etc/inittab (optimized)"

    # /etc/profile
    cat > "$ROOTFS_DIR/etc/profile" << 'EOF'
# /etc/profile - System-wide environment settings for Bourne shell

export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export PS1='\u@\h:\w\$ '
export PAGER=less
export EDITOR=vi

# Set umask
umask 022

# Source profile.d scripts
for script in /etc/profile.d/*.sh; do
    [ -r "$script" ] && . "$script"
done
unset script
EOF
    chmod 644 "$ROOTFS_DIR/etc/profile"
    log_info "  Created: /etc/profile"

    # Create profile.d directory
    mkdir -p "$ROOTFS_DIR/etc/profile.d"

    # /etc/network/interfaces
    cat > "$ROOTFS_DIR/etc/network/interfaces" << 'EOF'
# Loopback interface
auto lo
iface lo inet loopback

# DHCP on first ethernet interface
auto eth0
iface eth0 inet dhcp
EOF
    chmod 644 "$ROOTFS_DIR/etc/network/interfaces"
    log_info "  Created: /etc/network/interfaces"

    # /etc/resolv.conf
    cat > "$ROOTFS_DIR/etc/resolv.conf" << 'EOF'
# Generated by Kimigayo OS
nameserver 8.8.8.8
nameserver 8.8.4.4
EOF
    chmod 644 "$ROOTFS_DIR/etc/resolv.conf"
    log_info "  Created: /etc/resolv.conf"

    # /etc/os-release
    cat > "$ROOTFS_DIR/etc/os-release" << 'EOF'
NAME="Kimigayo OS"
VERSION="0.1.0"
ID=kimigayo
ID_LIKE=alpine
PRETTY_NAME="Kimigayo OS 0.1.0"
VERSION_ID="0.1.0"
HOME_URL="https://github.com/Kazuki-0731/Kimigayo"
BUG_REPORT_URL="https://github.com/Kazuki-0731/Kimigayo/issues"
EOF
    chmod 644 "$ROOTFS_DIR/etc/os-release"
    log_info "  Created: /etc/os-release"

    # Create motd (message of the day)
    cat > "$ROOTFS_DIR/etc/motd" << 'EOF'

    ╔════════════════════════════════════════════════════════╗
    ║                   Kimigayo OS v0.1.0                   ║
    ║        Lightweight, Fast, and Secure Container OS      ║
    ╚════════════════════════════════════════════════════════╝

    Documentation: https://github.com/Kazuki-0731/Kimigayo

EOF
    chmod 644 "$ROOTFS_DIR/etc/motd"
    log_info "  Created: /etc/motd"

    # /etc/rc.conf (OpenRC configuration) - Performance optimized
    cat > "$ROOTFS_DIR/etc/rc.conf" << 'EOF'
# Kimigayo OS - OpenRC Configuration (Performance Optimized)

# Enable parallel startup (faster boot)
rc_parallel="YES"

# Logging configuration (reduce overhead)
rc_logger="YES"
rc_log_level="warn"

# Timeout settings
rc_timeout_stopsec=30

# cgroup support (for containers)
rc_cgroup_mode="hybrid"
rc_controller_cgroups="YES"

# Disable hotplug (not needed in containers)
rc_hotplug="hwclock net.lo"

# Relax dependency checking (faster startup)
rc_depend_strict="NO"

# Crash handling
rc_crashed_stop="NO"
rc_crashed_start="YES"

# Console settings
unicode="YES"
EOF
    chmod 644 "$ROOTFS_DIR/etc/rc.conf"
    log_info "  Created: /etc/rc.conf (performance optimized)"

    # /etc/sysctl.d/ directory for kernel parameters
    mkdir -p "$ROOTFS_DIR/etc/sysctl.d"

    # /etc/sysctl.d/99-kimigayo-performance.conf
    cat > "$ROOTFS_DIR/etc/sysctl.d/99-kimigayo-performance.conf" << 'EOF'
# Kimigayo OS - Kernel Performance Tuning

# Memory management
vm.swappiness = 0
vm.dirty_ratio = 10
vm.dirty_background_ratio = 5
vm.overcommit_memory = 1

# Network optimization
net.core.rmem_default = 262144
net.core.rmem_max = 16777216
net.core.wmem_default = 262144
net.core.wmem_max = 16777216
net.ipv4.tcp_window_scaling = 1
net.ipv4.tcp_timestamps = 1
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_syncookies = 1

# File system
fs.file-max = 65536
vm.vfs_cache_pressure = 50

# Kernel
kernel.pid_max = 32768

# Security
kernel.randomize_va_space = 2
fs.suid_dumpable = 0
EOF
    chmod 644 "$ROOTFS_DIR/etc/sysctl.d/99-kimigayo-performance.conf"
    log_info "  Created: /etc/sysctl.d/99-kimigayo-performance.conf"

    log "✅ Configuration files created successfully"
}

# 入っているべきものが本当に入ったかを検証する
#
# 文章のルールではなく検証にしているのは、ここが「判定が常に偽」
# 「上流の prefix が変わった」といった突合漏れで静かに壊れる箇所だから。
# 実際に musl の libc.so と OpenRC のバイナリ 9 個が入らないまま
# 「✅ Root filesystem build completed!」と報告され続けていた。
# BusyBox が static-pie なので smoke テストでは露見しない。
verify_rootfs() {
    log "Verifying rootfs contents..."

    local errors=0
    local musl_arch="$ARCH"
    [ "$ARCH" = "arm64" ] && musl_arch="aarch64"

    # 動的リンカのリンク先が rootfs の中で解決できること。
    # [ -e ] は絶対シンボリックリンクをホスト側で解決してしまい、
    # Linux ホストでは glibc の /usr/lib が存在するため誤って通る。
    # そのため readlink して rootfs 基準で確かめる。
    local loader="$ROOTFS_DIR/lib/ld-musl-${musl_arch}.so.1"
    if [ -L "$loader" ]; then
        local target
        target="$(readlink "$loader")"
        case "$target" in
            /*) target="${ROOTFS_DIR}${target}" ;;
            *)  target="$(dirname "$loader")/${target}" ;;
        esac
        if [ ! -f "$target" ]; then
            log_error "  ✗ /lib/ld-musl-${musl_arch}.so.1 is a dangling symlink"
            log_error "      -> $(readlink "$loader") (not present in rootfs)"
            errors=$((errors + 1))
        else
            log_info "  ✓ dynamic loader resolves inside rootfs"
        fi
    elif [ -f "$loader" ]; then
        log_info "  ✓ dynamic loader present"
    else
        log_error "  ✗ /lib/ld-musl-${musl_arch}.so.1 missing"
        errors=$((errors + 1))
    fi

    # BusyBox 本体。存在だけでなくサイズも見る。
    # /bin/busybox は全アプレットのシンボリックリンク先なので、同名の実
    # バイナリを cp されるとリンク越しに中身を上書きされ、存在チェックは
    # 通るのに全コマンドが死ぬ（→ copy_over の説明）。
    if [ ! -f "$ROOTFS_DIR/bin/busybox" ]; then
        log_error "  ✗ /bin/busybox missing"
        errors=$((errors + 1))
    else
        local bb_rootfs bb_src
        bb_rootfs="$(wc -c < "$ROOTFS_DIR/bin/busybox" | tr -d ' ')"
        bb_src=0
        if [ -f "$BUSYBOX_INSTALL_DIR/bin/busybox" ]; then
            bb_src="$(wc -c < "$BUSYBOX_INSTALL_DIR/bin/busybox" | tr -d ' ')"
        fi
        if [ "$bb_src" -gt 0 ] && [ "$bb_rootfs" -lt $((bb_src * 8 / 10)) ]; then
            log_error "  ✗ /bin/busybox looks overwritten: ${bb_rootfs} bytes"
            log_error "      expected around ${bb_src} bytes (${BUSYBOX_INSTALL_DIR}/bin/busybox)"
            errors=$((errors + 1))
        else
            log_info "  ✓ /bin/busybox present (${bb_rootfs} bytes)"
        fi
    fi

    # OpenRC。create_config_files が作る inittab が参照するパスで確認する
    local rc_missing=""
    local f
    for f in openrc openrc-run rc-update start-stop-daemon; do
        [ -f "$ROOTFS_DIR/sbin/$f" ] || rc_missing="${rc_missing} ${f}"
    done
    if [ -n "$rc_missing" ]; then
        log_error "  ✗ OpenRC binaries missing from /sbin:${rc_missing}"
        errors=$((errors + 1))
    else
        log_info "  ✓ OpenRC binaries present in /sbin"
    fi

    # 共有ライブラリの結びつきを見る。
    #
    # ファイルの存在では分からない壊れ方が2つある。どちらも実際に
    # arm64 で踏んで、rootfs の検査は全項目通るのにイメージで
    # 実行すると落ちた。
    #
    #   1. libc.so に SONAME が無い
    #      これにリンクした実行ファイルの NEEDED が「libc.so」という
    #      ファイル名で記録される。実行時にローダ（それ自身が libc）が
    #      /usr/lib/libc.so を2つ目の libc として読み込み、1プロセスに
    #      libc が二重に載って Segmentation fault になる。
    #   2. libc.so が出荷しない共有ライブラリに依存している
    #      arm64 では -lgcc_s が入り込んで NEEDED: libgcc_s.so.1 が付き、
    #      Error relocating ... __letf2: symbol not found で
    #      動的リンクのバイナリが全滅した。
    #
    # readelf が無い環境（macOS のホスト等）では検査できないので警告に
    # 留める。CI はビルドコンテナ内で走るので必ず検査される。
    if command -v readelf >/dev/null 2>&1; then
        local libc_so="$ROOTFS_DIR/usr/lib/libc.so"
        if [ -f "$libc_so" ]; then
            if readelf -d "$libc_so" 2>/dev/null | grep -q 'SONAME'; then
                log_info "  ✓ libc.so has a SONAME"
            else
                log_error "  ✗ libc.so has no SONAME"
                log_error "      これにリンクした実行ファイルは NEEDED に 'libc.so' を"
                log_error "      記録し、実行時に libc が二重に載って segfault する"
                errors=$((errors + 1))
            fi
            local libc_needed
            libc_needed="$(readelf -d "$libc_so" 2>/dev/null | grep 'NEEDED' || true)"
            if [ -n "$libc_needed" ]; then
                log_error "  ✗ libc.so depends on shared libraries that are not shipped:"
                log_error "      ${libc_needed}"
                errors=$((errors + 1))
            else
                log_info "  ✓ libc.so is self-contained (no NEEDED)"
            fi
        fi

        # OpenRC の実行ファイルが libc を soname で参照していること
        local bad_needed=""
        for f in openrc openrc-run rc-update start-stop-daemon supervise-daemon; do
            [ -f "$ROOTFS_DIR/sbin/$f" ] || continue
            if readelf -d "$ROOTFS_DIR/sbin/$f" 2>/dev/null |
                    grep 'NEEDED' | grep -qE '\[libc\.so\]'; then
                bad_needed="${bad_needed} ${f}"
            fi
        done
        if [ -n "$bad_needed" ]; then
            log_error "  ✗ these binaries need a bare 'libc.so' instead of the soname:${bad_needed}"
            log_error "      libc.musl-${musl_arch}.so.1 になっていないと実行時に segfault する"
            errors=$((errors + 1))
        else
            log_info "  ✓ OpenRC binaries reference libc by soname"
        fi
    else
        log_warn "  readelf not found; skipping shared library checks"
    fi

    # コンポーネントの作り直し漏れ。
    #
    # .kimigayo-build-version はコンポーネント間の依存を見ないので、
    # musl を作り直しても BusyBox と OpenRC は「ビルド済み」と判定されて
    # 古いバイナリが残る。それは別の musl に対してリンクされたもので、
    # 実行すると Segmentation fault になる（2026-10-09 に実測）。
    #
    # 比較するのは**インストール先のスタンプファイルの mtime**。
    # rootfs 側のファイルは使えない。optimize_rootfs の strip が
    # 書き換えたものだけ mtime が更新され、既に strip 済みのものは
    # 据え置かれるため、順序が逆転する（実際に誤検知した。
    # libc.so が strip されて最も新しくなり、全部が「古い」と判定された）。
    # スタンプは各コンポーネントのビルド末尾に書かれ、以後触られない。
    #
    # musl は [1/4] で最初に作られるので、正常なビルドでは依存先の
    # スタンプが musl より必ず新しい。
    # （→ CLAUDE.md「musl を作り直したら、それにリンクしているものも
    #   作り直す」節）
    local musl_stamp="${MUSL_INSTALL_DIR}/.kimigayo-build-version"
    if [ -f "$musl_stamp" ]; then
        local stale=""
        local dep
        for dep in "BusyBox:${BUSYBOX_INSTALL_DIR}" "OpenRC:${OPENRC_INSTALL_DIR:-}"; do
            local name="${dep%%:*}" dir="${dep#*:}"
            [ -n "$dir" ] || continue
            local stamp="${dir}/.kimigayo-build-version"
            [ -f "$stamp" ] || continue
            if [ "$musl_stamp" -nt "$stamp" ]; then
                stale="${stale} ${name}"
            fi
        done
        if [ -n "$stale" ]; then
            log_error "  ✗ built before the current musl:${stale}"
            log_error "      musl を作り直したあと、これらを作り直していない。"
            log_error "      別の musl に対してリンクされているので実行時に落ちる。"
            log_error "      make clean-busybox clean-openrc してからやり直す。"
            errors=$((errors + 1))
        else
            log_info "  ✓ components were built after the current musl"
        fi
    fi

    # init スクリプトの shebang が解決できること。
    #
    # ファイルがあっても shebang の指す先が無ければ exec できない
    # （execve が ENOENT を返し "No such file or directory" になる）。
    # 2026-10-09 に 37 本中 36 本がこれで起動できない状態だった。
    # OpenRC の prefix が /usr なので shebang は /usr/sbin/openrc-run を
    # 指すが、rootfs には /sbin/openrc-run しか置いていなかった。
    if [ -d "$ROOTFS_DIR/etc/init.d" ]; then
        local bad_shebang="" not_exec="" total_scripts=0
        local script interp
        for script in "$ROOTFS_DIR/etc/init.d"/*; do
            [ -f "$script" ] || continue
            # **shebang の有無で判定する。`[ -x ]` で絞ってはいけない。**
            # functions.sh は `.` で読み込む関数ライブラリで shebang も
            # 実行権限も無い。一方、実行権限だけを条件にすると
            # 「実行権限が落ちた init スクリプト」を検査対象から外して
            # しまい、壊れたことに気づけない（2026-10-10 に実際に起きた）。
            case "$(head -1 "$script")" in "#!"*) ;; *) continue ;; esac
            total_scripts=$((total_scripts + 1))
            if [ ! -x "$script" ]; then
                not_exec="${not_exec} $(basename "$script")"
                continue
            fi
            interp="$(head -1 "$script" | sed -n 's|^#!\([^ ]*\).*|\1|p')"
            [ -n "$interp" ] || continue
            # rootfs 基準で解決する（ホスト側で解決させない）
            if [ ! -e "${ROOTFS_DIR}${interp}" ]; then
                bad_shebang="${bad_shebang} $(basename "$script")->${interp}"
            fi
        done
        if [ -n "$not_exec" ]; then
            log_error "  ✗ init scripts without the executable bit:"
            log_error "      ${not_exec}"
            log_error "      shebang を持つのに実行権限が無い。OpenRC から起動できない"
            errors=$((errors + 1))
        fi
        if [ -n "$bad_shebang" ]; then
            log_error "  ✗ init scripts whose interpreter is missing in the rootfs:"
            log_error "      ${bad_shebang}"
            log_error "      これらは exec できない（No such file or directory になる）"
            errors=$((errors + 1))
        fi
        if [ -z "$not_exec" ] && [ -z "$bad_shebang" ]; then
            log_info "  ✓ all ${total_scripts} init scripts are executable and their interpreters resolve"
        fi
    fi

    # FHS の骨格。空なので optimize_rootfs の空ディレクトリ掃除に
    # 消されやすい（実際に v0.1.0〜v2.0.1 で全部消えていた）。
    local dir_missing=""
    local d
    for d in tmp run run/lock var/log var/tmp home root mnt opt srv; do
        [ -d "$ROOTFS_DIR/$d" ] || dir_missing="${dir_missing} /${d}"
    done
    if [ -n "$dir_missing" ]; then
        log_error "  ✗ essential directories missing:${dir_missing}"
        errors=$((errors + 1))
    else
        log_info "  ✓ essential directories present"
    fi

    # /tmp と /var/tmp はスティッキービットが必要。
    # stat の書式は GNU と BSD で違うので POSIX の test -k で見る
    # （macOS の stat -f '%Lp' はスティッキービットを落とす）。
    for d in tmp var/tmp; do
        if [ -d "$ROOTFS_DIR/$d" ] && [ ! -k "$ROOTFS_DIR/$d" ]; then
            log_error "  ✗ /${d} is missing the sticky bit (should be 1777)"
            errors=$((errors + 1))
        fi
    done

    if [ "$errors" -gt 0 ]; then
        log_error "rootfs verification failed (${errors} problem(s))"
        return 1
    fi

    log "✅ rootfs verification passed"
}

# Generate rootfs metadata
generate_metadata() {
    log "Generating rootfs metadata..."

    local metadata_file="$ROOTFS_DIR/.kimigayo-build-info"

    cat > "$metadata_file" << EOF
# Kimigayo OS Build Information
BUILD_DATE=$(date -u '+%Y-%m-%d %H:%M:%S UTC')
BUILD_ARCH=$ARCH
IMAGE_TYPE=$IMAGE_TYPE
VERSION=0.1.0
BUILDER=$(whoami)
BUILD_HOST=$(hostname)
EOF

    chmod 644 "$metadata_file"
    log_info "  Created: /.kimigayo-build-info"

    log "✅ Metadata generated successfully"
}

# Calculate and display rootfs size
calculate_size() {
    log "Calculating rootfs size..."

    if command -v du >/dev/null 2>&1; then
        local size
        size=$(du -sh "$ROOTFS_DIR" 2>/dev/null | awk '{print $1}')
        log_info "  Total rootfs size: $size"

        # Count files
        local file_count
        file_count=$(find "$ROOTFS_DIR" -type f 2>/dev/null | wc -l)
        log_info "  Total files: $file_count"

        # Count directories
        local dir_count
        dir_count=$(find "$ROOTFS_DIR" -type d 2>/dev/null | wc -l)
        log_info "  Total directories: $dir_count"
    fi
}

# Main build process
main() {
    log "========================================"
    log "Kimigayo OS - Root Filesystem Builder"
    log "========================================"
    log "Architecture: $ARCH"
    log "Image Type: $IMAGE_TYPE"
    log "Output: $ROOTFS_DIR"
    log "========================================"

    # Check and build required components
    log "Checking required components..."

    # Determine musl arch (aarch64 vs arm64)
    local MUSL_ARCH="$ARCH"
    if [ "$ARCH" = "arm64" ]; then
        MUSL_ARCH="aarch64"
    fi

    # Check musl libc
    #
    # 以前は ${MUSL_CHECK_DIR}/lib/libc.a の有無で判定していたが、musl は
    # usr/lib/libc.a に入るため条件が常に成立せず、毎回フルビルドしていた。
    # インストール先の配置を当てに行かず、バージョンスタンプで判定する。
    local MUSL_CHECK_DIR="${BUILD_DIR}/musl-install-${MUSL_ARCH}"
    if ! kimigayo_is_built "$MUSL_CHECK_DIR" "$MUSL_VERSION"; then
        log_warn "musl libc ${MUSL_VERSION} not built yet, building..."
        bash "${SCRIPT_DIR}/download-musl.sh" || { log_error "Failed to download musl"; exit 1; }
        ARCH=$MUSL_ARCH bash "${SCRIPT_DIR}/build-musl.sh" || { log_error "Failed to build musl"; exit 1; }
        # Update MUSL_INSTALL_DIR for subsequent builds
        export MUSL_INSTALL_DIR="${MUSL_CHECK_DIR}"
    else
        log_info "✓ musl libc ${MUSL_VERSION} found at: ${MUSL_CHECK_DIR}"
        export MUSL_INSTALL_DIR="${MUSL_CHECK_DIR}"
    fi

    # Check BusyBox
    #
    # bin/busybox の有無だけだと、版を上げても古いバイナリをそのまま
    # rootfs に入れてしまう（1.36.1 が 1.38.0 のつもりで入りかけた）。
    # 版とバリアントの両方を見る。standard の BusyBox を minimal の
    # イメージに流用してしまう事故を防ぐ（→ build-stamp.sh のコメント）
    local BUSYBOX_BUILD_ID
    BUSYBOX_BUILD_ID="$(kimigayo_busybox_build_id "$BUSYBOX_VERSION" "$IMAGE_TYPE")"
    if ! kimigayo_is_built "$BUSYBOX_INSTALL_DIR" "$BUSYBOX_BUILD_ID"; then
        log_warn "BusyBox ${BUSYBOX_BUILD_ID} not built yet, building..."
        bash "${SCRIPT_DIR}/download-busybox.sh" || { log_error "Failed to download BusyBox"; exit 1; }
        ARCH=$ARCH IMAGE_TYPE=$IMAGE_TYPE MUSL_INSTALL_DIR="${MUSL_INSTALL_DIR}" \
            bash "${SCRIPT_DIR}/build-busybox.sh" || { log_error "Failed to build BusyBox"; exit 1; }
    else
        log_info "✓ BusyBox found at: ${BUSYBOX_INSTALL_DIR}/bin/busybox"
    fi

    # Check OpenRC
    #
    # build-rootfs.sh は musl と BusyBox しか面倒を見ていなかったため、
    # build-system/Makefile の init ターゲットを通らない経路
    # （make build-rootfs / make ci-build-local / rootfs 単体実行）では
    # OpenRC がビルドされず、copy_components が log_warn を出すだけで
    # init の無いイメージが出来上がっていた。
    local OPENRC_CHECK_DIR="${BUILD_DIR}/openrc-install-${ARCH}"
    if ! kimigayo_is_built "$OPENRC_CHECK_DIR" "$OPENRC_VERSION"; then
        log_warn "OpenRC ${OPENRC_VERSION} not built yet, building..."
        bash "${SCRIPT_DIR}/download-openrc.sh" || { log_error "Failed to download OpenRC"; exit 1; }
        ARCH=$ARCH MUSL_INSTALL_DIR="${MUSL_INSTALL_DIR}" \
            bash "${SCRIPT_DIR}/build-openrc.sh" || { log_error "Failed to build OpenRC"; exit 1; }
    else
        log_info "✓ OpenRC ${OPENRC_VERSION} found at: ${OPENRC_CHECK_DIR}"
    fi
    export OPENRC_INSTALL_DIR="${OPENRC_CHECK_DIR}"

    log "✅ All required components ready"
    log ""

    # Execute build steps
    create_directory_structure
    create_device_nodes
    copy_components
    create_config_files
    set_permissions
    optimize_rootfs
    verify_rootfs || exit 1
    generate_metadata
    calculate_size

    log ""
    log "========================================"
    log "✅ Root filesystem build completed!"
    log "========================================"
    log "Location: $ROOTFS_DIR"
    log ""

    # Display next steps
    log_info "Next steps:"
    log_info "  1. Review the rootfs: ls -la $ROOTFS_DIR"
    log_info "  2. Package and build the image: make package-rootfs build-image"
    log_info "  3. Smoke test the image: make test-smoke"

    # Record build success
    "${PROJECT_ROOT}/scripts/build-status.sh" record rootfs 2>/dev/null || true
}

# Run main function
main "$@"
