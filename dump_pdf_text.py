"""
dump_pdf_text.py — Ferramenta de diagnóstico: imprime o texto bruto extraído
de um PDF (todas as páginas), com marcadores de linha, para calibrar os
regex de extract_structured_data() (pdf_data_extractor.py) contra o formato
REAL do "Relatório de adesão ao tratamento e terapia" do AirView.

Uso:
    python dump_pdf_text.py reports/Hugo_Peixoto_Pacheco_Junior_D30.pdf
"""
import sys
from pdf_utils import extract_pdf_text


def main():
    if len(sys.argv) < 2:
        print("Uso: python dump_pdf_text.py <caminho_do_pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    texto = extract_pdf_text(pdf_path)

    print(f"=== Texto extraído de: {pdf_path} ===")
    print(f"=== Total de {len(texto.splitlines())} linhas ===\n")
    for i, linha in enumerate(texto.splitlines(), start=1):
        print(f"{i:3d}: {linha!r}")


if __name__ == "__main__":
    main()
