# EVA Development Context

> Последнее обновление: 2025-01-20

## Текущий статус

**Фаза:** 1-4 завершены (Backend полный)
**Следующее:** Gmail OAuth, Android клиент

## Что сделано

### Backend (100%)
- [x] FastAPI сервер
- [x] STT (Faster Whisper)
- [x] TTS (Edge-TTS)
- [x] LLM (Gemini/Claude переключаемые)
- [x] Memory система
- [x] User Profile + Onboarding
- [x] **Telegram бот** — отвечает через EVA
- [x] **Credential Vault** — шифрованное хранилище паролей
- [x] **Proactive Scheduler** — утренние приветствия, напоминания
- [x] **Adaptive Engine** — учится что работает

### Pending
- [ ] Gmail OAuth интеграция
- [ ] Android клиент

## Деплой

**Сервер:** 194.61.52.176:8080
**GitHub:** https://github.com/ctmakc/eva-assistant

**Portainer Stack Environment Variables:**
```
GEMINI_API_KEY=AIzaSyCzzSfAvhg222SRnRCp-s7_8xQkSdkuvNs
LLM_PROVIDER=gemini
TELEGRAM_BOT_TOKEN=<твой токен от @BotFather>
```

## API Endpoints

### Core
- `GET /api/v1/health` — статус
- `POST /api/v1/voice/process` — голос → ответ
- `POST /api/v1/chat/message` — текст → ответ

### Integrations
- `GET /api/v1/integrations/status` — статус интеграций
- `POST /api/v1/integrations/credentials` — сохранить креды
- `GET /api/v1/integrations/credentials` — список сервисов

### Scheduler
- `POST /api/v1/scheduler/reminder` — добавить напоминание
- `POST /api/v1/scheduler/setup/{user_id}` — настроить расписание

## Telegram бот

1. Создай бота через @BotFather
2. Получи токен
3. Добавь `TELEGRAM_BOT_TOKEN` в Portainer environment
4. Редеплой стэк
5. Напиши боту `/start`

## Восстановление контекста

```
Продолжаем EVA. Читай D:\EVA-PERSONAL-ASSISTANT\AGENTS.md и CONTEXT.md
```
