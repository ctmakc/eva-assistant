# EVA Development Context

> Этот файл автоматически обновляется для сохранения контекста разработки.
> Последнее обновление: 2025-01-20

## Текущий статус

**Фаза:** 1 — MVP (в процессе)
**Прогресс:** Backend готов, нужен деплой и тест

## Что сделано

### 2025-01-20
- [x] Создана папка проекта `D:\EVA-PERSONAL-ASSISTANT`
- [x] Написано полное ТЗ в `AGENTS.md`
- [x] **Фаза 1 — Backend:**
  - [x] Структура проекта создана
  - [x] Docker + docker-compose настроены
  - [x] FastAPI приложение с health endpoint
  - [x] STT сервис (Faster Whisper)
  - [x] TTS сервис (Edge-TTS)
  - [x] LLM сервис (Claude Haiku)
  - [x] Memory manager (история диалогов)
  - [x] Profile manager (профиль пользователя)
  - [x] API routes (voice/process, chat/message, etc.)
  - [x] README с инструкциями

## Структура проекта

```
D:\EVA-PERSONAL-ASSISTANT\
├── AGENTS.md              # Полное ТЗ
├── CONTEXT.md             # Этот файл
├── README.md              # Quick start
├── docker-compose.yml
├── .env.example
└── server/
    ├── Dockerfile
    ├── requirements.txt
    ├── main.py            # FastAPI app
    ├── config.py          # Settings
    ├── api/routes.py      # API endpoints
    ├── core/
    │   ├── stt.py         # Whisper
    │   ├── tts.py         # Edge-TTS
    │   └── llm.py         # Claude
    ├── personality/
    │   ├── memory.py      # Conversation history
    │   └── profile.py     # User profile
    ├── schemas/models.py  # Pydantic models
    ├── integrations/      # (Phase 2)
    └── proactive/         # (Phase 4)
```

## Решения и договорённости

| Тема | Решение |
|------|---------|
| Сервер | Docker на 194.61.52.176, порт 8000 |
| LLM | Claude Haiku (claude-3-haiku-20240307) |
| STT | Faster Whisper, модель "small" |
| TTS | Edge-TTS (Svetlana RU, Aria EN) |
| Характер EVA | Мягкая боевая подруга |
| Имя владельца | Максим |

## Следующие шаги

1. [ ] Создать `.env` файл с ANTHROPIC_API_KEY
2. [ ] Задеплоить на сервер (docker-compose up)
3. [ ] Протестировать API
4. [ ] Начать Android клиент

## Для восстановления контекста

```
Продолжаем работу над EVA. Прочитай D:\EVA-PERSONAL-ASSISTANT\AGENTS.md и D:\EVA-PERSONAL-ASSISTANT\CONTEXT.md
```

## API для тестирования

```bash
# Health check
curl http://194.61.52.176:8000/api/v1/health

# Текстовый чат
curl -X POST http://194.61.52.176:8000/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -d '{"text": "Привет!", "user_id": "maxim"}'

# Голосовой (с файлом)
curl -X POST http://194.61.52.176:8000/api/v1/voice/process \
  -F "audio=@voice.wav" \
  -F "user_id=maxim"
```
