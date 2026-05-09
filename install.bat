@echo off
setlocal enabledelayedexpansion
title Instalador TT Ratones 2026

echo ============================================================
echo   INSTALADOR TT_Ratones_2026
echo   Crea venv_310, venv_311, sincroniza paths SimBA y valida.
echo ============================================================
echo.

cd /d "%~dp0"

REM ============================================================
REM 1/8 - Verificar Python 3.10 y 3.11
REM ============================================================
echo [1/9] Verificando Python 3.10 y 3.11...
py -3.10 --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] No se encontro Python 3.10.
    echo         Instalalo desde https://www.python.org/downloads/release/python-31011/
    echo         IMPORTANTE: marca "Add Python to PATH" durante la instalacion.
    pause
    exit /b 1
)
py -3.11 --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] No se encontro Python 3.11.
    echo         Instalalo desde https://www.python.org/downloads/release/python-3119/
    echo         IMPORTANTE: marca "Add Python to PATH" durante la instalacion.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('py -3.10 --version') do echo   [OK] %%v
for /f "tokens=*" %%v in ('py -3.11 --version') do echo   [OK] %%v

REM ============================================================
REM 2/8 - Detectar GPU
REM ============================================================
echo.
echo [2/9] Detectando GPU...
set "GPU_TYPE=cpu"
set "TORCH_INDEX=https://download.pytorch.org/whl/cpu"
set "TORCH_PIN=torch==2.7.1+cpu torchvision==0.22.1+cpu"

nvidia-smi >nul 2>&1
if %errorlevel% equ 0 (
    set "GPU_TYPE=cuda"
    set "TORCH_INDEX=https://download.pytorch.org/whl/cu128"
    set "TORCH_PIN=torch==2.7.1+cu128 torchvision==0.22.1+cu128"
    echo   [OK] NVIDIA GPU detectada:
    nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
    echo   Se instalara PyTorch 2.7.1 con CUDA 12.8.
    echo   Compatible con RTX 20/30/40/50 series ^(Turing a Blackwell^).
) else (
    wmic path win32_VideoController get name 2>nul | findstr /I "AMD Radeon" >nul
    if !errorlevel! equ 0 (
        echo   [WARN] AMD GPU detectada.
        echo   PyTorch oficial NO soporta AMD en Windows.
        echo   Se instalara PyTorch CPU-only ^(funcional pero ~5x mas lento^).
        echo   Procesar un video llevara ~25 min en lugar de ~5 min con NVIDIA.
        choice /C YN /M "   Continuar con CPU-only"
        if errorlevel 2 (
            echo Instalacion cancelada.
            pause
            exit /b 1
        )
    ) else (
        echo   [WARN] No se detecto GPU NVIDIA ni AMD.
        echo   Se instalara PyTorch CPU-only ^(funcional pero ~5x mas lento^).
        choice /C YN /M "   Continuar con CPU-only"
        if errorlevel 2 (
            echo Instalacion cancelada.
            pause
            exit /b 1
        )
    )
)

REM ============================================================
REM 3/8 - Crear venv_310
REM ============================================================
echo.
echo [3/9] Creando venv_310 ^(SimBA + DeepLabCut + LSTM^)...
if exist venv_310\Scripts\python.exe (
    echo   [INFO] venv_310 ya existe, reutilizando.
) else (
    py -3.10 -m venv venv_310
    if %errorlevel% neq 0 (
        echo   [ERROR] No se pudo crear venv_310.
        pause
        exit /b 1
    )
    echo   [OK] venv_310 creado.
)

REM ============================================================
REM 4/8 - Crear venv_311
REM ============================================================
echo.
echo [4/9] Creando venv_311 ^(YOLO + B-SOiD + Streamlit^)...
if exist venv_311\Scripts\python.exe (
    echo   [INFO] venv_311 ya existe, reutilizando.
) else (
    py -3.11 -m venv venv_311
    if %errorlevel% neq 0 (
        echo   [ERROR] No se pudo crear venv_311.
        pause
        exit /b 1
    )
    echo   [OK] venv_311 creado.
)

