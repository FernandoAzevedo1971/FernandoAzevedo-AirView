"""
report_requester.py — Solicita o "Relatório de adesão ao tratamento e terapia"
no AirView e faz o download do PDF gerado.

Fluxo confirmado na tela real (/patients/{id}/charts):
  1) botão "Criar relatório" abre um MODAL
  2) <select> "Tipo de relatório" (dentro do modal) → escolhe a opção
     combinada (adesão + terapia — traz uso/adesão E pressão/vazamento/IAH)
  3) radio "Período de tempo fixo" (padrão, dentro do modal) → preenche
     dias + data final
  4) botão "Continuar" (dentro do modal) gera e baixa o PDF diretamente

IMPORTANTE: a página de fundo (/patients/{id}/charts) TEM CAMPOS QUASE
IDÊNTICOS aos do modal (um "30 dias" + data + botão "Actualização" que
controla o gráfico na tela, por trás do modal "Criar relatório"). Por
isso TODAS as buscas de elemento aqui são restritas ao modal — nunca à
página inteira — para não mexer sem querer nos controles de fundo.
"""
import os
import asyncio
import unicodedata
import logging
from datetime import date, timedelta
from pathlib import Path
from playwright.async_api import Page, Locator
from config import REPORT_SELECTORS, TIMEOUTS, BASE_URL
from patients import PatientEntry, navigate_to_patient
from utils import retry, sanitize_filename

logger = logging.getLogger("airview.report_requester")

# Seletores candidatos para o contêiner do modal (tentados em ordem)
_MODAL_CONTAINER_SELECTORS = (
    '[role="dialog"]',
    '.modal-content',
    '.modal-dialog',
    '.modal',
)


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


async def _escopo_modal(page: Page) -> Locator | Page:
    """
    Retorna um Locator restrito ao contêiner do modal aberto, se houver
    um reconhecível; caso contrário, retorna a própria `page` (escopo
    global, comportamento de fallback).
    """
    for selector in _MODAL_CONTAINER_SELECTORS:
        try:
            loc = page.locator(selector).last  # .last: o modal mais recente/no topo
            if await loc.is_visible(timeout=1200):
                return loc
        except Exception:
            continue
    logger.warning(
        "Contêiner do modal não identificado (nenhum de "
        f"{_MODAL_CONTAINER_SELECTORS} apareceu) — usando escopo da página "
        "inteira. Risco: pode interagir com os campos de FUNDO em vez dos "
        "do modal 'Criar relatório'."
    )
    return page


async def _achar(escopo, seletores: list, timeout_total: int = 8000):
    """
    Retorna o primeiro elemento visível dentre os seletores, DENTRO do
    escopo dado (modal ou página). Divide o timeout entre os seletores
    (não multiplica por cada um — evita esperas longas desnecessárias).
    """
    timeout_por_seletor = max(400, timeout_total // max(len(seletores), 1))
    for selector in seletores:
        try:
            loc = escopo.locator(selector).first
            await loc.wait_for(state="visible", timeout=timeout_por_seletor)
            return loc
        except Exception:
            continue
    return None


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
    await page.wait_for_timeout(1500)

    # --- 1) Abre o modal "Criar relatório" ---
    abriu = await _abrir_modal_relatorio(page)
    if not abriu:
        await page.screenshot(path=f"logs/report_not_found_{patient.index:02d}.png")
        raise RuntimeError(
            f"[{patient.name}] Botão 'Criar relatório' não encontrado. "
            f"Screenshot em logs/report_not_found_{patient.index:02d}.png"
        )

    modal = await _escopo_modal(page)

    # --- 2) Seleciona o tipo de relatório (adesão + terapia), DENTRO DO MODAL ---
    selecionado = await _selecionar_tipo_relatorio(page, modal)
    if not selecionado:
        await page.screenshot(path=f"logs/report_type_not_found_{patient.index:02d}.png")
        raise RuntimeError(
            f"[{patient.name}] Não foi possível selecionar o tipo de relatório "
            f"(adesão/terapia). Screenshot em logs/report_type_not_found_{patient.index:02d}.png"
        )

    # --- 3) Define o período (dias + data final), DENTRO DO MODAL, best-effort ---
    await _definir_periodo(page, modal, start_date, end_date)

    # --- 4) Clica em "Continuar" (dentro do modal) e captura o PDF gerado ---
    logger.info(f"[{patient.index}] Gerando relatório ({start_date} → {end_date})...")
    pdf_path = await _baixar_relatorio(page, modal, pdf_path)
    logger.info(f"[{patient.index}] PDF salvo: {pdf_path}")

    return pdf_path


async def _abrir_modal_relatorio(page: Page) -> bool:
    """Clica em 'Criar relatório' e confirma que o modal abriu."""
    botao = await _achar(page, REPORT_SELECTORS["reports_menu"], timeout_total=6000)
    if botao is None:
        return False
    await botao.click()
    logger.debug("'Criar relatório' clicado")

    # Confirma que o modal realmente abriu (marcador "Tipo de relatório")
    marcador = await _achar(page, REPORT_SELECTORS["report_modal_marker"], timeout_total=6000)
    return marcador is not None


async def _selecionar_tipo_relatorio(page: Page, modal) -> bool:
    """
    Localiza o <select> 'Tipo de relatório' DENTRO DO MODAL e escolhe a
    opção combinada (adesão + terapia), com fallback para só 'adesão'.
    """
    selects = await modal.locator("select:visible").all()
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


async def _definir_periodo(page: Page, modal, start_date: date, end_date: date) -> None:
    """
    Tenta preencher o período (dias + data final) DENTRO DO MODAL. É
    'best-effort': qualquer falha aqui é apenas registrada (warning) e
    NÃO interrompe o fluxo — o período padrão do site (ex.: 30 dias)
    ainda gera um relatório válido, só não no intervalo exato desejado.
    Não usa a tecla Escape (pode fechar o modal inteiro).
    """
    # Sem +1: os marcos do Next.js já definem o período como um offset direto
    # (D30 = dataInicio + 30 dias), então (end - start).days É o "30 dias"
    # que o médico espera ver — somar 1 dava 31 dias por engano.
    dias = (end_date - start_date).days

    try:
        campo_dias = await _achar(modal, REPORT_SELECTORS["period_days_input"], timeout_total=2500)
        if campo_dias is not None:
            await campo_dias.click()
            await campo_dias.fill(str(dias))
            logger.debug(f"Dias preenchidos: {dias}")
    except Exception as e:
        logger.warning(f"Não foi possível preencher dias do período: {e}")

    try:
        data_final_fmt = end_date.strftime("%d/%m/%Y")
        campo_data = await _achar(modal, REPORT_SELECTORS["period_end_date_input"], timeout_total=2500)
        if campo_data is not None:
            await campo_data.click()
            await campo_data.fill(data_final_fmt)
            logger.debug(f"Data final preenchida: {data_final_fmt}")
            # Fecha um datepicker clicando no título do modal (NUNCA Escape:
            # pode fechar o modal inteiro em vez de só o datepicker)
            try:
                titulo = modal.locator('text="Criar relatório"').first
                if await titulo.is_visible(timeout=800):
                    await titulo.click()
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"Não foi possível preencher data final — usando período padrão do site: {e}")

    await page.wait_for_timeout(400)


