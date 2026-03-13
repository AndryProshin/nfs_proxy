#!/usr/bin/env python3
"""
Полноценный HTTP сервер для работы с GDAL /vsicurl/
Поддерживает:
- Range запросы (206 Partial Content)
- HEAD запросы
- Content-Range заголовки
- Accept-Ranges: bytes
- Многопоточность
"""

from http.server import HTTPServer, ThreadingHTTPServer, BaseHTTPRequestHandler
import os
import sys
import time
import threading
from datetime import datetime
import signal

class VSICurlHandler(BaseHTTPRequestHandler):
    """Обработчик запросов, совместимый с GDAL /vsicurl/"""
    
    def do_HEAD(self):
        """Обработка HEAD запроса (проверка существования и размера)"""
        self.handle_request(method='HEAD')
    
    def do_GET(self):
        """Обработка GET запроса (с поддержкой Range)"""
        self.handle_request(method='GET')
    
    def handle_request(self, method):
        """Универсальная обработка запросов"""
        
        # Нормализация пути
        path = self.path.lstrip('/')
        if not path or '..' in path or path.startswith('/'):
            self.send_error(403, "Forbidden")
            return
        
        # Полный путь к файлу
        full_path = os.path.join(os.getcwd(), path)
        
        # Проверка существования
        if not os.path.exists(full_path):
            self.send_error(404, f"File not found: {path}")
            return
        
        if not os.path.isfile(full_path):
            self.send_error(400, "Not a regular file")
            return
        
        # Получаем размер файла
        file_size = os.path.getsize(full_path)
        last_modified = datetime.fromtimestamp(os.path.getmtime(full_path))
        
        # Парсим Range заголовок
        range_header = self.headers.get('Range', '')
        matches = range_header and method == 'GET'
        
        if matches and range_header.startswith('bytes='):
            # Разбираем диапазон
            try:
                ranges = range_header[6:].split('-')
                start = int(ranges[0]) if ranges[0] else 0
                end = int(ranges[1]) if ranges[1] else file_size - 1
                
                # Валидация
                if start < 0 or end >= file_size or start > end:
                    self.send_error(416, "Range Not Satisfiable")
                    return
                
                # Для HEAD запроса не читаем файл
                if method == 'HEAD':
                    self.send_response(206)
                    self.send_header('Content-Range', f'bytes {start}-{end}/{file_size}')
                    self.send_header('Content-Length', str(end - start + 1))
                    self.send_header('Content-Type', self.guess_type(path))
                    self.send_header('Accept-Ranges', 'bytes')
                    self.send_header('Last-Modified', self.date_time_string(last_modified.timestamp()))
                    self.end_headers()
                    return
                
                # Читаем и отправляем только запрошенный диапазон
                try:
                    with open(full_path, 'rb') as f:
                        f.seek(start)
                        data = f.read(end - start + 1)
                    
                    self.send_response(206)
                    self.send_header('Content-Range', f'bytes {start}-{end}/{file_size}')
                    self.send_header('Content-Length', str(len(data)))
                    self.send_header('Content-Type', self.guess_type(path))
                    self.send_header('Accept-Ranges', 'bytes')
                    self.send_header('Last-Modified', self.date_time_string(last_modified.timestamp()))
                    self.end_headers()
                    
                    # Отправляем данные
                    self.wfile.write(data)
                    
                    # Логирование
                    self.log_request_range(start, end, len(data), file_size)
                    
                except (BrokenPipeError, ConnectionResetError):
                    # Клиент закрыл соединение - нормально для GDAL
                    pass
                
            except ValueError:
                self.send_error(400, "Invalid Range header")
        else:
            # Запрос без Range или невалидный Range - отдаем весь файл
            if method == 'HEAD':
                self.send_response(200)
                self.send_header('Content-Length', str(file_size))
                self.send_header('Content-Type', self.guess_type(path))
                self.send_header('Accept-Ranges', 'bytes')
                self.send_header('Last-Modified', self.date_time_string(last_modified.timestamp()))
                self.end_headers()
                return
            
            # GET запрос без Range
            try:
                self.send_response(200)
                self.send_header('Content-Length', str(file_size))
                self.send_header('Content-Type', self.guess_type(path))
                self.send_header('Accept-Ranges', 'bytes')
                self.send_header('Last-Modified', self.date_time_string(last_modified.timestamp()))
                self.end_headers()
                
                with open(full_path, 'rb') as f:
                    # Отправляем чанками по 64KB
                    while True:
                        chunk = f.read(65536)
                        if not chunk:
                            break
                        try:
                            self.wfile.write(chunk)
                        except (BrokenPipeError, ConnectionResetError):
                            break
                
                self.log_request_full(file_size)
                
            except Exception as e:
                print(f"Error sending file: {e}")
    
    def guess_type(self, path):
        """Определение MIME-типа"""
        ext = os.path.splitext(path)[1].lower()
        types = {
            '.tif': 'image/tiff',
            '.tiff': 'image/tiff',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.txt': 'text/plain',
        }
        return types.get(ext, 'application/octet-stream')
    
    def log_request_range(self, start, end, length, total):
        """Логирование Range запросов"""
        timestamp = time.strftime('%H:%M:%S')
        percent = (length / total) * 100
        client = self.client_address[0]
        print(f"[{timestamp}] {client} - RANGE {start}-{end} ({length} bytes, {percent:.1f}% of {total}) - {self.path}")
    
    def log_request_full(self, size):
        """Логирование полных запросов"""
        timestamp = time.strftime('%H:%M:%S')
        client = self.client_address[0]
        print(f"[{timestamp}] {client} - FULL {size} bytes - {self.path}")
    
    def log_message(self, format, *args):
        # Подавляем стандартное логирование
        pass

def run_server(port=8000, directory=None, threaded=True):
    """Запуск сервера"""
    
    if directory:
        os.chdir(directory)
    
    # Выбираем сервер (многопоточный или обычный)
    server_class = ThreadingHTTPServer if threaded else HTTPServer
    server = server_class(('', port), VSICurlHandler)
    
    # Обработка Ctrl+C
    def signal_handler(sig, frame):
        print("\nОстанавливаем сервер...")
        server.shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    print("=" * 60)
    print(f"🌐 VSICurl-совместимый сервер запущен")
    print("=" * 60)
    print(f"📁 Директория: {os.getcwd()}")
    print(f"🔌 Порт: {port}")
    print(f"⚡ Многопоточный: {threaded}")
    print(f"📡 URL: http://localhost:{port}/")
    print(f"\nПоддерживаемые возможности:")
    print(f"  ✅ Range запросы (206 Partial Content)")
    print(f"  ✅ HEAD запросы")
    print(f"  ✅ Accept-Ranges: bytes")
    print(f"  ✅ Content-Range заголовки")
    print(f"  ✅ Правильная обработка для GDAL /vsicurl/")
    print(f"\nНажми Ctrl+C для остановки")
    print("=" * 60)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nСервер остановлен")
        server.shutdown()

if __name__ == '__main__':
    # Парсинг аргументов командной строки
    port = 8000
    directory = None
    threaded = True
    
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    if len(sys.argv) > 2:
        directory = sys.argv[2]
    if len(sys.argv) > 3:
        threaded = sys.argv[3].lower() == 'true'
    
    run_server(port, directory, threaded)