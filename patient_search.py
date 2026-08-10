"""
patient_search.py — Localiza um paciente no AirView pelo nome cadastrado
no MONITORAMENTO_CPAP_FAPS.

Descoberta importante: o AirView exibe os nomes como "Sobrenome, Nome"
(ex.: "Pacheco Junior, Hugo Peixoto"), enquanto o Firestore guarda
"Nome Sobrenome" (ex.: "Hugo Peixoto Pacheco Junior"). A comparação por
CONJUNTO DE PALAVRAS (ignorando ordem, acentos e maiúsculas) resolve isso
sem arriscar casar o paciente errado — dado que isto é dado de saúde,
a correspondência é EXATA (mesmo conjunto de palavras) ou falha com erro
claro; nunca "chuta" o candidato mais parecido.
"""
import re
import logging
import unicodedata
from playwright.async_api import Page
from config import SEARCH_SELECTORS, TIMEOUTS, BASE_URL

logger = logging.getLogger("airview.patient_search")


def _normalizar(nome: str) -> frozenset:
    """
    Remove acentos, pontuação e caixa; retorna o conjunto de palavras.
    'Hugo Peixoto Pacheco Junior' e 'Pacheco Junior, Hugo Peixoto'
    normalizam para o MESMO conjunto.
    """
    sem_acento = unicodedata.normalize("NFKD", nome)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    palavras = re.findall(r"[a-zA-Z0-9]+", sem_acento.lower())
    return frozenset(palavras)


async def find_patient_url(page: Page, patient_name: str) -> str:
    """
    Busca o paciente pelo nome e retorna a URL completa da página dele
    (formato /patients/{uuid}/charts).

    Estratégia (em ordem, para não depender de um único comportamento):
    1. Vai para /wireless, busca pelo nome (#q + #searchItems) e escaneia
       os resultados
    2. Se não achar correspondência EXATA, recarrega /wireless SEM busca
       (lista completa) e escaneia de novo — o comportamento de busca do
       AirView com nomes fora de ordem ("Sobrenome, Nome") não é garantido,
       então a lista completa é o fallback mais confiável

    A correspondência é por CONJUNTO DE PALAVRAS (ordem/acentos/caixa
    ignorados), mas EXATA — nenhuma palavra pode faltar ou sobrar. Dado
    que isto é dado de saúde, o código nunca "chuta" o candidato mais
    parecido: sem correspondência exata única, falha com erro claro.

    Raises:
        RuntimeError se não achar nenhuma correspondência exata, ou se
        achar mais de uma (ambiguidade — melhor parar do que arriscar).
    """
    logger.info(f"Buscando paciente: {patient_name!r}")
    alvo = _normalizar(patient_name)
    if not alvo:
        raise ValueError(f"Nome de paciente vazio ou inválido: {patient_name!r}")

    resultado = await _tentar_achar(page, patient_name, alvo, usar_busca=True)
    if resultado:
        return resultado

    logger.info("Não achou via busca — recarregando lista completa (sem filtro)...")
    resultado = await _tentar_achar(page, patient_name, alvo, usar_busca=False)
    if resultado:
        return resultado

    await page.screenshot(path="logs/search_sem_match.png")
    raise RuntimeError(
        f"Paciente {patient_name!r} não encontrado no AirView (nem via busca, nem na "
        f"lista completa). Verifique se o nome no cadastro tem exatamente as mesmas "
        f"palavras do AirView (a ordem pode diferir, ex.: 'Nome Sobrenome' vs "
        f"'Sobrenome, Nome'). Screenshot: logs/search_sem_match.png"
    )


async def _tentar_achar(page: Page, patient_name: str, alvo: frozenset, usar_busca: bool):
    """
    Carrega /wireless (com ou sem busca) e retorna a URL do paciente se
    houver correspondência exata única. Retorna None se não achar (para
    o chamador tentar a próxima estratégia). Lança RuntimeError se achar
    mais de uma correspondência (ambiguidade real, não deve ser ignorada).
    """
    # 'domcontentloaded' (não 'networkidle'): a lista de pacientes tem
    # tráfego de rede contínuo que nunca fica "parado".
    await page.goto(f"{BASE_URL}/wireless", wait_until="domcontentloaded",
                    timeout=TIMEOUTS["page_load"])
    await page.wait_for_timeout(2500)
    await _dispensar_cookies(page)

    if usar_busca:
        campo = None
        for selector in SEARCH_SELECTORS["search_input"]:
            try:
                el = page.locator(selector).first
                await el.wait_for(state="visible", timeout=4000)
                campo = el
                break
            except Exception:
                continue

        if campo is not None:
            await campo.click()
            await campo.fill(patient_name)
            submetido = False
            for selector in SEARCH_SELECTORS["search_button"]:
                try:
                    btn = page.locator(selector).first
                    if await btn.is_visible(timeout=1500):
                        await btn.click()
                        submetido = True
                        break
                except Exception:
                    continue
            if not submetido:
                await campo.press("Enter")
            # Não usa 'networkidle' pelo mesmo motivo acima; espera curta
            # e fixa é mais previsível para este tipo de página.
            await page.wait_for_timeout(2000)
        else:
            logger.debug("Campo de busca não encontrado nesta tentativa")
            return None

    # --- Varre os links de paciente e compara por conjunto de palavras ---
    candidatos = []
    for selector in SEARCH_SELECTORS["search_result"]:
        links = await page.locator(selector).all()
        if not links:
            continue
        for link in links:
            try:
                href = await link.get_attribute("href")
                texto = await link.inner_text()
            except Exception:
                continue
            if href and texto and texto.strip():
                candidatos.append((texto.strip(), href))
        if candidatos:
            break  # achou com este seletor, não precisa tentar os próximos

    if not candidatos:
        return None

    exatos = [(t, h) for t, h in candidatos if _normalizar(t) == alvo]

    if len(exatos) > 1:
        nomes = [t for t, _ in exatos]
        raise RuntimeError(
            f"Mais de um paciente com o mesmo nome normalizado para {patient_name!r}: "
            f"{nomes}. Verifique manualmente no AirView para evitar erro de paciente."
        )

    if len(exatos) == 1:
        texto, href = exatos[0]
        url = href if href.startswith("http") else BASE_URL + href
        logger.info(f"Paciente encontrado: {texto!r} → {url}")
        return url

    return None


async def _dispensar_cookies(page: Page) -> None:
    """Clica em 'Aceitar cookies' se o banner OneTrust estiver visível."""
    for selector in (
        "#onetrust-accept-btn-handler",
        "#accept-recommended-btn-handler",
        'button:has-text("Aceitar cookies")',
    ):
        try:
            btn = page.locator(selector).first
            if await btn.is_visible(timeout=1500):
                await btn.click()
                await page.wait_for_timeout(500)
                return
        except Exception:
            continue
