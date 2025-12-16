# OpenRC Init Scripts for Kimigayo OS

This directory contains custom OpenRC init scripts and service definitions for Kimigayo OS.

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
**Dependencies**: localmount, clock

### klogd
BusyBox klogd kernel logging service.

**Configuration**: `/etc/conf.d/klogd`
**Runlevel**: boot
**Dependencies**: syslog, clock

### networking
Configures network interfaces:
- Brings up loopback interface
- Configures interfaces from `/etc/network/interfaces`

**Runlevel**: default
**Dependencies**: localmount, bootmisc

### crond
BusyBox crond scheduling service.

**Configuration**: `/etc/conf.d/crond`
**Runlevel**: default
**Dependencies**: localmount, logger

## Runlevels

Kimigayo OS uses the following OpenRC runlevels:

| Runlevel | Description | Services |
|----------|-------------|----------|
| sysinit  | System initialization | OpenRC built-ins (devfs, dmesg) |
| boot     | Early boot services | bootmisc, hostname, syslog, klogd |
| default  | Normal runtime | networking, crond |
| shutdown | System shutdown | OpenRC built-ins |

## Installation

The init scripts and runlevels are automatically installed during the rootfs build process. To manually set up runlevels:

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

- OpenRC (>= 0.52.1)
- BusyBox (>= 1.36.1)
- musl libc (>= 1.2.4)

## See Also

- [OpenRC Service Script Guide](https://github.com/OpenRC/openrc/blob/master/service-script-guide.md)
- [BusyBox Documentation](https://busybox.net/documentation.html)
- Kimigayo OS Specification: `../../SPECIFICATION.md`
