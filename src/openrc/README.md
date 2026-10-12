# OpenRC Init Scripts for Kimigayo OS

This directory contains custom OpenRC init scripts and service definitions for Kimigayo OS.

> **These files are NOT installed into the image (reference only).**
> As of 2026-10-13, no build script reads `src/openrc/`: `scripts/build-rootfs.sh`
> does not copy it, and `scripts/test-openrc-integration.sh` no longer checks
> these files either (it tests the built OpenRC in `build/openrc-install-<arch>`).
> The same applies to `configs/openrc/` (`rc.conf`, `services-*.list`,
> `inittab.optimized`).
>
> What the image actually contains:
>
> - **Init scripts and runlevels**: upstream OpenRC's own, as installed by
>   `scripts/build-openrc.sh` and copied by `build-rootfs.sh`
>   (`copy_over "$OPENRC_INSTALL_DIR/etc" ...`). `build-rootfs.sh` then removes
>   scripts that can never run in a container (`remove_unusable_init_scripts`)
>   and adapts `sysctl` / `bootmisc` to BusyBox (`patch_openrc_for_busybox`)
> - **`/etc/rc.conf`, `/etc/inittab`, `/etc/network/interfaces`,
>   `/etc/sysctl.d/99-kimigayo-performance.conf`**: written by heredocs in
>   `scripts/build-rootfs.sh`
>
> The descriptions below describe the files in this directory, not the image.

## Directory Structure

```
src/openrc/
├── init.d/          # Init scripts
│   ├── bootmisc     # Boot-time miscellaneous tasks
│   ├── hostname     # Set system hostname
│   ├── syslog       # System logging (syslogd)
│   ├── klogd        # Kernel logging
│   ├── networking   # Network interface management
│   └── crond        # Cron daemon
├── conf.d/          # Configuration files
│   ├── syslog       # syslogd configuration
│   ├── klogd        # klogd configuration
│   ├── crond        # crond configuration
│   └── hostname     # hostname configuration
└── runlevels/       # Runlevel setup
    └── setup-runlevels.sh   # Script to configure runlevels
```

## Init Scripts

### bootmisc
Performs miscellaneous boot-time tasks:
- Cleans `/tmp` directory
- Creates `/run` directory
- Sets up `/var/run` and `/var/lock` symlinks
- Creates necessary runtime directories

**Runlevel**: boot

### hostname
Sets the system hostname from `/etc/hostname` or uses default.

**Runlevel**: boot

### syslog
BusyBox syslogd system logging service.

**Configuration**: `/etc/conf.d/syslog`
**Runlevel**: boot
**Dependencies**: need localmount, use clock

### klogd
BusyBox klogd kernel logging service.

**Configuration**: `/etc/conf.d/klogd`
**Runlevel**: boot
**Dependencies**: need syslog, use clock

### networking
Configures network interfaces:
- Brings up loopback interface
- Configures interfaces from `/etc/network/interfaces`

**Runlevel**: default
**Dependencies**: need localmount, after bootmisc

### crond
BusyBox crond scheduling service.

**Configuration**: `/etc/conf.d/crond`
**Runlevel**: default
**Dependencies**: need localmount, use logger, after bootmisc

## Runlevels

`runlevels/setup-runlevels.sh` would set up the following runlevels.
**The image does not use this layout**; it uses upstream OpenRC's runlevels
(check with `docker run --rm <image> rc-update show`).

| Runlevel | Description | Services |
|----------|-------------|----------|
| sysinit  | System initialization | OpenRC built-ins (devfs, dmesg) |
| boot     | Early boot services | bootmisc, hostname, syslog, klogd |
| default  | Normal runtime | networking, crond |
| shutdown | System shutdown | OpenRC built-ins |

## Installation

These scripts are **not** installed by the rootfs build. To try them on a rootfs manually:

```bash
cd src/openrc/runlevels
./setup-runlevels.sh /path/to/rootfs
```

## Service Management

Once the system is running with OpenRC:

```bash
# Start a service
rc-service syslog start

# Stop a service
rc-service networking stop

# Check service status
rc-status

# Add service to runlevel
rc-update add crond default

# Remove service from runlevel
rc-update del crond default
```

## Customization

To customize service behavior, edit the configuration files in `conf.d/`:

```bash
# Example: Change syslog options
vi /etc/conf.d/syslog
# Modify SYSLOGD_OPTS variable

# Restart service to apply changes
rc-service syslog restart
```

## BusyBox Integration

All services are designed to work with BusyBox implementations:
- `syslogd` - BusyBox system logger
- `klogd` - BusyBox kernel logger
- `crond` - BusyBox cron daemon
- Network tools - BusyBox `ip`, `ifconfig`

## Dependencies

- OpenRC / BusyBox / musl libc (versions are defined only in `versions.mk`)

## See Also

- [OpenRC Service Script Guide](https://github.com/OpenRC/openrc/blob/master/service-script-guide.md)
- [BusyBox Documentation](https://busybox.net/documentation.html)
- Kimigayo OS Specification: `../../SPECIFICATION.md`
