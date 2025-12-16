#!/bin/sh
#
# OpenRC Runlevel Setup Script for Kimigayo OS
# Configures default runlevels for the init system
#

set -e

INSTALL_DIR="${1:-/}"
RUNLEVEL_DIR="${INSTALL_DIR}/etc/runlevels"
INIT_DIR="${INSTALL_DIR}/etc/init.d"

echo "Setting up OpenRC runlevels..."
echo "Installation directory: $INSTALL_DIR"

# Create runlevel directories
mkdir -p "${RUNLEVEL_DIR}/sysinit"
mkdir -p "${RUNLEVEL_DIR}/boot"
mkdir -p "${RUNLEVEL_DIR}/default"
mkdir -p "${RUNLEVEL_DIR}/shutdown"

echo "Created runlevel directories"

# sysinit runlevel - system initialization
# (OpenRC built-in scripts handle most of this)
echo "Configuring sysinit runlevel..."
# devfs, dmesg, mdev/udev typically go here (provided by OpenRC)

# boot runlevel - early boot services
echo "Configuring boot runlevel..."
if [ -f "${INIT_DIR}/bootmisc" ]; then
    ln -sf "${INIT_DIR}/bootmisc" "${RUNLEVEL_DIR}/boot/bootmisc"
    echo "  - Added bootmisc"
fi

if [ -f "${INIT_DIR}/hostname" ]; then
    ln -sf "${INIT_DIR}/hostname" "${RUNLEVEL_DIR}/boot/hostname"
    echo "  - Added hostname"
fi

if [ -f "${INIT_DIR}/syslog" ]; then
    ln -sf "${INIT_DIR}/syslog" "${RUNLEVEL_DIR}/boot/syslog"
    echo "  - Added syslog"
fi

if [ -f "${INIT_DIR}/klogd" ]; then
    ln -sf "${INIT_DIR}/klogd" "${RUNLEVEL_DIR}/boot/klogd"
    echo "  - Added klogd"
fi

# default runlevel - normal runtime services
echo "Configuring default runlevel..."
if [ -f "${INIT_DIR}/networking" ]; then
    ln -sf "${INIT_DIR}/networking" "${RUNLEVEL_DIR}/default/networking"
    echo "  - Added networking"
fi

if [ -f "${INIT_DIR}/crond" ]; then
    ln -sf "${INIT_DIR}/crond" "${RUNLEVEL_DIR}/default/crond"
    echo "  - Added crond"
fi

# shutdown runlevel
# (OpenRC built-in scripts handle shutdown)
echo "Configuring shutdown runlevel..."

echo ""
echo "Runlevel setup completed!"
echo ""
echo "Runlevel summary:"
echo "  sysinit: System initialization (OpenRC built-ins)"
echo "  boot:    bootmisc, hostname, syslog, klogd"
echo "  default: networking, crond"
echo "  shutdown: System shutdown (OpenRC built-ins)"
