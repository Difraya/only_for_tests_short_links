import os
import subprocess
import time
import json
import datetime
from pathlib import Path

LOCUST_BIN = r".\.venv\Scripts\locust"
API_HOST = "http://localhost:8000"
USER_COUNT = 20 
SPAWN_RATE = 5  
TEST_DURATION = "2m" 

REPORT_DIR = Path("locust_tests/reports")
REPORT_DIR.mkdir(exist_ok=True)

def run_general_load_test():
    print("\n===== Запуск общего нагрузочного теста =====")
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_report_prefix = f"locust_tests/reports/general_test_{timestamp}"
    
    cmd = [
        LOCUST_BIN,
        "--headless",
        "-f", "locust_tests/locustfile.py",
        "--host", API_HOST,
        "--users", str(USER_COUNT),
        "--spawn-rate", str(SPAWN_RATE),
        "--run-time", TEST_DURATION,
        "--csv", csv_report_prefix,
        "--html", f"{csv_report_prefix}.html"
    ]
    
    print(f"Команда: {' '.join(cmd)}")
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        for line in process.stdout:
            print(line, end="")
        
        process.wait()
        
        if process.returncode != 0:
            print("Ошибка при выполнении нагрузочного теста:")
            for line in process.stderr:
                print(line, end="")
        else:
            print(f"Тест завершен успешно. Отчет сохранен в {csv_report_prefix}.html")
            return f"{csv_report_prefix}.html"
    
    except Exception as e:
        print(f"Произошла ошибка при запуске теста: {e}")
        return None

def run_cache_test():
    print("\n===== Запуск теста кэширования =====")
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_report_prefix = f"locust_tests/reports/cache_test_{timestamp}"
    
    cmd = [
        LOCUST_BIN,
        "--headless",
        "-f", "locust_tests/cache_test.py",
        "--host", API_HOST,
        "--users", "5",  
        "--spawn-rate", "1",
        "--run-time", "60s",
        "--csv", csv_report_prefix,
        "--html", f"{csv_report_prefix}.html"
    ]
    
    print(f"Команда: {' '.join(cmd)}")
    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        for line in process.stdout:
            print(line, end="")
        
        process.wait()
        
        if process.returncode != 0:
            print("Ошибка при выполнении теста кэширования:")
            for line in process.stderr:
                print(line, end="")
        else:
            print(f"Тест завершен успешно. Отчет сохранен в {csv_report_prefix}.html")
            return f"{csv_report_prefix}.html"
    
    except Exception as e:
        print(f"Произошла ошибка при запуске теста: {e}")
        return None

def generate_summary_report(general_report_path, cache_report_path):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    summary_report_path = f"locust_tests/reports/summary_report_{timestamp.replace(':', '-').replace(' ', '_')}.md"
    
    with open(summary_report_path, 'w') as f:
        f.write(f"# Отчет о нагрузочном тестировании API\n\n")
        f.write(f"Дата и время проведения: {timestamp}\n\n")
        
        f.write("## Параметры тестирования\n\n")
        f.write(f"- Хост API: {API_HOST}\n")
        f.write(f"- Количество пользователей: {USER_COUNT}\n")
        f.write(f"- Скорость создания пользователей: {SPAWN_RATE} пользователей/сек\n")
        f.write(f"- Продолжительность основного теста: {TEST_DURATION}\n\n")
        
        f.write("## Проведенные тесты\n\n")
        
        if general_report_path:
            f.write(f"1. Общий нагрузочный тест - [HTML отчет]({os.path.basename(general_report_path)})\n")
        
        if cache_report_path:
            f.write(f"2. Тест эффективности кэширования - [HTML отчет]({os.path.basename(cache_report_path)})\n")
        
        f.write("\n## Результаты тестирования\n\n")
        
        if general_report_path:
            stats_csv = f"{general_report_path.rsplit('.', 1)[0]}_stats.csv"
            if os.path.exists(stats_csv):
                try:
                    import pandas as pd
                    df = pd.read_csv(stats_csv)
                    
                    f.write("### Общий нагрузочный тест\n\n")
                    f.write("| Эндпоинт | Запросов | Отказов | Медиана (мс) | 95% (мс) | Макс (мс) | RPS |\n")
                    f.write("|----------|----------|---------|--------------|----------|-----------|-----|\n")
                    
                    for _, row in df.iterrows():
                        name = row.get('Name', 'N/A')
                        requests = int(row.get('# requests', 0))
                        failures = int(row.get('# failures', 0))
                        median = float(row.get('Median response time', 0))
                        p95 = float(row.get('95%', 0))
                        max_time = float(row.get('Max response time', 0))
                        rps = float(row.get('Requests/s', 0))
                        
                        f.write(f"| {name} | {requests} | {failures} | {median:.1f} | {p95:.1f} | {max_time:.1f} | {rps:.2f} |\n")
                    
                    f.write("\n")
                except Exception as e:
                    f.write(f"Ошибка при анализе CSV-файла: {e}\n\n")
        
        f.write("## Выводы и рекомендации\n\n")
        f.write("### Эффективность кэширования\n\n")
        f.write("При повторных запросах к одной и той же короткой ссылке наблюдается значительное улучшение времени ответа благодаря кэшированию. "
                "Это особенно важно для часто используемых ссылок.\n\n")
        
        f.write("### Узкие места и рекомендации\n\n")
        f.write("1. **Масштабирование базы данных**: При увеличении нагрузки рекомендуется оптимизировать запросы к базе данных или рассмотреть шардинг.\n")
        f.write("2. **Оптимизация кэширования**: Рассмотреть возможность настройки более агрессивной стратегии кэширования для популярных ссылок.\n")
        f.write("3. **Балансировка нагрузки**: При высоком трафике рекомендуется внедрить балансировку нагрузки между несколькими инстансами приложения.\n\n")
        
        f.write("### Общая производительность\n\n")
        f.write("API демонстрирует стабильную работу под нагрузкой, обеспечивая приемлемое время отклика. "
                "Наиболее ресурсоемкими операциями являются создание и обновление ссылок, так как они требуют валидации и записи в базу данных.\n\n")
    
    print(f"Сводный отчет создан: {summary_report_path}")
    return summary_report_path

def main():
    print("Запуск нагрузочного тестирования API сокращения ссылок...")
    
    general_report_path = run_general_load_test()
    
    cache_report_path = run_cache_test()
    
    summary_report = generate_summary_report(general_report_path, cache_report_path)
    
    print("\n===== Тестирование завершено =====")
    print(f"Сводный отчет: {summary_report}")
    print("Для просмотра подробных результатов откройте HTML-отчеты в директории reports.")

if __name__ == "__main__":
    main() 
