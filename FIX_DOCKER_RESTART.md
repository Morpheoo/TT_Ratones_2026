# 🔧 SOLUCIÓN: Docker No Se Levanta Después de Apagar PC

## Problema Encontrado

Después de apagar y encender la PC, al ejecutar `launcher.bat`, Docker no se levantaba automáticamente. Los status badges mostraban:
- ❌ Docker Container: "Docker no disponible"  
- ❌ Base de Datos: "Motor SQL no creado"

**Causa raíz:** 
1. **Error en Home.py** - El import de la BD era incorrecto (`db.connection` → debería ser `src.db.connection`)
2. **Función `_check_docker_status()` muy frágil** - No manejaba bien los casos donde el contenedor existía pero estaba detenido

---

## ✅ Soluciones Implementadas

### 1. **Arreglo de Import**
```python
# ANTES (incorrecto):
from db.connection import get_db_engine

# DESPUÉS (correcto):
from src.db.connection import get_db_engine
```

### 2. **Mejorada `_check_docker_status()`**
Ahora:
- ✓ Verifica Docker daemon correctamente
- ✓ Usa `docker ps -a` (incluye contenedores detenidos)
- ✓ Mensajes de error descriptivos
- ✓ Timeout robusto

### 3. **Nuevo Tool: `recovery_docker.py`**
Script que levanta Docker manualmente si es necesario:

```bash
python recovery_docker.py
```

**Qué hace:**
1. Verifica Docker daemon
2. Si no está corriendo, abre Docker Desktop (Windows)
3. Espera a que esté listo (máx 30 segundos)
4. Ejecuta `docker-compose up -d`
5. Espera a que PostgreSQL responda

### 4. **Menu Batch: `recover_docker.bat`**
Ejecuta el recovery tool desde Windows sin terminal:

```bash
recover_docker.bat
```

---

## 🚀 Cómo Usar Ahora

### **Opción 1: Normal (Debería funcionar ahora)**
```bash
launcher.bat
```

El batch ahora debería:
1. ✓ Verificar Docker daemon
2. ✓ Si no está corriendo, abrirlo
3. ✓ Ejecutar `start_services.py`
4. ✓ Levantar Streamlit

### **Opción 2: Si Aún Falla**
```bash
recover_docker.bat
```

O desde terminal:
```bash
python recovery_docker.py
```

Esto fuerza el levantamiento de Docker y contenedores.

### **Opción 3: Verificar Estado Rápido**
```bash
python quick_diag.py
```

---

## 📋 Orden Recomendado

### **Si todo está normal:**
```bash
launcher.bat    # Abre la app
```

### **Si falla Docker después de apagar:**
```bash
recover_docker.bat    # Levanta Docker
launcher.bat          # Abre la app
```

### **Si quieres debuguear:**
```bash
python quick_diag.py       # Chequeo rápido (10 seg)
python test_docker_setup.py # Test completo (1-2 min)
recover_docker.bat         # Si algo falló
```

---

## 🔍 Qué Cambió

| Componente | Antes | Después |
|-----------|-------|---------|
| **Home.py - Import** | `db.connection` ❌ | `src.db.connection` ✓ |
| **_check_docker_status()** | Frágil | Robusta |
| **Recovery** | No existía | `recovery_docker.py` + `recover_docker.bat` |
| **Manejo de contenedores detenidos** | Falla silenciosa | Detecta y reporta |

---

## 💡 Tips

### Si Docker Desktop no abre automáticamente:
```bash
# Abre manualmente desde Windows Start Menu
# O desde terminal:
"C:\Program Files\Docker\Docker\Docker Desktop.exe"
```

### Para revisar logs de PostgreSQL:
```bash
docker logs tt_ratones_db
```

### Para reiniciar servicios completamente:
```bash
docker-compose down
docker-compose up -d
```

### Para limpiar y empezar de cero:
```bash
docker-compose down -v    # Elimina volúmenes (cuidado - borra datos)
docker-compose up -d      # Recrea todo
```

---

## 📞 Si Aún Tienes Problemas

1. **Ejecuta**: `python test_docker_setup.py` (test completo)
2. **Revisa**: Los logs de Docker → `docker logs tt_ratones_db`
3. **Intenta**: `recover_docker.bat` (fuerza levantamiento)
4. **Verifica**: que Docker Desktop está correctamente instalado

---

## ✨ Resumen

**Antes:** Apagabas la PC, la encendías, y Docker se quedaba apagado.

**Ahora:** 
- ✓ `launcher.bat` abre Docker automáticamente
- ✓ Si falla, tienes `recover_docker.bat` para recuperar
- ✓ Los status badges en la app ahora reportan correctamente

**Para usar:** Simplemente ejecuta `launcher.bat` como siempre. Si algo falla, ejecuta `recover_docker.bat`.

¿Necesitas algo más? Let me know!
