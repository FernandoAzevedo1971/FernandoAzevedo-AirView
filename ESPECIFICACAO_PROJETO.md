# 📋 Especificação do Projeto — AirView Sync

> **Documento de planejamento consolidado — versão 2 (arquitetura de integração).**
> A v1 deste documento descrevia um painel web próprio em Python (FastAPI).
> Essa abordagem foi **descartada** ao descobrir que o médico já tinha um
> painel completo em Next.js/Firebase (`MONITORAMENTO_CPAP_FAPS`). Este
> documento descreve a arquitetura **atual**: o Python vira um robô de
> sincronização que alimenta esse painel existente.
>
> **Autor / Cliente:** Dr. Fernando Azevedo — Pneumologia & Medicina do Sono
> **Repositório automação:** `FernandoAzevedo1971/FernandoAzevedo-AirView`
> **Repositório painel:** `FernandoAzevedo1971/MONITORAMENTO_CPAP_FAPS`

---

## 1. Visão Geral

Existem **dois projetos** trabalhando juntos:

| Projeto | Stack | Papel |
|---|---|---|
| **MONITORAMENTO_CPAP_FAPS** | Next.js + Firebase/Firestore | Painel principal: cadastro de pacientes, marcos (D1/D3/D7/D14/D30), alertas de adesão, gráficos, notificações |
| **FernandoAzevedo-AirView** (este repo) | Python + Playwright | Robô: entra no ResMed AirView, baixa relatórios, extrai dados com IA, alimenta o painel via API |

O médico **nunca interage diretamente** com o robô Python além de executá-lo
(manual ou agendado). Toda a experiência de uso continua sendo o painel Next.js.

---

## 2. Por que essa arquitetura (histórico da decisão)

1. Primeiro pedido: script simples para baixar 10 relatórios do AirView.
2. Evoluiu para: aplicação web própria (Python/FastAPI) com cadastro de
   pacientes e agendamento de marcos (D0/D+3/D+7/D+14/D+21/D+30).
3. Ao tentar publicar na nuvem, descobrimos que **já existia** um projeto
   Next.js/Firebase (`MONITORAMENTO_CPAP_FAPS`) com cadastro de pacientes,
   marcos, alertas e gráficos **já prontos e em produção**.
4. Decisão: **não duplicar** o painel. O Python vira só o "braço robótico"
   que sabe entrar no AirView — o Next.js continua sendo o cérebro/interface.

**Por que não reescrever a automação em Node.js?** Porque a limitação real
(rodar um navegador Chromium por 30-60s) existe em qualquer linguagem — não
é uma limitação do Python. Reescrever não eliminaria a necessidade de um
processo de longa duração rodando em algum lugar (local ou servidor
dedicado). Reaproveitar o código Python já testado foi a escolha mais eficiente.

---

## 3. Arquitetura

```
┌──────────────────────────┐         ┌───────────────────────────┐
│  MONITORAMENTO_CPAP_FAPS │  HTTP   │   FernandoAzevedo-AirView   │
│  (Next.js + Firebase)    │◀───────▶│   (Python + Playwright)     │
│                           │  JSON   │                             │
│ • Cadastro de pacientes  │         │ • Login no AirView          │
│ • Marcos D1/D3/D7/D14/D30│         │ • Busca paciente por nome   │
│ • Dashboard e gráficos   │         │ • Baixa PDF de adesão       │
│ • Alertas de adesão      │         │ • Extrai dados (GPT-4o)     │
│ • Firestore (fonte única │         │ • Envia via API             │
│   da verdade)            │         │                             │
└──────────────────────────┘         └───────────────────────────┘
     roda no Vercel/local                  roda LOCAL (ou agendado)
```

**Autenticação entre os serviços:** chave secreta compartilhada
(`AIRVIEW_SYNC_SECRET`, header `x-api-key`) — não é login de usuário Firebase,
é uma credencial de serviço-para-serviço.

---

## 4. Modelo de Dados (Firestore — já existente, não modificado)

