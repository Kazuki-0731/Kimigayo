# Kimigayo OS + Node.js
# Node.js runtime based on Kimigayo OS

FROM ishinokazuki/kimigayo-os:latest

LABEL maintainer="Kimigayo OS Team"
LABEL description="Node.js runtime on Kimigayo OS"
LABEL version="1.0.0"

# Install Node.js and npm using Alpine packages temporarily
# (In future, this will use 'isn install nodejs npm')
RUN apk add --no-cache \
    nodejs \
    npm

# Create application directory
WORKDIR /app

# Copy package files
# COPY package*.json ./

# Install dependencies
# RUN npm ci --only=production

# Copy application code
# COPY . .

# Set environment variables
ENV NODE_ENV=production
ENV PORT=3000

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost:3000/health || exit 1

# Default command
CMD ["node", "--version"]
