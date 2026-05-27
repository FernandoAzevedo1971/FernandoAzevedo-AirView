"""
patients.py — Extração da lista de pacientes da página /wireless
Ordena por data de cadastro mais recente e retorna os TOP N pacientes.
"""
import os
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional
from playwright.async_api import Page
from config import PATIENT_LIST_SELECTORS, TIMEOUTS, BASE_URL
from utils import retry

logger = logging.getLogger("airview.patients")

# Formatos de data comuns no AirView (pt-BR e en-US)
DATE_FORMATS = [
    "%d/%m/%Y",   # 27/05/2025
    "%d/%m/%y",   # 27/05/25
    "%Y-%m-%d",   # 2025-05-27
    "%m/%d/%Y",   # 05/27/2025
    "%m/%d/%y",   # 05/27/25
    "%d-%m-%Y",   # 27-05-2025
    "%b %d, %Y",  # May 27, 2025
    "%d %b %Y",   # 27 May 2025
    "%d de %b de %Y",  # 27 de mai de 2025
]


def _parse_date(text: str) -> Optional[date]:
    """Tenta converter texto em data usando múltiplos formatos."""
    if not text:
        return None
    text = text.strip()
    # Extrai apenas a parte de data (ignora hora se houver)
    text = re.split(r'\s+\d{1,2}:\d{2}', text)[0].strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


@dataclass
class PatientEntry:
    index: int          # posição final (1-10 após ordenação)
    name: str
    href: str           # URL completa da página do paciente
    registration_date: Optional[date] = field(default=None)
    raw_date_text: str = ""


@retry(max_attempts=3, delay=5.0)
async def get_patient_list(page: Page) -> list[PatientEntry]:
    """
    Navega até /wireless, carrega TODOS os pacientes visíveis,
    ordena por data de cadastro mais recente e retorna os TOP MAX_PATIENTS.
    """
    max_patients = int(os.getenv("MAX_PATIENTS", "10"))
    wireless_url = f"{BASE_URL}/wireless"

    logger.info(f"Navegando para: {wireless_url}")
    await page.goto(wireless_url, wait_until="networkidle", timeout=TIMEOUTS["page_load"])
    await page.wait_for_timeout(3000)

    # --- Estratégia 1: Tenta ordenar clicando no cabeçalho da coluna de data ---
    sorted_by_site = await _try_sort_by_date_column(page)
    if sorted_by_site:
        logger.info("Ordenação por data aplicada via cabeçalho da tabela")
        await page.wait_for_timeout(2000)

    # --- Carrega todas as linhas disponíveis ---
    rows = await _get_all_rows(page)
    if not rows:
        await page.screenshot(path="logs/wireless_error.png", full_page=True)
        raise RuntimeError(
            "Não foi possível encontrar a lista de pacientes em /wireless. "
            "Screenshot salvo em logs/wireless_error.png"
        )

    logger.info(f"Total de linhas na página: {len(rows)}")

    # --- Extrai dados de cada linha ---
    all_patients = []
    for i, row in enumerate(rows):
        entry = await _extract_row_data(page, row, i)
        if entry:
            all_patients.append(entry)

    logger.info(f"Pacientes extraídos: {len(all_patients)}")

    # --- Estratégia 2: Ordena no Python por data de cadastro (mais recente primeiro) ---
    if not sorted_by_site:
        patients_with_date = [p for p in all_patients if p.registration_date]
        patients_without_date = [p for p in all_patients if not p.registration_date]

        if patients_with_date:
            patients_with_date.sort(key=lambda p: p.registration_date, reverse=True)
            logger.info(
                f"Ordenados por data de cadastro (Python): "
                f"{len(patients_with_date)} com data, "
                f"{len(patients_without_date)} sem data"
            )
            all_patients = patients_with_date + patients_without_date
        else:
            logger.warning(
                "Nenhuma data de cadastro encontrada nas linhas. "
                "Usando ordem original da página."
            )

    # --- Pega os TOP N ---
    top_patients = all_patients[:max_patients]

    # Reatribui índices sequenciais (1-10)
    for i, p in enumerate(top_patients, start=1):
        p.index = i

    for p in top_patients:
        date_str = p.registration_date.strftime("%d/%m/%Y") if p.registration_date else "sem data"
        logger.info(f"  [{p.index:02d}] {p.name} | cadastro: {date_str} | {p.href}")

    logger.info(f"Selecionados {len(top_patients)} pacientes mais recentes")
    return top_patients


