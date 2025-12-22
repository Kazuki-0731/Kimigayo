#!/usr/bin/env python3
"""
Sample Python application for Kimigayo OS
A simple HTTP server using built-in http.server
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Kimigayo OS + Python</title>
            </head>
            <body>
                <h1>Welcome to Kimigayo OS + Python!</h1>
                <p>Ultra-lightweight Python runtime on Kimigayo OS</p>
                <ul>
                    <li><a href="/api/info">System Info</a></li>
                    <li><a href="/api/health">Health Check</a></li>
                </ul>
            </body>
            </html>
            """
            self.wfile.write(html.encode())

        elif self.path == '/api/info':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            info = {
                'os': 'Kimigayo OS',
                'python_version': os.sys.version,
                'platform': os.sys.platform,
            }
            self.wfile.write(json.dumps(info, indent=2).encode())

        elif self.path == '/api/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            health = {'status': 'healthy', 'service': 'kimigayo-python'}
            self.wfile.write(json.dumps(health).encode())

        else:
            self.send_response(404)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'404 Not Found')

    def log_message(self, format, *args):
        # Custom logging format
        print(f"[{self.log_date_time_string()}] {format % args}")

def run_server(port=8000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    print(f"Starting server on port {port}...")
    print(f"Visit http://localhost:{port}")
    httpd.serve_forever()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    run_server(port)
