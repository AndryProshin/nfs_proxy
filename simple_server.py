# simple_server_fixed.py
from http.server import HTTPServer, SimpleHTTPRequestHandler
import os

class RangeHTTPRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        # Это самая важная строка - говорит GDAL, что поддерживаем частичное чтение
        self.send_header('Accept-Ranges', 'bytes')
        super().end_headers()
    
    def do_GET(self):
        # Просто вызываем родительский метод, он уже умеет обрабатывать Range
        super().do_GET()

# Запуск
port = 8000
server = HTTPServer(('', port), RangeHTTPRequestHandler)
print(f"Сервер на http://localhost:{port} с поддержкой Range")
print(f"Директория: {os.getcwd()}")
server.serve_forever()