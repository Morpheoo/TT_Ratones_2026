# 📊 QUERIES SQL PARA pgAdmin - COPIA Y PEGA

## Cómo usar estas queries en pgAdmin:

1. Abre pgAdmin: http://localhost:5050
2. Login: admin@ratones.com / admin
3. En el árbol izquierdo, expande tu servidor PostgreSQL
4. Haz click en Tools > Query Tool
5. Copia cualquiera de las queries siguientes y pégala
6. Presiona F5 o haz click en ▶ Execute

---

## 1️⃣ VALIDACIÓN BÁSICA

### Query: Verificar conexión
```sql
SELECT 
    'PostgreSQL Online' as status,
    version() as database_version,
    current_user as connected_user,
    current_database() as database_name;
```

**Resultado esperado:** Información del servidor.

---

### Query: Listar todas las tablas
```sql
SELECT 
    table_name,
    table_type
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
```

**Resultado esperado:** 7 tablas (users, treatments, experiments, roi_configurations, analysis_results, security_audit_log, behavior_edits).

---

## 2️⃣ ANÁLISIS DE ESTRUCTURA

### Query: Ver estructura completa
```sql
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
ORDER BY table_name, ordinal_position;
```

**Resultado esperado:** Lista de todas las columnas con tipos de datos.

---

### Query: Ver PRIMARY KEYS
```sql
SELECT
    constraint_name,
    table_name,
    column_name
FROM information_schema.key_column_usage
WHERE table_schema = 'public'
    AND constraint_name LIKE '%pkey'
ORDER BY table_name;
```

**Resultado esperado:** Todas las claves primarias.

---

### Query: Ver FOREIGN KEYS (relaciones)
```sql
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
```

**Resultado esperado:** Todas las relaciones entre tablas.

---

### Query: Ver UNIQUE constraints
```sql
SELECT
    constraint_name,
    table_name,
    column_name
FROM information_schema.key_column_usage
WHERE table_schema = 'public'
    AND constraint_name LIKE '%_unique' OR constraint_name LIKE '%_key'
    AND constraint_name NOT LIKE '%pkey'
ORDER BY table_name;
```

**Resultado esperado:** Campos únicos de cada tabla.

---

## 3️⃣ CONTEO Y ESTADÍSTICAS

### Query: Contar registros por tabla
```sql
SELECT 
    'users' as table_name, COUNT(*) as rows FROM users
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
ORDER BY table_name;
```

**Resultado esperado:** Número de registros en cada tabla.

---

### Query: Tamaño de cada tabla
```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

**Resultado esperado:** Tamaño en MB/GB de cada tabla.

---

## 4️⃣ EXPLORACIÓN DE DATOS

### Query: Ver usuarios
```sql
SELECT 
    id,
    username,
    email,
    role,
    created_at,
    updated_at
FROM users
ORDER BY created_at DESC
LIMIT 10;
```

**Resultado esperado:** Primeros 10 usuarios registrados.

---

### Query: Ver tratamientos
```sql
SELECT 
    treatment_id,
    name,
    description,
    dosage,
    unit,
    created_at
FROM treatments
ORDER BY created_at DESC
LIMIT 10;
```

**Resultado esperado:** Tratamientos disponibles.

---

### Query: Ver experimentos
```sql
SELECT 
    experiment_id,
    name,
    status,
    start_date,
    end_date,
    description
FROM experiments
ORDER BY start_date DESC
LIMIT 10;
```

**Resultado esperado:** Experimentos registrados.

---

### Query: Ver configuraciones de ROI
```sql
SELECT 
    roi_id,
    experiment_id,
    roi_name,
    roi_type,
    coordinates,
    created_at
FROM roi_configurations
ORDER BY created_at DESC
LIMIT 10;
```

**Resultado esperado:** Configuraciones de Regiones de Interés.

---

### Query: Ver resultados de análisis
```sql
SELECT 
    result_id,
    experiment_id,
    analysis_type,
    confidence_score,
    created_at
FROM analysis_results
ORDER BY created_at DESC
LIMIT 10;
```

**Resultado esperado:** Resultados de análisis.

---

## 5️⃣ CONSULTAS CON JOINS (relaciones)

### Query: Experimentos con usuario y tratamiento
```sql
SELECT 
    e.experiment_id,
    e.name as experiment_name,
    u.username,
    t.name as treatment_name,
    e.status,
    e.start_date,
    e.end_date
FROM experiments e
LEFT JOIN users u ON e.user_id = u.id
LEFT JOIN treatments t ON e.treatment_id = t.id
ORDER BY e.start_date DESC
LIMIT 10;
```

**Resultado esperado:** Vista completa de experimentos con información relacionada.

---

### Query: Experimentos por usuario
```sql
SELECT 
    u.username,
    COUNT(e.experiment_id) as total_experiments,
    COUNT(CASE WHEN e.status = 'completed' THEN 1 END) as completed,
    COUNT(CASE WHEN e.status = 'in_progress' THEN 1 END) as in_progress,
    COUNT(CASE WHEN e.status = 'pending' THEN 1 END) as pending
