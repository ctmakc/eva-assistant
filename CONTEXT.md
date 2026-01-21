# EVA Development Context

> Последнее обновление: 2025-01-20

## Текущий статус

**Фаза:** Backend завершён
**Следующее:** Android клиент

## Что сделано

### Backend (100%)
- [x] FastAPI сервер с аутентификацией
- [x] STT (Faster Whisper)
- [x] TTS (Edge-TTS)
- [x] LLM (Gemini/Claude переключаемые)
- [x] Memory система
- [x] User Profile + Onboarding
- [x] Telegram бот
- [x] Credential Vault
- [x] Proactive Scheduler
- [x] Adaptive Engine
- [x] **Admin API** — управление ключами через API
- [x] **JWT Auth** — защита эндпоинтов

## Деплой

**Сервер:** 194.61.52.176:8080
**GitHub:** https://github.com/ctmakc/eva-assistant

## Первый запуск

1. Задеплоить через Portainer (без API ключей в env)
2. Открыть `/docs`
3. Вызвать `POST /api/v1/admin/setup` с паролем
4. Через админ-эндпоинты добавить API ключи

## Восстановление контекста

```
Продолжаем EVA. Читай D:\EVA-PERSONAL-ASSISTANT\AGENTS.md и CONTEXT.md
```
