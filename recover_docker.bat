@echo off
setlocal enabledelayedexpansion
title Docker Recovery Tool

echo ========================================================
echo       DOCKER RECOVERY TOOL
echo ========================================================
echo.

cd /d "%~dp0"

echo [INFO] Ejecutando recovery_docker.py...
echo.

python recovery_docker.py

echo.
pause
