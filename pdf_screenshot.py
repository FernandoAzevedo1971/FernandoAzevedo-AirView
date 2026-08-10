"""
pdf_screenshot.py — Converte a 1ª página de um PDF em PNG.

Usa pypdfium2 (padrão — instalação sem compilação, funciona em qualquer
versão do Python) e cai para pymupdf caso ele esteja instalado e o
pypdfium2 não. Ambos produzem o mesmo resultado.
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
        dpi: Resolução em DPI (padrão 300, boa para leitura por IA)

    Returns:
        Caminho do arquivo PNG gerado
    """
    logger.info(f"Convertendo PDF → PNG: {pdf_path}")

    try:
        output = _render_with_pypdfium2(pdf_path, output_path, dpi)
    except ImportError:
        logger.debug("pypdfium2 indisponível — tentando pymupdf")
        output = _render_with_pymupdf(pdf_path, output_path, dpi)

    file_size_kb = Path(output).stat().st_size // 1024
    logger.info(f"PNG gerado: {output} ({file_size_kb}KB, {dpi}DPI)")
    return output


def _render_with_pypdfium2(pdf_path: str, output_path: str, dpi: int) -> str:
    """Renderização via pypdfium2 (sem etapa de compilação na instalação)."""
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(pdf_path)
    try:
        if len(doc) == 0:
            raise ValueError(f"PDF vazio ou inválido: {pdf_path}")
        page = doc[0]
        # scale = dpi / 72 (72 é o DPI base do PDF)
        bitmap = page.render(scale=dpi / 72.0)
        bitmap.to_pil().save(output_path)
    finally:
        doc.close()

    return str(output_path)


def _render_with_pymupdf(pdf_path: str, output_path: str, dpi: int) -> str:
    """Renderização via pymupdf (fallback, caso já esteja instalado)."""
    try:
        import fitz  # pymupdf
    except ImportError:
        raise ImportError(
            "Nenhuma biblioteca de PDF encontrada. "
            "Execute: pip install pypdfium2 pillow"
        )

    doc = fitz.open(pdf_path)
    try:
        if doc.page_count == 0:
            raise ValueError(f"PDF vazio ou inválido: {pdf_path}")
        page = doc.load_page(0)
        scale = dpi / 72.0
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        pix.save(str(output_path))
    finally:
        doc.close()

    return str(output_path)
