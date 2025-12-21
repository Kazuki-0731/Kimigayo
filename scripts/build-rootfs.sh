#!/bin/bash
# Kimigayo OS - Root Filesystem Builder
# Creates FHS-compliant directory structure and essential device nodes

set -e  # Exit on error
set -u  # Exit on undefined variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

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

    local size_before=$(du -sh "$ROOTFS_DIR" | awk '{print $1}')
    log_info "Size before optimization: $size_before"

    # 1. Strip all binaries and shared libraries
    log_info "Step 1: Stripping binaries and libraries..."
    local stripped_count=0

    # Temporarily disable exit on error for strip commands
    set +e

    # Strip all ELF binaries
    find "$ROOTFS_DIR" -type f -executable 2>/dev/null | while read -r file; do
        if file "$file" 2>/dev/null | grep -q "not stripped"; then
            if strip --strip-all "$file" 2>/dev/null; then
                stripped_count=$((stripped_count + 1))
            fi
        fi
    done

    # Strip shared libraries
    find "$ROOTFS_DIR" -type f -name "*.so*" 2>/dev/null | while read -r file; do
        if file "$file" 2>/dev/null | grep -q "not stripped"; then
            if strip --strip-unneeded "$file" 2>/dev/null; then
                stripped_count=$((stripped_count + 1))
            fi
        fi
    done

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
    local a_files=$(find "$ROOTFS_DIR" -type f -name "*.a" 2>/dev/null | wc -l)
    if [ "$a_files" -gt 0 ]; then
        find "$ROOTFS_DIR" -type f -name "*.a" -delete 2>/dev/null || true
        removed_count=$((removed_count + a_files))
    fi

    # Remove libtool archives (.la files) if any
    local la_files=$(find "$ROOTFS_DIR" -type f -name "*.la" 2>/dev/null | wc -l)
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
        find "$ROOTFS_DIR/usr/share" -type f -size +1k 2>/dev/null | while read -r file; do
            if file "$file" 2>/dev/null | grep -q "text"; then
                if gzip -9 "$file" 2>/dev/null; then
                    compressed_count=$((compressed_count + 1))
                fi
            fi
        done
    fi

    # Re-enable exit on error
    set -e

    if [ -d "$ROOTFS_DIR/usr/share" ]; then
        local gz_files=$(find "$ROOTFS_DIR/usr/share" -type f -name "*.gz" 2>/dev/null | wc -l)
        if [ "$gz_files" -gt 0 ]; then
            log_success "  ✓ Compressed $gz_files files"
        else
            log_info "  ✓ No large text files to compress"
        fi
    else
        log_info "  ✓ No large text files to compress"
    fi

    # Clean up empty directories
    find "$ROOTFS_DIR" -type d -empty -delete 2>/dev/null || true

    local size_after=$(du -sh "$ROOTFS_DIR" | awk '{print $1}')
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

        # Copy headers (optional, for development)
        if [ -d "$MUSL_INSTALL_DIR/include" ] && [ "$IMAGE_TYPE" != "minimal" ]; then
            mkdir -p "$ROOTFS_DIR/usr/include"
            cp -a "$MUSL_INSTALL_DIR/include"/* "$ROOTFS_DIR/usr/include/" 2>/dev/null || true
            log_info "  ✓ musl headers copied"
        fi
    else
        log_warn "musl installation directory not found: $MUSL_INSTALL_DIR"
    fi

    # Copy kernel modules (if built)
    if [ -d "$KERNEL_OUTPUT_DIR" ]; then
        log_info "Copying kernel modules..."

        # Copy kernel modules if they exist
        if [ -d "$KERNEL_OUTPUT_DIR/lib/modules" ]; then
            mkdir -p "$ROOTFS_DIR/lib/modules"
            cp -a "$KERNEL_OUTPUT_DIR/lib/modules"/* "$ROOTFS_DIR/lib/modules/" 2>/dev/null || true
            log_info "  ✓ Kernel modules copied"
        fi

        # Copy kernel binary
        if [ -f "$KERNEL_OUTPUT_DIR/boot/vmlinuz" ]; then
            mkdir -p "$ROOTFS_DIR/boot"
            cp "$KERNEL_OUTPUT_DIR/boot/vmlinuz" "$ROOTFS_DIR/boot/"
            log_info "  ✓ Kernel binary copied"
        fi
    else
        log_warn "Kernel output directory not found: $KERNEL_OUTPUT_DIR"
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
        if [ -d "$OPENRC_INSTALL_DIR/bin" ]; then
            cp -a "$OPENRC_INSTALL_DIR/bin"/* "$ROOTFS_DIR/bin/" 2>/dev/null || true
        fi
        if [ -d "$OPENRC_INSTALL_DIR/sbin" ]; then
            cp -a "$OPENRC_INSTALL_DIR/sbin"/* "$ROOTFS_DIR/sbin/" 2>/dev/null || true
        fi

        # Copy libraries
        if [ -d "$OPENRC_INSTALL_DIR/lib" ]; then
            cp -a "$OPENRC_INSTALL_DIR/lib"/* "$ROOTFS_DIR/lib/" 2>/dev/null || true
        fi

        # Copy init scripts and configuration
        if [ -d "$OPENRC_INSTALL_DIR/etc" ]; then
            cp -a "$OPENRC_INSTALL_DIR/etc"/* "$ROOTFS_DIR/etc/" 2>/dev/null || true
        fi

        # Copy shared data
        if [ -d "$OPENRC_INSTALL_DIR/usr/share" ]; then
            cp -a "$OPENRC_INSTALL_DIR/usr/share"/* "$ROOTFS_DIR/usr/share/" 2>/dev/null || true
        fi

        log_info "  ✓ OpenRC copied"
    else
        log_warn "OpenRC installation directory not found: $OPENRC_INSTALL_DIR"
    fi

    log "✅ Components copied successfully"
}

# Create essential configuration files
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
        local size=$(du -sh "$ROOTFS_DIR" 2>/dev/null | awk '{print $1}')
        log_info "  Total rootfs size: $size"

        # Count files
        local file_count=$(find "$ROOTFS_DIR" -type f 2>/dev/null | wc -l)
        log_info "  Total files: $file_count"

        # Count directories
        local dir_count=$(find "$ROOTFS_DIR" -type d 2>/dev/null | wc -l)
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

    # Execute build steps
    create_directory_structure
    create_device_nodes
    copy_components
    create_config_files
    set_permissions
    optimize_rootfs
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
    log_info "  2. Create an image: make iso or make docker-image"
    log_info "  3. Test in QEMU: make qemu-test"

    # Record build success
    "${PROJECT_ROOT}/scripts/build-status.sh" record rootfs 2>/dev/null || true
}

# Run main function
main "$@"
