"""
login.py — Autenticação no AirView ResMed.

O AirView usa Okta com login em DUAS ETAPAS:
  1) informa o usuário → clica em "Avançar"
  2) a tela de senha aparece → informa a senha → clica em "Entrar"

A função abaixo lida com as duas etapas e também com o caso (mais raro)
de a senha já estar visível na primeira tela.
"""
import os
import logging
from playwright.async_api import Page
from config import LOGIN_SELECTORS, TIMEOUTS, BASE_URL
from utils import try_selectors, retry

logger = logging.getLogger("airview.login")


async def _achar(page, seletores, timeout=8000):
    """Retorna o primeiro elemento visível dentre os seletores, ou None."""
    for selector in seletores:
        try:
            loc = page.locator(selector).first
            await loc.wait_for(state="visible", timeout=timeout)
            logger.debug(f"Elemento encontrado via {selector!r}")
            return loc
        except Exception:
            continue
    return None


async def _mensagem_de_erro(page) -> str:
    """Lê mensagens de erro/desafio exibidas na tela de login, se houver."""
    for selector in LOGIN_SELECTORS.get("error_message", []):
        try:
            loc = page.locator(selector).first
            if await loc.is_visible(timeout=1500):
                texto = (await loc.inner_text()).strip()
                if texto:
                    return " ".join(texto.split())[:200]
        except Exception:
            continue
    return ""


@retry(max_attempts=3, delay=5.0)
async def perform_login(page: Page) -> None:
    """
    Realiza login no AirView (fluxo de duas etapas).
    Lança exceção com diagnóstico claro se não conseguir.
    """
    username = os.getenv("AIRVIEW_USER")
    password = os.getenv("AIRVIEW_PASS")

    if not username or not password:
        raise ValueError(
            "AIRVIEW_USER e AIRVIEW_PASS devem estar definidos no arquivo .env"
        )

    logger.info(f"Navegando para: {BASE_URL}/login")
    await page.goto(f"{BASE_URL}/login", wait_until="networkidle",
                    timeout=TIMEOUTS["page_load"])
    await page.wait_for_timeout(2500)   # deixa o SPA/Okta renderizar

    # ---------- Etapa 1: usuário ----------
    logger.info("Etapa 1/2 — preenchendo usuário...")
    campo_usuario = await _achar(page, LOGIN_SELECTORS["email_field"], timeout=12000)
    if campo_usuario is None:
        await page.screenshot(path="logs/login_erro_usuario.png", full_page=True)
        raise RuntimeError(
            "Campo de usuário não encontrado na tela de login. "
            "Screenshot: logs/login_erro_usuario.png"
        )
    await campo_usuario.click()
    await campo_usuario.fill(username)

    # A senha já está visível (login de uma etapa)?
    campo_senha = await _achar(page, LOGIN_SELECTORS["password_field"], timeout=2000)

    if campo_senha is None:
        # Login de duas etapas: avança para a tela de senha
        logger.info("Senha não visível — clicando em 'Avançar'...")
        botao_avancar = await _achar(page, LOGIN_SELECTORS["next_button"], timeout=8000)
        if botao_avancar is None:
            await page.screenshot(path="logs/login_erro_avancar.png", full_page=True)
            raise RuntimeError(
                "Botão de avançar (etapa 1) não encontrado. "
                "Screenshot: logs/login_erro_avancar.png"
            )
        await botao_avancar.click()
        await page.wait_for_timeout(3000)

        logger.info("Etapa 2/2 — preenchendo senha...")
        campo_senha = await _achar(page, LOGIN_SELECTORS["password_field"], timeout=15000)
        if campo_senha is None:
            erro = await _mensagem_de_erro(page)
            await page.screenshot(path="logs/login_erro_senha.png", full_page=True)
            raise RuntimeError(
                f"Campo de senha não apareceu após avançar. "
                f"{('Mensagem na tela: ' + erro) if erro else ''} "
                f"Screenshot: logs/login_erro_senha.png"
            )
    else:
        logger.info("Senha visível na mesma tela (login de uma etapa)")

    await campo_senha.click()
    await campo_senha.fill(password)

    # ---------- Confirmar ----------
    logger.info("Confirmando login...")
    botao_entrar = await _achar(page, LOGIN_SELECTORS["submit_button"], timeout=8000)
    if botao_entrar is None:
        # Alguns formulários aceitam Enter no campo de senha
        logger.info("Botão de entrar não encontrado — tentando tecla Enter")
        await campo_senha.press("Enter")
    else:
        await botao_entrar.click()

    # ---------- Verificar sucesso ----------
    try:
        await page.wait_for_url(
            lambda url: "/login" not in url and "signin" not in url.lower(),
            timeout=TIMEOUTS["page_load"],
        )
        logger.info(f"✓ Login realizado. URL: {page.url}")
    except Exception:
        erro = await _mensagem_de_erro(page)
        await page.screenshot(path="logs/login_erro_final.png", full_page=True)
        detalhe = f" Mensagem na tela: {erro}" if erro else ""
        raise RuntimeError(
            f"Login não concluído — a página continua na tela de autenticação.{detalhe} "
            f"Pode ser senha incorreta, verificação em duas etapas (2FA) ou captcha. "
            f"Screenshot: logs/login_erro_final.png"
        )
