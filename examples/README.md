# Kimigayo OS - Derivative Images

This directory contains sample derivative images built on top of Kimigayo OS.

## Available Images

### 1. **Nginx** - Web Server
- **Directory**: `nginx/`
- **Base Size**: ~10-15MB
- **Use Case**: Static websites, reverse proxy, load balancer
- **Documentation**: [nginx/README.md](nginx/README.md)

**Quick Start:**
```bash
docker build -t kimigayo-nginx examples/nginx/
docker run -d -p 8080:80 kimigayo-nginx
```

### 2. **Python** - Python Runtime
- **Directory**: `python/`
- **Base Size**: ~50-80MB
- **Use Case**: Web APIs, data processing, automation scripts
- **Documentation**: [python/README.md](python/README.md)

**Quick Start:**
```bash
docker build -t kimigayo-python examples/python/
docker run -d -p 8000:8000 \
  -v $(pwd)/examples/python/app.py:/app/app.py \
  kimigayo-python python /app/app.py
```

### 3. **Node.js** - JavaScript Runtime
- **Directory**: `nodejs/`
- **Base Size**: ~50-90MB
- **Use Case**: Web applications, APIs, real-time services
- **Documentation**: [nodejs/README.md](nodejs/README.md)

**Quick Start:**
```bash
docker build -t kimigayo-nodejs examples/nodejs/
docker run -d -p 3000:3000 \
  -v $(pwd)/examples/nodejs:/app \
  kimigayo-nodejs node /app/app.js
```

## Size Comparison

| Image | Kimigayo OS | Traditional Alpine | Traditional Debian |
|-------|-------------|--------------------|--------------------|
| **Base OS** | 1-3MB | 7-8MB | 95MB |
| **+ Nginx** | ~10-15MB | ~40MB | ~140MB |
| **+ Python** | ~50-80MB | ~150MB | ~350MB |
| **+ Node.js** | ~50-90MB | ~150MB | ~400MB |

**Savings**: 60-70% smaller than Alpine-based images

## Common Patterns

### Multi-stage Builds

Reduce final image size by building in one stage and copying to runtime stage:

```dockerfile
# Builder stage
FROM python:3.11-alpine AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Runtime stage
FROM ishinokazuki/kimigayo-os:latest
COPY --from=builder /root/.local /usr/local
WORKDIR /app
COPY . .
CMD ["python", "app.py"]
```

### Development vs Production

**Development** (with shell access):
```dockerfile
FROM ishinokazuki/kimigayo-os:standard
# ... install tools ...
CMD ["/bin/sh"]
```

**Production** (minimal):
```dockerfile
FROM ishinokazuki/kimigayo-os:minimal
# ... only runtime deps ...
CMD ["./app"]
```

## Creating Your Own Derivative Image

### Step 1: Create Dockerfile

```dockerfile
FROM ishinokazuki/kimigayo-os:latest

# Install your dependencies
RUN apk add --no-cache your-package

# Copy application
COPY . /app
WORKDIR /app

# Set up runtime
EXPOSE 8080
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

   FROM ishinokazuki/kimigayo-os:latest
   COPY --from=build /app /app
   ```

3. **Layer caching**
   ```dockerfile
   # Copy dependencies first
   COPY requirements.txt .
   RUN pip install -r requirements.txt

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
   FROM ishinokazuki/kimigayo-os:0.1.0
   # not :latest in production
   ```

3. **Scan for vulnerabilities**
   ```bash
   trivy image your-image:latest
   ```

### Performance

1. **Minimize layers**
   ```dockerfile
   RUN apk add --no-cache \
       package1 \
       package2 \
       package3
   ```

2. **Clean up in same layer**
   ```dockerfile
   RUN apk add --no-cache build-deps && \
       # ... build ... && \
       apk del build-deps
   ```

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
# Health check
docker run --rm test-image wget --spider localhost:8080

# Integration tests
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
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
        run: docker run --rm my-image test

      - name: Push to registry
        run: |
          echo "${{ secrets.DOCKER_PASSWORD }}" | docker login -u "${{ secrets.DOCKER_USERNAME }}" --password-stdin
          docker push my-image
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

GPL-2.0 - See [LICENSE](../LICENSE) for details
