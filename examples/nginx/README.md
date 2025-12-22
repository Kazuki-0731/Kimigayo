# Kimigayo OS + Nginx

Nginx web server running on Kimigayo OS - ultra-lightweight container OS.

## Features

- **Lightweight**: Based on Kimigayo OS (1-3MB base)
- **Fast**: Optimized nginx configuration
- **Secure**: Security headers and hardened configuration
- **Production-ready**: Health checks and logging configured

## Quick Start

### Build the image

```bash
docker build -t kimigayo-nginx:latest examples/nginx/
```

### Run the container

```bash
docker run -d -p 8080:80 --name my-nginx kimigayo-nginx:latest
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

Mount your content directory:

```bash
docker run -d -p 8080:80 \
  -v $(pwd)/my-website:/var/www/html:ro \
  kimigayo-nginx:latest
```

### Custom nginx configuration

Mount your nginx config:

```bash
docker run -d -p 8080:80 \
  -v $(pwd)/my-nginx.conf:/etc/nginx/nginx.conf:ro \
  -v $(pwd)/my-site.conf:/etc/nginx/conf.d/default.conf:ro \
  kimigayo-nginx:latest
```

## Production Deployment

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  nginx:
    image: kimigayo-nginx:latest
    ports:
      - "80:80"
    volumes:
      - ./html:/var/www/html:ro
      - ./logs:/var/log/nginx
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost/"]
      interval: 30s
      timeout: 3s
      retries: 3
```

Run:
```bash
docker-compose up -d
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
        - containerPort: 80
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
            port: 80
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
    targetPort: 80
  type: LoadBalancer
```

## Performance

Based on Kimigayo OS benchmarks:

- **Image Size**: ~10-15MB (vs 140MB for nginx:alpine)
- **Memory Usage**: ~30-50MB under load
- **Startup Time**: <2 seconds

## Security

Built-in security features:

- No root user execution
- Security headers enabled
- Directory listing disabled
- Hidden files access denied
- Regular security updates via Kimigayo OS

## Monitoring

### Access logs

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

Ensure your content directory has correct permissions:
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
