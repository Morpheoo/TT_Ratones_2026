# 🆘 TROUBLESHOOTING - PostgreSQL + pgAdmin

## ❌ Problema: No puedo conectar a pgAdmin

### Síntoma
- Navegador muestra "Connection refused" al abrir http://localhost:5050

### Causas y soluciones

**1. Docker no está corriendo**
```powershell
# Verificar
docker info

# Si falla, abre Docker Desktop manualmente
# Start Menu > Docker Desktop
```

**2. Contenedor pgAdmin no está levantado**
```powershell
# Ver estado
docker-compose ps

# Si pgadmin_ratones no aparece o está "Exited"
docker-compose up -d pgadmin
docker logs pgadmin_ratones
```

**3. Puerto 5050 está en uso por otra aplicación**
```powershell
# Verificar qué usa el puerto
netstat -ano | findstr :5050

# Solución: cambiar puerto en docker-compose.yml
# Cambiar: "5050:80" por "5051:80"
# Luego: docker-compose restart
```

**4. pgAdmin tarda en iniciar**
- Espera 20-30 segundos y recarga la página
- Los primeros inicios pueden ser lentos

---

## ❌ Problema: Credenciales incorrectas en pgAdmin

### Síntoma
- Login fallido con "Invalid username or password"

### Solución

**Revisar archivo .env:**
```powershell
cat .env | findstr PGADMIN

# Debería mostrar:
# PGADMIN_DEFAULT_EMAIL=admin@ratones.com
# PGADMIN_DEFAULT_PASSWORD=admin
```

**Credenciales por defecto:**
```
Email: admin@ratones.com
Contraseña: admin
```

**Si las cambiaste en .env:**
```powershell
# Detener y limpiar
docker-compose down

# Eliminar volumen de pgAdmin (perderá configuración)
docker volume rm tt_ratones_2026_pgadmin_data

# Levantar nuevamente
docker-compose up -d
```

---

## ❌ Problema: No puedo conectar PostgreSQL en pgAdmin

### Síntoma
- pgAdmin abre pero al intentar registrar el servidor, falla la conexión

### Paso a paso

**1. Verificar que PostgreSQL está corriendo**
```powershell
docker-compose ps

# Debería mostrar "Up" para tt_ratones_db
```

**2. Verificar que PostgreSQL responde**
```powershell
docker exec tt_ratones_db pg_isready -U admin

# Respuesta esperada: "accepting connections"
```

**3. Ver logs de PostgreSQL**
```powershell
docker logs tt_ratones_db

# Buscar errores o "ready to accept connections"
```

**4. En pgAdmin, usar HOST CORRECTO**

⚠️ IMPORTANTE:

```
SI PGADMIN ESTÁ EN DOCKER:
  Host: db          ← Nombre del servicio en docker-compose.yml
  Port: 5432
  User: admin
  Password: admin_secure_password
  
SI USAS DBEAVER O HERRAMIENTA EXTERNA:
  Host: localhost   ← O la IP de tu máquina
  Port: 5432
  User: admin
  Password: admin_secure_password
```

**5. Probar conexión desde terminal**
```powershell
# Desde PowerShell
docker exec tt_ratones_db psql -U admin -d postgres -c "SELECT 1"

# Si devuelve "(1 row)" → PostgreSQL está bien

# Si falla → Ver logs:
docker logs tt_ratones_db
```

---

## ❌ Problema: No veo las tablas en pgAdmin

### Síntoma
- Conecto a PostgreSQL pero las tablas no aparecen
- O aparecen tablas vacías

### Causas y soluciones

**1. Las tablas aún no existen**

Verifica que se crearon:
```powershell
docker exec tt_ratones_db psql -U admin -d ratones_lab -c "\dt"

# Debería listar: users, treatments, experiments, etc.
```

Si no aparecen:
- Ejecuta los scripts de inicialización de BD
- O importa un dump SQL:
```powershell
docker exec tt_ratones_db psql -U admin -d ratones_lab -f /path/to/schema.sql
```

**2. Estás mirando la base de datos equivocada**

En pgAdmin:
1. Expande "Servers" > "tt_ratones_db"
2. Haz click en "Databases"
3. Busca **"ratones_lab"** (no "postgres")
4. Expande > "Schemas" > "public" > "Tables"

**3. pgAdmin tiene caché**

Presiona F5 o refresh en el navegador

---

## ❌ Problema: Error: "FATAL: password authentication failed"

### Síntoma
- Al conectar a PostgreSQL desde pgAdmin: "FATAL: password authentication failed for user..."

### Causa
- Credenciales incorrectas
- Usuario no existe

### Solución

**1. Verificar credenciales en .env**
```powershell
cat .env | findstr POSTGRES_

# Debería tener:
# POSTGRES_USER=admin
# POSTGRES_PASSWORD=admin_secure_password
# POSTGRES_DB=ratones_lab
```

**2. En pgAdmin, asegurar que usas:**
```
Username: admin
Password: admin_secure_password
```

**3. Si aún falla, recrear contenedor**
```powershell
# Bajar
docker-compose down

# Limpiar volumen
docker volume rm tt_ratones_2026_postgres_data

# Levantar (recreará todo)
docker-compose up -d
```

---

## ❌ Problema: Puerto 5432 en uso

### Síntoma
```
Error: Ports are not available: listen tcp 0.0.0.0:5432: bind: An attempt was made to access a socket in a way forbidden by its access rules
```

### Solución

**Opción 1: Ver qué ocupa el puerto**
```powershell
netstat -ano | findstr :5432
taskkill /PID [PID] /F
```

**Opción 2: Usar otro puerto**
1. Edita `docker-compose.yml`
2. Cambia `5432:5432` por `5433:5432`
3. Ejecuta `docker-compose up -d`
4. Conecta desde localhost:5433

