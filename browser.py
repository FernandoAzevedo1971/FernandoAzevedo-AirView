"""
browser.py — Ciclo de vida do browser Playwright (Chromium headless)
"""
import os
import logging
from pathlib import Path
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

logger = logging.getLogger("airview.browser")


class AirViewBrowser:
    """Gerencia o ciclo de vida do browser Chromium."""

    def __init__(self):
        self.playwright = None
        self.browser: Browser = None
        self.context: BrowserContext = None

    async def start(self) -> Page:
        """Inicializa o browser e retorna uma página pronta para uso."""
        headless = os.getenv("HEADLESS", "true").lower() == "true"
        slow_mo = int(os.getenv("SLOW_MO", "0"))

        # Garante que a pasta de downloads existe
        Path("reports").mkdir(exist_ok=True)
        downloads_path = str(Path("reports").resolve())

        logger.info(f"Iniciando Chromium (headless={headless}, slow_mo={slow_mo}ms)")

        # Localiza o binário do Chrome.
        # Prioridade:
        #   1. Variável de ambiente PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH
        #   2. Chrome instalado pelo Playwright (default — usado ao rodar localmente)
        #   3. Chrome baixado via puppeteer (fallback para ambientes restritos)
        #   4. Chrome/Chromium do sistema
        # Se nada for encontrado, executable_path fica None e o Playwright usa
        # seu próprio Chromium (o caminho normal de `playwright install chromium`).
        import glob
        chrome_candidates = [os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH", "")]
        # Puppeteer cache (qualquer versão) — usado no ambiente cloud restrito
        chrome_candidates += sorted(
            glob.glob(str(Path.home() / ".cache/puppeteer/chrome/*/chrome-linux64/chrome")),
            reverse=True,  # versão mais recente primeiro
        )
        chrome_candidates += [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
        ]
        executable_path = None
        for candidate in chrome_candidates:
            if candidate and Path(candidate).exists():
                executable_path = candidate
                logger.info(f"Usando Chrome: {executable_path}")
                break
        if not executable_path:
            logger.info("Usando Chromium padrão do Playwright")

        self.playwright = await async_playwright().start()
        launch_kwargs = dict(
            headless=headless,
            slow_mo=slow_mo,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",      # Crítico em ambientes Linux/Docker
                "--disable-gpu",
                "--disable-blink-features=AutomationControlled",  # Evita detecção de bot
                "--window-size=1280,900",
                "--ignore-certificate-errors",  # Necessário em ambientes com proxy SSL
            ],
        )
        if executable_path:
            launch_kwargs["executable_path"] = executable_path

        self.browser = await self.playwright.chromium.launch(**launch_kwargs)

        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            accept_downloads=True,
            # downloads_path não é parâmetro do new_context, usamos save_as() depois
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
        )

        # Bloquear recursos desnecessários para acelerar a navegação
        await self.context.route(
            "**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf,mp4,webp,ico}",
            lambda route: route.abort(),
        )

        page = await self.context.new_page()

        # Timeout padrão para todas as operações
        timeout_ms = int(os.getenv("TIMEOUT_MS", "30000"))
        page.set_default_timeout(timeout_ms)
        page.set_default_navigation_timeout(timeout_ms)

        logger.info("Browser inicializado com sucesso")
        return page

    async def close(self):
        """Encerra o browser e libera recursos."""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("Browser encerrado")
        except Exception as e:
            logger.warning(f"Erro ao encerrar browser: {e}")
