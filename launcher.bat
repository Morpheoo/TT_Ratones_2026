@echo off
setlocal
title TT Ratones 2026
cd /d "%~dp0"

echo ========================================================
echo        SISTEMA DE ASISTENCIA PARA EPM - TT 2026
echo ========================================================
echo.

if not exist "run_app.py" (
    echo [ERROR] La instalacion esta incompleta: falta run_app.py.
    if not defined TT_SILENT pause
    exit /b 1
)

set "APP_PYTHON=venv_311\Scripts\python.exe"
if exist "runtime\py311\python.exe" set "APP_PYTHON=runtime\py311\python.exe"

if not exist "%APP_PYTHON%" (
    echo [ERROR] No se encontro el runtime de la aplicacion.
    echo [INFO]  Reinstala TT Ratones 2026 con el instalador oficial.
    if not defined TT_SILENT pause
    exit /b 1
)

"%APP_PYTHON%" -c "import streamlit, sqlalchemy" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] El runtime esta incompleto o danado.
    echo [INFO]  Reinstala la aplicacion. El launcher no descargara paquetes.
    if not defined TT_SILENT pause
    exit /b 1
)

echo [INFO] Iniciando la aplicacion local...
echo [INFO] Puedes cerrar esta ventana cuando termines de usarla.
echo.
"%APP_PYTHON%" run_app.py

if errorlevel 1 (
    echo.
    echo [ERROR] La aplicacion termino con un error.
    echo [INFO]  Ejecuta validar_instalacion.bat para obtener un diagnostico.
    if not defined TT_SILENT pause
)
