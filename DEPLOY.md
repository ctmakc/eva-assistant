# EVA Personal Assistant - Deployment Guide

## Quick Start (TL;DR)

```bash
# 1. Clone & configure
git clone <repo>
cd EVA-PERSONAL-ASSISTANT
cp server/.env.example server/.env

# 2. Deploy backend
docker-compose up -d

# 3. Open browser, setup admin
http://YOUR_SERVER:8080/setup

# 4. Install Android APK
adb install EVA-Assistant.apk
```

---

## Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Android App    │────▶│  FastAPI Server │────▶│  Gemini/Claude  │
│  (Kotlin)       │◀────│  (Python)       │◀────│  (LLM API)      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                    ┌──────────┼──────────┐
                    ▼          ▼          ▼
              ┌─────────┐ ┌─────────┐ ┌─────────┐
              │Telegram │ │  Gmail  │ │ Whisper │
              │   Bot   │ │  OAuth  │ │  (STT)  │
              └─────────┘ └─────────┘ └─────────┘
```

---

## 1. Backend Deployment (Docker)

### Prerequisites
- Docker & Docker Compose
- Server with 2GB+ RAM (Whisper needs memory)
- Open port 8080

### Step 1: Configure Environment

```bash
cd server
cp .env.example .env
nano .env
```

Edit `.env`:
```env
# REQUIRED - Generate random strings (32+ chars)
API_SECRET_KEY=your-random-secret-key-here-32chars
VAULT_MASTER_KEY=another-random-key-for-encryption

# OPTIONAL - Can be set via Admin UI later
GEMINI_API_KEY=
ANTHROPIC_API_KEY=
TELEGRAM_BOT_TOKEN=

# LLM Provider: "gemini" (free) or "anthropic"
LLM_PROVIDER=gemini
```

Generate random keys:
```bash
# Linux/Mac
openssl rand -hex 32

# Or Python
python -c "import secrets; print(secrets.token_hex(32))"
```

### Step 2: Deploy with Docker

```bash
cd EVA-PERSONAL-ASSISTANT
docker-compose up -d
```

Check logs:
```bash
docker-compose logs -f eva-server
```

You should see:
```
INFO - Loading STT model (Whisper)...
INFO - ✓ STT ready
INFO - ✓ TTS ready
INFO - ✨ EVA is ready!
```

### Step 3: Initial Admin Setup

1. Open browser: `http://YOUR_SERVER:8080/`
2. You'll be redirected to `/setup`
3. Create admin password (min 8 chars)
4. You're in the dashboard!

### Step 4: Configure API Keys

In the dashboard (`/dashboard`):

1. **Gemini API Key** (recommended, free):
   - Go to https://makersuite.google.com/app/apikey
   - Create API key
   - Paste in dashboard

2. **Telegram Bot** (optional):
   - Message @BotFather on Telegram
   - `/newbot` → follow instructions
   - Copy token, paste in dashboard
   - **Important**: After saving, restart container:
     ```bash
     docker-compose restart eva-server
     ```

3. **Gmail** (optional):
   - Go to https://console.cloud.google.com
   - Create project or select existing
   - Enable Gmail API
   - Create OAuth 2.0 credentials (Web application)
   - Add redirect URI: `http://YOUR_SERVER:8080/api/v1/gmail/callback`
   - Enter Client ID & Secret in dashboard

---

## 2. Android App Installation

### Option A: Install Pre-built APK

```bash
# USB debugging enabled on phone
adb install EVA-Assistant.apk
```

Or transfer `EVA-Assistant.apk` to phone and install manually.

### Option B: Build from Source

```bash
cd android
./gradlew assembleDebug
# APK: android/app/build/outputs/apk/debug/app-debug.apk
```

### Configure Android App

1. Open EVA app
2. Grant microphone permission
3. Tap settings (gear icon)
4. Set Server URL: `http://YOUR_SERVER:8080`
5. Tap "Check Connection" - should show green checkmark

---

## 3. API Keys & Credentials Summary

