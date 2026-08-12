"""
pdf_data_extractor.py — Extrai os dados estruturados do "Relatório de adesão
ao tratamento e terapia" do AirView diretamente do TEXTO do PDF (via
pdf_utils.extract_pdf_text), usando expressões regulares.

Alternativa 100% gratuita à extração via GPT-4o Vision (gpt_analyzer.py): o
PDF gerado pelo AirView tem texto real (não é imagem escaneada), com
rótulos padronizados — dá para extrair os números com precisão exata, sem
custo e sem risco de "alucinação" de IA.

Padrões calibrados a partir do texto real de um relatório combinado
(adesão + terapia), ex.:

    Usage days 26/30 days (87%)
    Average usage (days used) 5 hours 26 minutes
    Pressure - cmH2O Median: 11.5 95th percentile: 12.3 Maximum: 12.3
    Leaks - L/min Median: 3.1 95th percentile: 17.7 Maximum: 23.7
    Events per hour AI: 1.2 HI: 3.9 AHI: 5.1

Se o AirView mudar o layout do relatório e algum campo parar de ser
encontrado, use dump_pdf_text.py para ver o texto real atualizado e
recalibrar os padrões abaixo.
"""
import re
import logging

from pdf_utils import extract_pdf_text

logger = logging.getLogger("airview.pdf_data_extractor")

# Mesma lista de campos que gpt_analyzer.STRUCTURED_FIELDS — precisam bater
# com CapturaAutomaticaInput no Next.js (src/lib/firestore/capturas.ts)
STRUCTURED_FIELDS = [
    "usoHorasMedia",
    "diasUso",
    "percentualUso",
    "iahResidual",
    "vazamento",
    "vazamentoMedio",
    "pressaoMediana",
    "pressaoP95",
    "periodoDias",
]

_PATTERNS = {
    # "Usage days 26/30 days (87%)" -> diasUso=26, periodoDias=30, percentualUso=87
    "usage_days": re.compile(
        r"Usage days\s+(\d+)\s*/\s*(\d+)\s*days?\s*\((\d+)%\)", re.IGNORECASE
    ),
    # "Average usage (days used) 5 hours 26 minutes" -> usoHorasMedia
    "avg_usage": re.compile(
        r"Average usage \(days used\)\s+(\d+)\s*hours?\s+(\d+)\s*minutes?", re.IGNORECASE
    ),
    # "Pressure - cmH2O Median: 11.5 95th percentile: 12.3 Maximum: 12.3"
    "pressure": re.compile(
        r"Pressure.*?Median:\s*([\d.]+)\s+95th percentile:\s*([\d.]+)", re.IGNORECASE
    ),
    # "Leaks - L/min Median: 3.1 95th percentile: 17.7 Maximum: 23.7"
    "leaks": re.compile(
        r"Leaks.*?Median:\s*([\d.]+)\s+95th percentile:\s*([\d.]+)", re.IGNORECASE
    ),
    # "Events per hour AI: 1.2 HI: 3.9 AHI: 5.1"
    "ahi": re.compile(
        r"Events per hour.*?AHI:\s*([\d.]+)", re.IGNORECASE
    ),
}


def extract_structured_data_from_text(texto: str) -> dict:
    """
    Recebe o texto bruto do PDF (todas as páginas) e retorna um dict com os
    campos de STRUCTURED_FIELDS. Campos não encontrados vêm como None —
    nunca inventa valor (mesma garantia que o prompt do GPT-4o tinha).
    """
    result = {field: None for field in STRUCTURED_FIELDS}

    for linha in texto.splitlines():
        m = _PATTERNS["usage_days"].search(linha)
        if m:
            result["diasUso"] = int(m.group(1))
            result["periodoDias"] = int(m.group(2))
            result["percentualUso"] = int(m.group(3))
            continue

        m = _PATTERNS["avg_usage"].search(linha)
        if m:
            horas, minutos = int(m.group(1)), int(m.group(2))
            result["usoHorasMedia"] = round(horas + minutos / 60, 2)
            continue

        m = _PATTERNS["pressure"].search(linha)
        if m:
            result["pressaoMediana"] = float(m.group(1))
            result["pressaoP95"] = float(m.group(2))
            continue

        m = _PATTERNS["leaks"].search(linha)
        if m:
            result["vazamento"] = float(m.group(1))
            result["vazamentoMedio"] = float(m.group(2))
            continue

        m = _PATTERNS["ahi"].search(linha)
        if m:
            result["iahResidual"] = float(m.group(1))
            continue

    found = sum(1 for v in result.values() if v is not None)
    logger.info(f"Extração via regex concluída: {found}/{len(STRUCTURED_FIELDS)} campos preenchidos")
    if found < len(STRUCTURED_FIELDS):
        faltando = [f for f, v in result.items() if v is None]
        logger.warning(f"Campos não encontrados no texto do PDF: {faltando}")

    return result


def extract_structured_data(pdf_path: str) -> dict:
    """Extrai os dados estruturados diretamente do PDF (sem IA, sem custo)."""
    logger.info(f"Extraindo dados estruturados (regex) de: {pdf_path}")
    texto = extract_pdf_text(pdf_path)
    return extract_structured_data_from_text(texto)
