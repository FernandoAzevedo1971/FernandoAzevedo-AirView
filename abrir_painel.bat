@echo off
REM Sobe o painel MONITORAMENTO_CPAP_FAPS (Next.js) se ainda nao estiver
REM rodando, e abre o navegador nele. Pensado para virar um icone na
REM area de trabalho (duplo-clique).
REM
REM Se a pasta do MONITORAMENTO_CPAP_FAPS estiver em outro lugar no seu
REM computador, ajuste a linha NEXTJS_DIR abaixo.

setlocal

set "NEXTJS_DIR=C:\Users\FERNANDO\Projetos IA Fernando\MONITORAMENTO_CPAP_FAPS"
set "URL=http://localhost:3000"

echo ============================================================
echo   Painel MONITORAMENTO_CPAP_FAPS
echo ============================================================
echo.

REM --- Ja esta rodando? Se sim, so abre o navegador. ---
powershell -NoProfile -Command "try { Invoke-WebRequest -Uri '%URL%' -UseBasicParsing -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel%==0 (
    echo O painel ja estava rodando. Abrindo o navegador...
    start "" "%URL%"
    goto fim
)

if not exist "%NEXTJS_DIR%" (
    echo ERRO: pasta do painel nao encontrada em:
    echo   %NEXTJS_DIR%
    echo.
    echo Edite a linha NEXTJS_DIR no arquivo abrir_painel.bat com o caminho correto.
    pause
    exit /b 1
)

echo Iniciando o painel (isso abre uma segunda janela — pode deixar aberta)...
start "Painel MONITORAMENTO_CPAP_FAPS" cmd /k "cd /d "%NEXTJS_DIR%" && npm.cmd run dev"

echo Aguardando o painel ficar pronto...
:esperar
timeout /t 2 /nobreak >nul
powershell -NoProfile -Command "try { Invoke-WebRequest -Uri '%URL%' -UseBasicParsing -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if not %errorlevel%==0 goto esperar

echo Painel pronto! Abrindo o navegador...
start "" "%URL%"

:fim
endlocal
