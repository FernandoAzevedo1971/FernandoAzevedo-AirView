"""
claude_analyzer.py — Analisa o PNG do relatório usando GPT-4o Vision (OpenAI API)
e gera um laudo médico em português estruturado.
"""
import os
import base64
import logging
from pathlib import Path

logger = logging.getLogger("airview.analyzer")

# ---------------------------------------------------------------------------
# Prompt médico especializado (Dr. Fernando Azevedo)
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
    Envia o PNG ao GPT-4o Vision e salva o laudo gerado em arquivo .md.

    Args:
        png_path: Caminho para o PNG da 1ª página do relatório PDF
        patient_name: Nome do paciente (para log)
        output_path: Caminho onde o laudo .md será salvo

    Returns:
        Texto do laudo gerado
    """
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError(
            "openai não está instalado. Execute: pip install openai"
        )

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY não está definida no arquivo .env. "
            "Obtenha sua chave em https://platform.openai.com/api-keys"
        )

    logger.info(f"Enviando PNG ao GPT-4o Vision: {png_path}")

    # Lê e codifica o PNG em base64
    with open(png_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    client = OpenAI(api_key=api_key)

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
                            "detail": "high",   # alta resolução para leitura de dados clínicos
                        },
                    },
                    {
                        "type": "text",
                        "text": MEDICAL_PROMPT,
                    },
                ],
            }
        ],
    )

    laudo = response.choices[0].message.content

    # Salva o laudo como arquivo Markdown
    Path(output_path).write_text(laudo, encoding="utf-8")

    logger.info(
        f"Laudo gerado para {patient_name}: {output_path} "
        f"({len(laudo)} caracteres)"
    )

    return laudo
