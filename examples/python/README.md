# Kimigayo OS + Python

Python runtime running on Kimigayo OS - a small container OS without a package manager.

## Features

- **Small**: 49.5MB including Python and its standard library (arm64, measured 2026-10-12; `python:alpine` is 57.4MB)
- **Python 3 from Alpine 3.24** (3.14 at the time of writing). The command is **`python3`** (there is no `python`). **pip is not in the image** - install packages in a build stage (below)
- **Runs as non-root**: `USER 65534` (nobody)
- **Health check**: `HEALTHCHECK` on `/api/health`, unbuffered output for `docker logs`

## Quick Start

### Build the image

```bash
docker build -t kimigayo-python:latest examples/python/
```

### Run the sample application

The image contains the sample [app.py](app.py) and starts it by default.

```bash
docker run -d -p 8000:8000 --name my-python kimigayo-python:latest
```

### Test

```bash
curl http://localhost:8000
curl http://localhost:8000/api/info
curl http://localhost:8000/api/health
```

## Customization

### Use your own Python application

**pip is not available in Kimigayo.** Install packages in an Alpine 3.24 build
stage (the same Python version as the example, so compiled extensions match)
into a directory, copy it, and point `PYTHONPATH` at it.

Create `Dockerfile`:

```dockerfile
# Build stage: has pip
FROM alpine:3.24 AS builder
RUN apk add --no-cache python3 py3-pip
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/stage/app/lib -r requirements.txt

# Runtime stage: Python only
FROM kimigayo-python:latest
COPY --from=builder /stage/app/lib /app/lib
ENV PYTHONPATH=/app/lib
WORKDIR /app
COPY app.py .

CMD ["python3", "app.py"]
```

Packages with C extensions that link to system libraries (e.g. a database
driver) also need those shared libraries; collect them with `ldd` as the
[Dockerfile](Dockerfile) does for `lib-dynload`.

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
flask
```

Build and run (with the Dockerfile above):
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
fastapi
uvicorn
```

Both examples were confirmed to run with the build-stage pattern above
(2026-10-12, Flask 3.1.2 / FastAPI 0.143.0). Pin versions in your own
`requirements.txt`.

## Production Deployment

### Docker Compose

```yaml
services:
  python-app:
    image: kimigayo-python:latest   # or your image built as above
    ports:
      - "8000:8000"
    environment:
      - PYTHONUNBUFFERED=1
      - PORT=8000
    command: ["python3", "app.py"]
    restart: unless-stopped
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
        image: kimigayo-python:latest   # or your image built as above
        command: ["python3", "app.py"]
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

## Image Size

| Image | Size |
|-------|------|
| `kimigayo-python` (this example) | 49.5MB |
| `python:alpine` | 57.4MB |

Measured 2026-10-12 on arm64 (`docker images`), built from
`ishinokazuki/kimigayo-os:3.0.2` and Alpine 3.24's Python 3.14.8.
`python:alpine` includes pip; this example does not.
Memory usage and startup time have not been measured.

## Environment Variables

- `PYTHONUNBUFFERED=1`: Disable Python output buffering
- `PYTHONDONTWRITEBYTECODE=1`: Don't write .pyc files
- `PYTHONPATH`: Where packages installed in the build stage live (e.g. `/app/lib`)
- `PORT`: Application port (default: 8000)

## Troubleshooting

### Module not found

Packages cannot be installed inside the running container (no pip).
Add them to `requirements.txt` and rebuild (see
[Use your own Python application](#use-your-own-python-application)).
To see what is installed:
```bash
docker exec -it my-python ls /app/lib
```

### Port already in use

Change the host port:
```bash
docker run -p 8080:8000 kimigayo-python
```

### Permission errors

The container runs as uid 65534. Mounted files must be readable by it:
```bash
chmod -R 755 ./app
```

## Support

- [Kimigayo OS Documentation](../../docs/)
- [GitHub Issues](https://github.com/Kazuki-0731/Kimigayo/issues)
- [Python Documentation](https://docs.python.org/3/)
