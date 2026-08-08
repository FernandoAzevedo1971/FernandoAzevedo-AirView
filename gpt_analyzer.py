"""
gpt_analyzer.py — Analisa o PNG do relatório AirView usando GPT-4o Vision.

Duas funções:
  1. extract_structured_data() — extrai números (uso, IAH, vazamento, pressão)
     em JSON, para alimentar a "Captura" do sistema MONITORAMENTO_CPAP_FAPS.
     É a função PRINCIPAL do fluxo de sincronização.
  2. analyze_report() — gera um laudo médico narrativo em português (carta
     ao paciente). Recurso OPCIONAL, salvo localmente para uso manual do
     médico — não é enviado ao Next.js.
"""
import os
import json
import base64
import logging
from pathlib import Path

logger = logging.getLogger("airview.analyzer")

# ---------------------------------------------------------------------------
# 1. Extração estruturada (alimenta a Captura no Firestore)
# ---------------------------------------------------------------------------

# Campos esperados — devem bater com CapturaAutomaticaInput no Next.js
# (src/lib/firestore/capturas.ts)
STRUCTURED_FIELDS = [
    "usoHorasMedia",   # horas médias de uso por noite
    "diasUso",         # número de dias com uso registrado no período
    "percentualUso",   # % de dias com uso (0-100)
    "iahResidual",      # índice de apneia-hipopneia residual (eventos/hora)
    "vazamento",        # vazamento mediano (L/min)
    "vazamentoMedio",   # vazamento no percentil 95 ou médio (L/min)
    "pressaoMediana",   # pressão mediana de terapia (cmH2O)
    "pressaoP95",       # pressão no percentil 95 (cmH2O)
    "periodoDias",       # duração total do período do relatório (dias)
]

EXTRACTION_PROMPT = f"""Você é um especialista em leitura de relatórios de terapia CPAP/APAP do
sistema ResMed AirView ("Relatório de adesão ao tratamento").

Analise a imagem do relatório fornecida e extraia os seguintes valores numéricos.
Responda APENAS com um objeto JSON válido, sem texto adicional, com exatamente
estas chaves (use null quando o valor não estiver visível no relatório):

{{
  "usoHorasMedia": <horas médias de uso por noite, número decimal, ex: 5.5>,
  "diasUso": <número de dias com uso registrado no período, inteiro>,
  "percentualUso": <percentual de dias com uso sobre o total do período, 0-100>,
  "iahResidual": <índice de apneia-hipopneia residual, eventos/hora>,
  "vazamento": <vazamento mediano, em L/min>,
  "vazamentoMedio": <vazamento no percentil 95 (ou médio, se P95 não disponível), em L/min>,
  "pressaoMediana": <pressão mediana de terapia, em cmH2O>,
  "pressaoP95": <pressão no percentil 95, em cmH2O>,
  "periodoDias": <duração total do período coberto pelo relatório, em dias, inteiro>
}}

Regras:
- Use ponto decimal (não vírgula).
- Se um valor não aparecer claramente no relatório, use null — não invente.
- Não inclua nenhum texto fora do objeto JSON."""


def extract_structured_data(png_path: str) -> dict:
    """
    Envia o PNG ao GPT-4o Vision e retorna um dict com os campos numéricos
    do relatório (ver STRUCTURED_FIELDS), prontos para alimentar a Captura
    automática no Firestore via a API do Next.js.

    Campos ausentes/irreconhecíveis vêm como None.
    """
    client = _get_openai_client()

    logger.info(f"Extraindo dados estruturados de: {png_path}")
    image_data = _encode_image(png_path)

    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=1024,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_data}",
                            "detail": "high",
                        },
                    },
                    {"type": "text", "text": EXTRACTION_PROMPT},
                ],
            }
        ],
    )

    raw = response.choices[0].message.content
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error(f"GPT-4o não retornou JSON válido: {raw!r}")
        raise ValueError(f"Resposta do GPT-4o não é JSON válido: {e}") from e

    # Normaliza: garante que só os campos esperados sejam propagados
    result = {field: data.get(field) for field in STRUCTURED_FIELDS}

    found = sum(1 for v in result.values() if v is not None)
    logger.info(f"Extração concluída: {found}/{len(STRUCTURED_FIELDS)} campos preenchidos")

    return result


