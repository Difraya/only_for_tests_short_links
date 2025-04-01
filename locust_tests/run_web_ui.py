import subprocess
import webbrowser
import time
import sys

# Константы
LOCUST_BIN = r".\.venv\Scripts\locust"
API_HOST = "http://localhost:8000"
LOCUST_PORT = 8089
LOCUST_WEB_URL = f"http://localhost:{LOCUST_PORT}"

def run_locust_web_ui(test_file="locustfile.py"):
    """
    Запускает веб-интерфейс Locust для интерактивного управления тестами
    """
    print(f"Запуск веб-интерфейса Locust для файла {test_file}...")
    
    # Формируем команду
    cmd = [
        LOCUST_BIN,
        "-f", f"locust_tests/{test_file}",
        "--host", API_HOST,
        "--web-port", str(LOCUST_PORT)
    ]
    
    print(f"Команда: {' '.join(cmd)}")
    
    try:
        # Запускаем процесс Locust
        process = subprocess.Popen(cmd)
        
        # Даем немного времени для запуска веб-сервера
        print(f"Ожидание запуска веб-интерфейса на порту {LOCUST_PORT}...")
        time.sleep(2)
        
        # Открываем браузер с веб-интерфейсом
        print(f"Открытие веб-интерфейса в браузере: {LOCUST_WEB_URL}")
        webbrowser.open(LOCUST_WEB_URL)
        
        print("\nИнтерфейс запущен! Нажмите Ctrl+C для завершения работы.")
        
        # Ждем нажатия Ctrl+C для завершения
        process.wait()
    
    except KeyboardInterrupt:
        print("\nПолучен сигнал прерывания. Завершение работы...")
        # Завершаем процесс Locust
        process.terminate()
        process.wait()
    except Exception as e:
        print(f"Произошла ошибка при запуске веб-интерфейса: {e}")
        if 'process' in locals():
            process.terminate()
            process.wait()
        sys.exit(1)

def main():
    """
    Главная функция
    """
    # Проверяем наличие аргументов командной строки
    if len(sys.argv) > 1:
        if sys.argv[1] == "cache":
            # Запускаем тест кэширования
            run_locust_web_ui("cache_test.py")
        else:
            # Предполагаем, что это имя файла теста
            run_locust_web_ui(sys.argv[1])
    else:
        # По умолчанию запускаем основной тестовый файл
        run_locust_web_ui()

if __name__ == "__main__":
    main() 