"""
report_requester.py — Solicita o "Relatório de adesão ao tratamento" no AirView
e faz o download do PDF gerado.
"""
import os
import logging
import asyncio
from datetime import date, timedelta
from pathlib import Path
from playwright.async_api import Page
from config import REPORT_SELECTORS, TIMEOUTS, BASE_URL
from patients import PatientEntry, navigate_to_patient
from utils import try_selectors, retry, sanitize_filename

logger = logging.getLogger("airview.report_requester")


def _get_date_range() -> tuple[date, date]:
    """Retorna (data_inicio, data_fim) para os últimos REPORT_DAYS dias."""
    days = int(os.getenv("REPORT_DAYS", "14"))
    end = date.today()
    start = end - timedelta(days=days - 1)  # inclusive
    return start, end


@retry(max_attempts=3, delay=8.0)
async def request_report(page: Page, patient: PatientEntry) -> str:
    """
    Navega até o perfil do paciente, solicita o "Relatório de adesão ao tratamento"
    com período de 14 dias e faz download do PDF.

    Returns:
        Caminho absoluto do arquivo PDF baixado.
    """
    start_date, end_date = _get_date_range()
    safe_name = sanitize_filename(patient.name)
    pdf_path = str(Path("reports") / f"paciente_{patient.index:02d}_{safe_name}.pdf")

    logger.info(f"[{patient.index}] Navegando para perfil: {patient.name}")
    await navigate_to_patient(page, patient)
    await page.wait_for_timeout(2000)

    # --- Estratégia 1: Menu de relatórios ---
    menu_opened = await _try_open_report_menu(page)

    if menu_opened:
        # Seleciona "Relatório de adesão ao tratamento"
        adherence_selected = await _try_select_adherence_report(page)
    else:
        # Estratégia 2: Procura diretamente na página
        adherence_selected = await _try_select_adherence_report(page)

    if not adherence_selected:
        await page.screenshot(path=f"logs/report_not_found_{patient.index:02d}.png")
        raise RuntimeError(
            f"[{patient.name}] Não foi possível localizar 'Relatório de adesão ao tratamento'. "
            f"Screenshot em logs/report_not_found_{patient.index:02d}.png"
        )

    # --- Define período de 14 dias ---
    await _set_period(page, start_date, end_date)

    # --- Gera/baixa o relatório ---
    logger.info(f"[{patient.index}] Gerando relatório ({start_date} → {end_date})...")
    pdf_path = await _download_report(page, pdf_path)
    logger.info(f"[{patient.index}] PDF salvo: {pdf_path}")

    return pdf_path


async def _try_open_report_menu(page: Page) -> bool:
    """Tenta abrir o menu de relatórios. Retorna True se conseguiu."""
    for selector in REPORT_SELECTORS["reports_menu"]:
        try:
            btn = page.locator(selector).first
            await btn.wait_for(state="visible", timeout=5000)
            await btn.click()
            await page.wait_for_timeout(1000)
            logger.debug(f"Menu de relatórios aberto com: {selector!r}")
            return True
        except Exception:
            continue
    return False


async def _try_select_adherence_report(page: Page) -> bool:
    """Tenta selecionar 'Relatório de adesão ao tratamento'. Retorna True se conseguiu."""
    for selector in REPORT_SELECTORS["adherence_report"]:
        try:
            el = page.locator(selector).first
            await el.wait_for(state="visible", timeout=5000)
            await el.click()
            await page.wait_for_timeout(1000)
            logger.debug(f"Relatório de adesão selecionado com: {selector!r}")
            return True
        except Exception:
            continue
    return False


async def _set_period(page: Page, start_date: date, end_date: date) -> None:
    """
    Define o período do relatório para os últimos 14 dias.
    Tenta 3 estratégias: botão preset → inputs de data → parâmetros de URL.
    """
    # Estratégia 1: Botão de preset "14 dias"
    for selector in REPORT_SELECTORS["period_14_days"]:
        try:
            btn = page.locator(selector).first
            await btn.wait_for(state="visible", timeout=4000)
            await btn.click()
            await page.wait_for_timeout(1000)
            logger.debug(f"Período de 14 dias selecionado via botão preset: {selector!r}")
            return
        except Exception:
            continue

    # Estratégia 2: Inputs de data
    try:
        start_inputs = await page.locator('input[type="date"]').all()
        if len(start_inputs) >= 2:
            await start_inputs[0].fill(start_date.strftime("%Y-%m-%d"))
            await start_inputs[1].fill(end_date.strftime("%Y-%m-%d"))
            await start_inputs[1].press("Tab")
            await page.wait_for_timeout(1000)
            logger.debug("Período definido via inputs de data")
            return
    except Exception:
        pass

    # Estratégia 3: Inputs por nome
    for start_sel in REPORT_SELECTORS["date_start_input"]:
        try:
            start_el = page.locator(start_sel).first
            await start_el.fill(start_date.strftime("%Y-%m-%d"))
            break
        except Exception:
            continue

    for end_sel in REPORT_SELECTORS["date_end_input"]:
        try:
            end_el = page.locator(end_sel).first
            await end_el.fill(end_date.strftime("%Y-%m-%d"))
            await end_el.press("Enter")
            break
        except Exception:
            continue

    await page.wait_for_timeout(1000)
    logger.debug("Período definido via inputs nomeados (ou sem período definido)")


async def _download_report(page: Page, pdf_path: str) -> str:
    """
    Clica no botão de gerar/baixar e captura o download do PDF.
    Retorna o caminho do arquivo salvo.
    """
    generate_btn = None
    for selector in REPORT_SELECTORS["generate_button"]:
        try:
            btn = page.locator(selector).first
            await btn.wait_for(state="visible", timeout=5000)
            generate_btn = btn
            logger.debug(f"Botão de geração encontrado: {selector!r}")
            break
        except Exception:
            continue

    if generate_btn is None:
        raise RuntimeError("Botão de gerar/baixar relatório não encontrado na página")

    # Intercepta o download
    try:
        async with page.expect_download(timeout=TIMEOUTS["download"]) as dl_info:
            await generate_btn.click()
        download = await dl_info.value
        await download.save_as(pdf_path)
        return pdf_path
    except Exception as e:
        # Fallback: tenta encontrar link de download na nova janela/aba
        logger.warning(f"Download direto falhou ({e}), tentando via nova aba...")
        async with page.context.expect_page() as page_info:
            await generate_btn.click()
        new_page = await page_info.value
        await new_page.wait_for_load_state("load")
        # Se abriu um PDF no browser, salva via URL
        pdf_url = new_page.url
        if ".pdf" in pdf_url.lower() or "application/pdf" in (await new_page.content())[:100]:
            response = await page.request.get(pdf_url)
            with open(pdf_path, "wb") as f:
                f.write(await response.body())
            await new_page.close()
            return pdf_path
        await new_page.close()
        raise RuntimeError(f"Não foi possível baixar o PDF: {pdf_url}")
