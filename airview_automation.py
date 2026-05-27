#!/usr/bin/env python3
"""
airview_automation.py — Orquestrador principal da automação AirView ResMed

Fluxo:
1. Login em https://airview.resmed.com
2. Coleta os 10 primeiros pacientes de /wireless
3. Para cada paciente:
   a. Solicita "Relatório de adesão ao tratamento" (últimos 14 dias)
   b. Baixa o PDF gerado
   c. Extrai screenshot da 1ª página (PNG, 300 DPI)
   d. Envia PNG ao Claude Vision para análise médica
   e. Salva laudo em .md
4. Gera log consolidado de todas as saídas

Uso:
    python airview_automation.py
"""
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

from browser import AirViewBrowser
from login import perform_login
from patients import get_patient_list
from report_requester import request_report
from pdf_screenshot import capture_first_page
from claude_analyzer import analyze_report
from utils import setup_logging, sanitize_filename


async def main():
    # Carrega variáveis de ambiente do .env
    load_dotenv()

    # Configura logging
    logger = setup_logging()
    logger.info("=" * 60)
    logger.info("  AirView Automation — Dr. Fernando Azevedo")
    logger.info("=" * 60)

    # Cria pastas necessárias
    Path("reports").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)

    # Verifica chave da API Anthropic (aviso antecipado)
    if not os.getenv("ANTHROPIC_API_KEY"):
        logger.warning(
            "ANTHROPIC_API_KEY não configurada — laudos Claude não serão gerados. "
            "Configure a chave no arquivo .env para análise completa."
        )

    browser_manager = AirViewBrowser()
    results_summary = []

    try:
        page = await browser_manager.start()

        # ── Step 1: Login ────────────────────────────────────────────────
        logger.info("PASSO 1: Realizando login...")
        await perform_login(page)
        logger.info("✓ Login realizado com sucesso\n")

        # ── Step 2: Lista de pacientes ───────────────────────────────────
        logger.info("PASSO 2: Carregando lista de pacientes (/wireless)...")
        patients = await get_patient_list(page)
        logger.info(f"✓ {len(patients)} pacientes encontrados\n")

        # ── Step 3: Processa cada paciente ───────────────────────────────
        total = len(patients)
        for patient in patients:
            logger.info(f"{'─' * 50}")
            logger.info(f"PACIENTE [{patient.index}/{total}]: {patient.name}")
            logger.info(f"{'─' * 50}")

            safe_name = sanitize_filename(patient.name)
            prefix = f"reports/paciente_{patient.index:02d}_{safe_name}"
            pdf_path = f"{prefix}.pdf"
            png_path = f"{prefix}_pag1.png"
            laudo_path = f"{prefix}_laudo.md"

            result = {
                "index": patient.index,
                "name": patient.name,
                "pdf": None,
                "png": None,
                "laudo": None,
                "error": None,
            }

            # ── 3a: Download do PDF ─────────────────────────────────────
            try:
                logger.info(f"  [3a] Solicitando PDF do relatório de adesão...")
                pdf_path = await request_report(page, patient)
                result["pdf"] = pdf_path
                logger.info(f"  ✓ PDF: {pdf_path}")
            except Exception as e:
                error_msg = f"Erro ao baixar PDF: {e}"
                logger.error(f"  ✗ {error_msg}")
                result["error"] = error_msg
                results_summary.append(result)
                # Continua para o próximo paciente
                await asyncio.sleep(int(os.getenv("DELAY_BETWEEN_PATIENTS", "2")))
                continue

            # ── 3b: Screenshot da 1ª página ─────────────────────────────
            try:
                logger.info(f"  [3b] Gerando screenshot da 1ª página do PDF...")
                png_path = capture_first_page(pdf_path, png_path, dpi=300)
                result["png"] = png_path
                logger.info(f"  ✓ PNG: {png_path}")
            except Exception as e:
                error_msg = f"Erro ao gerar PNG: {e}"
                logger.error(f"  ✗ {error_msg}")
                result["error"] = (result["error"] or "") + f" | {error_msg}"

            # ── 3c: Análise Claude Vision ────────────────────────────────
            if result["png"] and os.getenv("ANTHROPIC_API_KEY"):
                try:
                    logger.info(f"  [3c] Enviando ao Claude Vision para análise médica...")
                    analyze_report(png_path, patient.name, laudo_path)
                    result["laudo"] = laudo_path
                    logger.info(f"  ✓ Laudo: {laudo_path}")
                except Exception as e:
                    error_msg = f"Erro na análise Claude: {e}"
                    logger.error(f"  ✗ {error_msg}")
                    result["error"] = (result["error"] or "") + f" | {error_msg}"
            elif not os.getenv("ANTHROPIC_API_KEY"):
                logger.info("  [3c] PULADO — ANTHROPIC_API_KEY não configurada")

            results_summary.append(result)
            logger.info("")

            # Pausa respeitosa entre pacientes
            await asyncio.sleep(int(os.getenv("DELAY_BETWEEN_PATIENTS", "2")))

    except KeyboardInterrupt:
        logger.warning("Execução interrompida pelo usuário (Ctrl+C)")
    except Exception as e:
        logger.critical(f"Erro crítico: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await browser_manager.close()

    # ── Resumo final ─────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("  RESUMO DA EXECUÇÃO")
    logger.info("=" * 60)

    success_count = 0
    for r in results_summary:
        status = "✓" if not r["error"] else "✗"
        pdf_ok = "✓ PDF" if r["pdf"] else "✗ PDF"
        png_ok = "✓ PNG" if r["png"] else "✗ PNG"
        laudo_ok = "✓ Laudo" if r["laudo"] else "✗ Laudo"
        logger.info(
            f"  [{r['index']:02d}] {status} {r['name'][:30]:<30} | "
            f"{pdf_ok} | {png_ok} | {laudo_ok}"
        )
        if r["error"]:
            logger.info(f"       Erro: {r['error']}")
        else:
            success_count += 1

    logger.info(f"\n  Total: {success_count}/{len(results_summary)} pacientes processados com sucesso")
    logger.info(f"  Arquivos em: reports/")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
