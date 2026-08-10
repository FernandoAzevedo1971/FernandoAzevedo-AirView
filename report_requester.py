"""
report_requester.py — Solicita o "Relatório de adesão ao tratamento e terapia"
no AirView e faz o download do PDF gerado.

Fluxo confirmado na tela real (/patients/{id}/charts):
  1) botão "Criar relatório" abre um modal
  2) <select> "Tipo de relatório" → escolhe a opção combinada
     (adesão + terapia — traz uso/adesão E pressão/vazamento/IAH)
  3) radio "Período de tempo fixo" (padrão) → preenche dias + data final
  4) botão "Continuar" gera e baixa o PDF diretamente
"""
import os
import re
import unicodedata
import logging
from datetime import date, timedelta
from pathlib import Path
from playwright.async_api import Page
from config import REPORT_SELECTORS, TIMEOUTS, BASE_URL
from patients import PatientEntry, navigate_to_patient
from utils import retry, sanitize_filename

logger = logging.getLogger("airview.report_requester")


def _get_date_range() -> tuple[date, date]:
    """Retorna (data_inicio, data_fim) para os últimos REPORT_DAYS dias."""
    days = int(os.getenv("REPORT_DAYS", "14"))
    end = date.today()
    start = end - timedelta(days=days - 1)  # inclusive
    return start, end


def _normalizar(texto: str) -> str:
    """Remove acentos e caixa, para comparação tolerante de texto."""
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return sem_acento.lower()


@retry(max_attempts=3, delay=8.0)
async def request_report(
    page: Page,
    patient: PatientEntry,
    start_date: date = None,
    end_date: date = None,
    pdf_path: str = None,
) -> str:
    """
    Navega até o perfil do paciente, solicita o relatório de adesão e
    terapia, e faz download do PDF.

    Args:
        page: página Playwright já autenticada
        patient: PatientEntry com nome e href/URL do paciente
        start_date: início do período (default: REPORT_DAYS atrás)
        end_date: fim do período (default: hoje)
        pdf_path: caminho de saída do PDF (default: reports/paciente_NN_nome.pdf)

    Returns:
        Caminho absoluto do arquivo PDF baixado.
    """
    if start_date is None or end_date is None:
        start_date, end_date = _get_date_range()

    if pdf_path is None:
        safe_name = sanitize_filename(patient.name)
        pdf_path = str(Path("reports") / f"paciente_{patient.index:02d}_{safe_name}.pdf")

    logger.info(f"[{patient.index}] Navegando para perfil: {patient.name}")
    await navigate_to_patient(page, patient)
    await page.wait_for_timeout(2000)

    # --- 1) Abre o modal "Criar relatório" ---
    abriu = await _abrir_modal_relatorio(page)
    if not abriu:
        await page.screenshot(path=f"logs/report_not_found_{patient.index:02d}.png")
        raise RuntimeError(
            f"[{patient.name}] Botão 'Criar relatório' não encontrado. "
            f"Screenshot em logs/report_not_found_{patient.index:02d}.png"
        )

    # --- 2) Seleciona o tipo de relatório (adesão + terapia) ---
    selecionado = await _selecionar_tipo_relatorio(page)
    if not selecionado:
        await page.screenshot(path=f"logs/report_type_not_found_{patient.index:02d}.png")
        raise RuntimeError(
            f"[{patient.name}] Não foi possível selecionar o tipo de relatório "
            f"(adesão/terapia). Screenshot em logs/report_type_not_found_{patient.index:02d}.png"
        )

    # --- 3) Define o período (dias + data final) ---
    await _definir_periodo(page, start_date, end_date)

    # --- 4) Clica em "Continuar" e captura o PDF gerado ---
    logger.info(f"[{patient.index}] Gerando relatório ({start_date} → {end_date})...")
    pdf_path = await _baixar_relatorio(page, pdf_path)
    logger.info(f"[{patient.index}] PDF salvo: {pdf_path}")

    return pdf_path


async def _abrir_modal_relatorio(page: Page) -> bool:
    """Clica em 'Criar relatório' e confirma que o modal abriu."""
    for selector in REPORT_SELECTORS["reports_menu"]:
        try:
            btn = page.locator(selector).first
            await btn.wait_for(state="visible", timeout=6000)
            await btn.click()
            logger.debug(f"'Criar relatório' clicado via: {selector!r}")
            break
        except Exception:
            continue
    else:
        return False

    # Confirma que o modal realmente abriu (marcador "Tipo de relatório")
    for selector in REPORT_SELECTORS["report_modal_marker"]:
        try:
            await page.locator(selector).first.wait_for(state="visible", timeout=6000)
            return True
        except Exception:
            continue
    return False


