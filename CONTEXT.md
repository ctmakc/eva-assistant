# EVA Development Context

> Последнее обновление: 2025-01-20

## Текущий статус

**Фаза:** Backend 100% завершён ✅
**Следующее:** Android клиент

## Что сделано

### Core
- [x] FastAPI сервер
- [x] STT (Faster Whisper)
- [x] TTS (Edge-TTS)
- [x] LLM (Gemini/Claude)

### Personality
- [x] Memory система
- [x] User Profile + Onboarding
- [x] Adaptive Engine (учится что работает)

### Integrations
- [x] Telegram бот
- [x] Gmail OAuth (чтение/отправка писем)
- [x] Credential Vault (шифрованное хранилище)

### Proactive
- [x] Scheduler (утренние приветствия, напоминания)

### Security & Admin
- [x] JWT аутентификация
- [x] Admin API
- [x] **Web Dashboard** (!)

## Деплой

**URL:** http://194.61.52.176:8080/
**GitHub:** https://github.com/ctmakc/eva-assistant

### Portainer Environment:
```
API_SECRET_KEY=random-32-char-string
VAULT_MASTER_KEY=another-random-string
```

### Первый запуск:
1. Открой http://194.61.52.176:8080/
2. Создай пароль админа
3. Добавь Gemini API Key
4. (Опционально) Подключи Gmail, Telegram

## Endpoints

| URL | Описание |
|-----|----------|
| `/` | Web Dashboard |
| `/docs` | Swagger API docs |
| `/api/v1/health` | Health check |
| `/api/v1/chat/message` | Текстовый чат |
| `/api/v1/voice/process` | Голосовой чат |
| `/api/v1/gmail/summary` | Сводка почты |

## Восстановление контекста

```
Продолжаем EVA. Читай D:\EVA-PERSONAL-ASSISTANT\AGENTS.md и CONTEXT.md
```
