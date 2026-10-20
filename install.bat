@echo off
setlocal enabledelayedexpansion

echo ======================================================================
echo    Instalador de PowerBI MCP Server y Skills para Claude
echo ======================================================================
echo.

where uv >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [*] Usando uv como gestor de paquetes...
    echo [*] Sincronizando dependencias del proyecto...
    uv sync
    if %ERRORLEVEL% NEQ 0 (
        echo [!] Error al sincronizar dependencias con uv.
        pause
        exit /b 1
    )
    echo.
    echo [*] Configurando Servidor MCP y Skills para Claude...
    uv run python scripts/install.py
) else (
    where python >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        echo [*] uv no encontrado, usando python del sistema...
        python scripts/install.py
    ) else (
        echo [ERROR] Ni 'uv' ni 'python' se encuentran instalados en el PATH.
        echo Por favor instala uv (https://astral.sh/uv) o Python 3.11+.
        pause
        exit /b 1
    )
)

echo.
echo ======================================================================
echo    Instalacion finalizada. Ya puedes abrir o reiniciar Claude.
echo ======================================================================
pause
