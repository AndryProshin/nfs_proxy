#!/usr/bin/env python3
# test_gdal_http.py - тестируем работу GDAL с HTTP

from osgeo import gdal
import sys
import time

def test_http_access(url):
    """Тестируем разные операции с GDAL через HTTP"""
    
    print(f"\n=== Тестируем: {url} ===\n")
    
    # 1. Открытие файла (читает только заголовок)
    print("1. Открываем файл...")
    start = time.time()
    ds = gdal.Open(url)
    open_time = time.time() - start
    print(f"   Открыто за {open_time:.3f} сек")
    
    if not ds:
        print("   ОШИБКА: Не удалось открыть файл")
        return
    
    # 2. Читаем метаданные (тоже быстро, только заголовок)
    print(f"\n2. Метаданные:")
    print(f"   Размер: {ds.RasterXSize} x {ds.RasterYSize}")
    print(f"   Бандов: {ds.RasterCount}")
    
    gt = ds.GetGeoTransform()
    if gt:
        print(f"   Геотрансформация: {gt}")
    
    # 3. Читаем маленький кусочек из середины
    print(f"\n3. Читаем маленький блок 100x100 из середины...")
    band = ds.GetRasterBand(1)
    
    x_center = ds.RasterXSize // 2
    y_center = ds.RasterYSize // 2
    
    start = time.time()
    data = band.ReadAsArray(x_center, y_center, 100, 100)
    read_time = time.time() - start
    
    print(f"   Прочитано за {read_time:.3f} сек")
    print(f"   Формат данных: {data.shape}, тип: {data.dtype}")
    print(f"   Минимум: {data.min()}, максимум: {data.max()}")
    
    # 4. Сравним с чтением большого куска
    print(f"\n4. Читаем большой блок 500x500...")
    start = time.time()
    data_big = band.ReadAsArray(0, 0, 500, 500)
    read_big_time = time.time() - start
    print(f"   Прочитано за {read_big_time:.3f} сек")
    
    # 5. Закрываем
    ds = None
    print(f"\n✓ Тест завершен")

def test_with_different_sizes(url):
    """Тестируем чтение блоков разного размера"""
    
    print("\n=== Тестирование скорости чтения разных блоков ===")
    ds = gdal.Open(url)
    band = ds.GetRasterBand(1)
    
    sizes = [(10,10), (100,100), (500,500), (1000,1000)]
    
    for xsize, ysize in sizes:
        if xsize > ds.RasterXSize or ysize > ds.RasterYSize:
            continue
            
        start = time.time()
        data = band.ReadAsArray(0, 0, xsize, ysize)
        elapsed = time.time() - start
        
        mb = (xsize * ysize * data.itemsize) / (1024*1024)
        print(f"  Блок {xsize:4} x {ysize:4} = {mb:.2f} MB, время: {elapsed:.3f} сек")
    
    ds = None

if __name__ == "__main__":
    # URL тестового файла
    base_url = "http://localhost:8000"
    
    # Укажите имя вашего файла
    filename = "srtm_90_512.tif"  # поменяйте на свой
    
    full_url = f"/vsicurl/{base_url}/{filename}"
    
    print("GDAL HTTP Access Test")
    print("=" * 50)
    print(f"Версия GDAL: {gdal.__version__}")
    
    test_http_access(full_url)
    
    # Если хотите протестировать чтение разных блоков:
    # test_with_different_sizes(full_url)