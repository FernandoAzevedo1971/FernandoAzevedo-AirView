@echo off
REM Abre o painel MONITORAMENTO_CPAP_FAPS no navegador padrao.
REM Pensado para virar um icone na area de trabalho (duplo-clique).
REM
REM O painel roda na nuvem (Vercel) — nao e preciso instalar nada nem
REM subir servidor local. Funciona em qualquer computador com internet.
REM
REM Para desenvolvimento local, rode "npm run dev" na pasta do app e
REM acesse http://localhost:3000 — este atalho nao faz mais isso, porque
REM o uso do dia a dia e o painel publicado.

setlocal

set "URL=https://monitoramento-cpap-ares.vercel.app"

echo ============================================================
echo   Painel MONITORAMENTO_CPAP_FAPS
echo ============================================================
echo.
echo Abrindo %URL%
echo.

start "" "%URL%"

endlocal
