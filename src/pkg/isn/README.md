# isn - Kimigayo OS Package Manager

Lightweight, secure package manager for Kimigayo OS written in Rust.

## Features

- **Fast & Lightweight**: Static binary with minimal dependencies
- **Secure**: Ed25519 signature verification for all packages
- **Atomic Operations**: All package operations are atomic
- **Dependency Resolution**: Automatic dependency resolution
- **SQLite Database**: Efficient package database using SQLite

## Commands

### Package Management
```bash
isn install <package>     # Install a package
isn remove <package>      # Remove a package
isn update                # Update package database
isn upgrade               # Upgrade all packages
```

### Package Information
```bash
isn search <query>        # Search for packages
isn info <package>        # Show package information
isn list                  # List installed packages
isn list --explicit       # List explicitly installed packages
```

### Security
```bash
isn verify <package>      # Verify package integrity
isn security-update       # Install security updates
```

## Building

### Static Binary (musl)
```bash
cargo build --release --target x86_64-unknown-linux-musl
```

### For ARM64
```bash
cargo build --release --target aarch64-unknown-linux-musl
```

## Architecture

- **CLI**: Command-line interface using `clap`
- **Database**: SQLite for package metadata
- **Security**: Ed25519 signatures using `ed25519-dalek`
- **Network**: HTTPS downloads using `reqwest` with rustls
- **Hashing**: SHA-256 checksums using `sha2`

## Configuration

Default configuration file: `/etc/isn/config.toml`

```toml
database_path = "/var/lib/isn/db.sqlite"
cache_dir = "/var/cache/isn"
mirrors = [
    "https://mirrors.kimigayo.org/packages"
]
```

## Database Schema

```sql
CREATE TABLE packages (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    version TEXT NOT NULL,
    description TEXT,
    installed_at INTEGER
);

CREATE TABLE dependencies (
    package_id INTEGER,
    depends_on TEXT,
    FOREIGN KEY (package_id) REFERENCES packages(id)
);
```

## Development Status

**Phase 5 (Current)**: Basic CLI and structure implementation
- [x] CLI argument parsing
- [x] Error handling
- [x] Database schema
- [x] Configuration management
- [ ] Package installation logic (Phase 6)
- [ ] Dependency resolution (Phase 6)
- [ ] Signature verification (Phase 6)

## License

MIT License
