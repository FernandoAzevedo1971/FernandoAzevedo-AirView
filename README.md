# AirView Sync — Robô de Sincronização

Robô Python que **automatiza a coleta de dados do ResMed AirView** e alimenta o
painel **MONITORAMENTO_CPAP_FAPS** (Next.js + Firebase), do Dr. Fernando Azevedo.

> ⚠️ Este projeto **não tem tela própria**. O painel, cadastro de pacientes,
> marcos de acompanhamento e alertas já existem no MONITORAMENTO_CPAP_FAPS.
> Este robô só entra no AirView, lê os relatórios e preenche os dados lá.

---

## O que ele faz

```
1. Pergunta ao MONITORAMENTO_CPAP_FAPS: "quais marcos vencem hoje?"
   (D1, D3, D7, D14 ou D30 — já cadastrados no Next.js)

2. Faz login no AirView (uma vez, reaproveitado para todos os marcos)

3. Para cada marco pendente:
   a. Localiza o paciente pelo nome
   b. Baixa o "Relatório de adesão ao tratamento"
      (período: data de início da terapia → data prevista do marco)
   c. Extrai um screenshot da 1ª página (guardado para conferência manual)
   d. Lê uso, IAH, vazamento, pressão direto do TEXTO do PDF (regex —
      sem IA, sem custo)
   e. Grava os números no Firestore via API do Next.js
      (aparece no painel como Captura de origem "automática")

4. Mostra um resumo no final — sucesso ou erro por paciente
```

O médico continua revisando cada marco normalmente no painel Next.js —
a única diferença é que os campos já chegam **preenchidos**.

---

## Pré-requisitos

- **Python 3.11+**
- Conta ativa no **AirView ResMed** (sem 2FA)
- Chave da **API OpenAI** (opcional — só para o laudo narrativo, veja
  abaixo) → https://platform.openai.com/api-keys
- O projeto **MONITORAMENTO_CPAP_FAPS** já rodando (local ou em produção),
  com as 2 rotas novas de sincronização adicionadas — veja
  [`INTEGRACAO_NEXTJS.md`](INTEGRACAO_NEXTJS.md).

---

## Instalação

```bash
git clone https://github.com/FernandoAzevedo1971/FernandoAzevedo-AirView.git
cd FernandoAzevedo-AirView

pip install -r requirements.txt
python -m playwright install chromium

cp .env.example .env
```

Edite o `.env`:
```env
AIRVIEW_USER=fazevedopneumosono
AIRVIEW_PASS=Sf271003**

NEXTJS_API_URL=http://localhost:3000
AIRVIEW_SYNC_SECRET=<a mesma chave configurada no Next.js>

# Opcional — só necessária se você usar o laudo narrativo (gpt_analyzer.py)
OPENAI_API_KEY=sk-...
```

> 💡 A `AIRVIEW_SYNC_SECRET` deve ser **idêntica** à variável de mesmo nome
> configurada no `.env.local` do MONITORAMENTO_CPAP_FAPS — é ela que autoriza
> este robô a gravar dados. Veja como gerar em
> [`INTEGRACAO_NEXTJS.md`](INTEGRACAO_NEXTJS.md).

---

## Executar

Com o MONITORAMENTO_CPAP_FAPS rodando (`npm run dev`, por exemplo), em outro
terminal:

```bash
python sync_runner.py
```

No Windows, também pode usar:
```cmd
executar_sync.bat
```

Pode ser executado sob demanda ou agendado (Agendador de Tarefas do Windows,
uma vez por dia) para manter o painel sempre atualizado sozinho.

---

## Ícone único na área de trabalho (abrir o painel)

`abrir_painel.bat` sobe o Next.js (se ainda não estiver rodando) e abre o
navegador direto no painel — um duplo-clique substitui abrir terminal,
navegar até a pasta e digitar `npm run dev` manualmente.

**Para virar um ícone na área de trabalho:**
1. No Explorer, clique com o botão direito em `abrir_painel.bat`
2. **Enviar para → Área de trabalho (criar atalho)**
3. (Opcional) Renomeie o atalho para algo como "Painel CPAP"

> 💡 Se a pasta do MONITORAMENTO_CPAP_FAPS não estiver em
> `C:\Users\FERNANDO\Projetos IA Fernando\MONITORAMENTO_CPAP_FAPS`, edite a
> linha `NEXTJS_DIR` no início do `abrir_painel.bat`.

Esse atalho só abre o painel — a sincronização com o AirView
(`sync_runner.py` / `executar_sync.bat`) continua sendo disparada à parte,
quando você quiser atualizar os dados.

---

## Estrutura do Projeto

```
├── sync_runner.py       # Orquestrador principal (login → dados → envio)
├── sync_client.py        # Fala com a API do Next.js (GET/POST)
├── pdf_data_extractor.py  # Extração estruturada via regex no texto do PDF (grátis)
├── gpt_analyzer.py        # GPT-4o Vision: laudo narrativo opcional (não usado no fluxo principal)
├── browser.py             # Ciclo de vida do Chromium (Playwright)
├── login.py               # Autenticação no AirView
├── patient_search.py      # Localiza paciente pelo nome
├── report_requester.py    # Solicita e baixa o PDF de adesão
├── pdf_screenshot.py       # Converte 1ª página do PDF em PNG (guardado para conferência)
├── pdf_utils.py            # Utilitários de leitura de PDF (extract_pdf_text)
├── dump_pdf_text.py         # Ferramenta de diagnóstico: imprime o texto bruto do PDF
├── patients.py              # Estrutura de dados do paciente (PatientEntry)
├── config.py                # Seletores CSS/XPath e constantes
├── utils.py                  # Retry, logging, helpers
├── requirements.txt
├── executar_sync.bat         # Atalho: roda a sincronização (Windows)
├── abrir_painel.bat           # Atalho: sobe o Next.js e abre o navegador (Windows)
├── INTEGRACAO_NEXTJS.md      # Código das rotas a adicionar no Next.js
└── ESPECIFICACAO_PROJETO.md  # Planejamento completo (histórico + arquitetura)
```

---

## Laudo narrativo (recurso opcional)

Além da extração estruturada (que alimenta o painel), o robô também sabe
gerar uma **carta ao paciente** em português, assinada pelo Dr. Fernando
Azevedo, com interpretação clínica e sugestões de ajuste de terapia. Esse
recurso é opcional e fica salvo localmente — não é enviado ao Next.js.

Veja `gpt_analyzer.analyze_report()` para usá-lo separadamente, se desejar.

---

## Troubleshooting

**"NEXTJS_API_URL não está definida"** → confira o `.env`.

**"401 Unauthorized" ao enviar captura** → a `AIRVIEW_SYNC_SECRET` no `.env`
do Python não bate com a do Next.js. Confirme que são idênticas nos dois lados.

**Paciente não encontrado no AirView** → o nome cadastrado no Next.js deve
ser **exatamente igual** ao nome no AirView (mesma grafia).

**Login falhou** → verifique `AIRVIEW_USER`/`AIRVIEW_PASS`; confirme que a
conta não tem 2FA ativado.