---

## ❌ Problema: Volumen no persiste datos

### Síntoma
- Bajo contenedores y subo nuevamente
- Los datos desaparecieron

### Causa
- El volumen no fue creado correctamente
- O se eliminó

### Solución

**1. Verificar que el volumen existe**
```powershell
docker volume ls | findstr postgres_data
```

**2. Ver donde está el volumen**
```powershell
docker volume inspect tt_ratones_2026_postgres_data

# Busca "Mountpoint": es la ruta en disco
```

**3. Verificar que docker-compose.yml tiene volumen**
```yaml
volumes:
  postgres_data:    # ← Debe existir

services:
  db:
    volumes:
      - postgres_data:/var/lib/postgresql/data  # ← Debe existir
```

**4. Si el volumen se perdió, recrearlo**
```powershell
# Bajar
docker-compose down

# Limpiar (CUIDADO - pierde datos)
docker volume rm tt_ratones_2026_postgres_data

# Levantar
docker-compose up -d

# Esperar a que PostgreSQL se inicialice (30-60 segundos)
```

---

## ❌ Problema: PostgreSQL se reinicia constantemente

### Síntoma
```
docker-compose ps

# Estado: "Restarting"
```

### Verificar logs
```powershell
docker logs tt_ratones_db

# Buscar líneas con ERROR o FATAL
```

### Causas comunes

**1. Volumen corruptado**
```powershell
docker-compose down -v
docker-compose up -d
```

**2. Memoria insuficiente**
- Aumenta memoria en Docker Desktop Settings
- O limpia caché: `docker system prune -a`

**3. Credenciales inválidas en .env**
- Verifica que POSTGRES_USER y POSTGRES_PASSWORD son válidas

---

## ❌ Problema: "Connection refused" desde pgAdmin a PostgreSQL

### Síntoma
- pgAdmin abre correctamente
- Pero al registrar servidor: "could not connect to server"

### Debug paso a paso

**1. Verificar que PostgreSQL está escuchando**
```powershell
docker exec tt_ratones_db netstat -an | findstr 5432

# Debería mostrar algo como:
# tcp    0    0 0.0.0.0:5432    0.0.0.0:*    LISTEN
```

**2. Verificar conectividad entre contenedores**
```powershell
# Desde pgAdmin, probar conexión al contenedor db
docker exec pgadmin_ratones ping db

# Debería responder sin errores
```

**3. Ver logs de PostgreSQL**
```powershell
docker logs -f tt_ratones_db

# Buscar: "ready to accept connections"
```

**4. Probar conexión manualmente**
```powershell
docker exec pgadmin_ratones psql -h db -U admin -d postgres -c "SELECT 1"

# Si funciona → El problema es en la configuración de pgAdmin
# Si falla → El problema es de conectividad entre contenedores
```

---

## ❌ Problema: Espacio en disco lleno

### Síntoma
```
Error: no space left on device
```

### Solución

**1. Ver espacio usado por Docker**
```powershell
docker system df
```

**2. Limpiar sin eliminar datos importantes**
```powershell
# Eliminar imágenes no usadas
docker image prune -a

# Eliminar contenedores parados
docker container prune

# Eliminar volúmenes no usados
docker volume prune

# Limpiar caché de build
docker builder prune
```

**3. Si aún no hay espacio**
```powershell
# Ver tamaño de volúmenes individuales
docker volume ls -q | % { docker volume inspect $_ } | findstr Mountpoint
```

---

## ❌ Problema: pgAdmin muy lento

### Síntoma
- pgAdmin tarda mucho en abrir
- Las queries son lentas

### Soluciones

**1. Reiniciar contenedores**
```powershell
docker-compose restart
```

**2. Limpiar caché de Docker**
```powershell
docker system prune
```

**3. Aumentar memoria en Docker Desktop**
- Settings > Resources > Memory: 4GB o más

**4. Si PostgreSQL es lento, reindexar**
```powershell
docker exec tt_ratones_db psql -U admin -d ratones_lab -c "REINDEX DATABASE ratones_lab"
```

---

## ✅ CHECKLIST DE VERIFICACIÓN

Antes de la defensa académica, ejecuta esto:

```powershell
# 1. Docker corriendo
docker info

# 2. Contenedores levantados
docker-compose ps

# 3. PostgreSQL listo
docker exec tt_ratones_db pg_isready -U admin

# 4. Tablas existen
docker exec tt_ratones_db psql -U admin -d ratones_lab -c "\dt"

# 5. Hay datos
docker exec tt_ratones_db psql -U admin -d ratones_lab -c "SELECT COUNT(*) FROM users"

# 6. pgAdmin accesible
Start-Process http://localhost:5050

# 7. Puerto 5050 abierto
Test-NetConnection -ComputerName localhost -Port 5050
```

Si todos los checks pasan ✓, estás listo.

---

## 🆘 Si NADA funciona

Reinicia todo desde cero:

```powershell
# Parar todo
docker-compose down

# Eliminar volúmenes (CUIDADO - pierde datos)
docker-compose down -v

# Limpiar Docker
docker system prune -a --volumes

# Levantar nuevamente
docker-compose up -d

# Esperar 30 segundos
Start-Sleep -Seconds 30

# Verificar
docker-compose ps
```

---

## 📞 CONTACTO/SOPORTE

Si sigues con problemas:

1. Revisa logs: `docker logs tt_ratones_db`
2. Verifica .env: `cat .env`
3. Comprueba docker-compose.yml: `cat docker-compose.yml`
4. Consulta logs de pgAdmin: `docker logs pgadmin_ratones`

¡Éxito! 🚀

