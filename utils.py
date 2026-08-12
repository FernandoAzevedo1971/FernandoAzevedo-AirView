"""
utils.py — Retry decorator, logging e helpers para AirView Automation
"""
import asyncio
import functools
import logging
from datetime import datetime
from pathlib import Path


def setup_logging() -> logging.Logger:
    """Configura logging para arquivo e console."""
    Path("logs").mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"logs/airview_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    logger = logging.getLogger("airview")
    logger.info(f"Log iniciado: {log_file}")
    return logger


def retry(max_attempts: int = 3, delay: float = 5.0, exceptions=(Exception,)):
    """
    Decorator para retentar uma corrotina assíncrona em caso de falha.

    Uso:
        @retry(max_attempts=3, delay=5.0)
        async def minha_funcao():
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    logger = logging.getLogger("airview")
                    logger.warning(
                        f"[{func.__name__}] Tentativa {attempt}/{max_attempts} falhou: {e}"
                    )
                    if attempt < max_attempts:
                        wait_time = delay * attempt  # backoff progressivo
                        logger.info(f"  Aguardando {wait_time}s antes de tentar novamente...")
                        await asyncio.sleep(wait_time)
            raise last_exc
        return wrapper
    return decorator


async def try_selectors(page, selectors: list, timeout: int = 10_000):
    """
    Tenta cada seletor na lista em ordem.
    Retorna o primeiro locator que resolver dentro do timeout.
    Lança RuntimeError se nenhum resolver.
    """
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            await locator.wait_for(state="visible", timeout=timeout)
            return locator
        except Exception:
            continue
    raise RuntimeError(
        f"Nenhum seletor funcionou (timeout={timeout}ms). Seletores tentados: {selectors}"
    )


def sanitize_filename(name: str, max_length: int = 40) -> str:
    """Remove caracteres inválidos de nome de arquivo."""
    import re
    safe = re.sub(r'[^\w\s\-]', '', name, flags=re.UNICODE)
    safe = re.sub(r'\s+', '_', safe.strip())
    return safe[:max_length]


def clean_secret_value(value: str | None) -> str | None:
    """
    Limpa um valor de segredo/chave lido do .env (API key, token, etc.)
    antes de usá-lo em headers HTTP.

    Cobre sujeiras comuns ao editar .env manualmente:
      - BOM (marca de ordem de bytes) que sobra no início do arquivo
      - aspas envolvendo o valor ("chave" ou 'chave')
      - espaços nas pontas
      - texto extra colado na mesma linha sem "#" (ex.: um comentário ou
        nota) — como chaves/segredos nunca têm espaço no meio, descartamos
        tudo a partir do primeiro espaço interno

    Sem isso, um valor "sujo" (com acentos/caracteres não-ASCII vindos do
    texto extra) quebra a codificação do header HTTP com um
    UnicodeEncodeError obscuro, longe de onde o problema realmente está.
    """
    if value is None:
        return None
    value = value.strip().lstrip("﻿")
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1].strip()
    partes = value.split()
    return partes[0] if partes else value
