@echo off
setlocal enabledelayedexpansion
title Launcher TT Ratones 2026

echo ========================================================
echo       SISTEMA DE ASISTENCIA PARA EPM - TT 2026
echo ========================================================
echo.

cd /d "%~dp0"

REM ============================================================
REM  Verificar archivos necesarios
REM ============================================================
if not exist "run_app.py" (
    echo [ERROR] No se encontro run_app.py
    echo [INFO]  Asegurate que estas en el directorio correcto del proyecto.
    pause
    exit /b 1
)
if not exist "start_services.py" (
    echo [ERROR] No se encontro start_services.py
    echo [INFO]  Por favor descarga los archivos mas recientes del proyecto.
    pause
    exit /b 1
)

REM ============================================================
REM  Docker Desktop (sin labels dentro de bloques if)
REM ============================================================
echo [INFO] Verificando Docker Desktop...
docker info >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK]   Docker ya estaba corriendo.
    goto :DOCKER_READY
)

echo [WARN] Docker no esta corriendo.
echo [INFO] Iniciando Docker Desktop...

if not exist "C:\Program Files\Docker\Docker\Docker Desktop.exe" (
    echo [ERROR] No se encontro Docker Desktop en la ubicacion esperada.
    echo [INFO]  Por favor abrelo manualmente y vuelve a ejecutar este script.
    pause
    exit /b 1
)
start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"

echo [INFO] Esperando a que Docker daemon inicie (max 60 segundos)...
set "count=0"

:WAIT_DOCKER
timeout /t 3 /nobreak >nul
docker info >nul 2>&1
if %errorlevel% equ 0 goto :DOCKER_READY
set /a count+=1
if !count! geq 20 (
    echo [ERROR] Docker tardo demasiado en iniciar. Intenta nuevamente.
    pause
    exit /b 1
)
goto :WAIT_DOCKER

:DOCKER_READY
echo [OK]   Docker daemon listo.

REM ============================================================
REM  Activar venv_311
REM ============================================================
echo.
echo ========================================================
echo [INFO] Activando entorno venv_311 y verificando dependencias...
echo ========================================================
echo.

if not exist "venv_311\Scripts\activate.bat" (
    echo [ERROR] No se encontro venv_311. Corre install.bat primero.
    pause
    exit /b 1
)
call venv_311\Scripts\activate.bat

REM ============================================================
REM  Verificar streamlit instalado
REM ============================================================
python -c "import streamlit" >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK]   Streamlit y dependencias presentes.
    goto :LAUNCH_APP
)

echo [WARN] Faltan librerias basicas en venv_311.
echo [INFO] Instalando desde requirements_venv311.txt...
pip install -r requirements_venv311.txt
if %errorlevel% neq 0 (
    echo [ERROR] Fallo la instalacion de dependencias.
    echo [INFO]  Volve a correr install.bat o revisa tu conexion a internet.
    pause
    exit /b 1
)
echo [OK]   Dependencias instaladas correctamente.

REM ============================================================
REM  Lanzar la app
REM ============================================================
:LAUNCH_APP
echo.
echo ========================================================
echo [INFO] Iniciando run_app.py (Streamlit + Postgres)
echo [INFO] Se abrira en tu navegador predeterminado.
echo [INFO] NO CIERRES esta ventana mientras uses la aplicacion.
echo ========================================================
echo.

python run_app.py

pause
