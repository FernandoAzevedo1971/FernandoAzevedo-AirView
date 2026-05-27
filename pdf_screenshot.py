"""
pdf_screenshot.py — Converte a 1ª página de um PDF em PNG usando pymupdf
"""
import logging
from pathlib import Path

logger = logging.getLogger("airview.pdf_screenshot")


def capture_first_page(pdf_path: str, output_path: str, dpi: int = 300) -> str:
    """
    Renderiza a primeira página do PDF em PNG com a resolução especificada.

    Args:
        pdf_path: Caminho para o arquivo PDF
        output_path: Caminho para salvar o PNG resultante
        dpi: Resolução em DPI (padrão 300 para boa qualidade de OCR/análise)

    Returns:
        Caminho do arquivo PNG gerado
    """
    try:
        import fitz  # pymupdf
    except ImportError:
        raise ImportError(
            "pymupdf não está instalado. Execute: pip install pymupdf"
        )

    logger.info(f"Convertendo PDF → PNG: {pdf_path}")

    doc = fitz.open(pdf_path)

    if doc.page_count == 0:
        doc.close()
        raise ValueError(f"PDF vazio ou inválido: {pdf_path}")

    page = doc.load_page(0)  # Primeira página (índice 0)

    # Fator de escala: DPI / 72 (DPI padrão do PDF)
    scale = dpi / 72.0
    mat = fitz.Matrix(scale, scale)

    # Renderiza em modo RGB (sem canal alpha)
    pix = page.get_pixmap(matrix=mat, alpha=False)

    # Salva como PNG
    output = str(output_path)
    pix.save(output)

    doc.close()

    file_size_kb = Path(output).stat().st_size // 1024
    logger.info(
        f"PNG gerado: {output} "
        f"({pix.width}x{pix.height}px, {file_size_kb}KB, {dpi}DPI)"
    )

    return output
