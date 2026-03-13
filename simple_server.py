# for whole files only

from http.server import HTTPServer, BaseHTTPRequestHandler
import os

class MinimalHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        filename = self.path.lstrip('/')
        try:
            with open(filename, 'rb') as f:
                self.send_response(200)
                self.send_header('Content-Type', 'image/tiff')
                self.send_header('Content-Length', str(os.path.getsize(filename)))
                self.end_headers()
                self.wfile.write(f.read())
        except:
            self.send_error(404)

print("Сервер на порту 8000 (без Range, но GDAL будет работать с GDAL_HTTP_SUPPORTED_RANGE=NO)")
HTTPServer(('', 8000), MinimalHandler).serve_forever()