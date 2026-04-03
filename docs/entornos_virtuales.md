# Entornos Virtuales del Proyecto TT Ratones 2026

## 📦 Estructura de Entornos

El proyecto utiliza **dos entornos virtuales separados** para manejar incompatibilidades entre bibliotecas:

### 🔷 **venv_311** (Python 3.11.9)
**Propósito**: Aplicación principal de Streamlit y análisis general

**Instalado:**
- Streamlit 1.52.1 (framework web)
- Pandas 2.3.3 (análisis de datos)
- NumPy 2.3.5
- OpenCV 4.11.0 (procesamiento de video)
- SQLAlchemy 2.0.45 (base de datos)
- Bcrypt 4.1.2 (autenticación)
- MoviePy (edición de video)
- Plotly, Matplotlib, Seaborn (visualización)
- Ultralytics (YOLO v8 - en instalación)

**NO incluye:**
- ❌ DeepLabCut
- ❌ TensorFlow 2.10 (incompatible con Python 3.11)

**Uso:**
```bash
# Activar entorno
venv_311\Scripts\activate

# Ejecutar aplicación
streamlit run Home.py
```

---

### 🔶 **venv_310** (Python 3.10.11)
**Propósito**: DeepLabCut y análisis de pose

**Instalado:**
- DeepLabCut 2.3.11
- TensorFlow 2.10.1 (GPU)
- MoviePy 2.1.2
- OpenCV 4.8.1.78
- NumPy 1.26.4

**Uso:**
```bash
# NO se activa manualmente
# Los scripts lo invocan automáticamente cuando necesitan DLC
```

---

## 🔄 Flujo de Trabajo

1. **Usuario inicia la app** → Usa `venv_311`
   - Streamlit corre en Python 3.11
   - Interfaz web, login, visualizaciones

2. **Usuario ejecuta análisis de keypoints (Módulo 02)** → Cambia a `venv_310`
   - Subprocess ejecuta DeepLabCut en Python 3.10
   - Genera archivos .h5 y .csv con coordenadas

3. **Usuario continúa con análisis final (Módulo 04)** → Vuelve a `venv_311`
   - YOLO tracking corre en Python 3.11
   - Renderiza visualizaciones

---

## ⚙️ Comandos de Instalación

### Reinstalar venv_311
```bash
# Eliminar entorno existente
rmdir /S /Q venv_311

# Crear nuevo entorno
py -3.11 -m venv venv_311

# Instalar dependencias
venv_311\Scripts\pip.exe install -r requirements_venv311.txt
```

### Reinstalar venv_310
```bash
# Ya existe, ver documentación anterior
```

---

## 📝 Archivos de Dependencias

- `requirements.txt` → Lista completa (mixta, puede causar conflictos)
- `requirements_venv311.txt` → Solo para Python 3.11 (app principal)
- *Pendiente*: `requirements_venv310.txt` → Solo para Python 3.10 (DeepLabCut)

---

## ⚠️ Notas Importantes

1. **NO mezclar entornos**: Nunca instales DeepLabCut en venv_311 ni Streamlit en venv_310
2. **run_app.bat usa venv_311**: El script de inicio automáticamente activa el entorno correcto
3. **GPU vs CPU**: 
   - venv_310 usa TensorFlow con soporte GPU (CUDA 11.2)
   - venv_311 puede usar PyTorch con GPU (CUDA 12.8) si está disponible
4. **Streamlit solo corre en venv_311**: No intentes ejecutar la app desde venv_310