REM ============================================================
REM 5/9 - Instalar venv_310 (~5-10 min)
REM ============================================================
echo.
echo [5/9] Instalando dependencias venv_310 ^(~5-10 min^)...
echo        - DeepLabCut, TensorFlow 2.15, Keras 2, SimBA
echo        - PyTorch CPU-only ^(no se usa GPU en este venv^)
echo.
call venv_310\Scripts\activate.bat
python -m pip install --upgrade --force-reinstall pip setuptools wheel
if %errorlevel% neq 0 (
    echo   [ERROR] No se pudo actualizar pip en venv_310.
    pause
    exit /b 1
)
pip install -r requirements_venv310.txt
if %errorlevel% neq 0 (
    echo   [ERROR] Fallo la instalacion de venv_310.
    echo          Revisar el log de pip arriba.
    pause
    exit /b 1
)
call venv_310\Scripts\deactivate.bat
echo   [OK] venv_310 listo.

REM ============================================================
REM 6/9 - Instalar venv_311 (~10-15 min, descarga PyTorch grande)
REM ============================================================
echo.
echo [6/9] Instalando dependencias venv_311 ^(~10-15 min^)...
echo        - PyTorch !TORCH_PIN!
echo        - YOLO ^(ultralytics^), Streamlit, B-SOiD deps
echo.
call venv_311\Scripts\activate.bat
python -m pip install --upgrade --force-reinstall pip setuptools wheel
if %errorlevel% neq 0 (
    echo   [ERROR] No se pudo actualizar pip en venv_311.
    pause
    exit /b 1
)
echo   [INFO] Instalando PyTorch desde !TORCH_INDEX! ...
pip install !TORCH_PIN! --index-url !TORCH_INDEX!
if %errorlevel% neq 0 (
    echo   [ERROR] Fallo la instalacion de PyTorch.
    echo          Verifica conexion a internet y vuelve a intentar.
    pause
    exit /b 1
)
echo   [INFO] Instalando resto de dependencias ^(streamlit, ultralytics, etc.^)...
pip install -r requirements_venv311.txt
if %errorlevel% neq 0 (
    echo   [ERROR] Fallo la instalacion de venv_311.
    pause
    exit /b 1
)
call venv_311\Scripts\deactivate.bat
echo   [OK] venv_311 listo.

REM ============================================================
REM 7/9 - Verificar Docker Desktop
REM ============================================================
echo.
echo [7/9] Verificando Docker Desktop...
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo   [WARN] Docker Desktop no esta corriendo o no esta instalado.
    echo          Si lo tenes instalado: abrilo y volvelo a chequear.
    echo          Si no lo tenes: descargalo de https://www.docker.com/products/docker-desktop/
    echo          La app Streamlit funciona sin Docker, pero el historial
    echo          de analisis ^(Postgres^) no estara disponible.
) else (
    echo   [OK] Docker Desktop disponible.
)

REM ============================================================
REM 8/9 - Sincronizar paths absolutos en project_config.ini de SimBA
REM ============================================================
echo.
echo [8/9] Sincronizando paths absolutos en SimBA project_config.ini...
echo        ^(SimBA guarda paths absolutos; este paso los reescribe a este equipo.^)
py -3.11 src\scripts\fix_simba_paths.py
if %errorlevel% neq 0 (
    echo   [WARN] fix_simba_paths.py reporto un error.
    echo          Si la extraccion de features falla con
    echo          "SIMBA NOT A DIRECTORY ERROR", correr a mano:
    echo            py -3.11 src\scripts\fix_simba_paths.py
)

REM ============================================================
REM 9/9 - Validacion final
REM ============================================================
echo.
echo [9/9] Validando instalacion completa...
echo.
call venv_311\Scripts\activate.bat
python validar_instalacion.py
set "VALIDA_EXIT=!errorlevel!"
call venv_311\Scripts\deactivate.bat

echo.
echo ============================================================
if !VALIDA_EXIT! equ 0 (
    echo   INSTALACION COMPLETA Y VALIDADA
    echo ============================================================
    echo.
    choice /C YN /M "Crear acceso directo en el Escritorio"
    if !errorlevel! equ 1 (
        call crear_acceso_directo.bat
    )
    echo.
    echo   Para iniciar la aplicacion:
    echo     1. Abre Docker Desktop ^(si vas a usar historial^)
    echo     2. Doble clic al acceso directo del Escritorio,
    echo        o ejecuta launcher.bat desde esta carpeta.
    echo.
) else (
    echo   INSTALACION COMPLETA, PERO LA VALIDACION REPORTO PROBLEMAS
    echo ============================================================
    echo.
    echo   Revisa el reporte de validar_instalacion.py arriba.
    echo   Lo mas comun: faltan modelos pesados ^(.sav, .keras, .pkl, .pt^).
    echo   Copia el contenido del USB sobre la raiz del proyecto.
    echo.
)
pause
