@echo off
REM Registra o protocolo cpapsync:// no Windows (rode uma unica vez), para
REM que um link como <a href="cpapsync://sincronizar"> no painel Next.js
REM abra e rode a sincronizacao com o AirView automaticamente -- sem
REM precisar deixar nenhum servidor rodando em segundo plano.

echo ============================================================
echo   Registrando o protocolo cpapsync://
echo ============================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0registrar_protocolo.ps1"

echo.
pause
