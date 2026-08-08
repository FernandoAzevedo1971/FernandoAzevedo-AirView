#!/usr/bin/env python3
"""
sync_runner.py — Robô de sincronização AirView → MONITORAMENTO_CPAP_FAPS

Fluxo:
  1. Pergunta ao Next.js quais marcos (D1/D3/D7/D14/D30) estão pendentes hoje
  2. Faz login no AirView (uma vez, sessão reaproveitada para todos os marcos)
  3. Para cada marco pendente:
     a. Localiza o paciente no AirView pelo nome
     b. Baixa o "Relatório de adesão ao tratamento" (período: dataInicio → dataPrevista)
     c. Extrai um screenshot da 1ª página (PNG)
     d. Envia o PNG ao GPT-4o Vision → extrai os números estruturados
     e. Envia os números ao Next.js → grava como Captura (origem: "automatica")
  4. Cada marco é isolado: falha em um não interrompe os demais
  5. Ao final, mostra um resumo

Uso:
    python sync_runner.py

Executar periodicamente (Agendador de Tarefas do Windows, cron, ou manual)
para manter o painel do Next.js sempre atualizado.
"""
import asyncio
import logging
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv

from browser import AirViewBrowser
from login import perform_login
from patient_search import find_patient_url
from report_requester import request_report
from pdf_screenshot import capture_first_page
from gpt_analyzer import extract_structured_data
from patients import PatientEntry
from sync_client import get_pending_marcos, push_captura, SyncConfigError
from utils import setup_logging, sanitize_filename

logger = logging.getLogger("airview.sync_runner")


def _report_period(data_inicio: date, data_prevista: date, today: date = None) -> tuple:
    """
    Define o período (start, end) do relatório de adesão para um marco:
    da data de início da terapia até a data prevista do marco (ou hoje,
    se o marco já venceu há mais tempo — nunca pede período no futuro).
    """
    today = today or date.today()
    end = min(data_prevista, today)
    if end <= data_inicio:
        end = data_inicio + timedelta(days=1)
    return data_inicio, end


async def _process_marco(page, marco: dict) -> dict:
    """Processa um único marco: baixa relatório, extrai dados, envia ao Next.js."""
    nome = marco["pacienteNome"]
    tipo = marco["tipo"]
    resultado = {"paciente": nome, "marco": tipo, "sucesso": False, "erro": None}

    try:
        data_inicio = date.fromisoformat(marco["dataInicio"])
        data_prevista = date.fromisoformat(marco["dataPrevista"])
    except (TypeError, ValueError, KeyError) as e:
        resultado["erro"] = f"Data de início/prevista ausente ou inválida: {e}"
        return resultado

    start_date, end_date = _report_period(data_inicio, data_prevista)

    try:
        logger.info(f"[{nome} / {tipo}] Buscando paciente no AirView...")
        url = await find_patient_url(page, nome)

        entry = PatientEntry(index=0, name=nome, href=url)

        safe_name = sanitize_filename(nome)
        prefix = f"reports/{safe_name}_{tipo}"
        pdf_path = f"{prefix}.pdf"
        png_path = f"{prefix}_pag1.png"

        logger.info(f"[{nome} / {tipo}] Baixando relatório de adesão ({start_date} → {end_date})...")
        pdf_path = await request_report(page, entry, start_date=start_date, end_date=end_date, pdf_path=pdf_path)

        logger.info(f"[{nome} / {tipo}] Gerando screenshot...")
        png_path = capture_first_page(pdf_path, png_path, dpi=300)

        logger.info(f"[{nome} / {tipo}] Extraindo dados com GPT-4o...")
        dados = extract_structured_data(png_path)

        logger.info(f"[{nome} / {tipo}] Enviando captura ao Next.js...")
        push_captura(
            paciente_id=marco["pacienteId"],
            marco_id=marco["marcoId"],
            dados=dados,
            data_inicio=start_date,
            data_fim=end_date,
        )

        resultado["sucesso"] = True
        logger.info(f"[{nome} / {tipo}] ✓ Concluído")

    except Exception as e:
        logger.error(f"[{nome} / {tipo}] ✗ Erro: {e}", exc_info=True)
        resultado["erro"] = str(e)

    return resultado


async def main():
    load_dotenv()
    setup_logging()
    Path("reports").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)

    logger.info("=" * 60)
    logger.info("  AirView Sync — MONITORAMENTO_CPAP_FAPS")
    logger.info("=" * 60)

    try:
        marcos = get_pending_marcos()
    except SyncConfigError as e:
        logger.critical(f"Configuração ausente: {e}")
        return
    except Exception as e:
        logger.critical(f"Falha ao consultar marcos pendentes no Next.js: {e}")
        return

    if not marcos:
        logger.info("Nenhum marco pendente hoje. Nada a fazer.")
        return

    browser = AirViewBrowser()
    resultados = []

    try:
        page = await browser.start()
        logger.info("Realizando login no AirView...")
        await perform_login(page)
        logger.info("✓ Login realizado\n")

        for marco in marcos:
            resultado = await _process_marco(page, marco)
            resultados.append(resultado)
            await asyncio.sleep(2)

    except Exception as e:
        logger.critical(f"Erro crítico: {e}", exc_info=True)
    finally:
        await browser.close()

    logger.info("=" * 60)
    logger.info("  RESUMO")
    logger.info("=" * 60)
    sucesso = 0
    for r in resultados:
        status = "✓" if r["sucesso"] else "✗"
        logger.info(f"  {status} {r['paciente']} — {r['marco']}" + (f" | erro: {r['erro']}" if r["erro"] else ""))
        if r["sucesso"]:
            sucesso += 1
    logger.info(f"\n  Total: {sucesso}/{len(resultados)} marcos sincronizados com sucesso")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
