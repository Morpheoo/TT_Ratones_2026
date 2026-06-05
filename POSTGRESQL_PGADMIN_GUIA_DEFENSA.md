# 🗄️ GUÍA COMPLETA: PostgreSQL + pgAdmin en Docker
## Para Presentación Académica - TT_Ratones_2026

---

## 📋 TABLA DE CONTENIDOS
1. [Comandos para levantar servicios](#1-levantar-servicios)
2. [Acceder a pgAdmin](#2-acceder-a-pgadmin)
3. [Registrar PostgreSQL en pgAdmin](#3-registrar-servidor)
4. [Verificar tablas y estructura](#4-verificar-tablas)
5. [Ejecutar queries](#5-ejecutar-queries)
6. [Revisar logs](#6-revisar-logs)
7. [Persistencia de datos](#7-persistencia)
8. [Para la defensa académica](#8-defensa-académica)

---

## 1️⃣ LEVANTAR SERVICIOS

### Paso 1.1: Verificar que Docker está corriendo

**Windows PowerShell:**
```powershell
docker info
```

**Respuesta esperada:** (Información de Docker sin errores)

Si falla, abre Docker Desktop manualmente desde Windows Start Menu.

### Paso 1.2: Levantar contenedores con docker-compose

**Windows PowerShell:**
```powershell
# Ir al directorio del proyecto
cd C:\ruta\a\tu\proyecto\TT_Ratones_2026

# Levantar servicios
docker-compose up -d

# Verificar que están corriendo
docker-compose ps
```

**Respuesta esperada:**
```
NAME                  COMMAND                  SERVICE    STATUS      PORTS
pgadmin_ratones       /entrypoint.sh           pgadmin    Up 1 min    0.0.0.0:5050->80/tcp
tt_ratones_db        docker-entrypoint.s…    db         Up 1 min    0.0.0.0:5432->5432/tcp
```

### Paso 1.3: Esperar a que PostgreSQL esté listo

```powershell
# Verificar que PostgreSQL responde
docker exec tt_ratones_db pg_isready -U admin
```

**Respuesta esperada:**
```
accepting connections
```

Si dice "rejecting connections", espera 5-10 segundos más y reinenta.

---

## 2️⃣ ACCEDER A pgAdmin

### Paso 2.1: Abrir pgAdmin en el navegador

1. **Abre tu navegador** (Chrome, Edge, Firefox, etc.)
2. **Ve a:** `http://localhost:5050`
3. **Se abrirá la pantalla de login de pgAdmin**

### Paso 2.2: Credenciales para pgAdmin

Usa las credenciales del archivo `.env`:

```
Email: admin@ratones.com       (PGADMIN_DEFAULT_EMAIL)
Contraseña: admin              (PGADMIN_DEFAULT_PASSWORD)
```

Haz clic en **Login**

### Paso 2.3: Interfaz de pgAdmin

Verás la interfaz con:
- **Panel izquierdo:** Árbol de servidores y bases de datos
- **Panel central:** Detalles y editor SQL
- **Panel superior:** Opciones y herramientas

**Nota:** En la primera carga, pgAdmin crea sus propias tablas. Es normal.

---

## 3️⃣ REGISTRAR SERVIDOR POSTGRESQL EN pgADMIN

### Paso 3.1: Crear nueva conexión

1. **En el panel izquierdo**, haz clic derecho en **Servers**
2. Selecciona **Register** → **Server...**

**Alternativa:** Búscalo en el menú:
- Menu principal → **Object** → **Register** → **Server**

### Paso 3.2: Configurar la conexión (Pestaña "General")

En la ventana "Register Server", completa:

**Campo: Name**
```
tt_ratones_db
```
(Nombre para identificar el servidor en pgAdmin)

Haz clic en la pestaña **Connection**

### Paso 3.3: Datos de Conexión (Pestaña "Connection")

⚠️ **IMPORTANTE:** El host depende de dónde ejecutes pgAdmin:

#### Si pgAdmin está EN Docker (como en tu caso):
```
Host name/address: db
Port: 5432
Maintenance database: postgres
Username: admin
Password: admin_secure_password
```

#### Si usas DBeaver o herramienta externa:
```
Host name/address: localhost  (o tu_ip_maquina)
Port: 5432
Maintenance database: postgres
Username: admin
Password: admin_secure_password
```

**¿Por qué "db" vs "localhost"?**
- pgAdmin está en Docker → Usa el nombre del servicio (`db`)
- DBeaver está en tu PC → Usa `localhost` (porque Docker expone 5432)

### Paso 3.4: Guardar la conexión

Haz clic en **Save**

**Resultado esperado:** Aparece `tt_ratones_db` en el árbol izquierdo bajo "Servers"

---

## 4️⃣ VERIFICAR TABLAS Y ESTRUCTURA

### Paso 4.1: Expandir el servidor

1. Haz clic en el **►** al lado de `tt_ratones_db`
2. Verás: Databases
3. Expande **Databases**
4. Verás: `ratones_lab` (o tu DB_NAME del .env)

### Paso 4.2: Ver tablas

1. Expande `ratones_lab` → **Schemas** → **public**
2. Expande **Tables**

Aquí deberías ver las tablas:
- ✓ users
- ✓ treatments
- ✓ experiments
- ✓ roi_configurations
- ✓ analysis_results
- ✓ security_audit_log
- ✓ behavior_edits

**Si NO ves tablas:**
→ Ir a sección "6. Revisar logs"

### Paso 4.3: Ver estructura de una tabla (Ejemplo: users)

1. Click derecho en **users**
2. Selecciona **Properties**
3. Verás:
   - **Columns:** id, username, email, password_hash, role, created_at, etc.
   - **Constraints:** 
     - PRIMARY KEY: id
     - UNIQUE: email, username
     - NOT NULL: username, email, etc.

### Paso 4.4: Ver datos en la tabla

1. Click derecho en **users**
2. Selecciona **View/Edit Data** → **All Rows**
3. Se abre una ventana mostrando todos los registros

**Columnas visibles:**
- id (Primary Key) 🔑
- username
- email
- password_hash (hasheada)
- role (admin, researcher, etc.)
- created_at (timestamp)

### Paso 4.5: Ver relaciones (Foreign Keys)

1. Click derecho en **experiments**
2. Selecciona **Properties**
3. Ve a la pestaña **Constraints**

Verás las Foreign Keys:
```
FK: user_id → users.id
FK: treatment_id → treatments.id
```

Esto muestra cómo las tablas están relacionadas.

---

## 5️⃣ EJECUTAR QUERIES SQL

### Paso 5.1: Abrir el editor SQL

1. En la barra superior, haz clic en **Tools**
2. Selecciona **Query Tool**

O presiona: **Alt + Shift + Q**

### Paso 5.2: Query simple para validar la BD

Copia y pega esta query:

```sql
-- Verificar conexión y estructura
SELECT 
    table_name,
    COALESCE(COUNT(*)::text, 'N/A') as row_count
FROM information_schema.tables
WHERE table_schema = 'public'
GROUP BY table_name
ORDER BY table_name;
```

**Qué hace:** Muestra todas las tablas y cuántas filas tienen.

**Cómo ejecutar:**
1. Pega la query en el editor
2. Haz clic en ▶ **Execute** (o presiona F5)

**Resultado esperado:**
```
table_name              | row_count
------------------------+----------
users                   | 5
treatments              | 12
experiments             | 3
roi_configurations      | 3
analysis_results        | 45
security_audit_log      | 128
behavior_edits          | 7
```

### Paso 5.3: Query para ver estructura completa

```sql
-- Ver todas las columnas y tipos de datos
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
ORDER BY table_name, ordinal_position;
```

**Resultado:** Lista completa de todas las columnas de tu BD.

### Paso 5.4: Query para relaciones (Foreign Keys)

```sql
-- Ver todas las Foreign Keys
SELECT 
    constraint_name,
    table_name,
    column_name,
    referenced_table_name,
    referenced_column_name
FROM (
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
) AS fks
ORDER BY table_name;
```

**Resultado:** Todas las relaciones entre tablas.

### Paso 5.5: Query para datos de ejemplo (experiments)

```sql
-- Ver experimentos con usuario y tratamiento
SELECT 
    e.experiment_id,
    e.name,
    u.username,
    t.name as treatment_name,
    e.start_date,
    e.status
FROM experiments e
JOIN users u ON e.user_id = u.id
JOIN treatments t ON e.treatment_id = t.id
ORDER BY e.start_date DESC
LIMIT 10;
```

**Resultado:** Experimentos con información relacionada de otras tablas.

---

## 6️⃣ REVISAR LOGS SI ALGO FALLA

### Paso 6.1: Logs de PostgreSQL

**Windows PowerShell:**
```powershell
# Ver logs del contenedor de BD
docker logs tt_ratones_db

# Ver logs en tiempo real
docker logs -f tt_ratones_db
```

**Qué buscar:**
```
✓ "database system is ready to accept connections"
✗ "could not create shared memory segment"
✗ "FATAL: password authentication failed"
```

### Paso 6.2: Logs de pgAdmin

```powershell
docker logs pgadmin_ratones
```

**Qué buscar:**
```
✓ "pgAdmin 4 started on..."
✗ "Connection refused"
```

### Paso 6.3: Entrar al contenedor para debuguear

```powershell
# Entrar a la shell del contenedor PostgreSQL
docker exec -it tt_ratones_db bash

# Una vez dentro, conectar a psql
psql -U admin -d ratones_lab

# Ver todas las tablas
\dt

# Ver usuarios
SELECT * FROM users;

# Salir
\q
exit
```

### Paso 6.4: Verificar conexión de red

```powershell
# Desde tu PC, verificar que el puerto 5432 responde
Test-NetConnection -ComputerName localhost -Port 5432

# Resultado esperado: TcpTestSucceeded: True
```

---

## 7️⃣ PERSISTENCIA DE DATOS

### Paso 7.1: Verificar volumen

```powershell
# Listar volúmenes
docker volume ls

# Inspeccionar el volumen
docker volume inspect tt_ratones_2026_postgres_data
```

**Respuesta esperada:**
```json
{
    "Name": "tt_ratones_2026_postgres_data",
    "Mountpoint": "C:\\ProgramData\\Docker\\volumes\\...",
    "Labels": {},
    "Scope": "local"
}
```

### Paso 7.2: Probar persistencia

```powershell
# 1. Ver datos actuales
docker exec tt_ratones_db psql -U admin -d ratones_lab -c "SELECT COUNT(*) FROM users;"

# 2. Detener contenedores
docker-compose down

# 3. Verificar que el volumen existe (persiste)
docker volume ls | findstr postgres_data

# 4. Levantar nuevamente
docker-compose up -d

# 5. Verificar que los datos siguen ahí
docker exec tt_ratones_db psql -U admin -d ratones_lab -c "SELECT COUNT(*) FROM users;"
```

**Resultado esperado:** El número de usuarios es el MISMO antes y después. ✓

### Paso 7.3: Para la defensa académica

Puedes decir:

> "Los datos persisten en un volumen de Docker (`postgres_data`) que está separado del contenedor. Esto significa que aunque reiniciemos los contenedores, la base de datos conserva toda la información. Esto es esencial para un sistema en producción."

---

## 8️⃣ PARA LA DEFENSA ACADÉMICA

### 8.1: ¿Por qué usar Docker + pgAdmin?

**Respuesta técnica:**

```
┌─────────────────────────────────────────────────────────────┐
│  ARQUITECTURA DEL SISTEMA - TT_Ratones_2026                │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐                                             │
│  │  Streamlit   │ ← Frontend (interfaz web)                 │
│  │  (Home.py)   │                                             │
│  └──────┬───────┘                                             │
│         │                                                     │
│         ↓ SQL Queries                                         │
│         │                                                     │
│  ┌──────────────┐        ┌──────────────┐                   │
│  │ PostgreSQL   │ ←──→   │   pgAdmin    │                   │
│  │   (Docker)   │        │   (Docker)   │                   │
│  └──────────────┘        └──────────────┘                   │
│         ↓                        ↓                            │
│    Datos persistidos      Visualización                       │
│    en volumen             de la BD                            │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### 8.2: Argumentos para la presentación

**1. Reproducibilidad:**
```
"Docker garantiza que el sistema funcione igual en cualquier 
máquina (Windows, Linux, Mac) sin configuración adicional."
```

**2. Escalabilidad:**
```
"Los contenedores pueden escalarse fácilmente. Si necesitamos 
más recursos, basta actualizar las configuraciones de Docker."
```

**3. Profesionalismo:**
```
"Docker es el estándar en la industria. Usar contenedores 
demuestra que el proyecto sigue buenas prácticas de DevOps."
```

**4. Persistencia de datos:**
```
"Los volúmenes de Docker garantizan que los datos persisten 
aunque reiniciemos los contenedores. Esto es fundamental 
para un sistema de producción."
```

**5. Monitoreo y debugging:**
```
"pgAdmin permite visualizar la BD de forma intuitiva, 
ejecutar queries, y verificar la integridad de los datos 
en tiempo real."
```

### 8.3: Slide para la presentación

Copia este texto para tu diapositiva:

---

**ARQUITECTURA DE LA BASE DE DATOS**

📦 **Containerización con Docker**
- PostgreSQL 15 en contenedor aislado
- Volumen persistente para datos
- Red interna entre contenedores (db ↔ pgAdmin ↔ Streamlit)

🔍 **Visualización con pgAdmin**
- Interfaz gráfica para administración
- Ejecución de queries SQL
- Monitoreo en tiempo real

✓ **Ventajas**
- Reproducibilidad: mismo sistema en cualquier máquina
- Escalabilidad: fácil aumentar recursos
- Profesionalismo: sigue estándares de DevOps
- Persistencia: volúmenes mantienen datos seguros

---

### 8.4: Demo en vivo para la defensa

**Paso a paso (5 minutos):**

1. **Mostrar docker-compose.yml**
   ```powershell
   cat docker-compose.yml
   ```
   "Aquí definimos 2 servicios: PostgreSQL y pgAdmin"

2. **Mostrar contenedores corriendo**
   ```powershell
   docker-compose ps
   ```
   "Ambos contenedores están activos"

3. **Abrir pgAdmin en navegador**
   - Ir a `http://localhost:5050`
   - Login
   - "Este es el servidor PostgreSQL conectado"

4. **Expandir tablas**
   - Mostrar `users`, `experiments`, `treatments`
   - "Aquí puedo ver la estructura completa"

5. **Ejecutar query**
   ```sql
   SELECT COUNT(*) as total_users FROM users;
   ```
   "Validamos que la base está funcional"

6. **Mostrar persistencia**
   - Bajar contenedores: `docker-compose down`
   - Levantarlos: `docker-compose up -d`
   - Query nuevamente: datos siguen ahí
   - "Los datos persisten. La BD es confiable"

**Tiempo total:** ~5-7 minutos

---

## 9️⃣ CHECKLIST PARA LA DEFENSA

Antes de la presentación, ejecuta esto para verificar todo:

```powershell
# 1. Verificar Docker corriendo
docker info

# 2. Levantar servicios
docker-compose up -d

# 3. Verificar contenedores
docker-compose ps

# 4. Esperar a PostgreSQL listo
Start-Sleep -Seconds 5

# 5. Test de conexión
docker exec tt_ratones_db pg_isready -U admin

# 6. Ver tablas
docker exec tt_ratones_db psql -U admin -d ratones_lab -c "\dt"

# 7. Contar registros
docker exec tt_ratones_db psql -U admin -d ratones_lab -c "SELECT 'users' as table_name, COUNT(*) as rows FROM users UNION ALL SELECT 'experiments', COUNT(*) FROM experiments;"

# 8. Abrir pgAdmin
Start-Process http://localhost:5050
```

Si todo sale bien, estás listo para la defensa. ✓

---

## 🆘 TROUBLESHOOTING RÁPIDO

| Problema | Solución |
|----------|----------|
| `Connection refused` | Docker no está corriendo. Abre Docker Desktop |
| Tablas no aparecen | Ejecuta `docker logs tt_ratones_db` para ver errores |
| pgAdmin no abre | Espera 10-15 segundos a que pgAdmin inicie |
| Contraseña incorrecta | Revisa el archivo `.env` |
| Puerto 5432 en uso | `docker-compose down` primero |
| Volumen no persiste | El volumen debe estar en docker-compose.yml |

---

## 📞 COMANDOS CLAVE RÁPIDOS

**Levantar todo:**
```powershell
docker-compose up -d
```

**Bajar todo:**
```powershell
docker-compose down
```

**Ver estado:**
```powershell
docker-compose ps
```

**Logs en vivo:**
```powershell
docker logs -f tt_ratones_db
```

**Ejecutar query desde CLI:**
```powershell
docker exec tt_ratones_db psql -U admin -d ratones_lab -c "SELECT * FROM users LIMIT 5;"
```

**Entrar al contenedor:**
```powershell
docker exec -it tt_ratones_db bash
```

---

## 🎓 LISTO PARA LA DEFENSA

Tienes todo lo que necesitas. Recuerda:

1. ✅ Levantar servicios con `docker-compose up -d`
2. ✅ Acceder a pgAdmin: `http://localhost:5050`
3. ✅ Mostrar tablas y estructura
4. ✅ Ejecutar queries para validar
5. ✅ Explicar la arquitectura y ventajas

¡Éxito en tu presentación! 🚀

