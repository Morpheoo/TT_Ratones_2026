# Guía de instalación y ejecución — TT_Ratones_2026

Documento para colaboradores nuevos que necesitan correr el sistema en su máquina.

---

## 1. Requisitos previos

| Componente | Versión mínima | Notas |
|---|---|---|
| Windows 10/11 | — | El sistema usa rutas Windows y PowerShell |
| Python 3.11 | `venv_311` | Para YOLO, Streamlit y pipeline principal |
| Python 3.10 | `venv_310` | Solo para SimBA (requiere TF/DLC legacy) |
| CUDA | 12.x | GPU NVIDIA recomendada (RTX o equivalente) |
| Docker Desktop | — | Para la base de datos PostgreSQL |
| Git | — | Para clonar el repositorio |

---

## 2. Archivos de modelos que debes recibir

Estos archivos **no están en el repositorio** (son muy grandes). Pídeselos al equipo:

| Archivo | Tamaño | Dónde colocarlo |
|---|---|---|
| `best.pt` (YOLO Pose v4) | 19 MB | `runs/pose/yolo11s_pose_raton_v4/weights/best.pt` |
| `Grooming.sav` (RF SimBA) | 148 MB | `data/simba_projects/grooming_thigmotaxis_yolo/models/generated_models/Grooming.sav` |
| `Thigmotaxis.sav` (RF SimBA) | 145 MB | `data/simba_projects/grooming_thigmotaxis_yolo/models/generated_models/Thigmotaxis.sav` |
| `grooming_lstm.keras` (LSTM) | 2.5 MB | `data/models/lstm_grooming_yolo/grooming_lstm.keras` |
| `scaler.pkl` (LSTM scaler) | <1 MB | `data/models/lstm_grooming_yolo/scaler.pkl` |
| `metadata.json` (LSTM meta) | <1 MB | `data/models/lstm_grooming_yolo/metadata.json` |
| `yolo_tracker.pt` (tracker) | 5 MB | `yolo_tracker.pt` (raíz del proyecto) |

También debes recibir la carpeta completa del proyecto SimBA:

```
data/simba_projects/grooming_thigmotaxis_yolo/
```

Esta contiene los CSV de entrenamiento (`targets_inserted/`), configuración de ROIs y el `project_config.ini` ya configurado.

---

## 3. Clonar el repositorio

```bash
git clone <URL_DEL_REPO> TT_Ratones_2026
cd TT_Ratones_2026
```

---

## 4. Crear los entornos virtuales

### venv_311 (principal — YOLO + Streamlit)

```powershell
python -m venv venv_311
venv_311\Scripts\activate
pip install ultralytics streamlit pandas numpy opencv-python sqlalchemy psycopg2-binary python-dotenv tensorflow scikit-learn joblib roboflow pyyaml
deactivate
```

### venv_310 (SimBA)

```powershell
py -3.10 -m venv venv_310
venv_310\Scripts\activate
pip install simba-uw-tf-dev
deactivate
```

> Si SimBA da error de instalación, prueba: `pip install simba-uw-tf-dev --no-deps` y luego instala dependencias manualmente.

---

## 5. Configurar la base de datos (PostgreSQL via Docker)

```powershell
# Asegúrate de que Docker Desktop esté corriendo, luego:
docker-compose up -d
```

Esto levanta PostgreSQL en el puerto 5432. La primera vez inicializa el esquema automáticamente desde `schema.sql`.

