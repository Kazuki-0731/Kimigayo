/**
 * Sample Node.js application for Kimigayo OS
 * A simple HTTP server using built-in http module
 */

const http = require('http');
const url = require('url');

const PORT = process.env.PORT || 3000;
const HOST = '0.0.0.0';

// Request handler
const requestHandler = (req, res) => {
  const parsedUrl = url.parse(req.url, true);
  const pathname = parsedUrl.pathname;

  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  // Handle OPTIONS for CORS
  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }

  // Route: Home
  if (pathname === '/' && req.method === 'GET') {
    res.writeHead(200, { 'Content-Type': 'text/html' });
    res.end(`
      <!DOCTYPE html>
      <html>
      <head>
        <title>Kimigayo OS + Node.js</title>
        <style>
          body { font-family: Arial, sans-serif; margin: 50px; }
          h1 { color: #333; }
          ul { margin-top: 20px; }
          a { color: #0066cc; text-decoration: none; }
          a:hover { text-decoration: underline; }
        </style>
      </head>
      <body>
        <h1>Welcome to Kimigayo OS + Node.js!</h1>
        <p>Ultra-lightweight Node.js runtime on Kimigayo OS</p>
        <h2>API Endpoints:</h2>
        <ul>
          <li><a href="/api/info">/api/info</a> - System information</li>
          <li><a href="/health">/health</a> - Health check</li>
        </ul>
      </body>
      </html>
    `);
    return;
  }

  // Route: System Info
  if (pathname === '/api/info' && req.method === 'GET') {
    const info = {
      os: 'Kimigayo OS',
      node_version: process.version,
      platform: process.platform,
      arch: process.arch,
      uptime: process.uptime(),
      memory: {
        total: Math.round(require('os').totalmem() / 1024 / 1024) + 'MB',
        free: Math.round(require('os').freemem() / 1024 / 1024) + 'MB',
        used: Math.round(process.memoryUsage().rss / 1024 / 1024) + 'MB'
      }
    };

    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(info, null, 2));
    return;
  }

  // Route: Health Check
  if (pathname === '/health' && req.method === 'GET') {
    const health = {
      status: 'healthy',
      service: 'kimigayo-nodejs',
      timestamp: new Date().toISOString()
    };

    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(health));
    return;
  }

  // 404 Not Found
  res.writeHead(404, { 'Content-Type': 'text/plain' });
  res.end('404 Not Found');
};

// Create server
const server = http.createServer(requestHandler);

// Start server
server.listen(PORT, HOST, () => {
  console.log(`Server running on http://${HOST}:${PORT}`);
  console.log(`Node.js version: ${process.version}`);
  console.log(`Platform: ${process.platform}`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('SIGTERM received, shutting down gracefully...');
  server.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
});

process.on('SIGINT', () => {
  console.log('SIGINT received, shutting down gracefully...');
  server.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
});
