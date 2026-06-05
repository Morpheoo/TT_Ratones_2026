# Guía: Base de Datos PostgreSQL en Línea

Esta guía te ayudará a migrar tu base de datos PostgreSQL local a un servicio en la nube para que tu aplicación funcione desde cualquier lugar.

## Opciones de Hosting PostgreSQL Gratuitas/Económicas

### Opción 1: Supabase (Recomendado - Fácil y Gratuito)
- **Plan gratuito**: Sí (500 MB de BD, suficiente para desarrollo)
- **Configuración**: 2 minutos
- **Ventajas**: Panel de administración, backup automático, SSL incluido

### Opción 2: Railway
- **Plan gratuito**: $5 de crédito mensual gratis
- **Configuración**: 3 minutos
- **Ventajas**: Deploy automático, fácil de usar

### Opción 3: Render
- **Plan gratuito**: Sí (BD suspendida después de inactividad)
- **Configuración**: 5 minutos
- **Ventajas**: Integración con Git

### Opción 4: AWS RDS (Profesional)
- **Plan gratuito**: 12 meses con límites
- **Configuración**: 10-15 minutos
- **Ventajas**: Más control, escalable

---

## CONFIGURACIÓN PASO A PASO

## 📘 Opción 1: SUPABASE (Más Fácil - RECOMENDADO)

### 1. Crear Cuenta y Proyecto
1. Ve a https://supabase.com
2. Crea una cuenta (con GitHub o email)
3. Clic en **"New Project"**
4. Configura:
   - **Name**: `tt-ratones-2026` (o el nombre que quieras)
   - **Database Password**: Crea una contraseña segura (GUÁRDALA)
   - **Region**: Elige el más cercano (ej: `South America (São Paulo)`)
5. Clic en **"Create new project"** (tarda ~2 minutos)

### 2. Obtener Credenciales
1. En el dashboard, ve a **Settings** → **Database**
2. Busca la sección **"Connection string"**
3. Selecciona **"URI"** y copia la cadena que se ve así:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxx.supabase.co:5432/postgres
   ```

### 3. Configurar .env
Abre tu archivo `.env` y actualiza:

```env
# Database Configuration (SUPABASE)
POSTGRES_USER=postgres
POSTGRES_PASSWORD=tu_password_de_supabase
POSTGRES_DB=postgres
DB_HOST=db.xxx.supabase.co
DB_PORT=5432

# Email Configuration (mantener igual)
GMAIL_SENDER_EMAIL=tu_correo@gmail.com
GMAIL_APP_PASSWORD=tu_app_password
```

**IMPORTANTE**: Reemplaza:
- `tu_password_de_supabase`: La contraseña que creaste en el paso 1
- `db.xxx.supabase.co`: El host que aparece en tu connection string

### 4. Migrar el Schema
Ejecuta en terminal:

```bash
venv_311\Scripts\activate
python -c "from src.db.connection import get_db_engine; from sqlalchemy import text; engine = get_db_engine(); print('Conexión exitosa!' if engine else 'Error de conexión')"
```

Si la conexión es exitosa, crea las tablas:

1. Ve a Supabase Dashboard → **SQL Editor**
2. Copia el contenido de tu archivo `schema.sql`
3. Pégalo en el editor y ejecuta con **RUN**

O desde Python:
```bash
python -c "from src.db.connection import get_db_engine; from sqlalchemy import text; engine = get_db_engine(); with open('schema.sql', 'r', encoding='utf-8') as f: schema = f.read(); with engine.connect() as conn: conn.execute(text(schema)); conn.commit(); print('Schema creado exitosamente')"
```

### 5. Ejecutar Migraciones
```bash
python src/db/migrations/add_user_profile_fields.py
```

### 6. Crear Usuario Administrador
```bash
python reset_db_admin.py
```

---

## 📗 Opción 2: RAILWAY

### 1. Crear Cuenta y Proyecto
1. Ve a https://railway.app
2. Login con GitHub
3. Clic en **"New Project"** → **"Provision PostgreSQL"**
4. Railway crea automáticamente la base de datos

### 2. Obtener Credenciales
1. Clic en tu servicio PostgreSQL
2. Ve a la pestaña **"Variables"**
3. Copia los valores de:
   - `PGUSER`
   - `PGPASSWORD`
   - `PGHOST`
   - `PGPORT`
   - `PGDATABASE`

### 3. Configurar .env
```env
# Database Configuration (RAILWAY)
POSTGRES_USER=postgres
POSTGRES_PASSWORD=[PGPASSWORD de Railway]
POSTGRES_DB=railway
DB_HOST=[PGHOST de Railway]
DB_PORT=5432

