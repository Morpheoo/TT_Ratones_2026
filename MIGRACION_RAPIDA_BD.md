# 🚀 Migración Rápida a Base de Datos en Línea

## Resumen de 5 Minutos (Usando Supabase)

### 1️⃣ Crear Base de Datos (2 min)
1. Ve a https://supabase.com → **Sign Up**
2. **New Project** → Nombre: `tt-ratones-2026`
3. Crea una **contraseña segura** (guárdala)
4. Región: **South America (São Paulo)** o la más cercana
5. Espera ~2 minutos mientras se crea

### 2️⃣ Obtener Credenciales (30 seg)
1. Dashboard → **Settings** → **Database**
2. Busca **Connection string** → **URI**
3. Copia: `postgresql://postgres:[PASSWORD]@db.xxx.supabase.co:5432/postgres`
4. Extrae:
   - Host: `db.xxx.supabase.co`
   - Password: `[PASSWORD]`

### 3️⃣ Actualizar .env (1 min)
Edita tu archivo `.env`:

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=tu_password_aqui
POSTGRES_DB=postgres
DB_HOST=db.xxx.supabase.co
DB_PORT=5432

GMAIL_SENDER_EMAIL=tu_correo@gmail.com
GMAIL_APP_PASSWORD=tu_app_password
```

### 4️⃣ Probar Conexión (30 seg)
```bash
venv_311\Scripts\activate
python test_remote_db.py
```

Debes ver: `RESULTADO: Conexión EXITOSA ✓`

### 5️⃣ Configurar Base de Datos (1 min)
```bash
python setup_remote_db.py
python src/db/migrations/add_user_profile_fields.py
python reset_db_admin.py
```

### 6️⃣ ¡Listo! Probar Aplicación
```bash
streamlit run Home.py
```

Ahora tu aplicación funciona en línea. Cualquier persona puede registrarse desde cualquier lugar.

---

## 📚 Documentación Completa
Para instrucciones detalladas, consulta: **[GUIA_BASE_DATOS_EN_LINEA.md](GUIA_BASE_DATOS_EN_LINEA.md)**

## 🔧 Scripts Útiles

| Script | Descripción |
|--------|-------------|
| `test_remote_db.py` | Prueba la conexión a la BD remota |
| `setup_remote_db.py` | Ejecuta el schema en la BD remota |
| `reset_db_admin.py` | Crea usuarios administradores |

## ⚠️ Importante

- **NUNCA** subas `.env` a Git (ya está en `.gitignore`)
- Usa contraseñas seguras (16+ caracteres)
- Supabase plan gratuito: 500 MB (suficiente para el proyecto)
- Si tienes problemas, consulta la guía completa o ejecuta `test_remote_db.py`

## 🌐 Otras Opciones

- **Railway**: https://railway.app (tiene crédito mensual gratis)
- **Render**: https://render.com (también gratuito)
- Ver guía completa para instrucciones detalladas de cada servicio

---

¿Dudas? Revisa **[GUIA_BASE_DATOS_EN_LINEA.md](GUIA_BASE_DATOS_EN_LINEA.md)** para troubleshooting y más opciones.
