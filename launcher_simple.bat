@echo off
setlocal enabledelayedexpansion
title Launcher TT Ratones 2026

echo ========================================================
echo       SISTEMA DE ASISTENCIA PARA EPM - TT 2026
echo ========================================================
echo.

cd /d "%~dp0"

echo [INFO] Verificando Docker Desktop...
docker info >nul 2>&1
if errorlevel 1 (
    echo [WARN] Docker no esta corriendo.
    echo [INFO] Por favor abre Docker Desktop manualmente.
    pause
    exit /b 1
)

echo [OK] Docker esta corriendo.
echo.

if exist "venv_311\Scripts\activate.bat" (
    echo [INFO] Activando entorno venv_311...
    call venv_311\Scripts\activate.bat
) else (
    echo [WARN] No se encontro venv_311
)

echo.
echo [INFO] Ejecutando aplicacion Streamlit...
echo [INFO] Se abrira en tu navegador predeterminado.
echo [INFO] NO CIERRES ESTA VENTANA mientras uses la aplicacion.
echo.

python run_app.py

pause
