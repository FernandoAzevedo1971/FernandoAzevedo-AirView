"""
pdf_utils.py — Utilitários de leitura de PDF: extração de texto e da data de
início da terapia a partir do "Relatório de adesão ao tratamento".
"""
import re
import logging
from datetime import datetime, date
from typing import Optional
from config import THERAPY_START_LABELS

logger = logging.getLogger("airview.pdf_utils")

DATE_FORMATS = [
    "%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y",
    "%d-%m-%Y", "%b %d, %Y", "%d %b %Y", "%d de %b de %Y",
]

# Padrão genérico de data (dd/mm/yyyy, yyyy-mm-dd, etc.)
DATE_PATTERN = re.compile(
    r'\b(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{4}[/\-]\d{2}[/\-]\d{2})\b'
)


def _parse_date(text: str) -> Optional[date]:
    """Converte texto em data tentando vários formatos."""
    if not text:
        return None
    text = text.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def extract_pdf_text(pdf_path: str) -> str:
    """Extrai todo o texto do PDF (todas as páginas)."""
    try:
        import fitz  # pymupdf
    except ImportError:
        raise ImportError("pymupdf não está instalado. Execute: pip install pymupdf")

    doc = fitz.open(pdf_path)
    text = "\n".join(page.get_text() for page in doc)
    doc.close()
    return text


def extract_therapy_start_date(pdf_path: str) -> Optional[date]:
    """
    Lê o PDF e tenta localizar a DATA DE INÍCIO DA TERAPIA.

    Estratégia:
    1. Procura por rótulos conhecidos (THERAPY_START_LABELS) e pega a data
       que aparece na mesma linha ou imediatamente após.
    2. Procura por um intervalo "dd/mm/yyyy - dd/mm/yyyy" e usa a primeira data.
    3. Fallback: a data mais antiga encontrada no documento.

    Returns:
        date da início da terapia, ou None se não encontrar.
    """
    try:
        text = extract_pdf_text(pdf_path)
    except Exception as e:
        logger.warning(f"Não foi possível extrair texto do PDF: {e}")
        return None

    lines = text.splitlines()

    # --- Estratégia 1: rótulos conhecidos ---
    for i, line in enumerate(lines):
        for label in THERAPY_START_LABELS:
            if label.lower() in line.lower():
                # Procura data na mesma linha
                match = DATE_PATTERN.search(line)
                if match:
                    parsed = _parse_date(match.group())
                    if parsed:
                        logger.info(f"Data de início da terapia (rótulo '{label}'): {parsed}")
                        return parsed
                # Procura nas 2 linhas seguintes
                for j in range(i + 1, min(i + 3, len(lines))):
                    match = DATE_PATTERN.search(lines[j])
                    if match:
                        parsed = _parse_date(match.group())
                        if parsed:
                            logger.info(f"Data de início da terapia (após '{label}'): {parsed}")
                            return parsed

    # --- Estratégia 2: intervalo "data - data" ---
    range_match = re.search(
        r'(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})\s*[-–—a]+\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})',
        text,
    )
    if range_match:
        parsed = _parse_date(range_match.group(1))
        if parsed:
            logger.info(f"Data de início (início do intervalo): {parsed}")
            return parsed

    # --- Estratégia 3: data mais antiga do documento ---
    all_dates = []
    for match in DATE_PATTERN.finditer(text):
        parsed = _parse_date(match.group())
        if parsed:
            all_dates.append(parsed)
    if all_dates:
        oldest = min(all_dates)
        logger.info(f"Data de início (data mais antiga do PDF): {oldest}")
        return oldest

    logger.warning("Nenhuma data de início da terapia encontrada no PDF")
    return None
