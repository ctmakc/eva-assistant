# EVA Personal Assistant

Персональный AI-компаньон с голосовым управлением.

## Quick Start

### 1. Деплой через Portainer

**Stack → Add stack → Repository**
- URL: `https://github.com/ctmakc/eva-assistant`
- Compose path: `docker-compose.yml`

**Environment variables:**
```
API_SECRET_KEY=your-random-secret-32-chars
VAULT_MASTER_KEY=another-random-secret
```

### 2. Первоначальная настройка

После деплоя открой: `http://YOUR_SERVER:8080/docs`

**Шаг 1: Создай админа**
```bash
curl -X POST http://YOUR_SERVER:8080/api/v1/admin/setup \
  -F "password=your-admin-password"
```

Сохрани полученный `token`!

**Шаг 2: Добавь API ключ**
```bash
curl -X POST http://YOUR_SERVER:8080/api/v1/admin/settings \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "key=gemini_api_key" \
  -F "value=YOUR_GEMINI_API_KEY"
```

### 3. Проверка

```bash
curl http://YOUR_SERVER:8080/api/v1/health
```

```bash
curl -X POST http://YOUR_SERVER:8080/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -d '{"text": "Привет!", "user_id": "maxim"}'
```

## API Endpoints

### Core
| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/api/v1/health` | GET | Статус сервера |
| `/api/v1/voice/process` | POST | Голос → ответ |
| `/api/v1/chat/message` | POST | Текст → ответ |

### Admin (требует токен)
| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/api/v1/admin/status` | GET | Статус админа |
| `/api/v1/admin/setup` | POST | Первичная настройка |
| `/api/v1/admin/login` | POST | Получить токен |
| `/api/v1/admin/settings` | GET | Текущие настройки |
| `/api/v1/admin/settings` | POST | Обновить настройку |

### Integrations
| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/api/v1/integrations/status` | GET | Статус интеграций |
| `/api/v1/integrations/credentials` | POST | Сохранить креды |

## Поддерживаемые API ключи

Добавляются через `POST /api/v1/admin/settings`:

- `gemini_api_key` - Google Gemini (бесплатно)
- `anthropic_api_key` - Claude (платно)
- `telegram_bot_token` - Telegram бот

## Безопасность

- API ключи хранятся в зашифрованном vault
- Admin API защищён JWT токенами
- Пароли хешируются bcrypt
- Никакие секреты не хранятся в git

## Логи

```bash
docker logs eva-assistant -f
```
