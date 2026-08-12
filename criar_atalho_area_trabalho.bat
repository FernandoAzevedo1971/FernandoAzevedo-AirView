@echo off
REM Cria automaticamente o atalho "Painel CPAP" na area de trabalho,
REM apontando para abrir_painel.bat. Rode este arquivo (duplo-clique)
REM UMA UNICA VEZ — depois disso, use o atalho criado no desktop.

echo ============================================================
echo   Criando atalho na area de trabalho...
echo ============================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0criar_atalho.ps1"

echo.
echo Pronto. Pode fechar esta janela e usar o icone "Painel CPAP" no desktop.
pause