# Email Configuration
GMAIL_SENDER_EMAIL=tu_correo@gmail.com
GMAIL_APP_PASSWORD=tu_app_password
```

### 4. Migrar Schema (igual que Supabase)
Sigue los pasos 4-6 de Supabase arriba.

---

## 📕 Opción 3: RENDER

### 1. Crear Cuenta y Base de Datos
1. Ve a https://render.com
2. Registrate con GitHub o email
3. Dashboard → **"New +"** → **"PostgreSQL"**
4. Configura:
   - **Name**: `tt-ratones-db`
   - **Database**: `ratones_lab`
   - **User**: `admin`
   - **Region**: Elige el más cercano
   - **Plan**: Free
5. Clic en **"Create Database"**

### 2. Obtener Credenciales
En el dashboard de tu BD, busca:
- **Internal Database URL**: Para conexiones desde la misma red de Render
- **External Database URL**: Para conexiones externas (usa esta)

Ejemplo:
```
postgres://admin:xxxx@dpg-xxxxx-a.oregon-postgres.render.com/ratones_lab
```

### 3. Configurar .env
Extrae los datos de la URL:

```env
# Database Configuration (RENDER)
POSTGRES_USER=admin
POSTGRES_PASSWORD=[password de la URL]
POSTGRES_DB=ratones_lab
DB_HOST=dpg-xxxxx-a.oregon-postgres.render.com
DB_PORT=5432

# Email Configuration
GMAIL_SENDER_EMAIL=tu_correo@gmail.com
GMAIL_APP_PASSWORD=tu_app_password
```

### 4. Migrar Schema (igual que Supabase)
Sigue los pasos 4-6 de Supabase arriba.

---

## 🔒 Seguridad Importante

### 1. Archivo .env
**NUNCA** subas tu archivo `.env` a Git. Asegúrate de que está en `.gitignore`:

```bash
# Verificar que .env está ignorado
cat .gitignore | grep ".env"
```

Si no está, añádelo:
```bash
echo .env >> .gitignore
```

### 2. Credenciales Seguras
- Usa contraseñas fuertes (16+ caracteres, mezcla de mayúsculas, minúsculas, números, símbolos)
- No compartas las credenciales por email o chat sin cifrar
- Rota las contraseñas periódicamente

### 3. IP Whitelisting (Opcional pero Recomendado)
Algunos servicios permiten restringir acceso por IP. Configúralo si tu aplicación tiene una IP fija.

---

## ✅ Verificar Conexión

### Script de Prueba
Crea `test_remote_db.py`:

```python
from src.db.connection import get_db_engine
from sqlalchemy import text

