@echo off
setlocal
title Diagnostico - TT Ratones 2026
cd /d "%~dp0"

set "APP_PYTHON=venv_311\Scripts\python.exe"
if exist "runtime\py311\python.exe" set "APP_PYTHON=runtime\py311\python.exe"

if not exist "%APP_PYTHON%" (
    echo [ERROR] No se encontro el runtime de la aplicacion.
    pause
    exit /b 1
)

"%APP_PYTHON%" validar_instalacion.py
echo.
pause
