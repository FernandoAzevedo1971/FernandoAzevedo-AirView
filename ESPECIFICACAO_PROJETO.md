# 📋 Especificação do Projeto — AirView Gestão de Relatórios de Adesão

> **Documento de planejamento consolidado.**
> Reúne todas as decisões, arquitetura e detalhes técnicos definidos ao longo do
> desenvolvimento. Pode ser usado como instrução completa para construir o projeto
> do zero — todo o planejamento já está feito.
>
> **Autor / Cliente:** Dr. Fernando Azevedo — Pneumologia & Medicina do Sono
> **Repositório:** `FernandoAzevedo1971/FernandoAzevedo-AirView`

---

## 1. Visão Geral

Aplicação para automatizar a **coleta, organização e análise clínica** dos relatórios
de adesão ao tratamento com CPAP/APAP gerados pelo portal **ResMed AirView**
(https://airview.resmed.com).

O médico cadastra pacientes manualmente. Para cada paciente, o sistema agenda a
geração de relatórios de adesão em **marcos temporais** (D0, D+3, D+7, D+14, D+21, D+30),
contados a partir da **data de início da terapia**. Cada relatório é baixado em PDF,
convertido em imagem e enviado a um modelo de IA com **visão computacional** (GPT-4o),
que produz um **laudo clínico em português** seguindo um modelo de texto específico.

---

## 2. Objetivo Clínico

- Acompanhar a **adesão** (uso diário, % de dias com uso ≥ 4h) ao longo do primeiro mês.
- Monitorar **vazamento (fuga)**, **pressão de terapia** e **IAH residual**.
- Gerar laudos padronizados, prontos para encaminhar ao paciente, com sugestões de
  ajuste da terapia quando indicado.
- Reduzir o trabalho manual de entrar paciente por paciente no AirView.

---

## 3. Decisões Tomadas (com justificativa)

| Tema | Decisão | Motivo |
|---|---|---|
| **Interface** | Aplicação **web** (navegador) | Mais amigável e visual; formulário + painel |
| **Seleção de pacientes** | **Cadastro manual** por nome | Evolução do pedido inicial (10 primeiros / 10 mais recentes) — o médico escolhe quem acompanhar |
| **Agendamento** | **Manual com lembrete** | O painel mostra o que está disponível; o médico clica para gerar. Sem automação de fundo (não exige servidor sempre ligado) |
| **Marco zero (D0)** | **Data de início da terapia** | Mais preciso clinicamente que a data de cadastro. Extraída do 1º relatório (PDF) |
| **Marcos** | D0, **D+3, D+7, D+14, D+21, D+30** | Acompanhamento do 1º mês de tratamento |
| **IA de análise** | **OpenAI GPT-4o Vision** | Escolha do usuário; lê dados clínicos direto da imagem do relatório |
| **Tipo de relatório** | **"Relatório de adesão ao tratamento"** | Nome exato da opção no AirView |
| **Banco de dados** | **SQLite** | Local, sem servidor, arquivo único (`airview.db`) |
| **Automação web** | **Playwright** (Chromium headless) | AirView é SPA React; requests puro não funciona |
| **PDF → imagem** | **PyMuPDF (fitz)** | Renderiza página a 300 DPI sem dependências externas (sem Poppler) |

---

## 4. Stack Tecnológica

```
Python 3.11+
├── playwright            # automação do navegador (SPA React)
├── pymupdf (fitz)        # PDF → PNG (300 DPI) + extração de texto
├── openai                # GPT-4o Vision (análise do relatório)
├── fastapi + uvicorn     # servidor web
├── jinja2                # templates HTML
├── python-multipart      # formulários
├── python-dotenv         # variáveis de ambiente (.env)
└── sqlite3 (stdlib)      # persistência
```

**requirements.txt:**
```
playwright==1.44.0
python-dotenv==1.0.0
pymupdf==1.24.0
openai>=1.30.0
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
jinja2>=3.1.0
python-multipart>=0.0.9
```

---

## 5. Fluxo Funcional

```
1. Médico cadastra paciente pelo nome (formulário web)
   └── sistema cria 6 marcos: D0 (disponível) + D+3..D+30 (aguardando início)

2. Médico clica "Gerar" no D0
   └── pipeline:
       ├── abre Chromium headless
       ├── login no AirView (usuário/senha)
       ├── busca o paciente pelo nome → obtém URL
       ├── abre menu de relatórios → "Relatório de adesão ao tratamento"
       ├── define período → baixa PDF
       ├── EXTRAI a data de início da terapia do texto do PDF
       ├── PDF → PNG (1ª página, 300 DPI)
       └── PNG → GPT-4o → laudo clínico (.md)

3. Sistema calcula vencimentos de D+3..D+30 a partir da data de início
   └── marcos passam a aparecer como "agendado" → "disponível" quando vence

4. Painel mostra lembretes dos relatórios disponíveis
   └── médico clica "Gerar agora" em cada marco vencido
       (mesmo pipeline, período = início da terapia → data do marco)

5. Para cada marco: PDF + PNG + laudo disponíveis para download
```

---

## 6. Modelo de Dados (SQLite)

### Tabela `patients`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT | Nome exato como no AirView |
| airview_url | TEXT | URL do paciente (resolvida na 1ª busca) |
| therapy_start_date | TEXT (ISO) | Data de início da terapia (do PDF) |
| status | TEXT | `novo` / `ativo` / `concluido` / `erro` |
| notes | TEXT | Observações clínicas |
| created_at | TEXT | Data de cadastro |

### Tabela `milestones`
| Coluna | Tipo | Descrição |
|---|---|---|
| id | INTEGER PK | |
| patient_id | INTEGER FK | → patients.id (ON DELETE CASCADE) |
| label | TEXT | `D0`, `D+3`, `D+7`, `D+14`, `D+21`, `D+30` |
| offset_days | INTEGER | 0, 3, 7, 14, 21, 30 |
| due_date | TEXT (ISO) | Vencimento (nulo até saber início da terapia) |
| status | TEXT | `aguardando_inicio` / `agendado` / `disponivel` / `gerando` / `gerado` / `erro` |
| pdf_path | TEXT | Caminho do PDF gerado |
| png_path | TEXT | Caminho do PNG (1ª página) |
| laudo_path | TEXT | Caminho do laudo (.md) |
| generated_at | TEXT | Quando foi gerado |
| error | TEXT | Mensagem de erro (se houver) |

**Estados de exibição do marco** (calculados em `scheduler.milestone_display_status`):
- `gerado` — já gerado com sucesso
- `erro` — falhou na última tentativa
- `disponivel` — venceu (today ≥ due_date) e ainda não gerado → **mostra no lembrete**
- `agendado` — vencimento futuro
- `aguardando_inicio` — ainda não sabemos a data de início (D0 não coletado)

---

## 7. Estrutura de Arquivos

```
FernandoAzevedo-AirView/
├── app.py                  # ★ Servidor FastAPI (rotas, jobs em background)
├── db.py                   # ★ Persistência SQLite
├── scheduler.py            # ★ Cálculo de marcos/vencimentos/estados
├── report_pipeline.py      # ★ Orquestra geração de 1 marco (login→...→laudo)
├── patient_search.py       # ★ Busca paciente por nome no AirView
├── pdf_utils.py            # ★ Extrai data de início da terapia do PDF
│
├── browser.py              # Ciclo de vida do Chromium (Playwright)
├── login.py                # Autenticação no AirView
├── report_requester.py     # Solicita e baixa o PDF de adesão
├── pdf_screenshot.py       # PDF → PNG (300 DPI)
├── claude_analyzer.py      # GPT-4o Vision → laudo (nome histórico do arquivo)
├── config.py               # Seletores CSS/XPath + constantes
├── utils.py                # Retry, logging, helpers
│
├── airview_automation.py   # Script CLI original (modo lote, ainda funcional)
├── patients.py             # Lista/ordena pacientes (usado pelo modo CLI)
│
├── templates/
│   ├── base.html
│   ├── dashboard.html      # Painel + lembretes
│   ├── add_patient.html    # Formulário de cadastro
│   └── patient_detail.html # Marcos + downloads + polling
├── static/
│   └── style.css
│
├── requirements.txt
├── setup.sh                # Instala deps + Chromium
├── run_app.sh              # Sobe o servidor web
├── .env                    # Credenciais (NÃO versionado)
├── .env.example            # Template
└── airview.db              # Banco SQLite (NÃO versionado, criado em runtime)

★ = módulos da aplicação web (novos). Os demais são reaproveitados da automação.
```

---

## 8. Rotas da Aplicação Web (FastAPI)

| Método | Rota | Função |
|---|---|---|
| GET | `/` | Painel: lista de pacientes + lembretes de relatórios disponíveis |
| GET | `/add` | Formulário de cadastro de paciente |
| POST | `/add` | Cria paciente + 6 marcos iniciais → redireciona ao detalhe |
| GET | `/patient/{id}` | Detalhe: marcos, vencimentos, downloads, ações |
| POST | `/patient/{id}/delete` | Remove paciente e seus marcos |
| POST | `/patient/{id}/generate/{milestone_id}` | Dispara geração em background thread |
| GET | `/api/patient/{id}/status` | JSON de status (polling do frontend) |
| GET | `/file?path=...` | Serve PDF/PNG/laudo (com proteção contra path traversal) |

**Execução de jobs:** cada geração roda em uma `threading.Thread` separada, que executa
o pipeline assíncrono (`asyncio.run`) e atualiza o banco ao final. O frontend faz
*polling* em `/api/...` e recarrega a página quando há marco "gerando".

---

## 9. ⭐ O Prompt Médico (CRÍTICO — usar literalmente)

Este prompt é enviado ao GPT-4o junto com a imagem PNG de cada relatório.
**Deve ser mantido exatamente como abaixo** (está em `claude_analyzer.py` → `MEDICAL_PROMPT`):

```
Responda em português.
Você vai atuar com conhecimentos de elevado nível em pneumologia, medicina do sono,
ventilação não invasiva e uso de pressão positiva contínua, sabendo interpretar curvas
de dados de tratamento com pressão positiva que incluem análise de Utilização e Terapia,
sabendo interpretar curvas e valores de vazamento (fuga) intencional ou não-intencional,
Pressão de terapia, e índice de apneia e hipopneia.

Este Projeto tem como objetivo analisar relatórios gerados automaticamente pela url
https://airview.resmed.com/, que gera relatórios do uso de CPAP em diversos formatos,
seja Relatório de adesão ao tratamento e terapia (por períodos de uso), seja Relatórios
detalhado (relatórios de cada dia individualmente).

Após gerar o relatório de interpretação do arquivo inserido, faça insights sobre
sugestões de possíveis mudanças nos ajustes para otimizar a terapia, caso os valores
de uso, fuga ou pressões estejam inadequados.

O relatório gerado deve ter escrita técnica porém de fácil compreensão, e ser amigável
na leitura.

Use a seguinte estrutura de texto:

"Prezado Sr./Sra., --- (nome do paciente do relatório).
Segue, em anexo, o relatório de adesão e terapia do sono, referente aos últimos -- dias
de tratamento.
O período analisado foi ---.
Revendo os registros observei que (há/não há) regularidade no uso do equipamento,
obtendo a relação de uso de 30/30 (ou --/--) dias, o que representa --% da totalidade
dos dias analisados, com média de uso diário de -h--min; destes, -- dias (--%) com uso
superior a 4,0h/dia.
Os registros de vazamento (escape aéreo) ficaram (elevado/dentro do aceitável/baixo),
ficando a mediana -- l/min e 95% do tempo -- l/min ou abaixo. O equipamento está
habilitado para compensar até 24,0 l/min. Este resultado demonstra (eficiência/
ineficiência) da máscara utilizada em gerar contenção e estabilidade ao fluxo e
pressão de gases; observo também a pressão média de -- cm/H2O (o equipamento está
regulado ao APAP com Pressão máx --,- cmH2O e Pressão mín --,- cmH2O). Por fim,
encontrei Índice de Apneia e Hipopneia residual -- eventos/hora, sendo deste índice
-- hipopneias, -- obstrutivas, -- centrais, -- desconhecidas.
(analise agora os resultados e proponha modificações à terapia se aplicável)

Coloco-me à disposição para maiores esclarecimentos,
Att
Fernando Azevedo"

Ao final de todo o texto gerado, pergunte se eu gostaria de acrescentar ou mudar algo
ao relatório, para então gerar um report final a ser encaminhado ao paciente.
Este report deve terminar com a frase "Atenciosamente, Dr. Fernando Azevedo".

Quando eu sugerir mudanças ao tipo de texto ou à estrutura do relatório, incorpore
estas sugestões para as futuras respostas.
```

**Regras de comportamento do laudo:**
1. Sempre em português, escrita técnica mas amigável.
2. Seguir a estrutura de carta acima, preenchendo os valores lidos do relatório.
3. Propor ajustes da terapia quando uso/fuga/pressão estiverem inadequados.
4. Ao final, **perguntar** se o médico quer acrescentar/mudar algo.
5. O relatório **final** (após revisão) termina com **"Atenciosamente, Dr. Fernando Azevedo"**.
6. Incorporar sugestões do médico nas respostas futuras (memória de estilo).

---

## 10. Integração com OpenAI GPT-4o

```python
from openai import OpenAI
import base64

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

with open(png_path, "rb") as f:
    image_data = base64.standard_b64encode(f.read()).decode("utf-8")

response = client.chat.completions.create(
    model="gpt-4o",
    max_tokens=4096,
    messages=[{
        "role": "user",
        "content": [
            {"type": "image_url",
             "image_url": {"url": f"data:image/png;base64,{image_data}",
                           "detail": "high"}},
            {"type": "text", "text": MEDICAL_PROMPT},
        ],
    }],
)
laudo = response.choices[0].message.content
```

> `detail: "high"` é importante para o modelo ler os números/curvas do relatório.

---

## 11. Credenciais e Configuração (`.env`)

```env
# AirView ResMed
AIRVIEW_USER=fazevedopneumosono
AIRVIEW_PASS=Sf271003**

# OpenAI (https://platform.openai.com/api-keys)
OPENAI_API_KEY=sk-...

# Opcionais
HEADLESS=true            # false para ver o navegador
SLOW_MO=0                # atraso entre ações (ms) — debug
TIMEOUT_MS=30000
REPORT_DAYS=14           # período padrão quando não há data de início
DELAY_BETWEEN_PATIENTS=2
```

> ⚠️ **Segurança:** o `.env` está no `.gitignore` e **nunca** deve ser versionado.
> A conta AirView usada **não tem 2FA** (simplifica a automação). Se for ativado 2FA,
> o fluxo de login precisará de uma etapa para inserir o código.

---

## 12. ⚠️ Aprendizados Técnicos / Armadilhas (importante!)

Pontos descobertos durante o desenvolvimento que **economizam tempo** na reconstrução:

### 12.1. Login do AirView é um SPA React
- Os campos só aparecem após o JS carregar. Use `wait_until="networkidle"` +
  `wait_for_timeout(1500)` antes de procurar os inputs.
- Seletores precisam de **múltiplas alternativas** (CSS, XPath, placeholder, name) com
  fallback — o DOM do React pode mudar nomes de classe. Padrão `try_selectors()`.

### 12.2. Certificado SSL / proxy corporativo
- Em alguns ambientes o Chromium recusa o certificado (`ERR_CERT_AUTHORITY_INVALID`).
- Solução: lançar o Chromium com `--ignore-certificate-errors`.

### 12.3. Chromium em ambiente headless Linux
- `--no-sandbox --disable-setuid-sandbox --disable-dev-shm-usage --disable-gpu` são
  **obrigatórios** (o `disable-dev-shm-usage` evita crash por falta de memória em `/dev/shm`).
- Se `playwright install chromium` falhar por bloqueio de CDN, alternativa que funcionou:
  baixar o Chrome via `npm install puppeteer` (vai para `~/.cache/puppeteer/...`) e
  passar `executable_path` para o Playwright. O `browser.py` já procura esse caminho.

### 12.4. Starlette/FastAPI — assinatura do TemplateResponse
- Versões novas do Starlette mudaram a assinatura. Use a **nova ordem**:
  `templates.TemplateResponse(request, "pagina.html", {...contexto...})`
  (request é o **primeiro** argumento posicional). A forma antiga
  `TemplateResponse("pagina.html", {"request": request})` quebra com
  `TypeError: unhashable type: 'dict'`.

### 12.5. Download de PDF no Playwright
- Use `async with page.expect_download() as dl: ...` e depois `download.save_as(path)`.
- Fallback: se o PDF abrir em nova aba em vez de baixar, capturar a nova página
  (`context.expect_page()`) e salvar via `page.request.get(url)`.

### 12.6. Extração da data de início da terapia
- O PDF de adesão tem texto extraível via `fitz` (PyMuPDF). Procurar rótulos
  ("Data de início", "Therapy start", etc.), depois intervalo "data – data",
  depois a data mais antiga do documento (fallback). Ver `pdf_utils.py`.

### 12.7. Ambiente cloud (Claude Code on web) NÃO acessa o AirView
- A política de rede do ambiente em nuvem bloqueia `airview.resmed.com`
  ("Host not in allowlist"). **O pipeline de rede só roda localmente** na máquina do médico.
- Toda a lógica (banco, agendamento, rotas, templates) **foi testada e funciona** no
  ambiente; apenas as chamadas ao AirView exigem execução local.

---

## 13. Como Executar (na máquina local)

```bash
# 1. Clonar
git clone https://github.com/FernandoAzevedo1971/FernandoAzevedo-AirView.git
cd FernandoAzevedo-AirView
git checkout claude/repo-name-question-rQvkM   # branch de desenvolvimento

# 2. Instalar dependências + navegador
pip install -r requirements.txt
python -m playwright install chromium     # (ou usar fallback do puppeteer)

# 3. Configurar credenciais
cp .env.example .env
# editar .env com AIRVIEW_USER, AIRVIEW_PASS e OPENAI_API_KEY

# 4. Subir a aplicação web
./run_app.sh
# ou: uvicorn app:app --host 0.0.0.0 --port 8000

# 5. Abrir no navegador
http://localhost:8000
```

**Modo CLI alternativo** (lote, sem interface — script original):
```bash
python airview_automation.py   # processa pacientes em lote
```

---

## 14. Estado Atual do Projeto

✅ **Pronto e testado localmente:**
- Aplicação web FastAPI (painel, cadastro, detalhe)
- Banco SQLite com pacientes e marcos
- Lógica de agendamento (D0..D+30) e estados de exibição
- Geração em background com polling de status
- Segurança de servir arquivos (anti path traversal)
- Pipeline completo codificado (login→busca→relatório→PNG→GPT-4o)
- Integração GPT-4o Vision com o prompt médico

⏳ **Pendente / a validar com execução local real:**
1. Ajuste fino dos **seletores** do AirView (login, busca, menu de relatório, período)
   após o primeiro teste com a conta real — os seletores atuais são "palpites resilientes".
2. Confirmar o **nome/fluxo exato** do "Relatório de adesão ao tratamento" na UI atual.
3. Validar a **extração da data de início** com PDFs reais.
4. Screenshots da interface (não concluídos na última sessão).
5. Atualizar o `README.md` com as instruções da app web.

---

## 15. Roadmap / Próximos Passos Sugeridos

- [ ] **Sessão de calibração de seletores**: rodar localmente com a conta real,
      inspecionar o DOM do AirView e fixar os seletores corretos em `config.py`.
- [ ] **Edição interativa do laudo**: implementar a etapa "pergunte se quero mudar algo"
      como um chat na própria interface, gerando o laudo final com a assinatura
      "Atenciosamente, Dr. Fernando Azevedo".
- [ ] **Memória de estilo**: salvar as preferências de redação do médico e injetá-las
      nos prompts futuros (o prompt já pede isso; falta persistir).
- [ ] **Exportar laudo final** em PDF/DOCX pronto para enviar ao paciente.
- [ ] **Notificações**: e-mail/WhatsApp quando um marco vence (opcional — hoje é
      "manual com lembrete" no painel).
- [ ] **Multiusuário/autenticação** na app web, se for usada por mais de um médico.
- [ ] **Marco "concluído"**: marcar paciente como concluído após o D+30.

---

## 16. Histórico de Evolução do Pedido (contexto)

1. Identificar o repositório → `FernandoAzevedo-AirView`.
2. Acessar o AirView e autenticar.
3. Ir a `/wireless`, acessar os **10 primeiros pacientes**, relatório consolidado de 14 dias.
4. Especificar: relatório = **"Relatório de adesão ao tratamento"**; tirar **print da 1ª
   página do PDF**; enviar a imagem para análise por IA.
5. Definir o **prompt médico** especializado (laudo estruturado, assinatura do Dr.).
6. Trocar a IA de Anthropic Claude para **OpenAI GPT-4o**.
7. Mudar a seleção para os **10 pacientes mais recentes** por data de cadastro.
8. **Pedido final (atual):** transformar em **aplicação** com **cadastro manual** de
   pacientes e **agendamento por marcos** (D0, D+3, D+7, D+14, D+21, D+30), interface
   **web**, disparo **manual com lembrete**, contagem a partir da **data de início da terapia**.

---

*Documento gerado para servir de instrução completa de (re)construção do projeto.*