async def _selecionar_tipo_relatorio(page: Page) -> bool:
    """
    Localiza o <select> 'Tipo de relatório' e escolhe a opção combinada
    (adesão + terapia), com fallback para só 'adesão' se a combinada
    não existir. Varre todos os <select> visíveis em vez de depender de
    um ID específico (não confirmado na inspeção).
    """
    selects = await page.locator("select:visible").all()
    if not selects:
        return False

    for palavras_chave in REPORT_SELECTORS["adherence_report_keywords_priority"]:
        for select in selects:
            try:
                opcoes = await select.locator("option").all_text_contents()
            except Exception:
                continue
            for i, texto in enumerate(opcoes):
                normalizado = _normalizar(texto)
                if all(p in normalizado for p in palavras_chave):
                    try:
                        await select.select_option(index=i)
                        logger.info(f"Tipo de relatório selecionado: {texto!r}")
                        await page.wait_for_timeout(800)
                        return True
                    except Exception:
                        continue
    return False


async def _definir_periodo(page: Page, start_date: date, end_date: date) -> None:
    """
    Preenche o período usando o modo 'Período de tempo fixo' (padrão):
    quantidade de dias + data final. Se os campos não forem encontrados,
    segue em frente mesmo assim — o valor padrão do site pode servir.
    """
    dias = (end_date - start_date).days + 1  # inclusive

    # Campo de quantidade de dias
    for selector in REPORT_SELECTORS["period_days_input"]:
        try:
            campo = page.locator(selector).first
            if await campo.is_visible(timeout=2000):
                await campo.click()
                await campo.fill(str(dias))
                logger.debug(f"Dias preenchidos: {dias}")
                break
        except Exception:
            continue

    # Campo de data final (tenta formato dd/mm/aaaa, o exibido na tela)
    data_final_fmt = end_date.strftime("%d/%m/%Y")
    for selector in REPORT_SELECTORS["period_end_date_input"]:
        try:
            campo = page.locator(selector).first
            if await campo.is_visible(timeout=2000):
                await campo.click()
                await campo.fill(data_final_fmt)
                await campo.press("Escape")  # fecha datepicker se abrir
                logger.debug(f"Data final preenchida: {data_final_fmt}")
                break
        except Exception:
            continue

    await page.wait_for_timeout(500)


async def _baixar_relatorio(page: Page, pdf_path: str) -> str:
    """
    Clica em 'Continuar' e captura o PDF gerado — confirmado que o PDF
    é aberto/baixado diretamente, sem etapa intermediária.
    """
    botao = None
    for selector in REPORT_SELECTORS["generate_button"]:
        try:
            btn = page.locator(selector).first
            await btn.wait_for(state="visible", timeout=5000)
            botao = btn
            logger.debug(f"Botão 'Continuar' encontrado via: {selector!r}")
            break
        except Exception:
            continue

    if botao is None:
        raise RuntimeError("Botão 'Continuar' não encontrado no modal de relatório")

    # Estratégia 1: download direto
    try:
        async with page.expect_download(timeout=TIMEOUTS["download"]) as dl_info:
            await botao.click()
        download = await dl_info.value
        await download.save_as(pdf_path)
        return pdf_path
    except Exception as e:
        logger.debug(f"Download direto não ocorreu ({e}); tentando nova aba...")

    # Estratégia 2: abre em nova aba (visualizador de PDF do navegador)
    try:
        async with page.context.expect_page(timeout=TIMEOUTS["download"]) as page_info:
            pass  # botão já foi clicado na tentativa acima em alguns casos
        new_page = await page_info.value
    except Exception:
        # O clique não foi feito ainda (a tentativa 1 pode ter falhado antes de clicar)
        async with page.context.expect_page(timeout=TIMEOUTS["download"]) as page_info:
            await botao.click()
        new_page = await page_info.value

    await new_page.wait_for_load_state("load")
    pdf_url = new_page.url
    response = await page.request.get(pdf_url)
    with open(pdf_path, "wb") as f:
        f.write(await response.body())
    await new_page.close()
    return pdf_path
