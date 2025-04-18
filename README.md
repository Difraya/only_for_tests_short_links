# Short Links API

API-сервис для создания коротких ссылок с возможностью кастомизации, отслеживания статистики и автоматического удаления по сроку действия.

![Покрытие тестами](https://img.shields.io/badge/coverage-92%25-brightgreen)

## Возможности

- Генерация коротких ссылок (с кастомным алиасом или случайным кодом)
- Редирект на оригинальный URL
- Просмотр статистики использования ссылки
- Удаление и обновление ссылок
- Аутентификация и авторизация пользователей (JWT)
- Автоматическое удаление просроченных ссылок
- Кэширование популярных ссылок (Redis)

## Технический стек

- **Backend**: FastAPI, Python 3.12
- **Аутентификация**: JWT
- **База данных**: PostgreSQL, SQLAlchemy (ORM)
- **Кэширование**: Redis
- **Тестирование**: pytest, coverage (92% покрытие кода)
- **Нагрузочное тестирование**: Locust
- **Контейнеризация**: Docker, Docker Compose

## Примеры запросов

### Регистрация
**POST** `/api/v1/auth/register`
```json
{
  "email": "user@example.com",
  "password": "strongpassword",
  "username": "your_username"
}
```
Ответ:
```json
{
  "id": "fb1c0618-...",
  "email": "user@example.com",
  "username": "your_username"
}
```

### Аутентификация (получение токена)
**POST** `/api/v1/auth/jwt/login`
```
username=user@example.com&password=strongpassword
```
Ответ:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Сокращение ссылки
**POST** `/api/v1/links/shorten`
```json
{
  "original_url": "https://example.com/page",
  "custom_alias": "my-alias",        // необязательно
  "expires_at": "2025-04-10T12:00"    // необязательно
}
```
Ответ:
```json
{
  "short_url": "http://localhost:8000/my-alias",
  "original_url": "https://example.com/page",
  "short_code": "my-alias",
  "custom_alias": "my-alias",
  "user_id": "fb1c0618-...",
  "clicks": 0,
  "expires_at": "2025-04-10T12:00:00",
  "created_at": "2025-04-01T19:59:40.725Z",
  "updated_at": "2025-04-01T19:59:40.725Z"
}
```

### Переход по короткой ссылке
**GET** `/{short_code}`
- Перенаправляет на оригинальный URL

### Получение статистики
**GET** `/api/v1/links/{short_code}/stats`

Ответ:
```json
{
  "id": "fb1c0618-...",
  "original_url": "https://example.com/",
  "short_code": "my-alias",
  "custom_alias": "my-alias",
  "user_id": "fb1c0618-...",
  "clicks": 5,
  "expires_at": "2025-04-10T12:00:00",
  "created_at": "2025-04-01T19:59:40.725Z",
  "updated_at": "2025-04-01T19:59:40.725Z",
  "short_url": "http://localhost:8000/my-alias"
}
```

### Удаление ссылки
**DELETE** `/api/v1/links/{short_code}`

### Обновление ссылки
**PUT** `/api/v1/links/{short_code}`
```json
{
  "original_url": "https://new-url.com",
  "custom_alias": "new-alias",
  "expires_at": "2025-05-10T12:00:00"
}
```

## Инструкция по запуску

### Через Docker Compose

1. Клонировать репозиторий:
```bash
git clone https://github.com/Difraya/only_for_tests_short_links.git
cd only_for_tests_short_links
```

2. Создать и заполнить файл `.env` (пример в `.env.example`):
```
# База данных
DB_USER=postgres
DB_PASS=password
DB_HOST=db
DB_PORT=5432
DB_NAME=shortlinks

# JWT
SECRET=your_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Redis
REDIS_BROKER_URL=redis://redis:6379/0
```

3. Запустить проект:
```bash
docker-compose up --build
```

4. Открыть в браузере: [http://localhost:8000/docs](http://localhost:8000/docs)

## Тестирование

### Модульные и интеграционные тесты

Запуск тестов и создание отчета о покрытии:

```bash
# Запуск всех тестов
python -m pytest 

# Запуск тестов с отчетом о покрытии
python -m pytest --cov=app --cov-report=html
```

Текущее покрытие кода тестами: ![Покрытие](https://img.shields.io/badge/coverage-92%25-brightgreen)

### Нагрузочное тестирование

Нагрузочное тестирование реализовано с использованием [Locust](https://locust.io/) 

#### Запуск нагрузочных тестов

1. Убедитесь, что API-сервер запущен:
   ```bash
   python -m app.main
   ```

2. Запустите нагрузочные тесты с веб-интерфейсом:
   ```bash
   python locust_tests/run_web_ui.py
   ```
   Это откроет веб-интерфейс по адресу http://localhost:8089, где вы сможете настроить и запустить тесты.

3. Запустите автоматические тесты с генерацией отчета:
   ```bash
   python locust_tests/run_load_tests.py
   ```
   Это запустит тесты и сгенерирует подробные отчеты в директории `locust_tests/reports/`.

#### Результаты по производительности

По результатам нагрузочного тестирования с 20 одновременными пользователями в течение 2 минут:

- **Производительность редиректов:** 45мс медианное время отклика, способность обрабатывать 26.7 редиректов в секунду
- **Операции API:** Стабильная производительность для создания ссылок, обновления и получения статистики
- **Эффективность кэширования:** 87.4% улучшение времени отклика для кэшированных редиректов (95мс → 12мс)
- **Общая стабильность:** 0.8% показатель отказов при нагрузке

Для детальных результатов нагрузочного тестирования смотрите HTML-отчет в `locust_tests/reports/load_test_report.html`.