```
users/{uid}/pacientes/{pacienteId}
  nome, dataInicio, aparelho, mascara, observacoes, ativo, criadoEm,
  categoria, modoVentilatorio, pressaoPrescrita

users/{uid}/pacientes/{pacienteId}/marcos/{marcoId}
  tipo: "D1" | "D3" | "D7" | "D14" | "D30"
  dataPrevista, status: "pendente" | "revisado" | "ignorado"
  notificadoEm, revisadoEm

users/{uid}/pacientes/{pacienteId}/capturas/{capturaId}
  marcoId, dataCaptura, dataInicio, dataFim,
  usoHorasMedia, diasUso, percentualUso, iahResidual,
  vazamento, vazamentoMedio, periodoDias,
  pressaoMediana, pressaoP95,             ← só a automação preenche
  origem: "automatica" | "manual",
  rawJson,                                 ← só a automação preenche
  desconfortos[], sintomas[]                ← só entrada manual do paciente
```

Os marcos (D1/D3/D7/D14/D30, offsets de 1/3/7/14/30 dias) e a `dataInicio`
já existem e são geridos **inteiramente pelo Next.js** — o Python só lê.

---

## 5. Fluxo de Sincronização

```
sync_runner.py (executado manualmente ou agendado):

1. GET /api/sync/pendentes  (autenticado por x-api-key)
   → lista de marcos com status "pendente" e dataPrevista <= hoje,
     já enriquecidos com dataInicio/aparelho/mascara do paciente

2. Se lista vazia → encerra (nada a fazer hoje)

3. Login único no AirView (sessão reaproveitada)

4. Para cada marco pendente:
   a. patient_search.find_patient_url(nome) → localiza o paciente
   b. report_requester.request_report(dataInicio → dataPrevista) → baixa PDF
   c. pdf_screenshot.capture_first_page() → PNG da 1ª página
   d. gpt_analyzer.extract_structured_data(png) → dict com os números
   e. POST /api/captura/importar → grava no Firestore como
      origem: "automatica"
   f. Falha em um paciente NÃO interrompe os demais

5. Resumo final no log (sucesso/erro por paciente)
```

> O robô **não marca o marco como "revisado"** — isso fica a critério do
> médico, que vê os dados já preenchidos no painel e confirma manualmente.
> Mantém o humano no controle da decisão clínica.

---

## 6. Integração Next.js — o que foi adicionado

Ver [`INTEGRACAO_NEXTJS.md`](INTEGRACAO_NEXTJS.md) para o código completo.
Resumo das 3 adições (nenhum arquivo existente foi alterado):

1. **`criarCapturaAutomatica()`** — nova função em `src/lib/firestore/capturas.ts`,
   espelha `criarCapturaManual()` mas seta `origem: "automatica"` e aceita os
   campos extras (`pressaoMediana`, `pressaoP95`, `dataInicio`, `dataFim`, `rawJson`).
2. **`GET /api/sync/pendentes`** — nova rota, protegida por `x-api-key`,
   retorna marcos pendentes hoje + dados do paciente necessários.
3. **`POST /api/captura/importar`** — nova rota, protegida por `x-api-key`,
   grava a captura automática (com validação dos campos numéricos).

Variáveis novas no `.env.local` do Next.js: `AIRVIEW_SYNC_SECRET`,
`AIRVIEW_SYNC_UID` (UID do Dr. Fernando no Firebase Auth).

---

## 7. Extração Estruturada — via regex no texto do PDF (ATUALIZADO — não usa mais IA)

> Esta seção descrevia originalmente extração via GPT-4o Vision. Migrado
> para regex depois de confirmar que o PDF do AirView tem **texto real**
> (não é imagem escaneada). Grátis, mais preciso (sem risco de
> "alucinação" de número) e todos os campos estão na página 1.

`pdf_data_extractor.py` lê o texto do PDF (`pdf_utils.extract_pdf_text()`)
e aplica regex calibrados nos rótulos reais do relatório combinado (em
inglês, mesmo com a UI em português):

```
Usage days 26/30 days (87%)
Average usage (days used) 5 hours 26 minutes
Pressure - cmH2O Median: 11.5 95th percentile: 12.3 Maximum: 12.3
Leaks - L/min Median: 3.1 95th percentile: 17.7 Maximum: 23.7
Events per hour AI: 1.2 HI: 3.9 AHI: 5.1
```

produzindo:

```json
{
  "usoHorasMedia": 5.43,
  "diasUso": 26,
  "percentualUso": 87,
  "iahResidual": 5.1,
  "vazamento": 3.1,
  "vazamentoMedio": 17.7,
  "pressaoMediana": 11.5,
  "pressaoP95": 12.3,
  "periodoDias": 30
}
```

