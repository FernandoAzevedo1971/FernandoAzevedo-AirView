# AirView ResMed — Gestão de Relatórios de Adesão

Aplicação para o **Dr. Fernando Azevedo** (Pneumologia / Medicina do Sono) que
automatiza a coleta e análise clínica dos relatórios de adesão do portal
**ResMed AirView** (https://airview.resmed.com).

**Aplicação web** onde o médico cadastra pacientes manualmente. Para cada paciente,
o sistema agenda relatórios em marcos temporais — **D0, D+3, D+7, D+14, D+21, D+30**
— contados a partir da **data de início da terapia**. Cada relatório é baixado em PDF,
convertido em imagem e enviado ao **GPT-4o Vision**, que gera um **laudo clínico**
em português.

> 📄 Planejamento completo em [`ESPECIFICACAO_PROJETO.md`](ESPECIFICACAO_PROJETO.md).

---

## Pré-requisitos

- **Python 3.11+**
- Conta ativa no **AirView ResMed** (sem 2FA)
- Chave da **API OpenAI** (`OPENAI_API_KEY`) → https://platform.openai.com/api-keys

---

## Como Rodar Localmente

```bash
# 1. Clonar o repositório
git clone https://github.com/FernandoAzevedo1971/FernandoAzevedo-AirView.git
cd FernandoAzevedo-AirView
git checkout claude/repo-name-question-rQvkM

# 2. Instalar dependências Python
pip install -r requirements.txt

# 3. Instalar o navegador do Playwright (só na 1ª vez)
python -m playwright install chromium

# 4. Configurar credenciais
cp .env.example .env
#    Edite o .env preenchendo:
#      AIRVIEW_USER, AIRVIEW_PASS e OPENAI_API_KEY

# 5. Subir a aplicação web
uvicorn app:app --port 8000
#    (ou: ./run_app.sh)

# 6. Abrir no navegador
#    http://localhost:8000
```

No painel: clique em **“+ Novo paciente”**, cadastre pelo nome (exatamente como no
AirView) e depois use **“Gerar agora”** no marco **D0** — o sistema faz login, baixa o
relatório, descobre a data de início da terapia e calcula os demais vencimentos.

> 💡 **Windows:** use `py -m pip install ...` e `py -m playwright install chromium`.
> Se `uvicorn` não for reconhecido, rode `python -m uvicorn app:app --port 8000`.

---

## Modo CLI (lote — opcional)

Além da app web, há o script original que processa vários pacientes de uma vez:

```bash
python airview_automation.py
```

---

## Instalação com script (Linux/Mac)

```bash
chmod +x setup.sh
./setup.sh          # instala deps + Chromium + cria .env
```

---

## Configuração (`.env`)

```env
AIRVIEW_USER=seu_usuario
AIRVIEW_PASS=sua_senha
OPENAI_API_KEY=sk-...

# Opcional
HEADLESS=true           # false para ver o browser na tela
SLOW_MO=0               # atraso entre ações (ms) — útil para debug
TIMEOUT_MS=30000        # timeout geral (ms)
MAX_PATIENTS=10         # quantos pacientes processar
REPORT_DAYS=14          # dias do relatório
DELAY_BETWEEN_PATIENTS=2
```

---

## Execução

```bash
python airview_automation.py
```

---

## Saídas

Os arquivos são salvos na pasta `reports/`:

| Arquivo | Descrição |
|---|---|
| `paciente_01_NomePaciente.pdf` | Relatório PDF original do AirView |
| `paciente_01_NomePaciente_pag1.png` | Screenshot da 1ª página (300 DPI) |
| `paciente_01_NomePaciente_laudo.md` | Laudo médico gerado pelo Claude Vision |

---

## Estrutura do Projeto

```
├── airview_automation.py   # Orquestrador principal
├── browser.py              # Gerenciamento do browser Playwright
├── login.py                # Autenticação no AirView
├── patients.py             # Lista de pacientes (/wireless)
├── report_requester.py     # Solicitação e download do PDF
├── pdf_screenshot.py       # Conversão PDF → PNG
├── claude_analyzer.py      # Análise via Claude Vision API
├── config.py               # Seletores CSS/XPath e constantes
├── utils.py                # Retry, logging, helpers
├── requirements.txt        # Dependências Python
└── setup.sh                # Script de instalação
```

---

## Laudo Médico Gerado

O laudo segue estrutura clínica padronizada incluindo:
- Identificação do paciente e período analisado
- Regularidade de uso (dias/total, %)
- Média de uso diário e dias com uso ≥ 4h
- Vazamentos (mediana e percentil 95)
- Pressão média e configurações APAP
- IAH residual (hipopneias, obstrutivas, centrais, desconhecidas)
- Sugestões de otimização da terapia
- Assinatura: **Dr. Fernando Azevedo**

---

## Troubleshooting

**Login falhou:**
- Verifique usuário/senha no `.env`
- Confirme que não tem 2FA ativado na conta

**Relatório não encontrado:**
- Screenshot de debug salvo em `logs/`
- O nome do relatório pode variar — edite `REPORT_SELECTORS` em `config.py`

**Laudo GPT-4o não gerado:**
- Verifique `OPENAI_API_KEY` no `.env`
- Confirme saldo na conta OpenAI (platform.openai.com/usage)

---

## Dependências

```
playwright==1.44.0      # automação web
pymupdf==1.24.0         # conversão PDF → PNG
openai>=1.30.0          # GPT-4o Vision API
python-dotenv==1.0.0    # variáveis de ambiente
```
