@echo off
setlocal enabledelayedexpansion
title Launcher TT Ratones 2026

echo ========================================================
echo       SISTEMA DE ASISTENCIA PARA EPM - TT 2026
echo ========================================================
echo.

REM *** Cambiar al directorio del .bat PRIMERO ***
cd /d "%~dp0"

REM *** Verificar que los archivos necesarios existen ***
if not exist "run_app.py" (
    echo [ERROR] No se encontro run_app.py
    echo [INFO] Asegurate que estás en el directorio correcto
    pause
    exit /b 1
)

if not exist "start_services.py" (
    echo [ERROR] No se encontro start_services.py
    echo [INFO] Por favor descarga los archivos más recientes del proyecto
    pause
    exit /b 1
)

echo [INFO] Verificando Docker Desktop...
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] Docker no esta corriendo.
    echo [INFO] Iniciando Docker Desktop...

    if exist "C:\Program Files\Docker\Docker\Docker Desktop.exe" (
        start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    ) else (
        echo [ERROR] No se encontro Docker Desktop en la ubicacion esperada.
        echo [INFO] Por favor abre Docker Desktop manualmente y vuelve a ejecutar este script.
        pause
        exit /b 1
    )

    echo [INFO] Esperando a que Docker daemon inicie (max 60 segundos)...
    set "count=0"
    :WAIT_DOCKER
    timeout /t 3 /nobreak >nul
    docker info >nul 2>&1
    if %errorlevel% neq 0 (
        set /a count+=1
        if !count! geq 20 (
            echo [ERROR] Docker tardo demasiado en iniciar. Intenta nuevamente.
            pause
            exit /b 1
        )
        goto WAIT_DOCKER
    )
    echo [OK] Docker daemon esta listo.
) else (
    echo [OK] Docker ya estaba corriendo.
)

echo.
echo ========================================================
echo [INFO] Iniciando servicios con run_app.py...
echo [INFO] Esto levantara docker-compose y esperara a PostgreSQL
echo ========================================================
echo.

REM *** Buscar venv_311 y activar si existe ***
if exist "venv_311\Scripts\activate.bat" (
    echo [INFO] Activando entorno venv_311...
    call venv_311\Scripts\activate.bat
) else (
    echo [WARN] No se encontro venv_311, usando python del sistema.
    echo [INFO] Se recomienda crear un entorno virtual para nuevas instalaciones.
)

echo.
echo [INFO] Comprobando dependencias de Python (Streamlit, SQLAlchemy, etc)...
python -c "import streamlit" >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] Faltan librerias basicas de Python. 
    echo [INFO] Iniciando instalacion automatica desde requirements_venv311.txt...
    pip install -r requirements_venv311.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Ocurrio un error al instalar las dependencias.
        echo [INFO] Es posible que necesites ejecutar "pip install -r requirements_venv311.txt" como administrador.
        pause
    ) else (
        echo [OK] Dependencias instaladas correctamente.
    )
) else (
    echo [OK] Dependencias de Python listas.
)

echo.
echo [INFO] Ejecutando run_app.py (esto abre Streamlit)...
echo [INFO] Se abrira en tu navegador predeterminado.
echo [INFO] NO CIERRE ESTA VENTANA mientras uses la aplicacion.
echo.

python run_app.py

pause