Campos não identificados no relatório vêm como `null` — nunca inventados.
Se o AirView mudar o layout do relatório, use `dump_pdf_text.py <pdf>`
para ver o texto real atualizado e recalibrar os padrões.

**O laudo narrativo (carta ao paciente) continua disponível** como recurso
opcional em `gpt_analyzer.analyze_report()` (GPT-4o Vision), usando o mesmo
prompt médico elaborado anteriormente (ver seção 9). Esse é o único lugar
do projeto que ainda usa IA/OpenAI — não é chamado por `sync_runner.py`,
fica salvo localmente e não é enviado ao Next.js.

---

## 8. Estrutura de Arquivos (Python)

```
FernandoAzevedo-AirView/
├── sync_runner.py         # ★ Orquestrador principal
├── sync_client.py          # ★ Cliente HTTP da API do Next.js
├── pdf_data_extractor.py    # ★ Extração estruturada via regex (grátis, sem IA)
├── gpt_analyzer.py          # GPT-4o: laudo narrativo opcional (não usado no fluxo principal)
│
├── browser.py               # Ciclo de vida do Chromium (Playwright)
├── login.py                 # Autenticação no AirView
├── patient_search.py        # Localiza paciente pelo nome
├── report_requester.py      # Solicita e baixa o PDF de adesão
├── pdf_screenshot.py         # PDF → PNG (300 DPI, guardado para conferência)
├── pdf_utils.py               # Utilitários de leitura de PDF (extract_pdf_text)
├── dump_pdf_text.py            # Diagnóstico: imprime o texto bruto do PDF
├── patients.py                 # PatientEntry (estrutura de dados)
├── config.py                    # Seletores CSS/XPath e constantes
├── utils.py                      # Retry, logging, helpers
│
├── requirements.txt
├── executar_sync.bat            # Atalho de execução (Windows)
├── .env / .env.example
├── INTEGRACAO_NEXTJS.md          # Código a colar no Next.js
└── ESPECIFICACAO_PROJETO.md      # Este documento

★ = módulos novos da arquitetura de sincronização
```

**Removido nesta versão** (redundante com o Next.js): `app.py`, `db.py`,
`scheduler.py`, `paths.py`, `report_pipeline.py`, `templates/`, `static/`,
`Dockerfile`, `railway.json`, `DEPLOY.md` — todo o painel web próprio.

---

## 9. ⭐ O Prompt Médico Narrativo (preservado da v1)

Usado por `gpt_analyzer.analyze_report()` — recurso opcional, não obrigatório
para o fluxo principal:

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

---

## 10. Credenciais e Configuração (`.env` do Python)

```env
AIRVIEW_USER=fazevedopneumosono
AIRVIEW_PASS=Sf271003**
OPENAI_API_KEY=sk-...

NEXTJS_API_URL=http://localhost:3000
AIRVIEW_SYNC_SECRET=<idêntica à do Next.js>
```

Conta AirView **sem 2FA** (simplifica o login automatizado).

---

## 11. ⚠️ Aprendizados Técnicos (herdados + novos)

### Herdados da v1
- Login do AirView é SPA React → aguardar `networkidle` + timeout extra.
- Certificado SSL pode exigir `--ignore-certificate-errors` no Chromium.
- Chromium headless Linux exige `--no-sandbox --disable-dev-shm-usage`.
- Download de PDF via `page.expect_download()`.
- Ambiente cloud (Claude Code on web) **bloqueia** `airview.resmed.com` —
  o robô só roda de fato numa máquina com rede liberada (local do médico).

### Novos (integração)
- **Chave secreta ≠ token de usuário**: as rotas `/api/sync/*` e
  `/api/captura/importar` usam `x-api-key` fixo, não `Authorization: Bearer
  <idToken>` do Firebase — porque o robô não é "um usuário logado".
- **`dataInicio` não é mais extraída do PDF**: já vem do Firestore (o médico
  digita ao cadastrar o paciente no Next.js). Isso eliminou a necessidade
  de `extract_therapy_start_date()` no fluxo principal.
- **Marcos são D1/D3/D7/D14/D30** (não D0/D+3/D+7/D+14/D+21/D+30 como na v1)
  — offsets de 1/3/7/14/30 dias a partir da `dataInicio`.
