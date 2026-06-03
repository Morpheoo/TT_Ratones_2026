# ✅ Checklist de configuración del Sistema

## Pre-requisitos
- [ ] Python 3.11 instalado
- [ ] Entorno virtual creado (`venv_311`)
- [ ] Dependencias instaladas (`pip install -r requirements.txt`)
- [ ] Git instalado (opcional)

## configuración de Base de Datos

### Opción A: Local (Docker)
- [ ] Docker Desktop instalado
- [ ] `docker-compose up -d` ejecutado exitosamente
- [ ] PostgreSQL corriendo en `localhost:5432`
- [ ] PgAdmin accesible en `http://localhost:5050`

### Opción B: Remota (Producción)
- [ ] Cuenta creada en servicio cloud (Supabase/Railway/Render)
- [ ] Base de datos PostgreSQL creada
- [ ] Credenciales de conexión obtenidas
- [ ] Variables en `.env` actualizadas con credenciales remotas
- [ ] Test de conexión exitoso (`python test_remote_db.py`)

## Archivo .env Configurado
- [ ] Archivo `.env` creado (copiado de `.env.example`)
- [ ] `POSTGRES_USER` configurado
- [ ] `POSTGRES_PASSWORD` configurado
- [ ] `POSTGRES_DB` configurado
- [ ] `DB_HOST` configurado (localhost o remoto)
- [ ] `DB_PORT` configurado (default: 5432)
- [ ] `GMAIL_SENDER_EMAIL` configurado
- [ ] `GMAIL_APP_PASSWORD` configurado (contraseña de app de Gmail)

## Base de Datos Inicializada
- [ ] Schema ejecutado (`python setup_remote_db.py` o directamente con `schema.sql`)
- [ ] Tabla `users` existe
- [ ] Tabla `experiments` existe
- [ ] Tabla `analysis_results` existe
- [ ] Tabla `roi_configurations` existe
- [ ] Tabla `security_audit_log` existe

## Migraciones Ejecutadas
- [ ] `python src/db/migrations/add_user_profile_fields.py` ejecutado
- [ ] Campos de perfil añadidos a tabla users:
  - [ ] `full_name`
  - [ ] `boleta` (estudiantes)
  - [ ] `carrera` (estudiantes)
  - [ ] `escuela` (estudiantes)
  - [ ] `num_empleado` (investigadores)
  - [ ] `area` (investigadores)
  - [ ] `centro` (investigadores)
  - [ ] `accepted_terms`

## Usuarios Administradores Creados
- [ ] `python reset_db_admin.py` ejecutado
- [ ] Al menos un usuario admin creado
- [ ] Credenciales de admin guardadas de forma segura

## Sistema de Correo Configurado
- [ ] Cuenta de Gmail configurada
- [ ] verificación en dos pasos activada en Gmail
- [ ] Contraseña de aplicación generada
- [ ] `GMAIL_SENDER_EMAIL` en `.env`
- [ ] `GMAIL_APP_PASSWORD` en `.env`
- [ ] Correo de prueba enviado exitosamente

## Pruebas de Funcionalidad

### Conexión a Base de Datos
```bash
python test_remote_db.py
```
- [ ] Resultado: `CONEXIÓN EXITOSA ✓`
- [ ] Todas las tablas listadas
- [ ] Conteo de usuarios correcto

### validación de Configuración
```bash
python check_setup.py
```
- [ ] Todas las validaciones pasadas
- [ ] Rutas de directorios correctas
- [ ] Variables de entorno cargadas

### Sistema de Autenticación
- [ ] Página de login carga correctamente (`streamlit run Home.py`)
- [ ] Formulario de registro para estudiantes funciona
- [ ] Formulario de registro para investigadores funciona
- [ ] Sistema de verificación por correo funciona:
  - [ ] Correo OTP recibido
  - [ ] código OTP validado correctamente
  - [ ] Cuenta activada exitosamente
- [ ] Login con cuenta verificada funciona
- [ ] Login con cuenta no verificada muestra mensaje apropiado

### Panel de Administración
- [ ] Admin puede acceder al panel (botón en sidebar)
- [ ] Lista de usuarios visible
- [ ] Acciones de admin funcionan:
  - [ ] Activar/Suspender usuarios
  - [ ] Ver logs de auditoría

## Seguridad
- [ ] Archivo `.env` está en `.gitignore`
- [ ] `.env` NO está versionado en Git
- [ ] Contraseñas son seguras (16+ caracteres)
- [ ] Contraseñas de BD diferentes a las de correo
- [ ] Credenciales guardadas en lugar seguro (gestor de contraseñas)

## Funcionalidad del Sistema

### Módulos Principales
- [ ] Home (Dashboard) carga correctamente
- [ ] módulo de Login/Registro funciona
- [ ] Ingesta de Video funciona
- [ ] configuración de Zonas funciona
- [ ] análisis Final funciona
- [ ] Resultados y estadísticas funciona
- [ ] comparación ANOVA funciona
- [ ] Perfil de usuario funciona

### Flujo Completo de Usuario Nuevo
1. [ ] Registro exitoso (estudiante o investigador)
2. [ ] Correo de verificación recibido
3. [ ] código OTP ingresado correctamente
4. [ ] Cuenta verificada
5. [ ] Login exitoso
6. [ ] Acceso a módulos permitido

## Deployment (Opcional)

### Streamlit Cloud
- [ ] Repositorio conectado a Streamlit Cloud
- [ ] Secrets configurados en Streamlit Cloud
- [ ] App desplegada y accesible públicamente
- [ ] Variables de entorno cargadas correctamente

### Servidor Propio
- [ ] Servidor configurado (VPS/Cloud)
- [ ] Dependencias instaladas en servidor
- [ ] `.env` configurado en servidor
- [ ] Aplicación corriendo como servicio
- [ ] Dominio configurado (opcional)
- [ ] HTTPS configurado (opcional pero recomendado)

## Documentación
- [ ] README.md actualizado
- [ ] Variables de entorno documentadas
- [ ] Credenciales de admin documentadas (en lugar seguro)
- [ ] Guías de uso creadas para usuarios finales

## Backup y Recuperación
- [ ] Script de backup de BD creado
- [ ] Backup automático configurado (si es posible)
- [ ] Backup manual realizado y probado
- [ ] Proceso de restauración documentado

---

## 🎉 Sistema Completamente Configurado

Si todos los items tienen ✓, tu sistema está listo para producción.

## 📞 Ayuda y Soporte

Si tienes problemas en algún paso:
1. Consulta [GUIA_BASE_DATOS_EN_LINEA.md](GUIA_BASE_DATOS_EN_LINEA.md)
2. Ejecuta `python test_remote_db.py` para diagnóstico
3. Revisa los logs de la aplicación
4. Verifica el archivo `.env`

## 🔄 Mantenimiento Regular

- [ ] Revisar logs de seguridad semanalmente
- [ ] Actualizar dependencias mensualmente
- [ ] Realizar backups de BD regularmente
- [ ] Revisar usuarios inactivos
- [ ] Rotar contraseñas cada 3-6 meses
