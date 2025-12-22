# Kimigayo OS + Python
# Python runtime based on Kimigayo OS

FROM ishinokazuki/kimigayo-os:latest

LABEL maintainer="Kimigayo OS Team"
LABEL description="Python runtime on Kimigayo OS"
LABEL version="1.0.0"

# Install Python and pip using Alpine packages
# Note: Kimigayo OS follows distroless design (no package manager)
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-setuptools \
    py3-wheel

# Create symbolic link for python command
RUN ln -sf /usr/bin/python3 /usr/bin/python

# Upgrade pip
RUN pip3 install --no-cache-dir --upgrade pip

# Create application directory
WORKDIR /app

# Copy requirements file (if exists)
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
# COPY app.py .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose port (default for Flask/FastAPI)
EXPOSE 8000

# Default command
CMD ["python3", "--version"]