Crea un archivo `.env` en la raíz del proyecto con estas variables:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ratones_tt2026
DB_USER=postgres
DB_PASSWORD=tu_password_aqui
```

---

## 6. Verificar que todo está en su lugar

```powershell
venv_311\Scripts\python.exe src\config.py
```

Debes ver todas las rutas marcadas como OK. Si algo falta, el script te lo indica.

---

## 7. Actualizar rutas de SimBA (IMPORTANTE)

El proyecto de SimBA usa rutas absolutas en su configuración. Cuando clonas el repositorio o lo mueves a otra ubicación, estas rutas deben actualizarse. El sistema lo hace **automáticamente** cada vez que ejecutas el pipeline, pero también puedes hacerlo manualmente:

```powershell
python fix_simba_paths.py
```

Este script detecta la ubicación actual del proyecto y actualiza todas las rutas en `project_config.ini`. **No necesitas editarlo manualmente**.

Si ves errores como "SIMBA NOT A DIRECTORY ERROR", ejecuta este script.

---

## 8. Arrancar la aplicación

```powershell
venv_311\Scripts\python.exe -m streamlit run Home.py
```

O usa el launcher incluido:

```powershell
.\launcher.bat
```

La app abre en `http://localhost:8501` en tu navegador.

---

## 9. Flujo de uso básico

```
Módulo 01 — Ingesta de Video
  └── Sube o selecciona el video .mp4 del ratón

Módulo 02 — Keypoints
  └── Motor: YOLO Pose v4 (ya fijo)
  └── Click: INICIAR EXTRACCIÓN (~3-4 min por video de 5 min)
  └── Resultado: CSV + video con keypoints en keypoints_yolo/{video}/

Módulo 03 — Configuración de Zonas
  └── Dibuja o carga las zonas del laberinto
  └── Click: GUARDAR CONFIGURACIÓN EXPERIMENTAL

Módulo 04 — Análisis Final
  └── Click: INICIAR PIPELINE MULTIMODAL
  └── Resultado: video multimodal + timelogs en resultados_yolo/{video}/
  └── Puedes DETENER en cualquier momento si algo va mal

Módulo 05 — Resultados y Estadísticas
  └── Ver métricas, heatmap y trayectoria del experimento
```

---

## 10. Carpetas de salida

| Carpeta | Contenido |
|---|---|
| `keypoints_yolo/{video}/` | CSV de keypoints (formato SimBA) + video overlay |
| `resultados_yolo/{video}/` | Video multimodal, timelogs de Grooming/Thigmotaxis, trayectoria |

---

## 10. Descripción de los modelos incluidos

| Modelo | Tipo | Descripción |
|---|---|---|
| `yolo11s_pose_raton_v4/weights/best.pt` | YOLO11s Pose | Detecta 8 keypoints del ratón. Entrenado con 3,953 imágenes. mAP50 = 99.5% |
| `Grooming.sav` | Random Forest (SimBA) | Clasificador de Grooming entrenado sobre features YOLO. 2,000 árboles, 10 videos anotados |
| `Thigmotaxis.sav` | Random Forest (SimBA) | Clasificador de Thigmotaxis entrenado sobre features YOLO. 2,000 árboles |
| `grooming_lstm.keras` | LSTM | Complemento temporal para Grooming. Actúa en modo rescue cuando el RF es ambiguo |
| `yolo_tracker.pt` | YOLO detector | Tracker visual para la trayectoria en el video multimodal final |

### Keypoints del modelo YOLO Pose v4

```
0 = nariz       4 = oreja-der
1 = torso       5 = pata-izq
2 = cola-base   6 = pata-der
3 = oreja-izq   7 = punta-cola
```

---

## 11. Solución de problemas comunes

**El pipeline de keypoints no arranca:**
- Verifica que `venv_311` esté creado y que `best.pt` esté en su lugar
- Revisa el log en `logs/keypoints/keypoints_extract.log`

**SimBA features falla con error de bodyparts:**
- Asegúrate de que `data/simba_projects/grooming_thigmotaxis_yolo/project_folder/logs/measures/pose_configs/bp_names/project_bp_names.csv` existe

**Docker no conecta:**
- Verifica que Docker Desktop esté corriendo: `docker ps`
- Verifica el archivo `.env` con las credenciales correctas

**La GPU no se detecta:**
- Instala los drivers CUDA compatibles con tu tarjeta
- Verifica con: `venv_311\Scripts\python.exe -c "import torch; print(torch.cuda.is_available())"`

---

## 12. Contacto

Proyecto: TT 2026 — ESCOM IPN  
Para dudas técnicas sobre el pipeline, contactar al equipo del proyecto.