# ---------------------------------------------------------------------------
# 2. Laudo narrativo (opcional — carta ao paciente, uso manual do médico)
# ---------------------------------------------------------------------------
MEDICAL_PROMPT = """Responda em português.
Você vai atuar com conhecimentos de elevado nível em pneumologia, medicina do sono, ventilação não invasiva e uso de pressão positiva contínua, sabendo interpretar curvas de dados de tratamento com pressão positiva que incluem análise de Utilização e Terapia, sabendo interpretar curvas e valores de vazamento (fuga) intencional ou não-intencional, Pressão de terapia, e índice de apneia e hipopneia.

Este Projeto tem como objetivo analisar relatórios gerados automaticamente pela url https://airview.resmed.com/, que gera relatórios do uso de CPAP em diversos formatos, seja Relatório de adesão ao tratamento e terapia (por períodos de uso), seja Relatórios detalhado (relatórios de cada dia individualmente).

Após gerar o relatório de interpretação do arquivo inserido, faça insights sobre sugestões de possíveis mudanças nos ajustes para otimizar a terapia, caso os valores de uso, fuga ou pressões estejam inadequados.

O relatório gerado deve ter escrita técnica porém de fácil compreensão, e ser amigável na leitura.

Use a seguinte estrutura de texto:

"Prezado Sr./Sra., --- (nome do paciente do relatório).
Segue, em anexo, o relatório de adesão e terapia do sono, referente aos últimos -- dias de tratamento.
O período analisado foi ---.
Revendo os registros observei que (há/não há) regularidade no uso do equipamento, obtendo a relação de uso de 30/30 (ou --/--) dias, o que representa --% da totalidade dos dias analisados, com média de uso diário de -h--min; destes, -- dias (--%) com uso superior a 4,0h/dia.
Os registros de vazamento (escape aéreo) ficaram (elevado/dentro do aceitável/baixo), ficando a mediana -- l/min e 95% do tempo -- l/min ou abaixo. O equipamento está habilitado para compensar até 24,0 l/min. Este resultado demonstra (eficiência/ineficiência) da máscara utilizada em gerar contenção e estabilidade ao fluxo e pressão de gases; observo também a pressão média de -- cm/H2O (o equipamento está regulado ao APAP com Pressão máx --,- cmH2O e Pressão mín --,- cmH2O). Por fim, encontrei Índice de Apneia e Hipopneia residual -- eventos/hora, sendo deste índice -- hipopneias, -- obstrutivas, -- centrais, -- desconhecidas.
(analise agora os resultados e proponha modificações à terapia se aplicável)

Coloco-me à disposição para maiores esclarecimentos,
Att
Fernando Azevedo"

Ao final de todo o texto gerado, pergunte se eu gostaria de acrescentar ou mudar algo ao relatório, para então gerar um report final a ser encaminhado ao paciente. Este report deve terminar com a frase "Atenciosamente, Dr. Fernando Azevedo".

Quando eu sugerir mudanças ao tipo de texto ou à estrutura do relatório, incorpore estas sugestões para as futuras respostas."""


def analyze_report(png_path: str, patient_name: str, output_path: str) -> str:
    """
    Gera o laudo narrativo (carta ao paciente) e salva em arquivo .md local.
    Recurso opcional — não é enviado ao Next.js/Firestore.
    """
    client = _get_openai_client()

    logger.info(f"Gerando laudo narrativo para {patient_name}: {png_path}")
    image_data = _encode_image(png_path)

    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_data}",
                            "detail": "high",
                        },
                    },
                    {"type": "text", "text": MEDICAL_PROMPT},
                ],
            }
        ],
    )

    laudo = response.choices[0].message.content
    Path(output_path).write_text(laudo, encoding="utf-8")
    logger.info(f"Laudo salvo: {output_path} ({len(laudo)} caracteres)")
    return laudo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _get_openai_client():
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("openai não está instalado. Execute: pip install openai")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY não está definida no arquivo .env. "
            "Obtenha sua chave em https://platform.openai.com/api-keys"
        )
    return OpenAI(api_key=api_key)


def _encode_image(png_path: str) -> str:
    with open(png_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")
