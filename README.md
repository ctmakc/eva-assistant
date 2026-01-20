# EVA Personal Assistant

Персональный AI-компаньон с голосовым управлением.

## Quick Start

### 1. Настройка окружения

```bash
cd eva-assistant
cp .env.example .env
# Отредактируй .env, добавь ANTHROPIC_API_KEY
```

### 2. Запуск через Docker

```bash
docker-compose up -d --build
```

### 3. Проверка

```bash
curl http://localhost:8000/api/v1/health
```

Ожидаемый ответ:
```json
{"status":"ok","version":"1.0.0","eva_status":"ready"}
```

### 4. API документация

Открой в браузере: http://localhost:8000/docs

## API Endpoints

| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/api/v1/health` | GET | Статус сервера |
| `/api/v1/voice/process` | POST | Голос → ответ (audio file) |
| `/api/v1/chat/message` | POST | Текст → ответ |
| `/api/v1/audio/{filename}` | GET | Получить аудиофайл |
| `/api/v1/user/profile` | GET | Профиль пользователя |
| `/api/v1/conversation/{user_id}/history` | GET | История диалога |
| `/api/v1/memory/{user_id}` | DELETE | Очистить память |

## Тестирование голоса

```bash
# Записать аудио (например, voice.wav) и отправить:
curl -X POST http://localhost:8000/api/v1/voice/process \
  -F "audio=@voice.wav" \
  -F "user_id=maxim"
```

## Тестирование текста

```bash
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -d '{"text": "Привет, как дела?", "user_id": "maxim"}'
```

## Структура проекта

```
eva-assistant/
├── server/
│   ├── main.py           # FastAPI приложение
│   ├── config.py         # Настройки
│   ├── api/routes.py     # API endpoints
│   ├── core/             # STT, TTS, LLM
│   ├── personality/      # Memory, Profile
│   └── data/             # Данные пользователей
├── docker-compose.yml
└── .env
```

## Логи

```bash
docker-compose logs -f eva-server
```

## Остановка

```bash
docker-compose down
```
