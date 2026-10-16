# Kimigayo OS + Node.js

Node.js runtime running on Kimigayo OS - a small container OS without a package manager.

## Features

- **Small**: 73.0MB including Node.js and its shared libraries (arm64, measured 2026-10-15; `node:alpine` is 181MB)
- **Node.js from Alpine 3.24** (v24 at the time of writing). **npm is not in the image** - install dependencies in a build stage (below)
- **Runs as non-root**: `USER 65534` (nobody)
- **Health check and graceful shutdown**: `HEALTHCHECK` on `/health`, `SIGTERM` closes the server

## Quick Start

### Build the image

```bash
docker build -t kimigayo-nodejs:latest examples/nodejs/
```

### Run the sample application

The image contains the sample [app.js](app.js) and starts it by default.

```bash
docker run -d -p 3000:3000 --name my-node kimigayo-nodejs:latest
```

### Test

```bash
curl http://localhost:3000
curl http://localhost:3000/api/info
curl http://localhost:3000/health
```

## Customization

### Use your own Node.js application

**npm is not available in Kimigayo.** Install `node_modules` in an Alpine 3.24
build stage (the same Alpine version the example takes Node.js from, so native
modules match) and copy the result. `npm ci` needs a `package-lock.json`.

Create `Dockerfile`:

```dockerfile
# Build stage: has npm
FROM alpine:3.24 AS builder
RUN apk add --no-cache nodejs npm
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev
COPY . .

# Runtime stage: Node.js only
FROM kimigayo-nodejs:latest
WORKDIR /app
COPY --from=builder /app /app

EXPOSE 3000
CMD ["node", "app.js"]
```

Add `node_modules` to `.dockerignore` so the host's copy is not sent.

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
    "express": "^4.21.2"
  }
}
```

Build and run (with the Dockerfile above):
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
services:
  nodejs-app:
    image: kimigayo-nodejs:latest   # or your image built as above
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - PORT=3000
    command: ["node", "app.js"]
    restart: unless-stopped
    # BusyBox wget does not accept --tries
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:3000/health"]
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
        image: kimigayo-nodejs:latest   # or your image built as above
        command: ["node", "app.js"]
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

## Image Size

| Image | Size |
|-------|------|
| `kimigayo-nodejs` (this example) | 73.0MB |
| `node:alpine` | 181MB |

Measured 2026-10-15 on arm64 (`docker images`), built from
`ishinokazuki/kimigayo-os:3.2.0` and Alpine 3.24's Node.js v24.18.1.
`node:alpine` includes npm; this example does not.
Memory usage and startup time have not been measured.

## Environment Variables

- `NODE_ENV`: Environment (development/production)
- `PORT`: Application port (default: 3000)
- `NODE_OPTIONS`: Node.js CLI options

## Best Practices

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

### Install dependencies in the build stage

Use `npm ci --omit=dev` (not the deprecated `--only=production`) in the
build stage. The npm cache stays in the build stage, so there is nothing
to clean up in the final image.

## Debugging

### Enable Node.js debugging

```bash
docker run -p 3000:3000 -p 9229:9229 \
  kimigayo-nodejs \
  node --inspect=0.0.0.0:9229 app.js
```

### View logs

```bash
docker logs -f my-node
```

### Execute commands in container

```bash
docker exec -it my-node /bin/sh
docker exec -it my-node node --version
```

## Troubleshooting

### Module not found

Dependencies cannot be installed inside the running container (no npm).
Add them to `package.json` and rebuild the image (see
[Use your own Node.js application](#use-your-own-nodejs-application)).

### Port already in use

Change the host port:
```bash
docker run -p 8080:3000 kimigayo-nodejs
```

### Out of memory

Set the heap size below the container's memory limit:
```bash
docker run --memory=512m -e NODE_OPTIONS="--max-old-space-size=384" kimigayo-nodejs
```

## Common Frameworks

Express.js has been confirmed to run with the build-stage pattern above
(2026-10-12). Other pure-JavaScript frameworks should work the same way;
packages with native add-ons must be built in the Alpine 3.24 stage and may
need extra shared libraries (collect them with `ldd`, as the
[Dockerfile](Dockerfile) does for Node.js).

## Support

- [Kimigayo OS Documentation](../../docs/)
- [GitHub Issues](https://github.com/Kazuki-0731/Kimigayo/issues)
- [Node.js Documentation](https://nodejs.org/docs/)