def test_connection():
    print("Probando conexión a base de datos remota...")
    engine = get_db_engine()
    
    if not engine:
        print("[ERROR] No se pudo obtener el engine")
        return False
    
    try:
        with engine.connect() as conn:
            # Test 1: Conexión básica
            result = conn.execute(text("SELECT versión()")).scalar()
            print(f"[OK] Conexión exitosa a PostgreSQL:")
            print(f"     Versión: {result}")
            
            # Test 2: Verificar tablas
            tables = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)).fetchall()
            print(f"\n[OK] Tablas encontradas: {len(tables)}")
            for table in tables:
                print(f"     - {table[0]}")
            
            # Test 3: Contar usuarios
            user_count = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
            print(f"\n[OK] Usuarios en BD: {user_count}")
            
            return True
            
    except Exception as e:
        print(f"[ERROR] Error de conexión: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    exit(0 if success else 1)
```

Ejecuta:
```bash
venv_311\Scripts\activate
python test_remote_db.py
```

---

## 🚀 Desplegar la Aplicación

Una vez que la BD esté en línea, también puedes desplegar tu aplicación Streamlit:

### Streamlit Cloud (Gratis y Fácil)
1. Ve a https://share.streamlit.io
2. Conecta tu repositorio de GitHub
3. Configura las **Secrets** (variables de entorno):
   - Ve a **Settings** → **Secrets**
   - Añade tu configuración:
     ```toml
     [database]
     POSTGRES_USER = "postgres"
     POSTGRES_PASSWORD = "tu_password"
     POSTGRES_DB = "postgres"
     DB_HOST = "db.xxx.supabase.co"
     DB_PORT = "5432"
     
     [email]
     GMAIL_SENDER_EMAIL = "tu_correo@gmail.com"
     GMAIL_APP_PASSWORD = "tu_app_password"
     ```
4. La app se despliega automáticamente

---

## 🐛 Troubleshooting

### Error: "connection refused"
- Verifica que `DB_HOST` y `DB_PORT` sean correctos
- Verifica que tu IP no esté bloqueada (whitelist)
- Prueba hacer ping al host

### Error: "authentication failed"
- Verifica `POSTGRES_USER` y `POSTGRES_PASSWORD`
- En Supabase, el usuario siempre es `postgres`
- Asegúrate de no tener espacios en las credenciales

### Error: "timeout"
- Verifica tu conexión a internet
- El firewall podría estar bloqueando el puerto 5432
- Intenta desde otra red

### Error: "database does not exist"
- Verifica el nombre en `POSTGRES_DB`
- Crea la BD manualmente en el panel del servicio

---

## 📊 Monitoreo

### Supabase
- Dashboard → **Database** → **Logs**
- Ver queries en tiempo real
- Métricas de uso

### Railway/Render
- Dashboard del servicio → **Metrics**
- CPU, memoria, conexiones activas

---

## 💰 Límites de Planes Gratuitos

| Servicio | Storage | Conexiones | Límite |
|----------|---------|------------|--------|
| **Supabase** | 500 MB | Ilimitadas | 2 proyectos activos |
| **Railway** | 1 GB | 100 | $5/mes de crédito |
| **Render** | 1 GB | 100 | Se suspende tras 90 días sin uso |

Para este proyecto académico, **Supabase** es la mejor opción.

---

## 🔄 Backup y Recuperación

### Backup Manual
```bash
# Instalar pg_dump si no lo tienes
# En Windows, viene con PostgreSQL

pg_dump -h [DB_HOST] -U [POSTGRES_USER] -d [POSTGRES_DB] -f backup.sql
```

### Restore
```bash
psql -h [DB_HOST] -U [POSTGRES_USER] -d [POSTGRES_DB] -f backup.sql
```

### Backup Automático
- **Supabase**: Backup automático diario
- **Railway**: Backups en plan Pro
- **Render**: Backups en plan Starter

---

## ✅ Checklist Final

- [ ] Base de datos creada en servicio cloud
- [ ] Credenciales guardadas de forma segura
- [ ] Archivo `.env` actualizado con credenciales remotas
- [ ] `.env` está en `.gitignore`
- [ ] Schema ejecutado (`schema.sql`)
- [ ] Migraciones ejecutadas (`add_user_profile_fields.py`)
- [ ] Usuario admin creado (`reset_db_admin.py`)
- [ ] Test de conexión exitoso (`test_remote_db.py`)
- [ ] Aplicación funcionando con BD remota
- [ ] Registro de usuarios probado desde la app

---

## 📞 Soporte

Si tienes problemas:
1. Revisa los logs de la aplicación
2. Verifica el archivo `.env`
3. Ejecuta `test_remote_db.py` para diagnóstico
4. Revisa los logs del servicio de BD (Supabase/Railway/Render)

¡Listo! Tu base de datos ahora es accesible desde cualquier lugar. 🎉
