@echo off
setlocal
title Acceso directo TT Ratones 2026

echo ============================================================
echo   Crear acceso directo en el Escritorio
echo ============================================================
echo.

cd /d "%~dp0"

REM Verificar que existan los archivos necesarios
if not exist "launcher.bat" (
    echo [ERROR] No se encontro launcher.bat en %cd%
    echo         Corre este script desde la raiz del proyecto.
    pause
    exit /b 1
)

set "ICON_PATH=%~dp0logo_ria.ico"
if not exist "%ICON_PATH%" (
    echo [WARN] No se encontro logo_ria.ico, el acceso directo
    echo        usara el icono por defecto de Windows.
    set "ICON_PATH="
)

REM Crear el .lnk usando PowerShell (respeta idioma del Escritorio)
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ws = New-Object -ComObject WScript.Shell;" ^
  "$desk = [Environment]::GetFolderPath('Desktop');" ^
  "$sc = $ws.CreateShortcut((Join-Path $desk 'TT Ratones 2026.lnk'));" ^
  "$sc.TargetPath = '%~dp0launcher.bat';" ^
  "$sc.WorkingDirectory = '%~dp0';" ^
  "$sc.Description = 'Sistema de deteccion EPM - TT Ratones 2026';" ^
  "if ('%ICON_PATH%' -ne '') { $sc.IconLocation = '%ICON_PATH%' };" ^
  "$sc.Save();" ^
  "Write-Host '[OK] Acceso directo creado en' $desk"

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] No se pudo crear el acceso directo.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Listo. Doble clic al icono "TT Ratones 2026" en el
echo   escritorio para iniciar la aplicacion.
echo ============================================================
echo.
pause
