@echo off
setlocal enabledelayedexpansion
title Test Suite - TT Ratones 2026

echo ========================================================
echo       TEST SUITE - Sistema de Verificación
echo ========================================================
echo.

cd /d "%~dp0"

echo Selecciona el tipo de test que deseas ejecutar:
echo.
echo   1) Quick Diagnostic (10 segundos - rápido)
echo   2) Full Test Suite (1-2 minutos - completo)
echo   3) Interactive Test (30-60 seg - flujo simulado)
echo   4) Run All Tests in Sequence
echo.

set /p choice="Opcion (1-4): "

if "%choice%"=="1" (
    echo.
    echo Ejecutando: python quick_diag.py
    echo.
    python quick_diag.py
) else if "%choice%"=="2" (
    echo.
    echo Ejecutando: python test_docker_setup.py
    echo.
    python test_docker_setup.py
) else if "%choice%"=="3" (
    echo.
    echo Ejecutando: python test_interactive.py
    echo.
    python test_interactive.py
) else if "%choice%"=="4" (
    echo.
    echo Ejecutando ALL TESTS...
    echo.
    
    echo ========================================================
    echo Running: quick_diag.py (10 segundos)
    echo ========================================================
    python quick_diag.py
    pause
    
    echo ========================================================
    echo Running: test_docker_setup.py (1-2 minutos)
    echo ========================================================
    python test_docker_setup.py
    pause
    
    echo ========================================================
    echo Running: test_interactive.py (30-60 segundos)
    echo ========================================================
    python test_interactive.py
    pause
    
) else (
    echo Opcion inválida
    pause
    exit /b 1
)

echo.
echo ========================================================
echo Test completado!
echo.
echo Proximo paso:
echo   - Si todos los tests pasaron: launcher.bat
echo   - Si hay problemas: python test_docker_setup.py
echo.
pause
