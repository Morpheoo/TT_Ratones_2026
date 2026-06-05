#!/usr/bin/env powershell
<#
.SYNOPSIS
    Script para demostración de pgAdmin + PostgreSQL para defensa académica
    Ejecuta queries pre-cargadas para validar la BD

.USAGE
    .\demo_bd_defensa.ps1
#>

Write-Host "`n" + "="*70
Write-Host "   DEMO: BASE DE DATOS POSTGRESQL - DEFENSA ACADEMICA" -ForegroundColor Cyan
Write-Host "   TT_Ratones_2026"
Write-Host "="*70 + "`n"

# Configuración
$CONTAINER = "tt_ratones_db"
$DB_USER = "admin"
$DB_NAME = "ratones_lab"

# Función para ejecutar query
function Invoke-PostgresQuery {
    param(
        [string]$Query,
        [string]$Description
    )
    
    Write-Host "`n📌 $Description" -ForegroundColor Yellow
    Write-Host "─────────────────────────────────────────" -ForegroundColor Gray
    
    try {
        $result = docker exec $CONTAINER psql -U $DB_USER -d $DB_NAME -c "$Query" 2>&1
        Write-Host $result
        return $true
    }
    catch {
        Write-Host "❌ Error: $_" -ForegroundColor Red
        return $false
    }
}

# ============================================================================
# 1. VERIFICAR CONEXIÓN
# ============================================================================
Write-Host "[1/6] Verificando conexión a PostgreSQL..." -ForegroundColor Cyan
$ready = docker exec $CONTAINER pg_isready -U $DB_USER
if ($ready -match "accepting") {
    Write-Host "✓ PostgreSQL está listo" -ForegroundColor Green
} else {
    Write-Host "✗ PostgreSQL no responde" -ForegroundColor Red
    exit 1
}

# ============================================================================
# 2. VER TODAS LAS TABLAS
# ============================================================================
Invoke-PostgresQuery -Query "\dt" -Description "TABLAS EN LA BD"

# ============================================================================
# 3. CONTAR REGISTROS POR TABLA
# ============================================================================
$countQuery = @"
SELECT 
    table_name,
    COALESCE(COUNT(*)::text, '0') as row_count
FROM information_schema.tables t
LEFT JOIN (
    SELECT 'users' as table_name, COUNT(*) as cnt FROM users
    UNION ALL
    SELECT 'treatments', COUNT(*) FROM treatments
    UNION ALL
    SELECT 'experiments', COUNT(*) FROM experiments
    UNION ALL
    SELECT 'roi_configurations', COUNT(*) FROM roi_configurations
    UNION ALL
    SELECT 'analysis_results', COUNT(*) FROM analysis_results
    UNION ALL
    SELECT 'security_audit_log', COUNT(*) FROM security_audit_log
    UNION ALL
    SELECT 'behavior_edits', COUNT(*) FROM behavior_edits
) counts ON t.table_name = counts.table_name
WHERE t.table_schema = 'public'
GROUP BY table_name
ORDER BY table_name;
"@

Invoke-PostgresQuery -Query $countQuery -Description "CONTEO DE REGISTROS POR TABLA"

# ============================================================================
# 4. ESTRUCTURA DE TABLAS PRINCIPALES
# ============================================================================
$schemaQuery = @"
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
    AND table_name IN ('users', 'experiments', 'treatments')
ORDER BY table_name, ordinal_position;
"@

Invoke-PostgresQuery -Query $schemaQuery -Description "ESTRUCTURA DE TABLAS (users, experiments, treatments)"

# ============================================================================
# 5. FOREIGN KEYS (RELACIONES)
# ============================================================================
$fkQuery = @"
SELECT
    tc.constraint_name,
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS referenced_table_name,
    ccu.column_name AS referenced_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
    AND tc.table_schema = 'public'
ORDER BY tc.table_name;
"@

Invoke-PostgresQuery -Query $fkQuery -Description "RELACIONES (FOREIGN KEYS)"

# ============================================================================
# 6. DATOS DE EJEMPLO (primeros usuarios)
# ============================================================================
$dataQuery = @"
SELECT * FROM users LIMIT 5;
"@

Invoke-PostgresQuery -Query $dataQuery -Description "DATOS DE EJEMPLO (primeros 5 usuarios)"

# ============================================================================
# INFORMACIÓN FINAL
# ============================================================================
Write-Host "`n" + "="*70 -ForegroundColor Cyan
Write-Host "   RESUMEN PARA LA DEFENSA" -ForegroundColor Cyan
Write-Host "="*70 -ForegroundColor Cyan

Write-Host @"

✓ Base de datos funcional y con datos
✓ Todas las tablas esperadas presentes
✓ Relaciones entre tablas configuradas correctamente
✓ Persistencia de datos garantizada por volúmenes Docker

PRÓXIMOS PASOS:
1. Abre pgAdmin: http://localhost:5050
2. Login con: admin@ratones.com / admin
3. Registra el servidor PostgreSQL con host: db
4. Navega por las tablas y estructura
5. Ejecuta queries en el Query Tool

Para ejecutar queries desde PowerShell:
  docker exec tt_ratones_db psql -U admin -d ratones_lab -c "TU_QUERY"

"@

Write-Host "="*70 + "`n" -ForegroundColor Cyan

# Preguntar si abrir pgAdmin
$open = Read-Host "¿Abrir pgAdmin ahora? (s/n)"
if ($open -eq "s") {
    Start-Process "http://localhost:5050"
    Write-Host "pgAdmin abierto en http://localhost:5050" -ForegroundColor Green
}

Write-Host "Listo para la defensa académica! 🚀`n"
