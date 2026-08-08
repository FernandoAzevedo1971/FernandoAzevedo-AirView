@echo off
REM Atalho para rodar a sincronizacao AirView -> MONITORAMENTO_CPAP_FAPS
REM Duplo-clique neste arquivo para executar.

cd /d "%~dp0"

echo ============================================
echo   AirView Sync
echo ============================================
echo.

where python >nul 2>nul
if %errorlevel%==0 (
    set PY_CMD=python
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        set PY_CMD=py
    ) else (
        echo Python nao encontrado. Instale em https://www.python.org/downloads/
        pause >nul
        exit /b 1
    )
)

%PY_CMD% -m sync_runner

echo.
echo ============================================
echo   Concluido. Pressione qualquer tecla para fechar.
echo ============================================
pause >nul
