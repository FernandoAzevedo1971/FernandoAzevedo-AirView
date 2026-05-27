"""
login.py — Fluxo de autenticação no AirView ResMed
"""
import os
import logging
from playwright.async_api import Page
from config import LOGIN_SELECTORS, TIMEOUTS, BASE_URL
from utils import try_selectors, retry

logger = logging.getLogger("airview.login")


@retry(max_attempts=3, delay=5.0)
async def perform_login(page: Page) -> None:
    """
    Realiza login no AirView.
    Lança exceção se as credenciais não estiverem configuradas ou se o login falhar.
    """
    username = os.getenv("AIRVIEW_USER")
    password = os.getenv("AIRVIEW_PASS")

    if not username or not password:
        raise ValueError(
            "AIRVIEW_USER e AIRVIEW_PASS devem estar definidos no arquivo .env"
        )

    login_url = f"{BASE_URL}/login"
    logger.info(f"Navegando para: {login_url}")

    await page.goto(login_url, wait_until="networkidle", timeout=TIMEOUTS["page_load"])

    # Pequena espera para React renderizar o formulário
    await page.wait_for_timeout(1500)

    logger.info("Preenchendo campo de usuário...")
    email_field = await try_selectors(page, LOGIN_SELECTORS["email_field"])
    await email_field.clear()
    await email_field.fill(username)

    logger.info("Preenchendo campo de senha...")
    pw_field = await try_selectors(page, LOGIN_SELECTORS["password_field"])
    await pw_field.clear()
    await pw_field.fill(password)

    logger.info("Clicando em Entrar...")
    submit = await try_selectors(page, LOGIN_SELECTORS["submit_button"])
    await submit.click()

    # Aguarda redirecionamento para fora da página de login
    try:
        await page.wait_for_url(
            lambda url: "/login" not in url and "signin" not in url.lower(),
            timeout=TIMEOUTS["page_load"],
        )
        logger.info(f"Login realizado com sucesso. URL atual: {page.url}")
    except Exception:
        # Tira screenshot para diagnóstico
        screenshot_path = "logs/login_error.png"
        await page.screenshot(path=screenshot_path)
        raise RuntimeError(
            f"Login falhou — ainda na página de login. "
            f"Verifique credenciais. Screenshot: {screenshot_path}"
        )
