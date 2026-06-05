@echo off
setlocal enabledelayedexpansion
title PostgreSQL + pgAdmin - Demo para Defensa Academica

echo.
echo ========================================================
echo   POSTGRESQL + pgADMIN PARA DEFENSA ACADEMICA
echo   TT_Ratones_2026
echo ========================================================
echo.

cd /d "%~dp0"

REM 1. Verificar Docker
echo [1/7] Verificando Docker...
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker no esta corriendo
    echo Abre Docker Desktop manualmente
    pause
    exit /b 1
)
echo OK - Docker daemon activo

REM 2. Levantar contenedores
echo.
echo [2/7] Levantando contenedores...
docker-compose up -d
if %errorlevel% neq 0 (
    echo ERROR: docker-compose fallo
    pause
    exit /b 1
)
echo OK - Contenedores levantados

REM 3. Esperar a que PostgreSQL esté listo
echo.
echo [3/7] Esperando a que PostgreSQL este listo...
timeout /t 3 /nobreak >nul
:WAIT_PG
docker exec tt_ratones_db pg_isready -U admin >nul 2>&1
if %errorlevel% neq 0 (
    echo ... esperando...
    timeout /t 2 /nobreak >nul
    goto WAIT_PG
)
echo OK - PostgreSQL listo

REM 4. Verificar tablas
echo.
echo [4/7] Verificando tablas...
docker exec tt_ratones_db psql -U admin -d ratones_lab -c "\dt" >nul 2>&1
if %errorlevel% neq 0 (
    echo ADVERTENCIA: No se pueden ver las tablas
    echo Ejecuta: docker logs tt_ratones_db
) else (
    echo OK - Tablas detectadas
)

REM 5. Mostrar contenedores
echo.
echo [5/7] Estado de contenedores:
docker-compose ps
echo.

REM 6. Query de prueba
echo [6/7] Ejecutando query de prueba...
echo.
docker exec tt_ratones_db psql -U admin -d ratones_lab -c "SELECT 'Sistema operativo y funcional' as status, COUNT(*) as usuarios FROM users;" 2>nul
echo.

REM 7. Abrir pgAdmin
echo [7/7] Abriendo pgAdmin en navegador...
timeout /t 2 /nobreak >nul
start http://localhost:5050

echo.
echo ========================================================
echo   LISTO PARA LA DEFENSA ACADEMICA
echo ========================================================
echo.
echo Credentials para pgAdmin:
echo   Email: admin@ratones.com
echo   Password: admin
echo.
echo Para registrar PostgreSQL en pgAdmin:
echo   Host: db
echo   Port: 5432
echo   User: admin
echo   Password: admin_secure_password
echo.
echo Para ejecutar queries:
echo   1. En pgAdmin, abre Tools ^> Query Tool
echo   2. O ejecuta desde PowerShell:
echo      docker exec tt_ratones_db psql -U admin -d ratones_lab -c "TU_QUERY"
echo.
pause
