# Testing Guide - Verificar que Todo Funciona

Aquí está la guía completa para probar que tu setup de Docker está funcionando correctamente.

## 🚀 OPCIÓN 1: Quick Diagnostic (10 segundos)

Para un chequeo rápido del estado actual:

```bash
python quick_diag.py
```

**Qué revisa:**
- ✓ Docker daemon está corriendo
- ✓ Contenedores están UP
- ✓ PostgreSQL responde
- ✓ Paquetes Python instalados
- ✓ Archivos del proyecto existen

**Cuándo usarlo:**
- Antes de abrir la app
- Cuando sospechas que algo está mal
- Para un chequeo rápido cada mañana

**Output esperado:**
```
✓ Docker daemon: RUNNING
✓ tt_ratones_db: UP
✓ pgadmin_ratones: UP
✓ PostgreSQL accepting connections: YES
```

---

## 🧪 OPCIÓN 2: Full Test Suite (1-2 minutos)

Para un test exhaustivo que verifica TODO:

```bash
python test_docker_setup.py
```

**Qué revisa:**
1. Docker CLI instalado
2. Docker daemon corriendo
3. docker-compose disponible
4. Archivos del proyecto existen
5. Estado de contenedores
6. Levanta docker-compose
7. PostgreSQL health check
8. Conexión psycopg2
9. SQLAlchemy engine
10. ejecución de start_services.py

**Cuándo usarlo:**
- Primera vez que configuras el proyecto
- Después de cambios importantes
- Cuando algo no funciona y necesitas debugging profundo

**Output esperado:**
```
  [✓ PASS] Docker CLI installed
  [✓ PASS] Docker daemon is running
  [✓ PASS] docker-compose (integrado) found
  [✓ PASS] docker-compose.yml exists
  [✓ PASS] PostgreSQL is ready
  ...
TEST SUMMARY: 10/10 tests PASSED (100%)
```

---

## 🔄 OPCIÓN 3: Interactive Test (30-60 segundos)

Para simular el flujo completo (como si ejecutaras launcher.bat):

```bash
python test_interactive.py
```

**Qué revisa:**
1. Docker basics
2. Archivos del proyecto
3. Simula flujo: launcher.bat → run_app.py → start_services.py
4. Verifica contenedores
5. Verifica conectividad a BD
6. Verifica integración con Streamlit

**Cuándo usarlo:**
- Cuando quieres verificar el flujo completo ANTES de ejecutar launcher.bat
- Para asegurarte que start_services.py funcionará

**Output esperado:**
```
RESUMEN: 12/12 tests PASSED (100%)

✓ TODOS LOS TESTS PASARON - Sistema listo para usar!
```

---

## 📋 Orden Recomendado de Tests

### Primera vez (Setup inicial):
```bash
python test_docker_setup.py    # Test completo (1-2 min)
python launcher.bat             # Abre la app
```

### Uso diario:
```bash
python quick_diag.py           # Check rápido (10 seg)
python launcher.bat            # Si todo OK, abre la app
```

### Si algo falla:
```bash
python quick_diag.py           # Identifica qué está mal
python test_interactive.py     # Debug más profundo
python test_docker_setup.py    # Si aún hay problemas
```

---

## 🐛 Interpretando Resultados

### ✓ PASS - Todo bien
No hay acción necesaria, todo está funcionando.

### ✗ FAIL - Hay un problema

**"Docker daemon no está corriendo"**
- Abre Docker Desktop
- Espera a que esté completamente listo
- Reinicia el test

**"docker-compose falló"**
- Verifica que docker-compose.yml existe en el directorio
- Revisa que el archivo .env tiene credenciales válidas
- Intenta: `docker-compose down && docker-compose up -d`

**"PostgreSQL no respondió a tiempo"**
- Espera más (a veces tarda 60+ segundos en la primera ejecución)
- Revisa: `docker logs tt_ratones_db`
- Si falla, reinicia: `docker-compose restart`

**"Conexión a base de datos falló"**
- Verifica credenciales en .env
- Revisa: `docker logs tt_ratones_db`
- Intenta reconectar: `docker exec tt_ratones_db psql -U admin -d ratones_lab -c "SELECT 1;"`

**"Paquete Python no instalado"**
- Instala: `pip install [package_name]`
- Ejemplo: `pip install psycopg2-binary`

---

## 🔍 Debugging Avanzado

### Ver logs de Docker en vivo:
```bash
docker logs -f tt_ratones_db
```
(Presiona Ctrl+C para salir)

### Entrar al contenedor de BD:
```bash
docker exec -it tt_ratones_db bash
psql -U admin -d ratones_lab
```

### Reiniciar servicios completos:
```bash
docker-compose down
docker-compose up -d
```

### Ver estado de todos los contenedores:
```bash
docker ps -a
```

---

## ✨ Si Todos los Tests Pasan

¡Felicidades! Ahora puedes:

1. **Usar el launcher:**
   ```bash
   launcher.bat
   ```

2. **O ejecutar directamente:**
   ```bash
   python run_app.py
   ```

3. **Streamlit debería abrirse automáticamente** con todo listo.

---

## 📞 Checklist Rápido

- [ ] Docker Desktop instalado y abierto
- [ ] docker-compose disponible (`docker-compose --versión`)
- [ ] Archivo .env presente con credenciales
- [ ] docker-compose.yml presente
- [ ] Python 3.11 o superior (para DLC)
- [ ] `quick_diag.py` muestra ✓ en todo
- [ ] `launcher.bat` abre Streamlit

Si todos los boxes están checked, ¡estás listo!
