# 🔘 Botão "Sincronizar com AirView" no painel Next.js

> Leve este documento para uma sessão com acesso ao repositório
> **MONITORAMENTO_CPAP_FAPS** — a implementação do botão em si é lá,
> não neste repositório (`FernandoAzevedo-AirView`).

## O que isso resolve

Hoje, para atualizar os dados do AirView, o médico precisa: abrir uma pasta
separada no Explorer, achar `executar_sync.bat` (ou um terminal +
`python sync_runner.py`), e voltar para o painel depois. A ideia é reduzir
isso a **um clique dentro do próprio painel**.

## Como funciona (arquitetura)

Um navegador **não pode** executar um programa no disco por questão de
segurança — não existe JavaScript capaz de rodar `python sync_runner.py`
diretamente. A solução é o Windows registrar um **protocolo customizado**
(`cpapsync://`), do mesmo jeito que `mailto:`, `zoommtg:` ou `vscode:`
funcionam: um link com esse prefixo pede ao sistema operacional para abrir
o programa associado — nesse caso, `executar_sync.bat`, que já existe no
repositório do robô.

```
Painel Next.js (navegador)          Windows                    Robô Python
┌─────────────────────┐         ┌──────────────┐          ┌──────────────────┐
│ <a href="cpapsync:// │  clique │ "Abrir com    │  confirma│ executar_sync.bat │
│   sincronizar">      │────────▶│  CPAP Sync?"  │─────────▶│ → sync_runner.py   │
│  🔄 Sincronizar      │         │  (1ª vez só)  │          │ (nova janela)      │
└─────────────────────┘         └──────────────┘          └──────────────────┘
```

Isso **já está pronto do lado do robô** — ver `registrar_protocolo.bat` /
`registrar_protocolo.ps1` neste repositório. O médico roda esse `.bat` uma
única vez (igual fez para o atalho da área de trabalho) e o protocolo fica
registrado permanentemente no Windows dele.

## O que falta: o botão em si (lado Next.js)

Um link simples, sem nenhuma chamada de API — é só um `<a href>`:

```tsx
<a
  href="cpapsync://sincronizar"
  className="btn-sync-airview"
  title="Abre o robô de sincronização com o AirView no seu computador"
>
  🔄 Sincronizar com AirView
</a>
```

Sugestão de posicionamento: no topo do painel principal (dashboard), perto
do título ou da lista de pacientes — é uma ação frequente, merece
visibilidade.

## Avisos importantes para o médico usar bem

1. **Na primeira vez**, o navegador vai mostrar um alerta de segurança tipo
   *"Este site quer abrir [App]"* — é o comportamento normal e esperado
   para qualquer link de protocolo customizado (o mesmo aconteceria com um
   link `zoommtg://` ou `vscode://`). Pode marcar "sempre permitir" para não
   ver de novo.
2. **Só funciona no computador onde `registrar_protocolo.bat` foi rodado**
   — o robô Python precisa estar instalado ali. Se o painel for acessado de
   outro computador ou celular, o botão simplesmente não vai fazer nada
   (o SO não vai reconhecer o protocolo).
3. **O resultado não volta pro navegador automaticamente** — clicar abre
   uma janela de terminal separada mostrando o progresso (e o RESUMO final
   "X/Y sincronizados"). O painel não sabe, sozinho, quando terminou.

## Melhoria opcional: mostrar a última sincronização no painel

Já que o botão não devolve status pro navegador, uma forma barata de dar
esse feedback **sem precisar de servidor nenhum**: mostrar, em algum canto
do painel, a data/hora da captura mais recente com `origem: "automatica"`
(já existe esse campo em cada documento de `capturas/`). Algo como:

```
Última sincronização automática: hoje às 09:51
```

Isso já responde "funcionou?" sem precisar de nenhuma integração nova —
é só uma query a mais no Firestore (a mais recente `capturas` com
`origem == "automatica"`, entre todos os pacientes).

## Alternativa mais integrada (não escolhida agora)

Existe uma opção mais "ao vivo" — um pequeno servidor Python rodando em
`localhost` que o botão chamaria via `fetch()`, mostrando o progresso e o
resultado direto na tela do painel, sem abrir terminal. Foi conscientemente
deixada de lado por exigir manter esse servidor sempre ativo (mais uma
coisa para lembrar de deixar rodando). Se no futuro isso incomodar, é uma
extensão natural do que já existe aqui — me avise se quiser essa versão.