| Service | Where to Get | Where to Enter | Required? |
|---------|--------------|----------------|-----------|
| **Gemini API** | [makersuite.google.com](https://makersuite.google.com/app/apikey) | Dashboard → API Keys | Yes (or Anthropic) |
| **Anthropic API** | [console.anthropic.com](https://console.anthropic.com) | Dashboard → API Keys | Alternative to Gemini |
| **Telegram Bot** | @BotFather on Telegram | Dashboard → API Keys | Optional |
| **Gmail OAuth** | [Google Cloud Console](https://console.cloud.google.com) | Dashboard → Gmail | Optional |

---

## 4. File Structure

```
EVA-PERSONAL-ASSISTANT/
├── server/                 # Backend (Python/FastAPI)
│   ├── main.py            # Entry point
│   ├── config.py          # Settings
│   ├── auth.py            # JWT authentication
│   ├── api/               # API routes
│   │   ├── routes.py      # Core endpoints
│   │   ├── admin.py       # Admin API
│   │   ├── dashboard.py   # Web UI
│   │   └── gmail_routes.py
│   ├── core/              # Core services
│   │   ├── stt.py         # Speech-to-Text (Whisper)
│   │   ├── tts.py         # Text-to-Speech (Edge TTS)
│   │   └── llm.py         # LLM (Gemini/Claude)
│   ├── personality/       # EVA personality
│   │   ├── profile.py     # User profiles
│   │   ├── memory.py      # Conversation memory
│   │   └── adaptive.py    # Adaptive learning
│   ├── integrations/      # External services
│   │   ├── telegram.py
│   │   ├── gmail.py
│   │   └── vault.py       # Encrypted credentials
│   ├── proactive/         # Scheduled tasks
│   │   └── scheduler.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── android/               # Android app (Kotlin)
│   ├── app/src/main/java/com/eva/assistant/
│   │   ├── MainActivity.kt
│   │   ├── ui/
│   │   │   ├── EvaViewModel.kt
│   │   │   ├── screens/
│   │   │   └── components/
│   │   ├── data/
│   │   │   ├── api/EvaApiClient.kt
│   │   │   └── model/
│   │   └── audio/
│   │       ├── AudioRecorder.kt
│   │       └── AudioPlayer.kt
│   └── build.gradle.kts
│
├── docker-compose.yml
├── DEPLOY.md              # This file
├── AGENTS.md              # Development roadmap
└── CONTEXT.md             # Project context
```

---

## 5. Data Persistence

All data stored in Docker volume `eva-data`:

```
/app/data/
├── profiles/          # User profiles (JSON)
├── memory/            # Conversation history (JSON)
├── credentials/       # Encrypted API keys (.enc)
├── audio/             # Generated TTS files (MP3)
└── auth/              # Admin password hash
```

Backup:
```bash
docker run --rm -v eva-data:/data -v $(pwd):/backup alpine tar czf /backup/eva-backup.tar.gz /data
```

Restore:
```bash
docker run --rm -v eva-data:/data -v $(pwd):/backup alpine tar xzf /backup/eva-backup.tar.gz -C /
```

---

## 6. API Endpoints Reference

### Public
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/voice/process` | Voice message (multipart) |
| POST | `/api/v1/chat/message` | Text message (JSON) |
| GET | `/api/v1/audio/{filename}` | Serve audio file |

### User
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/user/profile` | Get user profile |
| POST | `/api/v1/user/profile/name` | Update name |
| GET | `/api/v1/conversation/{user_id}/history` | Get chat history |
| DELETE | `/api/v1/memory/{user_id}` | Clear memory |

### Admin (requires JWT)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/status` | Check if initialized |
| POST | `/api/v1/admin/setup` | Initial setup |
| POST | `/api/v1/admin/login` | Get JWT token |
| GET | `/api/v1/admin/settings` | Get settings |
| POST | `/api/v1/admin/settings` | Update setting |

### Integrations
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/integrations/status` | Status of all integrations |
| POST | `/api/v1/integrations/credentials` | Store credentials |
| GET | `/api/v1/gmail/auth` | Start Gmail OAuth |
| GET | `/api/v1/gmail/summary` | Get email summary |

Full API docs: `http://YOUR_SERVER:8080/docs`

---

## 7. Troubleshooting

### Server won't start
```bash
# Check logs
docker-compose logs eva-server

# Common issues:
# - Port 8080 already in use
# - Not enough RAM for Whisper
# - Missing .env file
```

### "LLM not configured"
1. Open dashboard
2. Add Gemini or Anthropic API key
3. Restart container

### Telegram bot not responding
1. Check token is correct
2. Restart container after adding token
3. Send `/start` to bot first

### Android can't connect
1. Check server URL (include http://)
2. Check firewall allows port 8080
3. Both devices on same network (if local)

### Voice recognition bad quality
- Speak clearly, close to mic
- Reduce background noise
- Server defaults to "small" Whisper model (good balance)

---

## 8. Development

### Run backend locally (without Docker)
```bash
cd server
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
python main.py
```

### Run Android in emulator
```bash
cd android
./gradlew installDebug
# Or open in Android Studio
```

### API testing
```bash
# Health check
curl http://localhost:8080/api/v1/health

# Send text message
curl -X POST http://localhost:8080/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -d '{"text": "Привет!", "user_id": "test"}'
```

---

## 9. Security Notes

- Admin password hashed with bcrypt
- API keys encrypted with Fernet (AES-128)
- JWT tokens expire in 7 days
- CORS currently allows all origins (tighten for production)
- Gmail uses OAuth2 (no password storage)

**For production:**
1. Use HTTPS (nginx reverse proxy + Let's Encrypt)
2. Restrict CORS to your domains
3. Use strong, unique passwords
4. Regular backups of `eva-data` volume

---

## 10. Roadmap

See `AGENTS.md` for full development roadmap.

**Completed:**
- [x] Voice pipeline (STT → LLM → TTS)
- [x] Android client
- [x] Telegram integration
- [x] Gmail integration
- [x] Admin dashboard
- [x] Proactive scheduler

**Next:**
- [ ] Push notifications
- [ ] iOS client
- [ ] Reddit integration
- [ ] Calendar sync
- [ ] Arduino robot body

---

Questions? Issues? https://github.com/anthropics/claude-code/issues
