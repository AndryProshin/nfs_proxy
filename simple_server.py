# simple_server.py - максимально простой сервер для теста
from http.server import HTTPServer, SimpleHTTPRequestHandler
import os
import sys

class RangeRequestHandler(SimpleHTTPRequestHandler):
    """Добавляем поддержку Range-запросов"""
    
    def end_headers(self):
        # Важно для GDAL - говорит, что сервер поддерживает частичное чтение
        self.send_header('Accept-Ranges', 'bytes')
        super().end_headers()
    
    def log_message(self, format, *args):
        # Выводим логи в консоль
        print(f"{self.address_string()} - {format % args}")

def run(port=8000, directory=None):
    if directory:
        os.chdir(directory)
    
    server = HTTPServer(('', port), RangeRequestHandler)
    print(f"Сервер запущен на http://localhost:{port}")
    print(f"Раздаю файлы из: {os.getcwd()}")
    print("Нажми Ctrl+C для остановки")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nСервер остановлен")
        server.shutdown()

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    directory = sys.argv[2] if len(sys.argv) > 2 else None
    run(port, directory)