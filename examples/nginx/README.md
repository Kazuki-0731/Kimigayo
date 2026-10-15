# Kimigayo OS + Nginx

Nginx web server running on Kimigayo OS - a small container OS without a package manager.

## Features

- **Small**: 10.7MB including nginx (arm64, measured 2026-10-15; `nginx:alpine` is 68.5MB)
- **Runs as non-root**: `USER 65534` (nobody), listening on port 8080
- **Hardened configuration**: security headers, directory listing disabled, hidden files denied
- **Health check and logging**: `HEALTHCHECK` built in, access/error logs go to stdout/stderr (`docker logs`)

## Quick Start

### Build the image

```bash
docker build -t kimigayo-nginx:latest examples/nginx/
```

### Run the container

nginx listens on **8080** inside the container (a non-root process cannot bind
to ports below 1024).

```bash
docker run -d -p 8080:8080 --name my-nginx kimigayo-nginx:latest
```

### Test

```bash
curl http://localhost:8080
```

You should see:
```html
<html><body><h1>Welcome to Kimigayo OS + Nginx!</h1></body></html>
```

## Customization

### Add your own content

Mount your content directory (files must be readable by uid 65534):

```bash
docker run -d -p 8080:8080 \
  -v $(pwd)/my-website:/var/www/html:ro \
  kimigayo-nginx:latest
```

### Custom nginx configuration

Mount your nginx config. Keep `listen 8080` (or another port >= 1024),
`pid /tmp/nginx.pid` and do not use the `user` directive, because nginx runs
as uid 65534 (see [nginx.conf](nginx.conf) and [default.conf](default.conf)).

```bash
docker run -d -p 8080:8080 \
  -v $(pwd)/my-nginx.conf:/etc/nginx/nginx.conf:ro \
  -v $(pwd)/my-site.conf:/etc/nginx/conf.d/default.conf:ro \
  kimigayo-nginx:latest
```

## Production Deployment

### Docker Compose

Create `docker-compose.yml`:

```yaml
services:
  nginx:
    image: kimigayo-nginx:latest
    ports:
      - "80:8080"
    volumes:
      - ./html:/var/www/html:ro
    restart: unless-stopped
    # The image already has a HEALTHCHECK. BusyBox wget does not accept
    # --tries, so do not add it if you override this.
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:8080/"]
      interval: 30s
      timeout: 3s
      retries: 3
```

Run:
```bash
docker compose up -d
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kimigayo-nginx
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: kimigayo-nginx:latest
        ports:
        - containerPort: 8080
        resources:
          requests:
            memory: "64Mi"
            cpu: "100m"
          limits:
            memory: "128Mi"
            cpu: "200m"
        livenessProbe:
          httpGet:
            path: /
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: nginx-service
spec:
  selector:
    app: nginx
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
  type: LoadBalancer
```

## Image Size

| Image | Size |
|-------|------|
| `kimigayo-nginx` (this example) | 10.7MB |
| `nginx:alpine` | 68.5MB |

Measured 2026-10-15 on arm64 (`docker images`), built from
`ishinokazuki/kimigayo-os:3.1.0` and Alpine 3.24's nginx 1.30.4.
Memory usage and startup time have not been measured.

## Security

Built-in security features:

- Runs as non-root (uid 65534)
- Security headers enabled
- Directory listing disabled
- Hidden files access denied

**nginx itself comes from Alpine's package at build time.** Updates to
Kimigayo OS do not update it; rebuild the image to pick up a newer nginx.

## Monitoring

### Logs

Access and error logs are written to stdout/stderr:

```bash
docker logs my-nginx
```

### Nginx status

```bash
docker exec my-nginx nginx -t  # Test configuration
docker exec my-nginx nginx -s reload  # Reload config
```

## Troubleshooting

### Container won't start

Check logs:
```bash
docker logs my-nginx
```

### Permission issues

Ensure your content directory is readable by uid 65534:
```bash
chmod -R 755 ./html
```

### Configuration errors

Test nginx configuration:
```bash
docker exec my-nginx nginx -t
```

## Support

- [Kimigayo OS Documentation](../../docs/)
- [GitHub Issues](https://github.com/Kazuki-0731/Kimigayo/issues)
- [Docker Hub](https://hub.docker.com/r/ishinokazuki/kimigayo-os)
