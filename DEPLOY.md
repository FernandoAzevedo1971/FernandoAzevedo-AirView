# 🚀 Deploy na Nuvem (acessar de qualquer lugar)

Guia para publicar a aplicação em um servidor na nuvem com **deploy automático a
partir do GitHub**. Recomendamos o **Railway** (mais simples para este caso).

> ⚠️ **Antes de começar, leia os avisos importantes no final deste documento.**

---

## Por que Railway (e não Vercel)?

Esta aplicação abre um **navegador real** (Chromium) para acessar o AirView, roda
**tarefas longas** (30–60s por relatório) e faz **trabalho em segundo plano**. O
Vercel não suporta nada disso. O Railway roda um **contêiner sempre ligado**, que
suporta tudo — por isso funciona.

O projeto já vem pronto com:
- `Dockerfile` — imagem com Python + Playwright + Chromium
- `railway.json` — configuração de build
- **Login obrigatório** (usuário/senha) para proteger os dados
- **Persistência** configurável via volume (variável `APP_DATA_DIR`)

---

## Passo a passo — Railway

### 1. Criar conta e projeto
1. Acesse https://railway.app e faça login **com o GitHub**.
2. Clique em **New Project** → **Deploy from GitHub repo**.
3. Autorize e escolha o repositório **`FernandoAzevedo-AirView`**.
4. O Railway detecta o `Dockerfile` automaticamente e inicia o build.

### 2. Configurar as variáveis de ambiente
No projeto → aba **Variables** → adicione:

| Variável | Valor | Para que serve |
|---|---|---|
| `AIRVIEW_USER` | `fazevedopneumosono` | usuário do AirView |
| `AIRVIEW_PASS` | `sua_senha` | senha do AirView |
| `OPENAI_API_KEY` | `sk-...` | análise com GPT-4o |
| `APP_USER` | `escolha_um_usuario` | **login da aplicação** |
| `APP_PASSWORD` | `escolha_uma_senha_forte` | **senha da aplicação** |
| `APP_DATA_DIR` | `/data` | pasta de dados persistente |

> 🔐 **`APP_USER` e `APP_PASSWORD` são a sua proteção.** Sem elas, qualquer pessoa
> com o link acessa os dados dos pacientes. **Sempre defina uma senha forte.**

### 3. Adicionar um volume (persistência)
Sem isso, o banco de pacientes e os relatórios se perdem a cada novo deploy.
1. No serviço → aba **Settings** (ou **Volumes**) → **Add Volume**.
2. Mount path: **`/data`** (o mesmo valor de `APP_DATA_DIR`).

### 4. Publicar e acessar
1. O Railway faz o build e sobe a aplicação.
2. Em **Settings → Networking → Generate Domain**, gere uma URL pública
   (ex.: `https://airview-faps.up.railway.app`).
3. Abra a URL no navegador (celular, outro PC…). Vai pedir o **login**
   (`APP_USER` / `APP_PASSWORD`).

### 5. Deploy automático
Pronto! A partir de agora, **toda alteração enviada ao GitHub** (branch `main`)
dispara um novo deploy automaticamente. Sincronia total.

---

## Alternativa: Render

Mesma ideia. Em https://render.com → **New → Web Service** → conecte o GitHub →
selecione **Docker** como ambiente. Configure as mesmas variáveis, adicione um
**Disk** montado em `/data`, e gere a URL.

---

## ⚠️ Avisos importantes (leia com atenção)

### 1. Dados de pacientes na internet (LGPD)
A aplicação passará a guardar **nomes e dados clínicos de pacientes** num servidor
na nuvem. Você é responsável por esses dados (LGPD). Mitigações já aplicadas:
- **Login obrigatório** na aplicação.
- **HTTPS** automático (Railway/Render).
- Dados isolados no seu volume privado.

Ainda assim, avalie se prefere manter tudo **local** (mais privado). Para uso
remoto, use **senha forte** e **não compartilhe o link**.

### 2. O AirView pode bloquear o acesso
O login no AirView virá de um **servidor em datacenter** (IP diferente do seu
consultório, às vezes em outro país). O ResMed pode:
- pedir **verificação em 2 etapas (2FA)** ou **captcha**;
- **bloquear temporariamente** a conta por "acesso suspeito".

Se o botão **"Gerar agora"** falhar no login, provavelmente é isso. Nesse caso, as
saídas são: rodar **localmente** (do seu consultório), ou avaliar a **API oficial**
do ResMed (ResMed Data Exchange).

### 3. Custo
- **Railway**: ~US$ 5/mês (plano Hobby) + uso.
- **Render**: tem plano gratuito, mas o serviço "dorme" quando ocioso e tem
  limites — o build com Chromium pode estourar o plano free; o pago resolve.

---

## Resumo rápido

```
1. Railway → New Project → Deploy from GitHub → FernandoAzevedo-AirView
2. Variables: AIRVIEW_USER, AIRVIEW_PASS, OPENAI_API_KEY, APP_USER, APP_PASSWORD, APP_DATA_DIR=/data
3. Add Volume em /data
4. Generate Domain → abrir a URL → logar com APP_USER/APP_PASSWORD
5. Deploy automático a cada push no GitHub
```
