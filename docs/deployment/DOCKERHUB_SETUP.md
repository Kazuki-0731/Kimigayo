# Docker Hub Repository Setup

## Repository Information

### Account Details
- **Organization/Username**: kimigayo-os (to be created)
- **Repository Name**: kimigayo-os
- **Visibility**: Public
- **Description**: Lightweight, fast, and secure container-focused operating system inspired by Alpine Linux

### Repository Description

Kimigayo OS is a lightweight, fast, and secure container-focused operating system designed for Docker environments. Built with security-first principles and minimal footprint, it provides an excellent foundation for containerized applications and microservices.

**Key Features:**
- 🪶 **Ultra Lightweight**: Base image under 5MB
- ⚡ **Fast Boot**: System startup in under 10 seconds
- 🔒 **Security Hardened**: ASLR, DEP, PIE, and seccomp-BPF enabled by default
- 📦 **Package Manager**: Built-in `isn` package manager with Ed25519 signature verification
- 🏗️ **Modular Design**: Choose only the components you need
- 🔁 **Reproducible Builds**: Bit-identical build outputs for verification
- 🌐 **Multi-Architecture**: Supports x86_64 and ARM64

**Based on:**
- Linux Kernel (hardened)
- musl libc
- BusyBox
- OpenRC init system

## Tagging Strategy

### Version Tags

We follow **Semantic Versioning (SemVer)** for all releases:

#### Format
- `MAJOR.MINOR.PATCH` (e.g., `1.0.0`)
  - **MAJOR**: Incompatible API changes
  - **MINOR**: Backward-compatible new functionality
  - **PATCH**: Backward-compatible bug fixes

#### Image Variants

Each version comes in three variants based on image size and included features:

1. **Minimal** (`-minimal` suffix)
   - Size: < 5MB
   - Contains: Kernel + musl libc + minimal BusyBox
   - Use case: Absolute minimal footprint for specialized containers

2. **Standard** (no suffix, default)
   - Size: < 15MB
   - Contains: Minimal + common utilities + isn package manager
   - Use case: General-purpose container base image

3. **Extended** (`-extended` suffix)
   - Size: < 50MB
   - Contains: Standard + development tools + additional utilities
   - Use case: Development environments and feature-rich containers

#### Tag Examples

```
# Version-specific tags
kimigayo-os:0.1.0               # Standard variant, version 0.1.0
kimigayo-os:0.1.0-minimal       # Minimal variant, version 0.1.0
kimigayo-os:0.1.0-extended      # Extended variant, version 0.1.0

# Architecture-specific tags
kimigayo-os:0.1.0-amd64         # x86_64 architecture
kimigayo-os:0.1.0-arm64         # ARM64 architecture

# Combined variant and architecture
kimigayo-os:0.1.0-minimal-amd64
kimigayo-os:0.1.0-extended-arm64

# Rolling tags (auto-updated)
kimigayo-os:latest              # Latest stable standard variant
kimigayo-os:latest-minimal      # Latest stable minimal variant
kimigayo-os:latest-extended     # Latest stable extended variant
kimigayo-os:stable              # Latest stable release (alias for latest)
kimigayo-os:edge                # Latest development build (unstable)
```

### Tagging Workflow

1. **Development Builds** (`edge` tag)
   - Pushed on every commit to `main` branch
   - Not recommended for production use
   - Format: `edge`, `edge-minimal`, `edge-extended`

2. **Beta/RC Releases**
   - Pre-release versions for testing
   - Format: `0.1.0-beta.1`, `1.0.0-rc.2`

3. **Stable Releases**
   - Production-ready versions
   - Format: `0.1.0`, `1.0.0`
   - Also tagged as `latest` and `stable`

4. **Patch Updates**
   - Bug fixes and security patches
   - Format: `1.0.1`, `1.0.2`
   - Automatically update `latest` tag

## Repository Setup Instructions

### Step 1: Create Docker Hub Account

1. Visit https://hub.docker.com/signup
2. Register account with username: `kimigayo-os`
3. Verify email address
4. Complete profile setup

### Step 2: Create Repository

1. Log in to Docker Hub
2. Click "Create Repository"
3. Fill in repository details:
   - **Name**: `kimigayo-os`
   - **Description**: (Use description from above)
   - **Visibility**: Public
4. Click "Create"

### Step 3: Repository Settings

Configure the following settings:

#### Overview Tab
- Add the full description from above
- Add links to:
  - GitHub repository: `https://github.com/kimigayo-os/kimigayo`
  - Documentation: `https://docs.kimigayo-os.org` (to be created)
  - Issues: `https://github.com/kimigayo-os/kimigayo/issues`

#### Builds Tab (for future CI/CD integration)
- Will be configured with GitHub Actions
- Automated builds on tag push
- Multi-architecture builds using buildx

#### Collaborators Tab
- Add team members as needed
- Set appropriate permission levels

### Step 4: Docker Hub README

The Docker Hub README should include:

```markdown
# Kimigayo OS

Lightweight, fast, and secure container-focused operating system.

## Quick Start

### Pull the Image

```bash
# Standard variant (recommended)
docker pull kimigayo-os:latest

# Minimal variant
docker pull kimigayo-os:latest-minimal

# Extended variant
docker pull kimigayo-os:latest-extended
```

### Run a Container

```bash
# Interactive shell
docker run -it kimigayo-os:latest /bin/sh

# Run a command
docker run kimigayo-os:latest uname -a
```

### Use as Base Image

```dockerfile
FROM kimigayo-os:latest

# Install packages using isn
RUN isn install nginx

# Your application setup
COPY . /app
WORKDIR /app

CMD ["/usr/sbin/nginx", "-g", "daemon off;"]
```

## Image Variants

- **kimigayo-os:latest** - Standard variant (< 15MB)
- **kimigayo-os:latest-minimal** - Minimal variant (< 5MB)
- **kimigayo-os:latest-extended** - Extended variant (< 50MB)

## Documentation

- [Installation Guide](https://github.com/kimigayo-os/kimigayo/blob/main/docs/user/INSTALLATION.md)
- [Quick Start Guide](https://github.com/kimigayo-os/kimigayo/blob/main/docs/user/QUICKSTART.md)
- [Package Manager Guide](https://github.com/kimigayo-os/kimigayo/blob/main/docs/user/PACKAGE_MANAGER.md)
- [Security Guide](https://github.com/kimigayo-os/kimigayo/blob/main/docs/security/SECURITY_GUIDE.md)

## Features

- ✅ Ultra-lightweight (< 5MB base image)
- ✅ Fast boot time (< 10 seconds)
- ✅ Security hardened by default
- ✅ Reproducible builds
- ✅ Multi-architecture support (x86_64, ARM64)
- ✅ Built-in package manager (isn)
- ✅ Based on proven technologies (musl libc, BusyBox, OpenRC)

## License

See [LICENSE](https://github.com/kimigayo-os/kimigayo/blob/main/LICENSE) file.

## Support

- GitHub Issues: https://github.com/kimigayo-os/kimigayo/issues
- Security Issues: See [SECURITY.md](https://github.com/kimigayo-os/kimigayo/blob/main/docs/security/VULNERABILITY_REPORTING.md)
```

## Security Considerations

### Image Signing

All official images will be signed using:
- Docker Content Trust (DCT)
- Cosign for additional verification

### Vulnerability Scanning

Images will be automatically scanned with:
- Trivy
- Results published to GitHub Security tab

### Update Policy

- **Security patches**: Released within 24-48 hours of disclosure
- **Bug fixes**: Included in regular patch releases
- **Feature updates**: Follow SemVer minor version increments

## Metadata Labels

All images include OpenContainer Initiative (OCI) labels:

```dockerfile
LABEL org.opencontainers.image.title="Kimigayo OS"
LABEL org.opencontainers.image.description="Lightweight, fast, and secure container-focused operating system"
LABEL org.opencontainers.image.authors="Kimigayo OS Team"
LABEL org.opencontainers.image.url="https://github.com/kimigayo-os/kimigayo"
LABEL org.opencontainers.image.documentation="https://github.com/kimigayo-os/kimigayo/tree/main/docs"
LABEL org.opencontainers.image.source="https://github.com/kimigayo-os/kimigayo"
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.revision="${GIT_COMMIT}"
LABEL org.opencontainers.image.created="${BUILD_DATE}"
LABEL org.opencontainers.image.licenses="GPL-2.0"
```

## Next Steps

After repository setup:
1. Configure GitHub Actions for automated builds (Task 26)
2. Implement security scanning (Task 27)
3. Set up multi-architecture builds (Task 28)
4. Prepare first release (Task 29)
