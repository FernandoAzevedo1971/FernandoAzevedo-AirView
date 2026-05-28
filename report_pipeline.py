"""
report_pipeline.py — Orquestra a geração de UM relatório de marco para UM paciente.

Reaproveita os módulos de automação existentes:
  browser → login → patient_search → report_requester → pdf_screenshot
  → pdf_utils (data de início) → claude_analyzer (GPT-4o)

É chamado pela aplicação web (app.py) quando o usuário clica em "Gerar".
"""
import os
import asyncio
import logging
from datetime import date
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from browser import AirViewBrowser
from login import perform_login
from patient_search import find_patient_url
from report_requester import request_report
from pdf_screenshot import capture_first_page
from pdf_utils import extract_therapy_start_date
from claude_analyzer import analyze_report
from patients import PatientEntry
from scheduler import report_period
from utils import sanitize_filename

logger = logging.getLogger("airview.pipeline")


@dataclass
class PipelineResult:
    success: bool
    pdf_path: Optional[str] = None
    png_path: Optional[str] = None
    laudo_path: Optional[str] = None
    therapy_start_date: Optional[date] = None
    resolved_url: Optional[str] = None
    error: Optional[str] = None


async def _run_async(
    patient_id: int,
    patient_name: str,
    milestone_label: str,
    milestone_offset: int,
    airview_url: Optional[str],
    therapy_start: Optional[date],
) -> PipelineResult:
    """Executa o pipeline assíncrono completo para um marco."""
    result = PipelineResult(success=False)
    browser = AirViewBrowser()
    page = None

    safe_name = sanitize_filename(patient_name)
    prefix = f"reports/p{patient_id:03d}_{safe_name}_{milestone_label.replace('+', '')}"
    pdf_path = f"{prefix}.pdf"
    png_path = f"{prefix}_pag1.png"
    laudo_path = f"{prefix}_laudo.md"

    Path("reports").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)

    try:
        page = await browser.start()

        # 1. Login
        logger.info(f"[{patient_name} / {milestone_label}] Login...")
        await perform_login(page)

        # 2. Localiza o paciente (usa URL salva ou busca por nome)
        if airview_url:
            url = airview_url
            logger.info(f"[{patient_name}] Usando URL salva: {url}")
        else:
            url = await find_patient_url(page, patient_name)
            result_url = url  # será propagado para salvar no banco

        # Monta um PatientEntry compatível com request_report
        entry = PatientEntry(index=patient_id, name=patient_name, href=url)

        # 3. Define o período do relatório
        if therapy_start:
            start_date, end_date = report_period(therapy_start, milestone_offset)
        else:
            # D0: ainda não sabemos a data de início; usa últimos REPORT_DAYS dias
            start_date, end_date = None, None

        # 4. Solicita e baixa o PDF
        logger.info(f"[{patient_name} / {milestone_label}] Gerando relatório de adesão...")
        pdf_path = await request_report(
            page, entry, start_date=start_date, end_date=end_date, pdf_path=pdf_path
        )
        result.pdf_path = pdf_path

        # 5. Extrai a data de início da terapia (se ainda não temos)
        if not therapy_start:
            extracted = extract_therapy_start_date(pdf_path)
            if extracted:
                result.therapy_start_date = extracted
                logger.info(f"[{patient_name}] Data de início da terapia: {extracted}")

        # 6. Screenshot da 1ª página
        logger.info(f"[{patient_name} / {milestone_label}] Gerando PNG...")
        png_path = capture_first_page(pdf_path, png_path, dpi=300)
        result.png_path = png_path

        # 7. Análise GPT-4o Vision (se a chave estiver configurada)
        if os.getenv("OPENAI_API_KEY"):
            logger.info(f"[{patient_name} / {milestone_label}] Analisando com GPT-4o...")
            analyze_report(png_path, patient_name, laudo_path)
            result.laudo_path = laudo_path
        else:
            logger.warning("OPENAI_API_KEY ausente — laudo não gerado")

        # Propaga a URL resolvida (caso tenha sido por busca)
        if not airview_url:
            result.resolved_url = url

        result.success = True
        logger.info(f"[{patient_name} / {milestone_label}] ✓ Concluído")

    except Exception as e:
        logger.error(f"[{patient_name} / {milestone_label}] ✗ Erro: {e}", exc_info=True)
        result.error = str(e)
    finally:
        await browser.close()

    return result


def run_milestone(
    patient_id: int,
    patient_name: str,
    milestone_label: str,
    milestone_offset: int,
    airview_url: Optional[str] = None,
    therapy_start: Optional[date] = None,
) -> PipelineResult:
    """
    Wrapper síncrono — executa o pipeline assíncrono em um event loop próprio.
    Pensado para ser chamado dentro de uma thread de background pela app web.
    """
    return asyncio.run(
        _run_async(
            patient_id, patient_name, milestone_label,
            milestone_offset, airview_url, therapy_start,
        )
    )
