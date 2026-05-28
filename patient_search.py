"""
patient_search.py — Localiza um paciente no AirView pelo nome digitado pelo médico.
Usado pela aplicação web onde os pacientes são cadastrados manualmente.
"""
import logging
from playwright.async_api import Page
from config import SEARCH_SELECTORS, TIMEOUTS, BASE_URL

logger = logging.getLogger("airview.patient_search")


async def find_patient_url(page: Page, patient_name: str) -> str:
    """
    Busca o paciente pelo nome e retorna a URL da página dele.

    Estratégia:
    1. Vai para /wireless (ou home)
    2. Localiza o campo de busca e digita o nome
    3. Submete (Enter ou botão)
    4. Clica/captura o primeiro resultado e retorna sua URL

    Args:
        page: página Playwright autenticada
        patient_name: nome do paciente conforme cadastrado no AirView

    Returns:
        URL completa da página do paciente

    Raises:
        RuntimeError se o paciente não for encontrado.
    """
    logger.info(f"Buscando paciente: {patient_name!r}")

    await page.goto(f"{BASE_URL}/wireless", wait_until="networkidle",
                    timeout=TIMEOUTS["page_load"])
    await page.wait_for_timeout(2000)

    # --- Localiza e preenche o campo de busca ---
    search_input = None
    for selector in SEARCH_SELECTORS["search_input"]:
        try:
            el = page.locator(selector).first
            await el.wait_for(state="visible", timeout=4000)
            search_input = el
            logger.debug(f"Campo de busca encontrado: {selector!r}")
            break
        except Exception:
            continue

    if search_input is None:
        await page.screenshot(path=f"logs/search_no_input.png")
        raise RuntimeError(
            "Campo de busca não encontrado na página. "
            "Screenshot em logs/search_no_input.png"
        )

    await search_input.click()
    await search_input.fill(patient_name)
    await page.wait_for_timeout(1000)

    # Tenta submeter via Enter
    await search_input.press("Enter")
    await page.wait_for_timeout(2000)

    # Se houver botão de busca, tenta clicar também
    for selector in SEARCH_SELECTORS["search_button"]:
        try:
            btn = page.locator(selector).first
            if await btn.is_visible(timeout=1500):
                await btn.click()
                await page.wait_for_timeout(2000)
                break
        except Exception:
            continue

    await page.wait_for_load_state("networkidle", timeout=TIMEOUTS["network_idle"])
    await page.wait_for_timeout(1500)

    # --- Captura o primeiro resultado ---
    for selector in SEARCH_SELECTORS["search_result"]:
        try:
            result = page.locator(selector).first
            await result.wait_for(state="visible", timeout=4000)

            # Tenta obter href diretamente
            href = await result.get_attribute("href", timeout=2000)
            if href:
                url = href if href.startswith("http") else BASE_URL + href
                logger.info(f"Paciente encontrado (link direto): {url}")
                return url

            # Sem href: clica no resultado e captura a URL resultante
            await result.click()
            await page.wait_for_load_state("networkidle", timeout=TIMEOUTS["network_idle"])
            await page.wait_for_timeout(1500)
            if "/wireless" not in page.url or page.url != f"{BASE_URL}/wireless":
                logger.info(f"Paciente encontrado (via clique): {page.url}")
                return page.url
        except Exception:
            continue

    await page.screenshot(path=f"logs/search_no_result.png")
    raise RuntimeError(
        f"Paciente {patient_name!r} não encontrado nos resultados de busca. "
        f"Verifique se o nome está exatamente como no AirView. "
        f"Screenshot em logs/search_no_result.png"
    )