FROM users u
LEFT JOIN experiments e ON u.id = e.user_id
GROUP BY u.id, u.username
ORDER BY total_experiments DESC;
```

**Resultado esperado:** Estadísticas de experimentos por usuario.

---

### Query: ROI por experimento
```sql
SELECT 
    e.name as experiment_name,
    COUNT(r.roi_id) as total_rois,
    STRING_AGG(DISTINCT r.roi_type, ', ') as roi_types
FROM experiments e
LEFT JOIN roi_configurations r ON e.experiment_id = r.experiment_id
GROUP BY e.experiment_id, e.name
ORDER BY total_rois DESC;
```

**Resultado esperado:** ROIs asociados a cada experimento.

---

## 6️⃣ AUDITORÍA Y SEGURIDAD

### Query: Ver registro de auditoría
```sql
SELECT 
    log_id,
    user_id,
    action,
    entity_type,
    entity_id,
    changes,
    timestamp
FROM security_audit_log
ORDER BY timestamp DESC
LIMIT 20;
```

**Resultado esperado:** Últimas 20 acciones registradas.

---

### Query: Ediciones de comportamiento
```sql
SELECT 
    edit_id,
    analysis_result_id,
    behavior_label,
    confidence_before,
    confidence_after,
    reason,
    edited_by,
    edit_timestamp
FROM behavior_edits
ORDER BY edit_timestamp DESC
LIMIT 10;
```

**Resultado esperado:** Ediciones realizadas por investigadores.

---

## 7️⃣ QUERIES PARA LA DEFENSA ACADÉMICA

### Query: Estado general del sistema
```sql
WITH table_stats AS (
    SELECT 
        'users' as table_name, COUNT(*) as rows FROM users
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
)
SELECT 
    'TT_Ratones_2026' as project,
    (SELECT COUNT(*) FROM table_stats) as tables,
    (SELECT SUM(rows) FROM table_stats) as total_records,
    'Producción' as status,
    CURRENT_TIMESTAMP as timestamp;
```

**Resultado esperado:** Resumen ejecutivo del sistema.

---

### Query: Validar integridad referencial
```sql
-- Verificar que no hay orfandades (registros sin referencia)
SELECT 'Experiments sin usuario' as issue, COUNT(*) as count
FROM experiments WHERE user_id IS NULL
UNION ALL
SELECT 'Experiments sin tratamiento', COUNT(*)
FROM experiments WHERE treatment_id IS NULL
UNION ALL
SELECT 'ROI sin experimento', COUNT(*)
FROM roi_configurations WHERE experiment_id IS NULL
UNION ALL
SELECT 'Resultados sin experimento', COUNT(*)
FROM analysis_results WHERE experiment_id IS NULL;
```

**Resultado esperado:** Debería devolver todos ceros (sin orfandades).

---

## 🎓 PARA TU DEFENSA ACADÉMICA

Ejecuta estas queries en orden durante la presentación:

1. **Validación básica** → Muestra que está online
2. **Listar tablas** → Muestra toda la estructura
3. **Contar registros** → Muestra que hay datos reales
4. **Experimentos con JOIN** → Muestra relaciones funcionando
5. **Estado general** → Resumen para cerrar

**Tiempo estimado:** 3-5 minutos

---

## 💾 GUARDAR RESULTADOS

Para guardar los resultados de una query en CSV:

1. Ejecuta la query
2. Haz click derecho en los resultados
3. Selecciona "Download"
4. Elige formato (CSV, JSON, etc.)

Esto te permite anexar resultados a tu presentación.

---

## 🛠️ EJECUTAR QUERIES DESDE TERMINAL

Si prefieres ejecutar desde PowerShell:

```powershell
# Query simple
docker exec tt_ratones_db psql -U admin -d ratones_lab -c "SELECT COUNT(*) FROM users;"

# Query con formato tabla
docker exec tt_ratones_db psql -U admin -d ratones_lab -c "SELECT id, username, email FROM users LIMIT 5;"

# Query con resultado en archivo
docker exec tt_ratones_db psql -U admin -d ratones_lab -c "SELECT * FROM users;" > resultados.txt
```

---

## ✨ LISTOS

Con estas queries estás cubierto para demostrar:
- ✓ Estructura de BD
- ✓ Relaciones entre tablas
- ✓ Integridad de datos
- ✓ Volumen de información
- ✓ Funcionalidad del sistema

¡Éxito en la defensa! 🚀

