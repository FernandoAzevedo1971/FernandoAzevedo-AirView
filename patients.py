"""
patients.py — Estrutura de dados e navegação para um paciente do AirView.

No fluxo de sincronização, o paciente é localizado por nome via
patient_search.find_patient_url() — este módulo só define o formato
comum (PatientEntry) usado por report_requester.py e a navegação até
a página do paciente a partir de uma URL já conhecida.
"""
import logging
from dataclasses import dataclass
from playwright.async_api import Page
from config import TIMEOUTS

logger = logging.getLogger("airview.patients")


@dataclass
class PatientEntry:
    index: int      # identificador numérico livre (usado só em logs)
    name: str
    href: str        # URL completa da página do paciente no AirView


async def navigate_to_patient(page: Page, patient: PatientEntry) -> None:
    """Navega até a página do paciente a partir da URL já resolvida."""
    await page.goto(patient.href, wait_until="networkidle", timeout=TIMEOUTS["page_load"])
