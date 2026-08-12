"""
sync_client.py — Cliente HTTP para a API do MONITORAMENTO_CPAP_FAPS (Next.js).

Conversa com duas rotas novas do Next.js, protegidas por uma chave secreta
compartilhada (header x-api-key), NÃO por login de usuário:

  GET  /api/sync/pendentes        → lista marcos pendentes hoje + dados do paciente
  POST /api/captura/importar      → grava uma Captura com origem "automatica"

Configuração via .env:
  NEXTJS_API_URL       ex: http://localhost:3000  (ou a URL de produção)
  AIRVIEW_SYNC_SECRET  a mesma string configurada em AIRVIEW_SYNC_SECRET no Next.js
"""
import os
import logging
from datetime import date
from typing import Optional

from utils import clean_secret_value

logger = logging.getLogger("airview.sync_client")


class SyncConfigError(Exception):
    """Faltam variáveis de ambiente necessárias para falar com o Next.js."""


def _base_url() -> str:
    url = os.getenv("NEXTJS_API_URL", "").rstrip("/")
    if not url:
        raise SyncConfigError(
            "NEXTJS_API_URL não está definida no .env "
            "(ex: http://localhost:3000)"
        )
    return url


def _headers() -> dict:
    secret = clean_secret_value(os.getenv("AIRVIEW_SYNC_SECRET", ""))
    if not secret:
        raise SyncConfigError("AIRVIEW_SYNC_SECRET não está definida no .env")
    return {"x-api-key": secret, "Content-Type": "application/json"}


def get_pending_marcos() -> list:
    """
    Busca a lista de marcos pendentes hoje no Next.js.

    Cada item vem com: pacienteId, pacienteNome, marcoId, tipo (D1/D3/D7/D14/D30),
    dataPrevista, dataInicio, aparelho, mascara.
    """
    import requests

    url = f"{_base_url()}/api/sync/pendentes"
    logger.info(f"Buscando marcos pendentes: {url}")

    resp = requests.get(url, headers=_headers(), timeout=30)
    resp.raise_for_status()
    marcos = resp.json().get("marcos", [])

    logger.info(f"{len(marcos)} marco(s) pendente(s) encontrado(s)")
    for m in marcos:
        logger.info(f"  - {m['pacienteNome']} | {m['tipo']} | previsto: {m['dataPrevista']}")

    return marcos


def push_captura(
    paciente_id: str,
    marco_id: Optional[str],
    dados: dict,
    data_inicio: date,
    data_fim: date,
) -> dict:
    """
    Envia os dados extraídos do relatório AirView para gravação como
    Captura (origem "automatica") no Firestore, via API do Next.js.

    `dados` deve conter as chaves de gpt_analyzer.STRUCTURED_FIELDS.
    """
    import requests

    url = f"{_base_url()}/api/captura/importar"
    payload = {
        "pacienteId": paciente_id,
        "marcoId": marco_id,
        "dataInicio": data_inicio.isoformat(),
        "dataFim": data_fim.isoformat(),
        "rawJson": dados,
        **dados,
    }

    logger.info(f"Enviando captura automática: paciente={paciente_id} marco={marco_id}")
    resp = requests.post(url, json=payload, headers=_headers(), timeout=30)

    if not resp.ok:
        logger.error(f"Falha ao gravar captura ({resp.status_code}): {resp.text}")
    resp.raise_for_status()

    return resp.json()
