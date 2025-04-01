import time
import random
import string
import json
from locust import HttpUser, task, between, tag, events

# Функция для генерации случайной строки заданной длины
def generate_random_string(length=10):
    letters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(letters) for _ in range(length))

# Вспомогательная функция для генерации случайного URL
def generate_random_url():
    domains = ["example.com", "test.org", "demo.net", "sample.io"]
    paths = ["products", "articles", "users", "posts", "categories", "news"]
    
    domain = random.choice(domains)
    path_length = random.randint(1, 3)
    path_segments = [random.choice(paths) for _ in range(path_length)]
    
    path = "/".join(path_segments)
    
    # Добавляем возможные GET-параметры
    has_params = random.choice([True, False])
    url = f"https://www.{domain}/{path}"
    
    if has_params:
        params_count = random.randint(1, 3)
        params = []
        for _ in range(params_count):
            param_name = generate_random_string(5)
            param_value = generate_random_string(8)
            params.append(f"{param_name}={param_value}")
        
        url += "?" + "&".join(params)
    
    return url

# Глобальные переменные для хранения созданных данных
active_users = []
short_codes = []

class ShortLinkUser(HttpUser):
    """
    Класс имитирует поведение пользователей API сокращения ссылок
    """
    wait_time = between(1, 5)  # Паузы между выполнением задач (в секундах)
    
    def on_start(self):
        """Метод вызывается при запуске симуляции для каждого пользователя"""
        # Регистрация пользователя
        username = f"testuser_{generate_random_string(8)}"
        email = f"{username}@example.com"
        password = "Password123!"
        
        user_data = {
            "email": email,
            "password": password,
            "username": username
        }
        
        # Регистрируем пользователя
        register_response = self.client.post(
            "/api/v1/auth/register",
            json=user_data,
            name="/api/v1/auth/register"
        )
        
        # Если регистрация успешна, выполняем вход
        if register_response.status_code == 201:
            login_response = self.client.post(
                "/api/v1/auth/jwt/login",
                data={
                    "username": email,
                    "password": password
                },
                name="/api/v1/auth/jwt/login"
            )
            
            if login_response.status_code == 200:
                self.token = login_response.json()["access_token"]
                self.auth_headers = {"Authorization": f"Bearer {self.token}"}
                self.email = email
                self.password = password
                self.username = username
                
                # Добавляем пользователя в глобальный список
                user_info = {
                    "email": email,
                    "token": self.token,
                    "auth_headers": self.auth_headers
                }
                active_users.append(user_info)
    
    @tag("create")
    @task(5)  # Высокий приоритет (5 из 10)
    def create_short_link(self):
        """Создание новой короткой ссылки"""
        if not hasattr(self, "auth_headers"):
            return
        
        # Генерируем случайный URL
        original_url = generate_random_url()
        
        # С вероятностью 20% добавляем пользовательский алиас
        use_custom_alias = random.random() < 0.2
        custom_alias = generate_random_string(6) if use_custom_alias else None
        
        # С вероятностью 30% добавляем срок действия
        use_expiration = random.random() < 0.3
        expires_at = None
        if use_expiration:
            # Срок действия от 1 часа до 30 дней
            expiration_hours = random.randint(1, 30 * 24)
            current_time = time.time()
            expires_at_timestamp = current_time + expiration_hours * 3600
            # Преобразуем в формат ISO
            import datetime
            expires_at = datetime.datetime.fromtimestamp(expires_at_timestamp).strftime("%Y-%m-%dT%H:%M:%S")
        
        # Формируем JSON для запроса
        link_data = {"original_url": original_url}
        if custom_alias:
            link_data["custom_alias"] = custom_alias
        if expires_at:
            link_data["expires_at"] = expires_at
        
        # Делаем запрос
        with self.client.post(
            "/api/v1/links/shorten",
            json=link_data,
            headers=self.auth_headers,
            name="/api/v1/links/shorten",
            catch_response=True
        ) as response:
            if response.status_code == 201:
                # Если запрос успешен, сохраняем короткий код для последующих запросов
                response_data = response.json()
                if "short_code" in response_data:
                    short_code = response_data["short_code"]
                    short_codes.append(short_code)
                    response.success()
                else:
                    response.failure("Response does not contain short_code")
            else:
                response.failure(f"Failed to create short link: {response.status_code}")
    
    @tag("redirect")
    @task(3)  # Средний приоритет (3 из 10)
    def redirect_to_original(self):
        """Переход по короткой ссылке"""
        if not short_codes:
            return
        
        # Случайно выбираем короткий код из имеющихся
        short_code = random.choice(short_codes)
        
        # Осуществляем переход
        with self.client.get(
            f"/{short_code}",
            name="/{short_code}",
            allow_redirects=False,  # Не следуем за редиректом
            catch_response=True
        ) as response:
            # Проверяем, что получен редирект (статус 307 или 308)
            if response.status_code in [301, 302, 307, 308]:
                response.success()
            else:
                response.failure(f"Redirect failed: {response.status_code}")
    
    @tag("stats")
    @task(1)  # Низкий приоритет (1 из 10)
    def get_link_stats(self):
        """Получение статистики ссылки"""
        if not hasattr(self, "auth_headers") or not short_codes:
            return
        
        # Случайно выбираем короткий код из имеющихся
        short_code = random.choice(short_codes)
        
        # Запрашиваем статистику
        with self.client.get(
            f"/api/v1/links/{short_code}/stats",
            headers=self.auth_headers,
            name="/api/v1/links/{short_code}/stats",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                # Ссылка могла быть удалена другим пользователем
                # Удаляем код из списка
                if short_code in short_codes:
                    short_codes.remove(short_code)
                response.success()
            else:
                response.failure(f"Failed to get stats: {response.status_code}")
    
    @tag("update")
    @task(1)  # Низкий приоритет (1 из 10)
    def update_link(self):
        """Обновление ссылки"""
        if not hasattr(self, "auth_headers") or not short_codes:
            return
        
        # Случайно выбираем короткий код из имеющихся
        short_code = random.choice(short_codes)
        
        # Генерируем новый URL
        new_url = generate_random_url()
        
        # Формируем данные для обновления
        update_data = {"original_url": new_url}
        
        # Обновляем ссылку
        with self.client.put(
            f"/api/v1/links/{short_code}",
            json=update_data,
            headers=self.auth_headers,
            name="/api/v1/links/{short_code}",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code in [403, 404]:
                # Ссылка могла быть создана другим пользователем или удалена
                # Удаляем код из списка
                if short_code in short_codes:
                    short_codes.remove(short_code)
                response.success()
            else:
                response.failure(f"Failed to update link: {response.status_code}")
    
    @tag("delete")
    @task(1)  # Низкий приоритет (1 из 10)
    def delete_link(self):
        """Удаление ссылки"""
        if not hasattr(self, "auth_headers") or not short_codes:
            return
        
        # Случайно выбираем короткий код из имеющихся
        short_code = random.choice(short_codes)
        
        # Удаляем ссылку
        with self.client.delete(
            f"/api/v1/links/{short_code}",
            headers=self.auth_headers,
            name="/api/v1/links/{short_code}",
            catch_response=True
        ) as response:
            if response.status_code == 204:
                # Удаляем код из списка
                if short_code in short_codes:
                    short_codes.remove(short_code)
                response.success()
            elif response.status_code in [403, 404]:
                # Ссылка могла быть создана другим пользователем или уже удалена
                # Удаляем код из списка
                if short_code in short_codes:
                    short_codes.remove(short_code)
                response.success()
            else:
                response.failure(f"Failed to delete link: {response.status_code}")

# Дополнительный класс пользователя, который только переходит по ссылкам
# Имитирует обычных пользователей, которые только используют короткие ссылки
class RedirectOnlyUser(HttpUser):
    """
    Класс имитирует поведение обычных пользователей, которые только переходят по коротким ссылкам
    """
    wait_time = between(0.5, 3)  # Более частые запросы
    
    @task
    def redirect_to_original(self):
        """Переход по короткой ссылке"""
        if not short_codes:
            return
        
        # Случайно выбираем короткий код из имеющихся
        short_code = random.choice(short_codes)
        
        # Осуществляем переход
        with self.client.get(
            f"/{short_code}",
            name="/{short_code} (RedirectOnly)",
            allow_redirects=False,  # Не следуем за редиректом
            catch_response=True
        ) as response:
            # Проверяем, что получен редирект (статус 307 или 308)
            if response.status_code in [301, 302, 307, 308]:
                response.success()
            elif response.status_code == 410:
                # Ссылка истекла
                if short_code in short_codes:
                    short_codes.remove(short_code)
                response.success()
            elif response.status_code == 404:
                # Ссылка не найдена
                if short_code in short_codes:
                    short_codes.remove(short_code)
                response.success()
            else:
                response.failure(f"Redirect failed: {response.status_code}") 