- **GPT-4o com `response_format=json_object`** é mais confiável que pedir
  "responda em JSON" em texto livre — força saída estruturada válida.

---

## 12. Como Executar

**Pré-requisito:** ter feito as 3 adições do `INTEGRACAO_NEXTJS.md` no
projeto Next.js e configurado `.env.local` lá.

```bash
# 1. Next.js rodando (outro terminal)
cd MONITORAMENTO_CPAP_FAPS
npm run dev

# 2. Robô Python
cd FernandoAzevedo-AirView
pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env   # preencher credenciais
python sync_runner.py
```

No Windows, `executar_sync.bat` faz os passos 2 em diante com duplo-clique.

---

## 13. Estado Atual — ONDE PARAMOS

### ✅ FLUXO COMPLETO VALIDADO PONTA A PONTA (12/08/2026)

Teste real contra o AirView de produção terminou com:
```
✓ Hugo Peixoto Pacheco Junior — D30
✓ Marlon Meik Manso Monica — D30
Total: 2/2 marcos sincronizados com sucesso
```

**Lado Next.js (MONITORAMENTO_CPAP_FAPS) — testado localmente em 12/08, mas
não estava commitado (correção em 16/08/2026):** o teste ponta a ponta acima
rodou contra as 3 adições deste documento aplicadas manualmente no checkout
local do médico — elas nunca chegaram a ser commitadas/enviadas ao GitHub, e
o repositório publicado ficou sem `criarCapturaAutomatica()`, sem
`GET /api/sync/pendentes` e sem `POST /api/captura/importar`. Ou seja, o
botão de sincronização teria chamado rotas inexistentes em produção. Isso
foi corrigido em 16/08/2026 (branch `claude/cpap-airview-sync-panel-i2rkav`
do MONITORAMENTO_CPAP_FAPS): as 3 peças agora estão commitadas e com
`npm run build`/`npm test` passando, junto com o botão
"🔄 Sincronizar com AirView" no dashboard (ver seção 15).
- `criarCapturaAutomatica()` em `src/lib/firestore/capturas.ts`
- `GET /api/sync/pendentes`
- `POST /api/captura/importar`
- `.env.local` ainda precisa ser configurado manualmente pelo médico
  (`AIRVIEW_SYNC_SECRET`, `AIRVIEW_SYNC_UID`) — isso não vai para o git

**Lado Python — fluxo completo 100% funcionando:**
- **Login** — Okta em 2 etapas, banner de cookies dispensado automaticamente
- **Busca de paciente** — acha por conjunto de palavras (funciona mesmo com
  nomes invertidos no AirView, "Sobrenome, Nome"), com retry automático em
  timeouts de navegação pontuais
- **Geração e download do relatório** — modal "Criar relatório" → tipo
  "adesão ao tratamento e terapia" (combinado) → período fixo em dias →
  "Continuar" → PDF abre na mesma aba (sem evento de download), capturado
  via navegação de página
- **Extração dos dados — via regex no texto do PDF** (não mais GPT-4o
  Vision; ver seção 7 atualizada) — 9/9 campos extraídos corretamente nos
  dois testes reais, sem custo de API
- **Envio ao Next.js** — captura gravada com `origem: "automatica"`

Histórico dos 6 bugs de geração de relatório encontrados e corrigidos
(Escape fechando o modal, campos de fundo vs. modal, espera por download
que nunca ocorre, período 31 vs 30 dias, crash de `.page` ausente, botão
"Continuar" não sendo `<button>`) — todos confirmados corrigidos pelo teste
real acima.

### ▶️ PRÓXIMOS PASSOS AO RETOMAR

1. **Configurar `.env.local`** do Next.js com `AIRVIEW_SYNC_SECRET` (igual à
   do `.env` do Python) e `AIRVIEW_SYNC_UID` — ver seção 15, isso não é
   automático mesmo com as rotas já commitadas.
2. **Conferir no painel Next.js** se as 2 capturas automáticas (Hugo e
   Marlon, D30) aparecem corretas na página de cada paciente — números
   batendo com os PDFs em `reports/`.
3. **Testar outros marcos** (D1/D3/D7/D14) — só D30 foi validado até agora.
4. **Decidir sobre agendamento automático** (Agendador de Tarefas do
   Windows) para rodar `sync_runner.py` sem disparo manual.
