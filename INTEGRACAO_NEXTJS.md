# 🔌 Integração com o MONITORAMENTO_CPAP_FAPS (Next.js)

Este documento contém **tudo que precisa ser adicionado** ao projeto Next.js
para que o robô Python consiga sincronizar dados automaticamente. São
**3 adições** — nenhum arquivo existente é modificado, apenas criado.

---

## 1. Gerar a chave secreta

No terminal (qualquer um, Windows CMD serve):

```cmd
python -c "import secrets; print(secrets.token_hex(32))"
```

Copie o resultado — essa é a `AIRVIEW_SYNC_SECRET`. Ela vai em **dois lugares**:
- No `.env.local` do Next.js (abaixo)
- No `.env` do projeto Python (`AIRVIEW_SYNC_SECRET=...`)

## 2. Descobrir o seu UID do Firebase

1. Acesse o [Firebase Console](https://console.firebase.google.com) → seu projeto
2. **Authentication** → aba **Users**
3. Copie o valor da coluna **User UID** da sua conta (Dr. Fernando)

---

## 3. Adicionar ao `.env.local`

```env
AIRVIEW_SYNC_SECRET=<a chave gerada no passo 1>
AIRVIEW_SYNC_UID=<seu UID do Firebase, passo 2>
```

---

## 4. Adicionar função em `src/lib/firestore/capturas.ts`

Adicione este bloco **ao final** do arquivo existente (não remova nada):

```typescript
// --- Captura automática (usada pelo robô de sincronização AirView) ---

export interface CapturaAutomaticaInput {
  pacienteId: string;
  marcoId?: string | null;
  usoHorasMedia?: number | null;
  diasUso?: number | null;
  percentualUso?: number | null;
  iahResidual?: number | null;
  vazamento?: number | null;
  vazamentoMedio?: number | null;
  periodoDias?: number | null;
  pressaoMediana?: number | null;
  pressaoP95?: number | null;
  dataInicio?: string | null;
  dataFim?: string | null;
  rawJson?: Record<string, unknown> | null;
}

export async function criarCapturaAutomatica(
  uid: string,
  input: CapturaAutomaticaInput
): Promise<Captura> {
  const db = getAdminDb();
  const ref = db
    .collection("users")
    .doc(uid)
    .collection("pacientes")
    .doc(input.pacienteId)
    .collection("capturas")
    .doc();

  const dataCaptura = Timestamp.now();

  const dados = {
    marcoId: input.marcoId ?? null,
    dataCaptura,
    dataInicio: input.dataInicio ?? null,
    dataFim: input.dataFim ?? null,
    usoHorasMedia: input.usoHorasMedia ?? null,
    diasUso: input.diasUso ?? null,
    percentualUso: input.percentualUso ?? null,
    iahResidual: input.iahResidual ?? null,
    vazamento: input.vazamento ?? null,
    vazamentoMedio: input.vazamentoMedio ?? null,
    periodoDias: input.periodoDias ?? null,
    pressaoMediana: input.pressaoMediana ?? null,
    pressaoP95: input.pressaoP95 ?? null,
    origem: "automatica" as const,
    rawJson: input.rawJson ?? null,
    desconfortos: [],
    sintomas: [],
  };

  await ref.set(dados);

  return {
    id: ref.id,
    marcoId: dados.marcoId,
    dataCaptura: dataCaptura.toDate().toISOString(),
    dataInicio: dados.dataInicio,
    dataFim: dados.dataFim,
    usoHorasMedia: dados.usoHorasMedia,
    diasUso: dados.diasUso,
    percentualUso: dados.percentualUso,
    iahResidual: dados.iahResidual,
    vazamento: dados.vazamento,
    vazamentoMedio: dados.vazamentoMedio,
    periodoDias: dados.periodoDias,
    pressaoMediana: dados.pressaoMediana,
    pressaoP95: dados.pressaoP95,
    origem: "automatica",
    desconfortos: [],
    sintomas: [],
  };
}
```

---

## 5. Criar `src/app/api/sync/pendentes/route.ts` (arquivo novo)

Crie a pasta `src/app/api/sync/pendentes/` e o arquivo `route.ts` dentro dela:

```typescript
import { NextResponse } from "next/server";
import { timingSafeEqual } from "crypto";
import { listarPacientesAtivos } from "@/lib/firestore/pacientes";
import { listarMarcosPendentesHoje } from "@/lib/firestore/marcos";

function chaveValida(request: Request): boolean {
  const esperada = process.env.AIRVIEW_SYNC_SECRET;
  const recebida = request.headers.get("x-api-key");
  if (!esperada || !recebida) return false;
  const bufA = Buffer.from(esperada);
  const bufB = Buffer.from(recebida);
  if (bufA.length !== bufB.length) return false;
  return timingSafeEqual(bufA, bufB);
}

export async function GET(request: Request) {
  if (!chaveValida(request)) {
    return NextResponse.json({ error: "Não autorizado." }, { status: 401 });
  }

  const uid = process.env.AIRVIEW_SYNC_UID;
  if (!uid) {
    return NextResponse.json(
      { error: "AIRVIEW_SYNC_UID não configurado no servidor." },
      { status: 500 }
    );
  }

  const pacientes = await listarPacientesAtivos(uid);
  const pendentes = await listarMarcosPendentesHoje(
    uid,
    pacientes.map((p) => ({ id: p.id, nome: p.nome }))
  );

  const pacientesPorId = new Map(pacientes.map((p) => [p.id, p]));

  const marcos = pendentes.map((m) => {
    const paciente = pacientesPorId.get(m.pacienteId);
    return {
      pacienteId: m.pacienteId,
      pacienteNome: m.pacienteNome,
      marcoId: m.marcoId,
      tipo: m.tipo,
      dataPrevista: m.dataPrevista,
      dataInicio: paciente?.dataInicio ?? null,
      aparelho: paciente?.aparelho ?? null,
      mascara: paciente?.mascara ?? null,
    };
  });

  return NextResponse.json({ marcos });
}
```

---

## 6. Criar `src/app/api/captura/importar/route.ts` (arquivo novo)

Crie a pasta `src/app/api/captura/importar/` e o arquivo `route.ts` dentro dela:

```typescript
import { NextResponse } from "next/server";
import { timingSafeEqual } from "crypto";
import { criarCapturaAutomatica } from "@/lib/firestore/capturas";
import { buscarPacientePorId } from "@/lib/firestore/pacientes";

function chaveValida(request: Request): boolean {
  const esperada = process.env.AIRVIEW_SYNC_SECRET;
  const recebida = request.headers.get("x-api-key");
  if (!esperada || !recebida) return false;
  const bufA = Buffer.from(esperada);
  const bufB = Buffer.from(recebida);
  if (bufA.length !== bufB.length) return false;
  return timingSafeEqual(bufA, bufB);
}

const CAMPOS_NUMERICOS = [
  "usoHorasMedia",
  "diasUso",
  "percentualUso",
  "iahResidual",
  "vazamento",
  "vazamentoMedio",
  "periodoDias",
  "pressaoMediana",
  "pressaoP95",
] as const;

export async function POST(request: Request) {
  if (!chaveValida(request)) {
    return NextResponse.json({ error: "Não autorizado." }, { status: 401 });
  }

  const uid = process.env.AIRVIEW_SYNC_UID;
  if (!uid) {
    return NextResponse.json(
      { error: "AIRVIEW_SYNC_UID não configurado no servidor." },
      { status: 500 }
    );
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { error: "Corpo da requisição inválido (JSON malformado)." },
      { status: 400 }
    );
  }

  if (!body.pacienteId) {
    return NextResponse.json({ error: "Campo obrigatório: pacienteId." }, { status: 400 });
  }

  const paciente = await buscarPacientePorId(uid, body.pacienteId);
  if (!paciente) {
    return NextResponse.json({ error: "Paciente não encontrado." }, { status: 404 });
  }

  for (const campo of CAMPOS_NUMERICOS) {
    const valor = body[campo];
    if (valor == null) continue;
    if (typeof valor !== "number" || !Number.isFinite(valor) || valor < 0) {
      return NextResponse.json(
        { error: `Campo ${campo} deve ser um número não negativo.` },
        { status: 400 }
      );
    }
  }

  const captura = await criarCapturaAutomatica(uid, {
    pacienteId: body.pacienteId,
    marcoId: body.marcoId ?? null,
    usoHorasMedia: body.usoHorasMedia ?? null,
    diasUso: body.diasUso ?? null,
    percentualUso: body.percentualUso ?? null,
    iahResidual: body.iahResidual ?? null,
    vazamento: body.vazamento ?? null,
    vazamentoMedio: body.vazamentoMedio ?? null,
    periodoDias: body.periodoDias ?? null,
    pressaoMediana: body.pressaoMediana ?? null,
    pressaoP95: body.pressaoP95 ?? null,
    dataInicio: body.dataInicio ?? null,
    dataFim: body.dataFim ?? null,
    rawJson: body.rawJson ?? null,
  });

  return NextResponse.json({ captura }, { status: 201 });
}
```

---

## 7. Testar a integração

Com o Next.js rodando (`npm run dev`), teste as duas rotas manualmente antes
de rodar o robô Python. No CMD:

```cmd
curl -H "x-api-key: SUA_CHAVE_AQUI" http://localhost:3000/api/sync/pendentes
```

Deve retornar algo como `{"marcos":[...]}`. Se der `401`, a chave não bate
entre `.env` (Python) e `.env.local` (Next.js) — confira os dois.

Se der `{"marcos":[]}` (lista vazia), é porque não há marcos vencendo hoje —
normal se você acabou de cadastrar os pacientes.

---

## Resumo do que muda no Firestore

Nenhuma coleção nova é criada. As capturas automáticas vão para o **mesmo
lugar** das manuais (`users/{uid}/pacientes/{id}/capturas/{capturaId}`),
apenas com `origem: "automatica"` em vez de `"manual"` — e com os campos
`pressaoMediana`/`pressaoP95`/`dataInicio`/`dataFim` preenchidos, que hoje
só a automação consegue popular.