async def _baixar_relatorio(page: Page, modal, pdf_path: str) -> str:
    """
    Clica em 'Continuar' (dentro do modal) e captura o PDF gerado.
    Cobre 3 formas possíveis do PDF aparecer:
      1) download nativo do navegador
      2) nova aba/janela com o PDF
      3) a MESMA página navega para a URL do PDF (confirmado: é o que o
         AirView faz de fato — abre o PDF na mesma aba, sem disparar
         evento de download)

    Todos os "escutadores" são registrados ANTES do clique (ordem
    correta — Playwright só captura eventos que ocorrem depois de
    começar a escutar) e disputados num laço de verificação simples,
    sem esperar o timeout inteiro de uma estratégia que não vai ocorrer.
    """
    botao = await _achar(modal, REPORT_SELECTORS["generate_button"], timeout_total=6000)
    if botao is None:
        raise RuntimeError("Botão 'Continuar' não encontrado no modal de relatório")

    url_antes = page.url
    download_resultado = {}
    paginas_novas = []

    def _on_download(download):
        download_resultado.setdefault("download", download)

    def _capturar_pagina(p):
        paginas_novas.append(p)

    page.once("download", _on_download)
    page.context.on("page", _capturar_pagina)

    try:
        await botao.click()

        prazo, intervalo, decorrido = 20.0, 0.4, 0.0
        while decorrido < prazo:
            # --- Prioridade 1: download nativo do navegador ---
            if "download" in download_resultado:
                await download_resultado["download"].save_as(pdf_path)
                return pdf_path

            # --- Prioridade 2: nova aba abriu com o PDF ---
            if paginas_novas:
                new_page = paginas_novas[-1]
                await new_page.wait_for_load_state("load", timeout=8000)
                pdf_url = new_page.url
                response = await page.request.get(pdf_url)
                with open(pdf_path, "wb") as f:
                    f.write(await response.body())
                await new_page.close()
                return pdf_path

            # --- Prioridade 3: a MESMA página navegou para a URL do PDF ---
            if page.url != url_antes and ".pdf" in page.url.lower():
                response = await page.request.get(page.url)
                with open(pdf_path, "wb") as f:
                    f.write(await response.body())
                return pdf_path

            await asyncio.sleep(intervalo)
            decorrido += intervalo

        raise RuntimeError(
            f"Não foi possível capturar o PDF gerado em {prazo:.0f}s. "
            f"URL atual: {page.url}"
        )
    finally:
        page.context.remove_listener("page", _capturar_pagina)
