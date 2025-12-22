# Kimigayo OS + Node.js

Node.js runtime running on Kimigayo OS - ultra-lightweight container OS.

## Features

- **Lightweight**: Based on Kimigayo OS (1-3MB base) + Node.js (~40-60MB)
- **Fast**: Optimized Node.js environment
- **Modern**: Node.js 18+ with npm support
- **Production-ready**: Health checks and graceful shutdown

## Quick Start

### Build the image

```bash
docker build -t kimigayo-nodejs:latest examples/nodejs/
```

### Run the sample application

```bash
docker run -d -p 3000:3000 \
  -v $(pwd)/examples/nodejs:/app:ro \
  kimigayo-nodejs:latest \
  node /app/app.js
```

### Test

```bash
curl http://localhost:3000
curl http://localhost:3000/api/info
curl http://localhost:3000/health
```

## Customization

### Use your own Node.js application

Create `Dockerfile`:

```dockerfile
FROM kimigayo-nodejs:latest

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy application
COPY . .

# Expose port
EXPOSE 3000

# Start application
CMD ["node", "app.js"]
```

### Express.js Example

`app.js`:
```javascript
const express = require('express');
const app = express();

app.get('/', (req, res) => {
  res.json({
    message: 'Hello from Kimigayo OS + Node.js!',
    os: 'Kimigayo OS',
    framework: 'Express.js'
  });
});

app.get('/health', (req, res) => {
  res.json({ status: 'healthy' });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
});
```

`package.json`:
```json
{
  "name": "my-express-app",
  "version": "1.0.0",
  "dependencies": {
    "express": "^4.18.2"
  }
}
```

Build and run:
```bash
docker build -t my-express-app .
docker run -d -p 3000:3000 my-express-app
```

### Fastify Example

```javascript
const fastify = require('fastify')();

fastify.get('/', async (request, reply) => {
  return {
    message: 'Hello from Kimigayo OS + Node.js!',
    os: 'Kimigayo OS',
    framework: 'Fastify'
  };
});

fastify.get('/health', async (request, reply) => {
  return { status: 'healthy' };
});

const start = async () => {
  try {
    await fastify.listen({ port: 3000, host: '0.0.0.0' });
    console.log('Server is running on port 3000');
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();
```

## Production Deployment

### Docker Compose

```yaml
version: '3.8'

services:
  nodejs-app:
    image: kimigayo-nodejs:latest
    ports:
      - "3000:3000"
    volumes:
      - ./app:/app:ro
      - /app/node_modules  # Anonymous volume for node_modules
    environment:
      - NODE_ENV=production
      - PORT=3000
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:3000/health"]
      interval: 30s
      timeout: 3s
      retries: 3
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kimigayo-nodejs-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nodejs-app
  template:
    metadata:
      labels:
        app: nodejs-app
    spec:
      containers:
      - name: nodejs-app
        image: kimigayo-nodejs:latest
        ports:
        - containerPort: 3000
        env:
        - name: NODE_ENV
          value: "production"
        - name: PORT
          value: "3000"
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: nodejs-service
spec:
  selector:
    app: nodejs-app
  ports:
  - protocol: TCP
    port: 80
    targetPort: 3000
  type: LoadBalancer
```

## Performance

Based on Kimigayo OS benchmarks:

- **Image Size**: ~50-90MB (vs 150-200MB for node:alpine)
- **Memory Usage**: 50-150MB for typical applications
- **Startup Time**: <2 seconds
- **Cold start**: ~100ms

## Environment Variables

- `NODE_ENV`: Environment (development/production)
- `PORT`: Application port (default: 3000)
- `NODE_OPTIONS`: Node.js CLI options

## Best Practices

### Multi-stage build for smaller images

```dockerfile
# Builder stage
FROM node:18-alpine AS builder
WORKDIR /build
COPY package*.json ./
RUN npm ci --only=production

# Runtime stage
FROM kimigayo-nodejs:latest
WORKDIR /app
COPY --from=builder /build/node_modules ./node_modules
COPY . .
CMD ["node", "app.js"]
```

### Use .dockerignore

```
node_modules
npm-debug.log
.git
.gitignore
README.md
.env
.DS_Store
```

### Optimize npm install

```dockerfile
# Use npm ci instead of npm install
RUN npm ci --only=production

# Clean npm cache
RUN npm cache clean --force
```

## Debugging

### Enable Node.js debugging

```bash
docker run -p 3000:3000 -p 9229:9229 \
  kimigayo-nodejs \
  node --inspect=0.0.0.0:9229 app.js
```

### View logs

```bash
docker logs -f container_name
```

### Execute commands in container

```bash
docker exec -it container_name /bin/sh
docker exec -it container_name node --version
docker exec -it container_name npm list
```

## Troubleshooting

### Module not found

Ensure dependencies are installed:
```bash
docker exec -it container_name npm install
```

### Port already in use

Change the port:
```bash
docker run -p 8080:3000 -e PORT=3000 kimigayo-nodejs
```

### Out of memory

Increase Node.js heap size:
```bash
docker run -e NODE_OPTIONS="--max-old-space-size=4096" kimigayo-nodejs
```

## Common Frameworks

Compatible with popular Node.js frameworks:

- ✅ Express.js
- ✅ Fastify
- ✅ Koa
- ✅ NestJS
- ✅ Next.js
- ✅ Socket.io

## Support

- [Kimigayo OS Documentation](../../docs/)
- [GitHub Issues](https://github.com/Kazuki-0731/Kimigayo/issues)
- [Node.js Documentation](https://nodejs.org/docs/)
