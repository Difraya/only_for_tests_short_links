import time
import random
import string
import statistics
from locust import HttpUser, task, between, events

# Глобальные переменные для хранения метрик
response_times_with_cache = []
response_times_without_cache = []

# Функция для генерации случайной строки заданной длины
def generate_random_string(length=10):
    letters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(letters) for _ in range(length))

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("Начало теста кэширования...")
    # Сбрасываем метрики при запуске теста
    global response_times_with_cache, response_times_without_cache
    response_times_with_cache = []
    response_times_without_cache = []

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("\n--- Результаты теста кэширования ---")
    if response_times_with_cache:
        avg_with_cache = statistics.mean(response_times_with_cache)
        print(f"Среднее время ответа с кэшем: {avg_with_cache:.2f} мс")
    else:
        print("Нет данных о запросах с кэшем")
        
    if response_times_without_cache:
        avg_without_cache = statistics.mean(response_times_without_cache)
        print(f"Среднее время ответа без кэша: {avg_without_cache:.2f} мс")
    else:
        print("Нет данных о запросах без кэша")
    
    if response_times_with_cache and response_times_without_cache:
        avg_with_cache = statistics.mean(response_times_with_cache)
        avg_without_cache = statistics.mean(response_times_without_cache)
        improvement = ((avg_without_cache - avg_with_cache) / avg_without_cache) * 100
        print(f"Улучшение производительности благодаря кэшированию: {improvement:.2f}%")
    
    print("-------------------------------")

class CacheTestUser(HttpUser):
    """
    Класс для тестирования эффективности кэширования
    Стратегия: создаём ссылку, затем многократно переходим по ней, 
    чтобы убедиться, что она кэшируется, и измеряем разницу во времени ответа
    """
    wait_time = between(0.1, 0.5)  # Короткие паузы для интенсивного тестирования
    
    def on_start(self):
        """Метод вызывается при запуске симуляции"""
        # Регистрация пользователя
        username = f"cachetest_{generate_random_string(8)}"
        email = f"{username}@example.com"
        password = "Password123!"
        
        # Регистрируем пользователя
        self.client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": password,
                "username": username
            },
            name="Register User (Cache Test)"
        )
        
        # Логинимся
        login_response = self.client.post(
            "/api/v1/auth/jwt/login",
            data={
                "username": email,
                "password": password
            },
            name="Login (Cache Test)"
        )
        
        self.token = login_response.json()["access_token"]
        self.auth_headers = {"Authorization": f"Bearer {self.token}"}
        
        # Создаем тестовые ссылки для кэширования
        self.create_test_links()
    
    def create_test_links(self):
        """Создаем несколько тестовых ссылок для тестирования кэширования"""
        self.test_links = []
        
        # Создаем 5 ссылок для тестирования
        for i in range(5):
            # Используем одинаковый URL-паттерн для легкой идентификации
            original_url = f"https://www.example.com/cache-test/{i}"
            
            # Создаем ссылку
            response = self.client.post(
                "/api/v1/links/shorten",
                json={"original_url": original_url},
                headers=self.auth_headers,
                name="Create Link for Cache Test"
            )
            
            if response.status_code == 201:
                response_data = response.json()
                if "short_code" in response_data:
                    self.test_links.append(response_data["short_code"])
    
    @task
    def test_cache_efficiency(self):
        """
        Тестирование эффективности кэширования путем многократного доступа
        к одной и той же ссылке и измерения времени ответа
        """
        if not hasattr(self, "test_links") or not self.test_links:
            return
        
        # Выбираем случайную ссылку из созданных для теста
        short_code = random.choice(self.test_links)
        
        # Совершаем несколько последовательных запросов к одной и той же ссылке
        for i in range(10):
            # Делаем запрос и замеряем время
            start_time = time.time()
            response = self.client.get(
                f"/{short_code}",
                name=f"Access Link (Cache Test, iteration {i+1})",
                allow_redirects=False
            )
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000  # в миллисекундах
            
            if response.status_code in [301, 302, 307, 308]:
                # Первые несколько запросов, вероятно, не кэшированы
                if i < 3:
                    response_times_without_cache.append(response_time_ms)
                else:
                    # Последующие запросы должны использовать кэш
                    response_times_with_cache.append(response_time_ms)
    
    @task
    def test_cache_invalidation(self):
        """
        Тестирование инвалидации кэша после обновления ссылки
        """
        if not hasattr(self, "test_links") or not self.test_links:
            return
        
        # Выбираем случайную ссылку из созданных для теста
        short_code = random.choice(self.test_links)
        
        # Сначала переходим по ссылке несколько раз, чтобы она попала в кэш
        for _ in range(3):
            self.client.get(
                f"/{short_code}",
                name=f"Access Link Before Update",
                allow_redirects=False
            )
        
        # Обновляем ссылку
        new_url = f"https://www.example.com/updated-cache-test/{generate_random_string(5)}"
        self.client.put(
            f"/api/v1/links/{short_code}",
            json={"original_url": new_url},
            headers=self.auth_headers,
            name="Update Link (Cache Test)"
        )
        
        # Теперь делаем запрос после обновления
        start_time = time.time()
        response = self.client.get(
            f"/{short_code}",
            name=f"Access Link After Update",
            allow_redirects=False
        )
        end_time = time.time()
        response_time_ms = (end_time - start_time) * 1000  # в миллисекундах
        
        # После обновления первый запрос должен быть без кэша
        response_times_without_cache.append(response_time_ms)
        
        # Проверяем, что URL изменился (проверка по Location заголовку)
        if response.status_code in [301, 302, 307, 308]:
            location = response.headers.get("Location", "")
            if new_url not in location:
                print(f"Warning: Expected updated URL {new_url} in Location header, but got {location}") 