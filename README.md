# AirView ResMed — Automação de Relatórios de Adesão

Ferramenta de automação para o portal clínico **ResMed AirView** que:

1. 🔐 Faz login em https://airview.resmed.com
2. 👥 Coleta os **10 primeiros pacientes** da página `/wireless`
3. 📄 Para cada paciente: solicita o **"Relatório de adesão ao tratamento"** (últimos 14 dias) e baixa o PDF
4. 🖼️ Captura um **screenshot da 1ª página** do PDF (PNG, 300 DPI)
5. 🤖 Envia o PNG ao **Claude Vision** para análise médica especializada
6. 📝 Salva um **laudo técnico** em português por paciente (`*.md`)

Desenvolvido para o **Dr. Fernando Azevedo** — Pneumologista / Medicina do Sono.

---

## Pré-requisitos

- Python 3.11+
- Conta ativa no AirView ResMed (sem 2FA)
- Chave da API Anthropic (`ANTHROPIC_API_KEY`) → https://console.anthropic.com

---

## Instalação Rápida

```bash
# Clone o repositório
git clone https://github.com/FernandoAzevedo1971/FernandoAzevedo-AirView.git
cd FernandoAzevedo-AirView

# Instala dependências e browser
chmod +x setup.sh
./setup.sh

# Edita as credenciais
nano .env   # preenche AIRVIEW_USER, AIRVIEW_PASS e ANTHROPIC_API_KEY
```

---

## Configuração (`.env`)

```env
AIRVIEW_USER=seu_usuario
AIRVIEW_PASS=sua_senha
ANTHROPIC_API_KEY=sk-ant-...

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

**Laudo Claude não gerado:**
- Verifique `ANTHROPIC_API_KEY` no `.env`
- Confirme saldo na conta Anthropic

---

## Dependências

```
playwright==1.44.0      # automação web
pymupdf==1.24.0         # conversão PDF → PNG
anthropic==0.28.0       # Claude Vision API
python-dotenv==1.0.0    # variáveis de ambiente
```
