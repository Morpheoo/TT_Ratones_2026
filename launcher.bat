@echo off
setlocal
title Launcher TT Ratones 2026

echo ========================================================
echo       SISTEMA DE ASISTENCIA PARA EPM - TT 2026
echo ========================================================
echo.

echo [INFO] Verificando estado de Docker...
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] Docker no esta corriendo.
    echo [INFO] Iniciando Docker Desktop...
    
    if exist "C:\Program Files\Docker\Docker\Docker Desktop.exe" (
        start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    ) else (
        echo [ERROR] No se encontro Docker Desktop en la ruta estandar "C:\Program Files\Docker\Docker\Docker Desktop.exe".
        echo [ERROR] Por favor inicie Docker Desktop manualmente.
        pause
    )
    
    echo [INFO] Esperando a que Docker inicie (esto puede tardar unos minutos)...
    echo [INFO] Por favor espere hasta que el icono de la ballena este verde.
    
    :WAIT_DOCKER
    timeout /t 5 /nobreak >nul
    docker info >nul 2>&1
    if %errorlevel% neq 0 (
        goto WAIT_DOCKER
    )
    echo [OK] Docker esta listo!
) else (
    echo [OK] Docker ya esta corriendo.
)

echo.
echo [INFO] Levantando servicios de Base de Datos...
docker-compose up -d
if %errorlevel% neq 0 (
    echo [ERROR] Fallo al ejecutar docker-compose up. Verifique su instalacion.
    pause
    exit /b 1
)

echo.
echo [INFO] Iniciando Aplicacion Streamlit...
echo [INFO] Se abrira en su navegador predeterminado.
echo [INFO] NO CIERRE ESTA VENTANA NEGRA mientras use la aplicacion.
echo.

cd /d "%~dp0"
if exist "venv_311\Scripts\activate.bat" (
    call venv_311\Scripts\activate.bat
) else (
    echo [WARN] No se encontro venv_311, intentando usar python del sistema...
)

streamlit run Home.py

pause
