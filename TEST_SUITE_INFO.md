# 🧪 Test Suite Completo - Verificar Todo Funciona

## 📦 Archivos de Test Disponibles

Creé **5 archivos nuevos** para que puedas verificar que tu setup funciona:

### 1. **quick_diag.py** (2.2 KB) - ⚡ Rápido
**Tiempo: ~10 segundos**

Chequeo ultra-rápido del estado actual.

```bash
python quick_diag.py
```

✓ Docker daemon
✓ Contenedores UP
✓ PostgreSQL respondiendo
✓ Paquetes Python
✓ Archivos presentes

**Cuándo:** Antes de cada sesión / Chequeo rápido

---

### 2. **test_docker_setup.py** (10 KB) - 🔧 Completo
**Tiempo: ~1-2 minutos**

Suite exhaustiva de 10 tests individuales.

```bash
python test_docker_setup.py
```

**Tests incluídos:**
1. Docker CLI instalado
2. Docker daemon corriendo
3. docker-compose disponible
4. Archivos del proyecto existen
5. Estado de contenedores
6. docker-compose up -d
7. PostgreSQL health check
8. psycopg2 connection
9. SQLAlchemy engine
10. start_services.py execution

**Cuándo:** Setup inicial / Debugging profundo

---

### 3. **test_interactive.py** (6.9 KB) - 🔄 Interactivo
**Tiempo: ~30-60 segundos**

Simula el flujo completo como si ejecutaras launcher.bat.

```bash
python test_interactive.py
```

**Tests incluídos:**
1. Docker basics
2. Archivos del proyecto
3. Flujo: launcher.bat → run_app.py → start_services.py
4. Contenedores
5. Conectividad BD
6. Integración Streamlit

**Cuándo:** Quieres verificar el flujo antes de launcher.bat

---

### 4. **run_tests.bat** (2.0 KB) - 🎯 Menu
**Tiempo: Según selección**

Menu interactivo para ejecutar tests en Windows.

```bash
run_tests.bat
```

**Opciones:**
1. Quick Diagnostic
2. Full Test Suite
3. Interactive Test
4. Run All Tests in Sequence

**Cuándo:** Desde Windows sin escribir comandos

---

### 5. **TESTING_GUIDE.md** (4.8 KB) - 📖 Documentación
**Guía completa de testing.**

Incluye:
- Cómo usar cada test
- Orden recomendado
- Interpretación de resultados
- Debugging avanzado
- Checklist final

---

## 🚀 CÓMO EMPEZAR (3 pasos)

### Opción A: Rápido (10 segundos)
```bash
python quick_diag.py
```

### Opción B: Completo (1-2 minutos)
```bash
python test_docker_setup.py
```

### Opción C: Menu en Windows
```bash
run_tests.bat
```

---

## 📋 Orden Recomendado

### **Primera vez:**
1. Ejecuta: `python test_docker_setup.py`
2. Si todo pasa ✓: ejecuta `launcher.bat`

### **Uso diario:**
1. Ejecuta: `python quick_diag.py`
2. Si todo OK ✓: ejecuta `launcher.bat`

### **Si hay problemas:**
1. Ejecuta: `python quick_diag.py` (identifica qué falla)
2. Ejecuta: `python test_docker_setup.py` (debugging profundo)
3. Revisa: `TESTING_GUIDE.md` (soluciones)

---

## ✨ Resumen de lo que Implementé

| Componente | Archivo | Propósito |
|-----------|---------|----------|
| **Test Suite** | test_docker_setup.py | 10 tests exhaustivos |
| **Quick Check** | quick_diag.py | 10 segundos check |
| **Interactive** | test_interactive.py | Simula flujo real |
| **Menu GUI** | run_tests.bat | Menu en Windows |
| **Documentación** | TESTING_GUIDE.md | Guía de uso |

---

## 💡 Tips

1. **Primera vez:** Usa `test_docker_setup.py` para asegurarte que todo funciona
2. **Cada sesión:** Usa `quick_diag.py` para verificación rápida
3. **Si falla algo:** Revisa `TESTING_GUIDE.md` para soluciones
4. **Para debugging:** Usa comandos Docker directamente:
   ```bash
   docker logs tt_ratones_db        # Ver logs
   docker ps -a                      # Ver contenedores
   docker exec tt_ratones_db bash    # Entrar al contenedor
   ```

---

## 🎯 Meta

Ahora puedes verificar en **10 segundos** que todo funciona, sin sorpresas cuando abres la app. 

**¡Ejecuta uno de los tests y cuéntame qué tal!**
