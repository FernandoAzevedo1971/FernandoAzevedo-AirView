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

## 7. Extração Estruturada com GPT-4o

Diferente da v1 (que gerava só uma carta narrativa), agora o GPT-4o Vision
é usado com **`response_format: json_object`** para extrair valores numéricos
determinísticos:

```json
{
  "usoHorasMedia": 5.5,
  "diasUso": 12,
  "percentualUso": 85.7,
  "iahResidual": 2.3,
  "vazamento": 18.0,
  "vazamentoMedio": 12.0,
  "pressaoMediana": 9.5,
  "pressaoP95": 11.2,
  "periodoDias": 14
}
```

Campos não identificados no relatório vêm como `null` — nunca inventados.

**O laudo narrativo (carta ao paciente) continua disponível** como recurso
opcional em `gpt_analyzer.analyze_report()`, usando o mesmo prompt médico
elaborado anteriormente (ver seção 9 da v1, preservada abaixo). Ele é salvo
localmente, não é enviado ao Next.js.

---

## 8. Estrutura de Arquivos (Python)

```
FernandoAzevedo-AirView/
├── sync_runner.py         # ★ Orquestrador principal
├── sync_client.py          # ★ Cliente HTTP da API do Next.js
├── gpt_analyzer.py          # ★ GPT-4o: extração estruturada + laudo opcional
│
├── browser.py               # Ciclo de vida do Chromium (Playwright)
├── login.py                 # Autenticação no AirView
├── patient_search.py        # Localiza paciente pelo nome
├── report_requester.py      # Solicita e baixa o PDF de adesão
├── pdf_screenshot.py         # PDF → PNG (300 DPI)
├── pdf_utils.py               # Utilitários de leitura de PDF (auxiliar)
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

### ✅ Concluído e VALIDADO com dados reais

**Lado Next.js (MONITORAMENTO_CPAP_FAPS) — 100% pronto e testado:**
- `criarCapturaAutomatica()` adicionada em `src/lib/firestore/capturas.ts`
- `GET /api/sync/pendentes` — testada, retorna os pacientes reais (Hugo
  Peixoto Pacheco Junior e Marlon Meik Manso Monica, ambos com marco D30)
- `POST /api/captura/importar` — testada, grava captura real no Firestore
- `.env.local` configurado (`AIRVIEW_SYNC_SECRET`, `AIRVIEW_SYNC_UID`)

**Lado Python — ambiente pronto e login/busca 100% funcionando:**
- Clonado em `C:\Users\FERNANDO\Projetos IA Fernando\FernandoAzevedo-AirView`
- Dependências instaladas (trocou `pymupdf` → `pypdfium2`, não compila
  no Python 3.14 do usuário)
- **Login funciona de ponta a ponta** — Okta em 2 etapas (usuário →
  Avançar → senha), banner de cookies dispensado automaticamente
- **Busca de paciente funciona de ponta a ponta** — acha Hugo e Marlon
  corretamente mesmo com nomes invertidos no AirView ("Sobrenome, Nome")

### 🔧 Geração do relatório — muito perto de funcionar, várias rodadas de calibração

O fluxo real descoberto (via prints do usuário) é: botão **"Criar
relatório"** → modal com `<select>` **"Tipo de relatório"** → escolher
**"Relatório de adesão ao tratamento e terapia"** (opção combinada, traz
uso/adesão E pressão/vazamento/IAH) → período "Período de tempo fixo"
(dias + data final) → botão **"Continuar"** → PDF abre na mesma aba
(SEM disparar evento de download do navegador).

Bugs encontrados e corrigidos nesta sessão (nesta ordem):
1. Tecla Escape fechava o modal inteiro (removida)
2. Confundia campos de "fundo" (controlam o gráfico) com os do modal —
   corrigido restringindo tudo a um Locator escopado ao modal
3. Esperava até 60s por um evento de download que nunca ocorre (o PDF
   abre por navegação de página, não por download) — corrigido com
   verificação rápida em 3 frentes (download/nova aba/navegação)
4. Período calculado como 31 dias em vez de 30 (sobrava um `+1`)
5. Crash `'Page' object has no attribute 'page'` quando o modal não é
   reconhecido por nenhuma classe/role conhecida (aconteceu de verdade
   em produção) — corrigido passando `page` explicitamente
6. Botão "Continuar" não encontrado por NENHUM seletor `button:has-text`
   — hipótese: não é uma tag `<button>` (pode ser `<a>`, `<input>`, etc).
   Ampliada a busca para texto puro (`text="Continuar"`, funciona em
   qualquer tag) + estratégia de escopo do modal via XPath (ancestral
   comum do título + `<select>`, não depende de nomes de classe)

**Todos os fixes foram testados contra simuladores locais** que
reproduzem os problemas exatos vistos em produção — mas o fix do bug #6
(o mais recente) **ainda não foi validado contra o AirView real**.

### ▶️ PRÓXIMO PASSO AO RETOMAR

Com o Next.js rodando (`npm.cmd run dev`), no terminal da pasta Python:

```cmd
git pull
python sync_runner.py
```

**O que verificar:**
1. O texto do terminal — se completou sem erro, deve aparecer no RESUMO
   final "2/2 marcos sincronizados com sucesso"
2. `dir reports` — deve ter 2 PDFs (Hugo e Marlon)
3. **Enviar o PDF para análise** — ainda não vimos a página 2 do
   relatório completa (tem os dados de IAH/vazamento/pressão), precisa
   dela para validar/ajustar a extração do GPT-4o

Se ainda der erro, colar o texto completo do terminal — cada rodada
anterior revelou exatamente o próximo obstáculo.

### ⏳ Ainda pendente (depois que o PDF baixar com sucesso)

1. Ver a página 2 real do PDF e confirmar que `gpt_analyzer.py` extrai
   os campos certos (usoHorasMedia, iahResidual, vazamento, pressão)
2. Rodar o fluxo completo end-to-end pelo menos uma vez: PDF → PNG →
   GPT-4o → captura gravada no Firestore com `origem: "automatica"`
3. Conferir no painel Next.js se a captura aparece corretamente na
   página do paciente
4. Decidir se/quando agendar a execução automática (Agendador de
   Tarefas do Windows) para rodar sem precisar disparar manualmente

### ⚠️ Cuidado importante

Logins automatizados repetidos podem acionar a proteção da ResMed
(captcha, 2FA ou bloqueio temporário da conta). Se o robô falhar no
login várias vezes seguidas, **parar e testar o login manualmente** no
navegador comum antes de insistir.

---

## 14. Histórico de Evolução do Pedido

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
