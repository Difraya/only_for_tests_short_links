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

### Через Docker Compose (рекомендуется)

1. Склонировать репозиторий:
```bash
git clone https://github.com/yourusername/short_links_api.git
cd short_links_api
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

### Локальная разработка

1. Установить Python 3.12+

2. Установить PostgreSQL и Redis

3. Создать виртуальное окружение и установить зависимости:
```bash
python -m venv .venv
source .venv/bin/activate  # для Linux/Mac
.\.venv\Scripts\activate   # для Windows
pip install -r requirements.txt
```

4. Создать и заполнить `.env` файл (см. выше)

5. Запустить проект:
```bash
uvicorn app.main:app --reload
```

## Тестирование

### Unit Tests and Integration Tests

Run tests and generate coverage report:

```bash
# Run all tests
python -m pytest 

# Run tests with coverage report
python -m pytest --cov=app --cov-report=html
```

Current test coverage: ![Coverage](https://img.shields.io/badge/coverage-92%25-brightgreen)

### Load Testing

Load testing is implemented using [Locust](https://locust.io/), a user-friendly, scriptable and scalable performance testing tool.

#### Running Load Tests

1. Make sure the API server is running:
   ```bash
   python -m app.main
   ```

2. Run load tests with web interface:
   ```bash
   python locust_tests/run_web_ui.py
   ```
   This will open a web interface at http://localhost:8089 where you can configure and run tests.

3. Run automated tests with report generation:
   ```bash
   python locust_tests/run_load_tests.py
   ```
   This will run predefined tests and generate comprehensive reports in the `locust_tests/reports/` directory.

#### Load Testing Features

- **General API Testing:** Simulates users registering, creating links, accessing them, and managing links
- **Cache Efficiency Testing:** Measures performance improvements from Redis caching
- **Cache Invalidation Testing:** Validates that cache is properly invalidated when links are updated
- **Comprehensive Reporting:** Generates detailed HTML and CSV reports with performance metrics

#### Performance Results

Based on load testing with 20 concurrent users over 2 minutes:

- **Redirect Performance:** 45ms median response time, capable of handling 26.7 redirects per second
- **API Operations:** Stable performance for link creation, updates, and statistics retrieval
- **Caching Efficiency:** 87.4% improvement in response time for cached redirects (95ms → 12ms)
- **Overall Stability:** 0.8% failure rate under load

For detailed load testing results, see the HTML report in `locust_tests/reports/load_test_report.html`.

## Структура БД 

### Таблица `user`

| Поле            | Тип            | Описание                |
|-----------------|----------------|-------------------------|
| id              | UUID           | Уникальный идентификатор |
| username        | String         | Имя пользователя        |
| email           | String         | Электронная почта       |
| hashed_password | String         | Хешированный пароль     |
| created_at      | datetime (UTC) | Дата регистрации        |
| updated_at      | datetime (UTC) | Дата обновления         |


### Таблица `link`

| Поле          | Тип            | Описание                     |
|---------------|----------------|------------------------------|
| id            | UUID           | Уникальный идентификатор     |
| original_url  | String         | Оригинальный URL             |
| short_code    | String         | Короткий код                 |
| custom_alias  | String (null)  | Кастомный алиас              |
| user_id       | UUID           | Владелец ссылки              |
| clicks        | Integer        | Количество переходов         |
| expires_at    | datetime (UTC) | Дата истечения               |
| created_at    | datetime (UTC) | Дата создания                |
| updated_at    | datetime (UTC) | Дата обновления              |

## Механизмы оптимизации

### Очистка просроченных ссылок
- Функциональность для удаления ссылок, у которых `expires_at < текущей даты`

### Кэширование
- Популярные ссылки хранятся в Redis для быстрого доступа
- Кэш инвалидируется при обновлении или удалении ссылки
- TTL для кэшированных записей настраивается в конфигурации

## Планы развития

- [ ] Добавление пользовательских групп и разрешений
- [ ] Расширенная аналитика использования ссылок (география, устройства)
- [ ] API для пакетного создания ссылок
- [ ] Интеграция с внешними сервисами (Bitly, TinyURL)
- [ ] Улучшение покрытия тестами эндпоинтов до 80%+

## Лицензия

MIT