5. **Testar o botão "🔄 Sincronizar com AirView"** de ponta a ponta no
   Windows do médico, com o protocolo `cpapsync://` já registrado.

### ⚠️ Cuidado importante

Logins automatizados repetidos podem acionar a proteção da ResMed
(captcha, 2FA ou bloqueio temporário da conta). Se o robô falhar no
login várias vezes seguidas, **parar e testar o login manualmente** no
navegador comum antes de insistir.

---

## 15. Painel Next.js — trabalho feito em 16/08/2026

Sessão que implementou o botão de sync (seção 13, corrigindo a lacuna
descrita ali) e mais duas melhorias pedidas para o painel, tudo na branch
`claude/cpap-airview-sync-panel-i2rkav` do `MONITORAMENTO_CPAP_FAPS`:

1. **Painel de pacientes consolidado por gravidade** — a seção "Pacientes
   ativos" do dashboard virou uma tabela ordenada por gravidade
   (crítico → atenção → sem dados → bom), com aderência, IAH residual, fuga
   (mediana/P95) e pressão (mediana/P95) da última captura de cada paciente.
   O status reaproveita o motor de alertas clínicos já existente
   (`avaliarAlertas`/`sincronizarAlertas`) em vez de duplicar limiares.
2. **Botão "🔄 Sincronizar com AirView"** — `<a href="cpapsync://sincronizar">`
   no topo do dashboard, conforme `INTEGRACAO_BOTAO_SYNC.md`, mais um
   indicador "Última sincronização automática: ...".
3. **Editar dados de paciente já cadastrado** — nome, data de início,
   aparelho, máscara e observações agora são editáveis na ficha do
   paciente (antes só categoria/modo ventilatório/pressão prescrita eram).
   Corrigir a `dataInicio` recalcula a data prevista dos marcos ainda
   "pendente"; marcos já revisados/ignorados não são tocados.

Atenção especial (✅ corrigido em 17/08/2026, a pedido do médico): **os
campos `vazamento`/`vazamentoMedio` do modelo de dados têm nomes trocados**
em relação ao que o nome sugere — `vazamento` guarda a **mediana** da fuga e
`vazamentoMedio` guarda o **95º percentil** (ver seção 7 acima e
`pdf_data_extractor.py`, que sempre populou os dois campos corretamente).
O código do Next.js (`TabelaEvolucao.tsx`, `GraficosEvolucao.tsx`,
`CapturaForm.tsx`, `feedbackPaciente.ts`, `exportCsv.ts` e o motor de
alertas em `src/lib/alertas.ts`) rotulava/comparava esses campos como se
fosse o contrário — o alerta de "vazamento elevado" comparava a
**mediana** contra o limiar de 24 L/min pensado para o **P95**, o que
tendia a nunca disparar mesmo com fuga real alta. Todos esses pontos foram
corrigidos (68 testes passando) — os nomes dos campos no Firestore
continuam `vazamento`/`vazamentoMedio` por compatibilidade com dados já
gravados, só a interpretação/rotulagem foi corrigida.

---

## 16. Histórico de Evolução do Pedido

1. Acessar AirView, autenticar, baixar relatórios dos 10 primeiros pacientes.
2. Especificar relatório = "Relatório de adesão ao tratamento" + screenshot + IA.
3. Prompt médico especializado definido (laudo narrativo).
4. Troca de IA: Anthropic Claude → OpenAI GPT-4o.
5. Seleção mudou para os 10 pacientes mais recentes por data de cadastro.
6. Pedido de virar aplicação: cadastro manual + marcos D0/D+3/D+7/D+14/D+21/D+30,
   interface web própria, disparo manual com lembrete.
7. Tentativa de rodar localmente → erro 500 (corrigido: compatibilidade Starlette).
8. Pergunta sobre Vercel → explicado por que não serve (sem navegador/background).
9. Preparação para deploy em nuvem (Railway/Docker) com login e persistência.
10. Pergunta sobre custo do Railway → decisão de ficar local por enquanto.
11. **Descoberta:** já existia um projeto Next.js/Firebase completo
    (`MONITORAMENTO_CPAP_FAPS`) com pacientes, marcos (D1/D3/D7/D14/D30),
    alertas e gráficos.
12. **Pivô final:** descartar o painel Python; ele vira um robô de
    sincronização que alimenta o Next.js via API — arquitetura atual.