async def _try_sort_by_date_column(page: Page) -> bool:
    """
    Tenta clicar no cabeçalho da coluna de data para ordenar decrescente.
    Retorna True se conseguiu clicar em algum cabeçalho de data.
    """
    for selector in PATIENT_LIST_SELECTORS["date_column_header"]:
        try:
            header = page.locator(selector).first
            await header.wait_for(state="visible", timeout=4000)
            # Primeiro clique: ordena crescente. Segundo: decrescente.
            await header.click()
            await page.wait_for_timeout(800)
            await header.click()
            await page.wait_for_timeout(800)
            logger.debug(f"Cabeçalho de data clicado: {selector!r}")
            return True
        except Exception:
            continue
    return False


async def _get_all_rows(page: Page):
    """Retorna todas as linhas de pacientes usando seletores em cascata."""
    for selector in PATIENT_LIST_SELECTORS["patient_row"]:
        try:
            rows = await page.locator(selector).all()
            if rows:
                logger.info(f"Seletor de linhas: {selector!r} ({len(rows)} linhas)")
                return rows
        except Exception:
            continue
    return []


async def _extract_row_data(page: Page, row, row_index: int) -> Optional[PatientEntry]:
    """Extrai nome, link e data de cadastro de uma linha da tabela."""
    name = f"Paciente_{row_index + 1:02d}"
    href = ""
    registration_date = None
    raw_date_text = ""

    # Extrai nome
    for name_sel in PATIENT_LIST_SELECTORS["patient_name"]:
        try:
            text = await row.locator(name_sel).first.inner_text(timeout=2000)
            text = text.strip()
            if text and len(text) > 1:
                name = text
                break
        except Exception:
            continue

    # Extrai link
    for link_sel in PATIENT_LIST_SELECTORS["patient_link"]:
        try:
            raw_href = await row.locator(link_sel).first.get_attribute("href", timeout=2000)
            if raw_href:
                href = raw_href if raw_href.startswith("http") else BASE_URL + raw_href
                break
        except Exception:
            continue

    if not href:
        href = f"__click_row_{row_index + 1}"

    # Extrai data de cadastro
    for date_sel in PATIENT_LIST_SELECTORS["registration_date"]:
        try:
            text = await row.locator(date_sel).first.inner_text(timeout=2000)
            text = text.strip()
            if text:
                raw_date_text = text
                parsed = _parse_date(text)
                if parsed:
                    registration_date = parsed
                    break
        except Exception:
            continue

    # Se não achou data com seletor específico, varre todas as células buscando padrão de data
    if not registration_date:
        registration_date, raw_date_text = await _scan_cells_for_date(row)

    # Ignora linhas que claramente são cabeçalhos (sem link e sem data)
    if href.startswith("__click_row_") and not registration_date and name.startswith("Paciente_"):
        return None

    return PatientEntry(
        index=row_index + 1,
        name=name,
        href=href,
        registration_date=registration_date,
        raw_date_text=raw_date_text,
    )


async def _scan_cells_for_date(row) -> tuple[Optional[date], str]:
    """Varre todas as células da linha procurando padrão de data."""
    DATE_PATTERN = re.compile(
        r'\b(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{4}[/\-]\d{2}[/\-]\d{2})\b'
    )
    try:
        cells = await row.locator("td").all()
        for cell in cells:
            try:
                text = await cell.inner_text(timeout=1000)
                match = DATE_PATTERN.search(text)
                if match:
                    parsed = _parse_date(match.group())
                    if parsed:
                        return parsed, match.group()
            except Exception:
                continue
    except Exception:
        pass
    return None, ""


async def navigate_to_patient(page: Page, patient: PatientEntry) -> None:
    """Navega até a página do paciente (via URL ou click na linha)."""
    if patient.href.startswith("__click_row_"):
        row_index = int(patient.href.split("_")[-1]) - 1
        await page.goto(f"{BASE_URL}/wireless", wait_until="networkidle",
                        timeout=TIMEOUTS["page_load"])
        await page.wait_for_timeout(2000)
        for selector in PATIENT_LIST_SELECTORS["patient_row"]:
            try:
                rows = await page.locator(selector).all()
                if rows and row_index < len(rows):
                    await rows[row_index].click()
                    await page.wait_for_load_state("networkidle", timeout=TIMEOUTS["network_idle"])
                    return
            except Exception:
                continue
        raise RuntimeError(f"Não foi possível navegar até {patient.name} via click")
    else:
        await page.goto(patient.href, wait_until="networkidle", timeout=TIMEOUTS["page_load"])
