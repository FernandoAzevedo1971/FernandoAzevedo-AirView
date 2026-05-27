"""
patients.py — Extração da lista de pacientes da página /wireless
"""
import os
import logging
from dataclasses import dataclass
from playwright.async_api import Page
from config import PATIENT_LIST_SELECTORS, TIMEOUTS, BASE_URL
from utils import retry

logger = logging.getLogger("airview.patients")


@dataclass
class PatientEntry:
    index: int
    name: str
    href: str   # URL completa da página do paciente


@retry(max_attempts=3, delay=5.0)
async def get_patient_list(page: Page) -> list[PatientEntry]:
    """
    Navega até /wireless e coleta os primeiros MAX_PATIENTS pacientes.
    Retorna lista de PatientEntry com nome e URL.
    """
    max_patients = int(os.getenv("MAX_PATIENTS", "10"))
    wireless_url = f"{BASE_URL}/wireless"

    logger.info(f"Navegando para: {wireless_url}")
    await page.goto(wireless_url, wait_until="networkidle", timeout=TIMEOUTS["page_load"])

    # Aguarda React renderizar a lista
    await page.wait_for_timeout(3000)

    # Tenta encontrar as linhas de pacientes com múltiplos seletores
    rows = []
    for selector in PATIENT_LIST_SELECTORS["patient_row"]:
        try:
            all_rows = await page.locator(selector).all()
            if len(all_rows) > 0:
                rows = all_rows
                logger.info(f"Linhas de pacientes encontradas com seletor: {selector!r} ({len(rows)} linhas)")
                break
        except Exception:
            continue

    if not rows:
        # Último recurso: screenshot para diagnóstico
        await page.screenshot(path="logs/wireless_error.png", full_page=True)
        raise RuntimeError(
            "Não foi possível encontrar a lista de pacientes em /wireless. "
            "Screenshot salvo em logs/wireless_error.png"
        )

    patients = []
    for i, row in enumerate(rows[:max_patients], start=1):
        name = f"Paciente_{i:02d}"  # fallback
        href = ""

        # Extrai nome
        for name_sel in PATIENT_LIST_SELECTORS["patient_name"]:
            try:
                text = await row.locator(name_sel).first.inner_text(timeout=3000)
                text = text.strip()
                if text and len(text) > 1:
                    name = text
                    break
            except Exception:
                continue

        # Extrai link
        for link_sel in PATIENT_LIST_SELECTORS["patient_link"]:
            try:
                raw_href = await row.locator(link_sel).first.get_attribute("href", timeout=3000)
                if raw_href:
                    href = raw_href if raw_href.startswith("http") else BASE_URL + raw_href
                    break
            except Exception:
                continue

        # Fallback: se não tem link direto, salva URL da linha para click posterior
        if not href:
            href = f"__click_row_{i}"  # sinaliza uso de click

        patients.append(PatientEntry(index=i, name=name, href=href))
        logger.info(f"  [{i:02d}] {name} → {href}")

    logger.info(f"Total de pacientes coletados: {len(patients)}")
    return patients


async def navigate_to_patient(page: Page, patient: PatientEntry) -> None:
    """Navega até a página do paciente (via URL ou click na linha)."""
    if patient.href.startswith("__click_row_"):
        # Fallback: navegar de volta para /wireless e clicar na linha correta
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
