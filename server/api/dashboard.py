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
        <h2>📚 API Документация</h2>
        <a href="/docs" class="btn btn-secondary">Открыть Swagger UI</a>
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
                <label>Redirect URI</label>
                <input type="text" name="redirect_uri" required
                       value="http://194.61.52.176:8080/api/v1/gmail/callback">
            </div>
            <button type="submit">Продолжить</button>
        </form>
        <p class="mt-2"><a href="/dashboard">← Назад</a></p>
    </div>
    '''

    return HTMLResponse(base_template("Gmail Setup", content))


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
