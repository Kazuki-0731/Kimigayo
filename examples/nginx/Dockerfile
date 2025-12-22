# Kimigayo OS + Nginx
# Lightweight web server based on Kimigayo OS

FROM ishinokazuki/kimigayo-os:latest

LABEL maintainer="Kimigayo OS Team"
LABEL description="Nginx web server on Kimigayo OS"
LABEL version="1.0.0"

# Install dependencies using Alpine packages
# Note: Kimigayo OS follows distroless design (no package manager)
RUN apk add --no-cache nginx

# Create necessary directories
RUN mkdir -p /var/log/nginx \
    /var/lib/nginx/tmp \
    /var/www/html \
    /etc/nginx/conf.d

# Create default index.html
RUN echo '<html><body><h1>Welcome to Kimigayo OS + Nginx!</h1><p>Powered by Kimigayo OS - Ultra-lightweight container OS</p></body></html>' > /var/www/html/index.html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf
COPY default.conf /etc/nginx/conf.d/default.conf

# Expose HTTP port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

# Run nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
