# Kimigayo OS Package Repository

Official package repository for Kimigayo OS.

## Structure

```
repository/
├── packages/           # Package archives (.tar.gz)
│   ├── x86_64/        # x86_64 architecture packages
│   └── aarch64/       # ARM64 architecture packages
├── metadata/          # Package metadata (JSON)
│   ├── index.json     # Package index
│   └── packages/      # Individual package metadata
└── mirrors/           # Mirror configuration
    └── mirrors.toml   # Mirror server list
```

## Package Metadata Format

Each package has metadata in JSON format:

```json
{
  "name": "example-package",
  "version": "1.0.0",
  "arch": "x86_64",
  "description": "Example package",
  "homepage": "https://example.com",
  "license": "MIT",
  "maintainer": "Kimigayo OS Team <team@kimigayo.org>",
  "depends": ["dependency1", "dependency2>=1.0"],
  "provides": ["feature"],
  "conflicts": [],
  "replaces": [],
  "size": 1024,
  "installed_size": 4096,
  "checksum": {
    "sha256": "abcdef123456..."
  },
  "signature": {
    "algorithm": "ed25519",
    "public_key": "...",
    "signature": "..."
  },
  "build_date": "2025-01-01T00:00:00Z",
  "files": [
    "/usr/bin/example",
    "/usr/share/doc/example/README.md"
  ]
}
```

## Mirror Configuration

Mirrors are configured in `mirrors/mirrors.toml`:

```toml
[[mirror]]
name = "Official"
url = "https://packages.kimigayo.org"
priority = 100
regions = ["global"]

[[mirror]]
name = "Japan Mirror"
url = "https://jp.packages.kimigayo.org"
priority = 90
regions = ["asia", "jp"]
```

## Usage

### Adding a Package

1. Build the package archive
2. Generate metadata
3. Sign the package
4. Add to repository index

```bash
# Generate package metadata
isn-repo add-package package.tar.gz

# Update repository index
isn-repo update-index
```

### Hosting

The repository can be hosted via:
- Static HTTP server (nginx, Apache)
- CDN (CloudFlare, Fastly)
- Object storage (S3, GCS)

## Security

All packages must be:
1. **Signed** with Ed25519 signatures
2. **Checksummed** with SHA-256
3. **Verified** before installation

Public keys are distributed with the OS in `/etc/isn/keys/`.

## Phase Implementation

- **Phase 5**: Repository structure and metadata schema
- **Phase 6**: Package building and signing
- **Phase 7**: Mirror synchronization
- **Phase 8**: CDN distribution
