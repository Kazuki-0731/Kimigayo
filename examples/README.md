# Kimigayo OS - Derivative Images

This directory contains sample derivative images built on top of Kimigayo OS.

## Available Images

### 1. **Nginx** - Web Server
- **Directory**: `nginx/`
- **Image Size**: 10.7MB
- **Use Case**: Static websites, reverse proxy, load balancer
- **Documentation**: [nginx/README.md](nginx/README.md)

**Quick Start** (nginx listens on 8080 because it runs as non-root):
```bash
docker build -t kimigayo-nginx examples/nginx/
docker run -d -p 8080:8080 kimigayo-nginx
```

### 2. **Python** - Python Runtime
- **Directory**: `python/`
- **Image Size**: 49.6MB
- **Use Case**: Web APIs, data processing, automation scripts
- **Documentation**: [python/README.md](python/README.md)

**Quick Start** (starts the sample `app.py`; the command is `python3`):
```bash
docker build -t kimigayo-python examples/python/
docker run -d -p 8000:8000 kimigayo-python
```

### 3. **Node.js** - JavaScript Runtime
- **Directory**: `nodejs/`
- **Image Size**: 73.0MB
- **Use Case**: Web applications, APIs, real-time services
- **Documentation**: [nodejs/README.md](nodejs/README.md)

**Quick Start** (starts the sample `app.js`):
```bash
docker build -t kimigayo-nodejs examples/nodejs/
docker run -d -p 3000:3000 kimigayo-nodejs
```

## Size Comparison

| Image | Kimigayo OS example | Official Alpine-based image |
|-------|---------------------|-----------------------------|
| **Base OS** | 3.06MB (`3.1.0`, Standard) | 8.66MB (`alpine:3.24`) |
| **+ Nginx** | 10.7MB | 68.5MB (`nginx:alpine`) |
| **+ Python** | 49.6MB | 59.5MB (`python:alpine`) |
| **+ Node.js** | 73.0MB | 181MB (`node:alpine`) |

Measured 2026-10-15 on arm64 with `docker images`. The reduction depends on
the runtime: about 84% for nginx, 60% for Node.js, but only about 17% for
Python, whose size is mostly the interpreter and standard library. The
official images also include pip / npm, which these examples leave out.

## Common Patterns

### Multi-stage Builds

Install dependencies in a stage that has a package manager, then copy only
the result. Use the same Alpine version as the runtime you copy from, so
compiled extensions match:

```dockerfile
# Builder stage
FROM alpine:3.24 AS builder
RUN apk add --no-cache python3 py3-pip
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/stage/app/lib -r requirements.txt

# Runtime stage (the Python example image; Kimigayo itself has no Python)
FROM kimigayo-python:latest
COPY --from=builder /stage/app/lib /app/lib
ENV PYTHONPATH=/app/lib
WORKDIR /app
COPY . .
CMD ["python3", "app.py"]
```

### Development vs Production

**Development** (with shell access and more BusyBox applets):
```dockerfile
FROM ishinokazuki/kimigayo-os:3.2.0-standard
# ... COPY your tools from a builder stage ...
CMD ["/bin/sh"]
```

**Production** (minimal):
```dockerfile
FROM ishinokazuki/kimigayo-os:3.2.0-minimal
# ... only runtime deps ...
CMD ["./app"]
```

## Creating Your Own Derivative Image

### Step 1: Create Dockerfile

**Kimigayo has no package manager** (that is the design, see
[SPECIFICATION.md](../SPECIFICATION.md) 3.5). `apk`, `apt`, `dpkg` and `rpm`
are all absent, so **`RUN apk add` fails with `apk: not found`**.
Build in a stage that has a package manager and copy the result in.

```dockerfile
FROM alpine:3.24 AS builder
RUN apk add --no-cache your-package

# Resolve the shared libraries with ldd instead of listing them by hand -
# missing one shows up at runtime as
# "Error relocating ...: symbol not found".
RUN mkdir -p /stage/usr/bin /stage/usr/lib \
    && cp /usr/bin/your-binary /stage/usr/bin/ \
    && ldd /usr/bin/your-binary \
       | awk '/=>/ { print $3 } /^\/lib|^\/usr\/lib/ { print $1 }' \
       | grep -v 'ld-musl' | sort -u \
       | xargs -I{} cp -L {} /stage/usr/lib/

FROM ishinokazuki/kimigayo-os:3.2.0
COPY --from=builder /stage/ /
COPY . /app
WORKDIR /app
EXPOSE 8080

# Do not run as root. The image ships nobody (65534).
USER 65534

CMD ["./your-app"]
```

