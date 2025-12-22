# Kimigayo OS + Python

Python runtime running on Kimigayo OS - ultra-lightweight container OS.

## Features

- **Lightweight**: Based on Kimigayo OS (1-3MB base) + Python (~40-50MB)
- **Fast**: Optimized Python environment
- **Modern**: Python 3.x with pip support
- **Production-ready**: Environment variables and logging configured

## Quick Start

### Build the image

```bash
docker build -t kimigayo-python:latest examples/python/
```

### Run the sample application

```bash
docker run -d -p 8000:8000 \
  -v $(pwd)/examples/python/app.py:/app/app.py:ro \
  kimigayo-python:latest \
  python /app/app.py
```

### Test

```bash
curl http://localhost:8000
curl http://localhost:8000/api/info
curl http://localhost:8000/api/health
```

## Customization

### Use your own Python application

Create `Dockerfile`:

```dockerfile
FROM kimigayo-python:latest

WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Run application
CMD ["python", "app.py"]
```

### Flask Example

```python
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        'message': 'Hello from Kimigayo OS + Python!',
        'os': 'Kimigayo OS'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
```

Requirements:
```txt
flask==3.0.0
```

Build and run:
```bash
docker build -t my-flask-app .
docker run -d -p 8000:8000 my-flask-app
```

### FastAPI Example

```python
from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Kimigayo OS API")

@app.get("/")
def read_root():
    return {
        "message": "Hello from Kimigayo OS + Python!",
        "os": "Kimigayo OS",
        "framework": "FastAPI"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

Requirements:
```txt
fastapi==0.104.1
uvicorn==0.24.0
```

## Production Deployment

### Docker Compose

```yaml
version: '3.8'

services:
  python-app:
    image: kimigayo-python:latest
    ports:
      - "8000:8000"
    volumes:
      - ./app:/app:ro
    environment:
      - PYTHONUNBUFFERED=1
      - PORT=8000
    restart: unless-stopped
    command: python /app/app.py
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kimigayo-python-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: python-app
  template:
    metadata:
      labels:
        app: python-app
    spec:
      containers:
      - name: python-app
        image: kimigayo-python:latest
        ports:
        - containerPort: 8000
        env:
        - name: PYTHONUNBUFFERED
          value: "1"
        - name: PORT
          value: "8000"
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "500m"
```

## Performance

Based on Kimigayo OS benchmarks:

- **Image Size**: ~50-80MB (vs 150-200MB for python:alpine)
- **Memory Usage**: 50-100MB for simple applications
- **Startup Time**: <3 seconds

## Environment Variables

- `PYTHONUNBUFFERED=1`: Disable Python output buffering
- `PYTHONDONTWRITEBYTECODE=1`: Don't write .pyc files
- `PORT`: Application port (default: 8000)

## Best Practices

### Multi-stage build for smaller images

```dockerfile
# Builder stage
FROM python:3.11-alpine AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Runtime stage
FROM kimigayo-python:latest
COPY --from=builder /root/.local /usr/local
WORKDIR /app
COPY app.py .
CMD ["python", "app.py"]
```

### Use virtual environments

```dockerfile
FROM kimigayo-python:latest

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "app.py"]
```

## Troubleshooting

### Module not found

Ensure all dependencies are in `requirements.txt` and installed:
```bash
docker exec -it container_name pip list
```

### Port already in use

Change the port:
```bash
docker run -p 8080:8000 kimigayo-python
```

### Permission errors

Check file permissions in mounted volumes:
```bash
chmod -R 755 ./app
```

## Support

- [Kimigayo OS Documentation](../../docs/)
- [GitHub Issues](https://github.com/Kazuki-0731/Kimigayo/issues)
- [Python Documentation](https://docs.python.org/3/)
