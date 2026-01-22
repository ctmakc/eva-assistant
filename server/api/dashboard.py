"""Simple web dashboard for EVA admin."""

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import Optional

from auth import get_auth_manager, optional_auth
from config import get_settings
from integrations.vault import get_vault

router = APIRouter(tags=["dashboard"])

# ============== HTML Templates ==============

def base_template(title: str, content: str, token: str = None) -> str:
    """Base HTML template."""
    token_meta = f'<meta name="token" content="{token}">' if token else ''

    return f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    {token_meta}
    <title>{title} - EVA Admin</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #e0e0e0;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            text-align: center;
            padding: 40px 0;
        }}
        .header h1 {{
            color: #00d9ff;
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        .header p {{ color: #888; }}
        .card {{
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .card h2 {{
            color: #00d9ff;
            margin-bottom: 16px;
            font-size: 1.3em;
        }}
        .form-group {{
            margin-bottom: 16px;
        }}
        label {{
            display: block;
            margin-bottom: 6px;
            color: #aaa;
            font-size: 0.9em;
        }}
        input[type="text"], input[type="password"] {{
            width: 100%;
            padding: 12px;
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 8px;
            background: rgba(0,0,0,0.3);
            color: #fff;
            font-size: 1em;
        }}
        input:focus {{
            outline: none;
            border-color: #00d9ff;
        }}
        button, .btn {{
            background: linear-gradient(135deg, #00d9ff 0%, #00a8cc 100%);
            color: #000;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 1em;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
        }}
        button:hover, .btn:hover {{
            opacity: 0.9;
        }}
        .btn-secondary {{
            background: rgba(255,255,255,0.1);
            color: #fff;
        }}
        .status {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85em;
        }}
        .status-ok {{ background: rgba(0,255,100,0.2); color: #0f0; }}
        .status-warn {{ background: rgba(255,200,0,0.2); color: #fa0; }}
        .status-error {{ background: rgba(255,0,0,0.2); color: #f55; }}
        .alert {{
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 16px;
        }}
        .alert-success {{ background: rgba(0,255,100,0.1); border: 1px solid rgba(0,255,100,0.3); }}
        .alert-error {{ background: rgba(255,0,0,0.1); border: 1px solid rgba(255,0,0,0.3); }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; }}
        .stat {{
            background: rgba(0,217,255,0.1);
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-value {{ font-size: 2em; color: #00d9ff; }}
        .stat-label {{ color: #888; margin-top: 4px; }}
        a {{ color: #00d9ff; }}
        .mt-2 {{ margin-top: 16px; }}
        .text-muted {{ color: #666; font-size: 0.85em; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 EVA</h1>
            <p>Personal Assistant Admin Panel</p>
        </div>
        {content}
    </div>
</body>
</html>'''


# ============== Routes ==============

@router.get("/", response_class=HTMLResponse)
async def dashboard_home(is_auth: bool = Depends(optional_auth)):
    """Dashboard home page."""
    auth = get_auth_manager()

    if not auth.is_initialized:
        return RedirectResponse(url="/setup")

    if not is_auth:
        return RedirectResponse(url="/login")

    return RedirectResponse(url="/dashboard")


@router.get("/setup", response_class=HTMLResponse)
async def setup_page():
    """Initial setup page."""
    auth = get_auth_manager()

    if auth.is_initialized:
        return RedirectResponse(url="/login")

    content = '''
    <div class="card">
        <h2>🚀 Первоначальная настройка</h2>
        <p style="margin-bottom: 20px; color: #888;">
            Создай пароль для администратора EVA
        </p>
        <form method="POST" action="/setup">
            <div class="form-group">
                <label>Пароль администратора</label>
                <input type="password" name="password" required minlength="8"
                       placeholder="Минимум 8 символов">
            </div>
            <div class="form-group">
                <label>Повтори пароль</label>
                <input type="password" name="password2" required>
            </div>
            <button type="submit">Создать</button>
        </form>
    </div>
    '''

    return HTMLResponse(base_template("Setup", content))


@router.post("/setup", response_class=HTMLResponse)
async def setup_submit(password: str = Form(...), password2: str = Form(...)):
    """Handle setup form."""
    auth = get_auth_manager()

    if auth.is_initialized:
        return RedirectResponse(url="/login", status_code=303)

    if password != password2:
        content = '''
        <div class="alert alert-error">Пароли не совпадают</div>
        <a href="/setup">← Назад</a>
        '''
        return HTMLResponse(base_template("Error", content))

    if len(password) < 8:
        content = '''
        <div class="alert alert-error">Пароль должен быть минимум 8 символов</div>
        <a href="/setup">← Назад</a>
        '''
        return HTMLResponse(base_template("Error", content))

    auth.setup_admin(password)
    token = auth.create_access_token()

    # Redirect to dashboard with token in cookie-like way
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie("eva_token", token, httponly=True, max_age=604800)
    return response


@router.get("/login", response_class=HTMLResponse)
async def login_page(error: str = None):
    """Login page."""
    auth = get_auth_manager()

    if not auth.is_initialized:
        return RedirectResponse(url="/setup")

    error_html = '<div class="alert alert-error">Неверный пароль</div>' if error else ''

    content = f'''
    <div class="card">
        <h2>🔐 Вход</h2>
        {error_html}
        <form method="POST" action="/login">
            <div class="form-group">
                <label>Пароль</label>
                <input type="password" name="password" required autofocus>
            </div>
            <button type="submit">Войти</button>
        </form>
    </div>
    '''

    return HTMLResponse(base_template("Login", content))


@router.post("/login")
async def login_submit(password: str = Form(...)):
    """Handle login."""
    auth = get_auth_manager()

    if not auth.verify_password(password):
        return RedirectResponse(url="/login?error=1", status_code=303)

    token = auth.create_access_token()

    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie("eva_token", token, httponly=True, max_age=604800)
    return response


@router.get("/logout")
async def logout():
    """Logout."""
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("eva_token")
    return response


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard."""
    token = request.cookies.get("eva_token")
    auth = get_auth_manager()

    if not token or not auth.verify_token(token):
        return RedirectResponse(url="/login")

    settings = get_settings()
    vault = get_vault()

    # Check statuses
    gemini_ok = bool(settings.gemini_api_key) or vault.has("gemini")
    anthropic_ok = bool(settings.anthropic_api_key) or vault.has("anthropic")
    telegram_ok = bool(settings.telegram_bot_token) or vault.has("telegram")

    from integrations.gmail import get_gmail_integration
    gmail = get_gmail_integration()
    gmail_ok = gmail.is_authenticated

    from integrations.calendar import get_calendar_integration
    calendar = get_calendar_integration()
    calendar_ok = calendar.is_authenticated

    # Get stats
    import os
    import json
    profiles_dir = os.path.join(settings.data_dir, "profiles")
    memory_dir = os.path.join(settings.data_dir, "memory")

    user_count = 0
    total_messages = 0

    if os.path.exists(profiles_dir):
        user_count = len([f for f in os.listdir(profiles_dir) if f.endswith('.json')])

    if os.path.exists(memory_dir):
        for f in os.listdir(memory_dir):
            if f.endswith('.json'):
                try:
                    with open(os.path.join(memory_dir, f), 'r') as file:
                        data = json.load(file)
                        total_messages += len(data.get('messages', []))
                except Exception:
                    pass

    content = f'''
    <div class="card">
        <h2>📊 Статус</h2>
        <div class="grid">
            <div class="stat">
                <div class="stat-value">{"✅" if gemini_ok else "❌"}</div>
                <div class="stat-label">Gemini API</div>
            </div>
            <div class="stat">
                <div class="stat-value">{"✅" if telegram_ok else "❌"}</div>
                <div class="stat-label">Telegram</div>
            </div>
            <div class="stat">
                <div class="stat-value">{"✅" if gmail_ok else "❌"}</div>
                <div class="stat-label">Gmail</div>
            </div>
        </div>
    </div>

    <div class="card">
        <h2>📈 Статистика</h2>
        <div class="grid">
            <div class="stat">
                <div class="stat-value">{user_count}</div>
                <div class="stat-label">Пользователей</div>
            </div>
            <div class="stat">
                <div class="stat-value">{total_messages}</div>
                <div class="stat-label">Сообщений</div>
            </div>
        </div>
        <div class="mt-2">
            <a href="/api/v1/conversation/default/export?format=text" class="btn btn-secondary" target="_blank">Экспорт чата (txt)</a>
            <a href="/api/v1/admin/stats" class="btn btn-secondary" style="margin-left: 8px;" target="_blank">API Stats</a>
        </div>
    </div>

    <div class="card">
        <h2>🔑 API Ключи</h2>
        <form method="POST" action="/dashboard/settings">
            <div class="form-group">
                <label>Gemini API Key</label>
                <input type="password" name="gemini_api_key"
                       placeholder="{'••••••••' if gemini_ok else 'AIza...'}">
            </div>
            <div class="form-group">
                <label>Telegram Bot Token</label>
                <input type="password" name="telegram_bot_token"
                       placeholder="{'••••••••' if telegram_ok else '123456:ABC...'}">
            </div>
            <button type="submit">Сохранить</button>
        </form>
        <p class="text-muted mt-2">Оставь пустым чтобы не менять</p>
    </div>

    <div class="card">
        <h2>📧 Gmail</h2>
        {"<span class='status status-ok'>Подключен</span>" if gmail_ok else "<span class='status status-warn'>Не подключен</span>"}
        <div class="mt-2">
            {"<a href='/api/v1/gmail/summary' class='btn btn-secondary'>Проверить почту</a>" if gmail_ok else "<a href='/dashboard/gmail' class='btn'>Подключить Gmail</a>"}
        </div>
    </div>

    <div class="card">
        <h2>📅 Google Calendar</h2>
        {"<span class='status status-ok'>Подключен</span>" if calendar_ok else "<span class='status status-warn'>Не подключен</span>"}
        <div class="mt-2">
            {"<a href='/api/v1/calendar/today' class='btn btn-secondary' target='_blank'>Сегодня</a> <a href='/api/v1/calendar/upcoming' class='btn btn-secondary' target='_blank'>На неделю</a>" if calendar_ok else "<a href='/dashboard/calendar' class='btn'>Подключить Calendar</a>"}
        </div>
        <p class="text-muted mt-2">Команды: "что у меня сегодня", "мой календарь"</p>
    </div>

    <div class="card">
        <h2>📚 API Документация</h2>
        <a href="/docs" class="btn btn-secondary">Открыть Swagger UI</a>
    </div>

    <div class="card">
        <h2>🎤 Голос EVA</h2>
        <form method="POST" action="/dashboard/voice">
            <div class="form-group">
                <label>Русский голос</label>
                <select name="voice_ru" style="width: 100%; padding: 12px; border-radius: 8px; background: rgba(0,0,0,0.3); color: #fff; border: 1px solid rgba(255,255,255,0.2);">
                    <option value="ru-RU-SvetlanaNeural" {"selected" if settings.tts_voice_ru == "ru-RU-SvetlanaNeural" else ""}>Светлана (женский, мягкий)</option>
                    <option value="ru-RU-DariyaNeural" {"selected" if settings.tts_voice_ru == "ru-RU-DariyaNeural" else ""}>Дария (женский, тёплый)</option>
                    <option value="ru-RU-DmitryNeural" {"selected" if settings.tts_voice_ru == "ru-RU-DmitryNeural" else ""}>Дмитрий (мужской)</option>
                </select>
            </div>
            <div class="form-group">
                <label>Английский голос</label>
                <select name="voice_en" style="width: 100%; padding: 12px; border-radius: 8px; background: rgba(0,0,0,0.3); color: #fff; border: 1px solid rgba(255,255,255,0.2);">
                    <option value="en-US-AriaNeural" {"selected" if settings.tts_voice_en == "en-US-AriaNeural" else ""}>Aria (женский, дружелюбный)</option>
                    <option value="en-US-JennyNeural" {"selected" if settings.tts_voice_en == "en-US-JennyNeural" else ""}>Jenny (женский, нейтральный)</option>
                    <option value="en-US-SaraNeural" {"selected" if settings.tts_voice_en == "en-US-SaraNeural" else ""}>Sara (женский, мягкий)</option>
                    <option value="en-GB-SoniaNeural" {"selected" if settings.tts_voice_en == "en-GB-SoniaNeural" else ""}>Sonia (британский)</option>
                    <option value="en-US-GuyNeural" {"selected" if settings.tts_voice_en == "en-US-GuyNeural" else ""}>Guy (мужской)</option>
                </select>
            </div>
            <button type="submit">Сохранить голос</button>
        </form>
    </div>

    <div class="card">
        <h2>🌤️ Погода</h2>
        <form method="POST" action="/dashboard/weather">
            <div class="form-group">
                <label>OpenWeatherMap API Key</label>
                <input type="password" name="weather_api_key" placeholder="Получить бесплатно на openweathermap.org">
            </div>
            <div class="form-group">
                <label>Город по умолчанию</label>
                <input type="text" name="weather_city" placeholder="Kyiv">
            </div>
            <button type="submit">Сохранить</button>
        </form>
        <p class="text-muted mt-2">Команды: "какая погода", "прогноз погоды"</p>
    </div>

    <div class="card">
        <h2>📋 Логи</h2>
        <a href="/dashboard/logs" class="btn btn-secondary">Просмотр логов</a>
    </div>

    <div class="card">
        <h2>🔌 Интеграции</h2>
        <p style="color: #888; margin-bottom: 12px;">Умный дом, IoT устройства, сервисы</p>
        <a href="/dashboard/integrations" class="btn btn-secondary">Управление интеграциями</a>
    </div>

    <div class="mt-2" style="text-align: center;">
        <a href="/logout" style="color: #888;">Выйти</a>
    </div>
    '''

    return HTMLResponse(base_template("Dashboard", content, token))


@router.post("/dashboard/settings")
async def dashboard_save_settings(
    request: Request,
    gemini_api_key: str = Form(default=""),
    telegram_bot_token: str = Form(default="")
):
    """Save settings from dashboard."""
    token = request.cookies.get("eva_token")
    auth = get_auth_manager()

    if not token or not auth.verify_token(token):
        return RedirectResponse(url="/login", status_code=303)

    vault = get_vault()

    if gemini_api_key:
        vault.store("gemini", {"api_key": gemini_api_key})

    if telegram_bot_token:
        vault.store("telegram", {"api_key": telegram_bot_token})

    return RedirectResponse(url="/dashboard?saved=1", status_code=303)


@router.get("/dashboard/gmail", response_class=HTMLResponse)
async def dashboard_gmail(request: Request):
    """Gmail configuration page."""
    token = request.cookies.get("eva_token")
    auth = get_auth_manager()

    if not token or not auth.verify_token(token):
        return RedirectResponse(url="/login")

    from integrations.gmail import get_gmail_integration
    gmail = get_gmail_integration()

    if gmail.is_authenticated:
        return RedirectResponse(url="/dashboard")

    content = '''
    <div class="card">
        <h2>📧 Подключение Gmail</h2>
        <p style="margin-bottom: 20px; color: #888;">
            Для подключения Gmail нужны OAuth credentials из Google Cloud Console
        </p>
        <ol style="margin-bottom: 20px; line-height: 1.8; color: #aaa;">
            <li>Перейди на <a href="https://console.cloud.google.com" target="_blank">console.cloud.google.com</a></li>
            <li>Создай проект или выбери существующий</li>
            <li>Включи Gmail API в разделе APIs & Services</li>
            <li>Создай OAuth 2.0 credentials (тип: Web application)</li>
            <li>Добавь Redirect URI: <code style="background:#000;padding:2px 6px;">http://YOUR_SERVER:8080/api/v1/gmail/callback</code></li>
            <li>Скопируй Client ID и Client Secret</li>
        </ol>
        <form method="POST" action="/dashboard/gmail">
            <div class="form-group">
                <label>Client ID</label>
                <input type="text" name="client_id" required placeholder="xxx.apps.googleusercontent.com">
            </div>
            <div class="form-group">
                <label>Client Secret</label>
                <input type="password" name="client_secret" required>
            </div>
            <div class="form-group">
                <label>Redirect URI (замени YOUR_SERVER на IP/домен сервера)</label>
                <input type="text" name="redirect_uri" required
                       placeholder="http://YOUR_SERVER:8080/api/v1/gmail/callback">
            </div>
            <button type="submit">Продолжить</button>
        </form>
        <p class="mt-2"><a href="/dashboard">← Назад</a></p>
    </div>
    '''

    return HTMLResponse(base_template("Gmail Setup", content))


@router.get("/dashboard/calendar", response_class=HTMLResponse)
async def dashboard_calendar(request: Request):
    """Calendar configuration page."""
    token = request.cookies.get("eva_token")
    auth = get_auth_manager()

    if not token or not auth.verify_token(token):
        return RedirectResponse(url="/login")

    from integrations.calendar import get_calendar_integration
    calendar = get_calendar_integration()

    if calendar.is_authenticated:
        return RedirectResponse(url="/dashboard")

    content = '''
    <div class="card">
        <h2>📅 Подключение Google Calendar</h2>
        <p style="margin-bottom: 20px; color: #888;">
            Для подключения календаря нужны OAuth credentials из Google Cloud Console
        </p>
        <ol style="margin-bottom: 20px; line-height: 1.8; color: #aaa;">
            <li>Перейди на <a href="https://console.cloud.google.com" target="_blank">console.cloud.google.com</a></li>
            <li>Используй тот же проект, что и для Gmail (или создай новый)</li>
            <li>Включи Google Calendar API в разделе APIs & Services</li>
            <li>Используй те же OAuth credentials или создай новые</li>
            <li>Добавь Redirect URI: <code style="background:#000;padding:2px 6px;">http://YOUR_SERVER:8080/api/v1/calendar/callback</code></li>
        </ol>
        <form method="POST" action="/dashboard/calendar">
            <div class="form-group">
                <label>Client ID</label>
                <input type="text" name="client_id" required placeholder="xxx.apps.googleusercontent.com">
            </div>
            <div class="form-group">
                <label>Client Secret</label>
                <input type="password" name="client_secret" required>
            </div>
            <div class="form-group">
                <label>Redirect URI</label>
                <input type="text" name="redirect_uri" required
                       placeholder="http://YOUR_SERVER:8080/api/v1/calendar/callback">
            </div>
            <button type="submit">Продолжить</button>
        </form>
        <p class="mt-2"><a href="/dashboard">← Назад</a></p>
    </div>
    '''

    return HTMLResponse(base_template("Calendar Setup", content))


@router.post("/dashboard/calendar")
async def dashboard_calendar_submit(
    request: Request,
    client_id: str = Form(...),
    client_secret: str = Form(...),
    redirect_uri: str = Form(...)
):
    """Configure Calendar and redirect to auth."""
    token = request.cookies.get("eva_token")
    auth = get_auth_manager()

    if not token or not auth.verify_token(token):
        return RedirectResponse(url="/login", status_code=303)

    from integrations.calendar import get_calendar_integration
    calendar = get_calendar_integration()

    calendar.configure_oauth(client_id, client_secret, redirect_uri)

    # Redirect to Google OAuth
    return RedirectResponse(url="/api/v1/calendar/auth", status_code=303)


@router.post("/dashboard/gmail")
async def dashboard_gmail_submit(
    request: Request,
    client_id: str = Form(...),
    client_secret: str = Form(...),
    redirect_uri: str = Form(...)
):
    """Configure Gmail and redirect to auth."""
    token = request.cookies.get("eva_token")
    auth = get_auth_manager()

    if not token or not auth.verify_token(token):
        return RedirectResponse(url="/login", status_code=303)

    from integrations.gmail import get_gmail_integration
    gmail = get_gmail_integration()

    gmail.configure_oauth(client_id, client_secret, redirect_uri)

    # Redirect to Google OAuth
    return RedirectResponse(url="/api/v1/gmail/auth", status_code=303)


@router.post("/dashboard/voice")
async def dashboard_voice_submit(
    request: Request,
    voice_ru: str = Form(...),
    voice_en: str = Form(...)
):
    """Save voice settings."""
    token = request.cookies.get("eva_token")
    auth = get_auth_manager()

    if not token or not auth.verify_token(token):
        return RedirectResponse(url="/login", status_code=303)

    vault = get_vault()
    vault.store("voice_settings", {
        "voice_ru": voice_ru,
        "voice_en": voice_en
    })

    return RedirectResponse(url="/dashboard?voice_saved=1", status_code=303)


@router.post("/dashboard/weather")
async def dashboard_weather_submit(
    request: Request,
    weather_api_key: str = Form(default=""),
    weather_city: str = Form(default="Kyiv")
):
    """Save weather settings."""
    token = request.cookies.get("eva_token")
    auth = get_auth_manager()

    if not token or not auth.verify_token(token):
        return RedirectResponse(url="/login", status_code=303)

    if weather_api_key:
        vault = get_vault()
        vault.store("weather", {
            "api_key": weather_api_key,
            "default_city": weather_city
        })

        # Configure weather service
        from integrations.weather import get_weather_service
        weather = get_weather_service()
        weather.configure(weather_api_key, weather_city)

    return RedirectResponse(url="/dashboard?weather_saved=1", status_code=303)


@router.get("/dashboard/integrations", response_class=HTMLResponse)
async def dashboard_integrations(request: Request):
    """Integrations management page."""
    token = request.cookies.get("eva_token")
    auth = get_auth_manager()

    if not token or not auth.verify_token(token):
        return RedirectResponse(url="/login")

    from integrations.base import get_integration_registry

    registry = get_integration_registry()
    available = registry.list_available()
    connected = registry.list_connected()

    integrations_html = ""
    for name in available:
        is_connected = name in connected
        status_class = "status-ok" if is_connected else "status-warn"
        status_text = "Подключено" if is_connected else "Не подключено"

        integrations_html += f'''
        <div style="background: rgba(0,0,0,0.2); padding: 16px; border-radius: 8px; margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong style="color: #00d9ff;">{name}</strong>
                    <span class="status {status_class}" style="margin-left: 8px;">{status_text}</span>
                </div>
                <a href="/dashboard/integrations/{name}" class="btn btn-secondary" style="font-size: 0.85em; padding: 8px 16px;">
                    {"Настроить" if not is_connected else "Управление"}
                </a>
            </div>
        </div>
        '''

    if not integrations_html:
        integrations_html = '<p style="color: #888;">Нет доступных интеграций</p>'

    content = f'''
    <div class="card">
        <h2>🔌 Интеграции</h2>
        {integrations_html}
    </div>

    <div class="card">
        <h2>🔍 Поиск устройств</h2>
        <p style="color: #888; margin-bottom: 12px;">
            Сканировать локальную сеть на предмет умных устройств
        </p>
        <a href="/api/v1/integrations/discover" class="btn btn-secondary" target="_blank">
            Сканировать сеть
        </a>
    </div>

    <div class="card">
        <h2>➕ Добавить интеграцию</h2>
        <p style="color: #888; margin-bottom: 12px;">
            Поддерживаемые типы: Home Assistant, MQTT, Telegram, Gmail
        </p>
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
            <a href="/dashboard/integrations/home_assistant" class="btn btn-secondary">Home Assistant</a>
            <a href="/dashboard/integrations/mqtt" class="btn btn-secondary">MQTT</a>
        </div>
    </div>

    <div class="mt-2">
        <a href="/dashboard">← Назад</a>
    </div>
    '''

    return HTMLResponse(base_template("Integrations", content, token))


@router.get("/dashboard/integrations/{name}", response_class=HTMLResponse)
async def dashboard_integration_detail(request: Request, name: str):
    """Integration detail/setup page."""
    token = request.cookies.get("eva_token")
    auth = get_auth_manager()

    if not token or not auth.verify_token(token):
        return RedirectResponse(url="/login")

    if name == "mqtt":
        content = '''
        <div class="card">
            <h2>📡 MQTT</h2>
            <p style="color: #888; margin-bottom: 20px;">
                Подключи EVA к MQTT брокеру для управления IoT устройствами
            </p>

            <form method="POST" action="/dashboard/integrations/mqtt/connect">
                <div class="form-group">
                    <label>MQTT Broker Host</label>
                    <input type="text" name="host" required placeholder="192.168.1.100 или mqtt.example.com">
                </div>
                <div class="form-group">
                    <label>Port</label>
                    <input type="number" name="port" value="1883" placeholder="1883">
                </div>
                <div class="form-group">
                    <label>Username (опционально)</label>
                    <input type="text" name="username" placeholder="mqtt_user">
                </div>
                <div class="form-group">
                    <label>Password (опционально)</label>
                    <input type="password" name="password">
                </div>
                <div class="form-group">
                    <label>Topic Prefix (опционально)</label>
                    <input type="text" name="topic_prefix" placeholder="home/">
                </div>
                <button type="submit">Подключить</button>
            </form>
        </div>

        <div class="card">
            <h2>📖 Поддерживаемые устройства</h2>
            <ul style="color: #aaa; line-height: 1.8;">
                <li>Zigbee2MQTT устройства</li>
                <li>Tasmota устройства</li>
                <li>Home Assistant MQTT Discovery</li>
                <li>Любые MQTT-совместимые устройства</li>
            </ul>
        </div>

        <div class="mt-2">
            <a href="/dashboard/integrations">← Назад</a>
        </div>
        '''
        return HTMLResponse(base_template("MQTT Setup", content, token))

    elif name == "home_assistant":
        content = '''
        <div class="card">
            <h2>🏠 Home Assistant</h2>
            <p style="color: #888; margin-bottom: 20px;">
                Подключи EVA к Home Assistant для управления умным домом голосом
            </p>

            <form method="POST" action="/dashboard/integrations/home_assistant/connect">
                <div class="form-group">
                    <label>URL Home Assistant</label>
                    <input type="text" name="url" required placeholder="http://192.168.1.100:8123">
                </div>
                <div class="form-group">
                    <label>Long-Lived Access Token</label>
                    <input type="password" name="token" required placeholder="eyJ0eXAiOi...">
                    <p class="text-muted" style="margin-top: 8px;">
                        Получить: Home Assistant → Profile → Long-Lived Access Tokens
                    </p>
                </div>
                <button type="submit">Подключить</button>
            </form>
        </div>

        <div class="card">
            <h2>📖 Что можно делать</h2>
            <ul style="color: #aaa; line-height: 1.8;">
                <li>"Включи свет в гостиной"</li>
                <li>"Выключи все лампы"</li>
                <li>"Установи температуру 22 градуса"</li>
                <li>"Какой статус датчика движения"</li>
                <li>"Список всех устройств"</li>
            </ul>
        </div>

        <div class="mt-2">
            <a href="/dashboard/integrations">← Назад</a>
        </div>
        '''
    else:
        content = f'''
        <div class="card">
            <h2>Интеграция: {name}</h2>
            <p style="color: #888;">Настройка этой интеграции пока не реализована</p>
        </div>
        <div class="mt-2">
            <a href="/dashboard/integrations">← Назад</a>
        </div>
        '''

    return HTMLResponse(base_template(f"Integration: {name}", content, token))


@router.post("/dashboard/integrations/home_assistant/connect")
async def dashboard_ha_connect(
    request: Request,
    url: str = Form(...),
    token: str = Form(...)
):
    """Connect Home Assistant from dashboard."""
    cookie_token = request.cookies.get("eva_token")
    auth = get_auth_manager()

    if not cookie_token or not auth.verify_token(cookie_token):
        return RedirectResponse(url="/login", status_code=303)

    from integrations.base import get_integration_registry

    registry = get_integration_registry()
    ha = registry.create_integration("home_assistant")

    if ha:
        success = await ha.connect({"url": url, "api_token": token})

        if success:
            # Store in vault
            vault = get_vault()
            vault.store("integration_home_assistant", {"url": url, "api_token": token})

            return RedirectResponse(url="/dashboard/integrations?connected=home_assistant", status_code=303)

    return RedirectResponse(url="/dashboard/integrations/home_assistant?error=1", status_code=303)


@router.post("/dashboard/integrations/mqtt/connect")
async def dashboard_mqtt_connect(
    request: Request,
    host: str = Form(...),
    port: int = Form(default=1883),
    username: str = Form(default=""),
    password: str = Form(default=""),
    topic_prefix: str = Form(default="")
):
    """Connect MQTT from dashboard."""
    cookie_token = request.cookies.get("eva_token")
    auth = get_auth_manager()

    if not cookie_token or not auth.verify_token(cookie_token):
        return RedirectResponse(url="/login", status_code=303)

    from integrations.base import get_integration_registry

    registry = get_integration_registry()
    mqtt = registry.create_integration("mqtt")

    if mqtt:
        credentials = {
            "host": host,
            "port": port,
            "topic_prefix": topic_prefix
        }
        if username:
            credentials["username"] = username
        if password:
            credentials["password"] = password

        success = await mqtt.connect(credentials)

        if success:
            # Store in vault
            vault = get_vault()
            vault.store("integration_mqtt", credentials)

            return RedirectResponse(url="/dashboard/integrations?connected=mqtt", status_code=303)

    return RedirectResponse(url="/dashboard/integrations/mqtt?error=1", status_code=303)


@router.get("/dashboard/logs", response_class=HTMLResponse)
async def dashboard_logs(request: Request, level: str = None, lines: int = 100):
    """Log viewer page."""
    token = request.cookies.get("eva_token")
    auth = get_auth_manager()

    if not token or not auth.verify_token(token):
        return RedirectResponse(url="/login")

    import os
    from collections import deque

    settings = get_settings()
    log_file = settings.log_file
    max_lines = min(lines, 500)

    logs_html = ""
    total_logs = 0

    if os.path.exists(log_file):
        try:
            logs = deque(maxlen=max_lines)
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    if level and f" - {level.upper()} - " not in line:
                        continue
                    logs.append(line)

            total_logs = len(logs)

            for log_line in logs:
                color = "#888"
                if " - ERROR - " in log_line:
                    color = "#ff6b6b"
                elif " - WARNING - " in log_line:
                    color = "#ffa500"
                elif " - INFO - " in log_line:
                    color = "#00d9ff"

                escaped_line = log_line.replace("<", "&lt;").replace(">", "&gt;")
                logs_html += f'<div style="color: {color}; margin: 2px 0; font-family: monospace; font-size: 0.85em; white-space: pre-wrap;">{escaped_line}</div>'

        except Exception as e:
            logs_html = f'<div style="color: #ff6b6b;">Error reading logs: {e}</div>'
    else:
        logs_html = '<div style="color: #888;">No logs yet</div>'

    level_filter = level or ""
    content = f'''
    <div class="card">
        <h2>📋 Логи ({total_logs} записей)</h2>

        <div style="margin-bottom: 16px;">
            <a href="/dashboard/logs" class="btn btn-secondary" style="margin-right: 8px;">Все</a>
            <a href="/dashboard/logs?level=info" class="btn btn-secondary" style="margin-right: 8px;">INFO</a>
            <a href="/dashboard/logs?level=warning" class="btn btn-secondary" style="margin-right: 8px;">WARNING</a>
            <a href="/dashboard/logs?level=error" class="btn btn-secondary">ERROR</a>
        </div>

        <div style="background: #0a0a15; border-radius: 8px; padding: 16px; max-height: 500px; overflow-y: auto;">
            {logs_html}
        </div>

        <div class="mt-2">
            <a href="/dashboard">← Назад</a>
            <a href="/dashboard/logs?lines=500" style="margin-left: 16px;">Показать 500</a>
        </div>
    </div>
    '''

    return HTMLResponse(base_template("Logs", content, token))