### Step 2: Build

```bash
docker build -t your-image:latest .
```

### Step 3: Test

```bash
docker run -it --rm -p 8080:8080 your-image:latest
```

### Step 4: Optimize

1. **Use .dockerignore**
   ```
   .git
   node_modules
   *.md
   tests/
   ```

2. **Multi-stage builds**
   ```dockerfile
   FROM builder AS build
   # ... build steps ...

   FROM ishinokazuki/kimigayo-os:3.2.0
   COPY --from=build /app /app
   ```

3. **Layer caching** (in the *builder* stage - Kimigayo has no pip)
   ```dockerfile
   # Copy dependencies first
   COPY requirements.txt .
   RUN pip install --no-cache-dir --target=/stage/app/lib -r requirements.txt

   # Then copy code
   COPY . .
   ```

## Best Practices

### Security

1. **Don't run as root**
   ```dockerfile
   RUN adduser -D appuser
   USER appuser
   ```

2. **Use specific tags**
   ```dockerfile
   FROM ishinokazuki/kimigayo-os:3.2.0-standard
   # not :latest in production
   ```

3. **Scan for vulnerabilities**

   Image scanners that read a package database (such as `trivy image`)
   find nothing to scan in Kimigayo-based images, because there is no
   package database - the result is "not scanned", not "0 vulnerabilities".
   Generate an SBOM from the binaries and match it instead; Kimigayo does
   this for its own image in
   [scripts/scan-image.sh](../scripts/scan-image.sh) (versions read from the binaries → CycloneDX SBOM → Grype).

### Performance

1. **Minimize layers** (in the *builder* stage - Kimigayo has no `apk`)
   ```dockerfile
   FROM alpine:3.24 AS builder
   RUN apk add --no-cache \
       package1 \
       package2 \
       package3
   ```

2. **Nothing to clean up in the final image.** Build dependencies never
   reach it, because only the files you `COPY --from=builder` do. This is
   the point of having no package manager: there is no `apk del` step to
   forget.

3. **Use build cache**
   ```bash
   docker build --cache-from your-image:latest .
   ```

## Testing

### Local Testing

```bash
# Build
docker build -t test-image .

# Run
docker run -d --name test test-image

# Check logs
docker logs test

# Execute commands
docker exec -it test /bin/sh

# Clean up
docker stop test && docker rm test
```

### Automated Testing

```bash
# Health check (inside the running container; Minimal has no wget)
docker exec test wget -q --spider http://localhost:8080/

# Integration tests (with your own docker-compose.test.yml)
docker compose -f docker-compose.test.yml up --abort-on-container-exit
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Build and Push

on:
  push:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build image
        run: docker build -t my-image .

      - name: Test image
        run: docker run --rm my-image ./your-app --version

      - name: Push to registry
        run: |
          echo "${{ secrets.DOCKER_PASSWORD }}" | docker login -u "${{ secrets.DOCKER_USERNAME }}" --password-stdin
          docker tag my-image "${{ secrets.DOCKER_USERNAME }}/my-image:latest"
          docker push "${{ secrets.DOCKER_USERNAME }}/my-image:latest"
```

## Production Deployment

### Docker Compose

See individual READMEs for Docker Compose examples.

### Kubernetes

See individual READMEs for Kubernetes manifests.

### Cloud Platforms

For cloud-specific deployment guides, see [../docs/cloud/](../docs/cloud/).

## Troubleshooting

### Image won't build

1. Check base image is available:
   ```bash
   docker pull ishinokazuki/kimigayo-os:latest
   ```

2. Check Dockerfile syntax:
   ```bash
   docker build --no-cache .
   ```

### Container crashes on startup

1. Check logs:
   ```bash
   docker logs container-name
   ```

2. Run interactively:
   ```bash
   docker run -it --rm your-image /bin/sh
   ```

### Permission errors

1. Check file ownership:
   ```bash
   ls -la /path/in/container
   ```

2. Fix in Dockerfile:
   ```dockerfile
   RUN chown -R appuser:appuser /app
   ```

## Contributing

Want to add more derivative images? Please:

1. Create a new directory under `examples/`
2. Include Dockerfile, README.md, and sample application
3. Test thoroughly
4. Submit a pull request

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

## Support

- [Kimigayo OS Documentation](../docs/)
- [GitHub Issues](https://github.com/Kazuki-0731/Kimigayo/issues)
- [Docker Hub](https://hub.docker.com/r/ishinokazuki/kimigayo-os)

## License

Kimigayo OS components are licensed individually - see [LICENSE](../LICENSE) for details
