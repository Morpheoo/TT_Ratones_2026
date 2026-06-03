# Pilar 2: Pipeline técnico end-to-end

Fecha: 2026-05-05

Como funciona internamente el sistema de deteccion automática. Para
estado y métricas ver pilar 1 (`01_ESTADO_ACTUAL.md`). Para mejoras
pendientes ver pilar 3 (`03_PLAN_MEJORAS.md`).

---

## 1. Vision general del flujo

```
[1] Video MP4 (videos_data/{stem}.mp4)
       |
       v
[2] YOLO Pose v4 detection (~3.5 min)
       |  Modelo: runs/pose/yolo11s_pose_raton_v4/weights/best.pt
       |  Script: src/scripts/yolo_pose_to_csv.py
       v
[3] Bridge SimBA-friendly (instantaneo)
       |  Output: keypoints_yolo/{stem}/bridge_{stem}.csv
       v
[4] SimBA features extraction (~1.5 s)
       |  ROI / pared / wall configs
       |  Output: data/simba_projects/grooming_thigmotaxis_yolo/.../features_extracted/{stem}.csv
       v
[5] LSTM Grooming inference (~5 s)
       |  Modelo: data/models/lstm_grooming_yolo/grooming_lstm.keras
       |  Output: resultados_yolo/{stem}/{stem}_grooming_lstm.csv
       v
[6] RF Grooming + RF Thigmotaxis predict (~10 s)
       |  Modelos: Grooming.sav (269 MB), Thigmotaxis.sav (286 MB)
       v
[7] Smoothing + thresholds + LSTM rescue
       |  Configurable via CLI args
       v
[8] Render multimodal video + timelogs + trayectoria
       |  Script: src/scripts/generar_video_prediccion.py
       |  Outputs: resultados_yolo/{stem}/{stem}_*.mp4 / *.csv
```

## 2. Componentes detallados

### 2.1 YOLO Pose v4

**Funcion**: detecta 8 keypoints del raton en cada frame.

| Keypoint | Indice | Mapeo a SimBA |
|---|---:|---|
| nariz | 0 | Nose |
| torso | 1 | Center |
| cola-base | 2 | Tail_base |
| oreja-izq | 3 | Ear_left |
| oreja-der | 4 | Ear_right |
| pata-izq | 5 | Lat_left |
| pata-der | 6 | Lat_right |
| punta-cola | 7 | Tail_end |

Skeleton: `[(0,3),(0,4),(0,1),(1,5),(1,6),(1,2),(2,7)]`

**Script**: `src/scripts/yolo_pose_to_csv.py`
**Outputs**:
- `keypoints_yolo/{stem}/{stem}_yolo_pose.csv` (formato DLC-like, 8 keypoints x,y,p)
- `keypoints_yolo/{stem}/{stem}_yolo_keypoints.mp4` (video con overlay)
- `keypoints_yolo/{stem}/bridge_{stem}.csv` (formato SimBA con nombres mapeados)

### 2.2 SimBA features extraction

**Funcion**: a partir del bridge CSV, computa 242 features por frame
incluyendo:

- Distancias inter-keypoint (basicas)
- Movement features (derivadas temporales)
- Mouse euclidean distances en multiples ventanas (5, 6, 7.5, 15 frames)
- ROI features: distancia a `paredX` (X=1..6, las 6 paredes del laberinto)
- ROI in-zone flags: si keypoints estan en `Brazo Abierto/Cerrado/Centro`
- Sum probabilities (de las p de keypoints)

**Configuración ROI**: archivo JSON con poligonos (en `logs/analysis/zonas_activas.json`).

**Script**: `src/scripts/compute_simba_features.py` (o uses SimBA's GUI).

### 2.3 SimBA RF (Grooming + Thigmotaxis)

**Funcion**: predict_proba por frame. Probabilidad continua [0, 1].

**Configuración combo (deployment 2026-05-05)**:

```ini
[create ensemble settings]
under_sample_setting = None
under_sample_ratio = 1.0
rf_n_estimators = 2000
rf_min_sample_leaf = 10
rf_max_features = sqrt
rf_criterion = entropy
class_weights = balanced
```

**Script de reentreno**: `src/scripts/retrain_simba_models.py --yolo`
- Sin `--behavior`: reentrena ambos modelos
- Con `--behavior Grooming` o `--behavior Thigmotaxis`: solo uno
- `--no-backup`: no guarda backup del modelo previo

**Backups automaticos** en `data/simba_projects/grooming_thigmotaxis_yolo/models/generated_models/backups/`.

### 2.4 LSTM Grooming (rescue)

**Funcion**: prediccion temporal complementaria al RF. Lee features
extraidas y predice `Probability_Grooming_LSTM` por frame.

**Modelo**: 
- Path: `data/models/lstm_grooming_yolo/grooming_lstm.keras` (~2.6 MB)
- Status: **DESACTUALIZADO** (entrenado con 11 videos en 2026-04, no se ha
  reentrenado con los 26 actuales)
- **Compatibilidad**: roto en keras 3 (necesita keras 2). El pipeline
  espera el CSV ya generado, no carga el modelo directamente.

**Script de inferencia**: `src/scripts/infer_grooming_lstm.py`

**Output**: `resultados_yolo/{stem}/{stem}_grooming_lstm.csv` con columnas
`Frame, Probability_Grooming_LSTM, Grooming_LSTM`.

### 2.5 Lógica de combinacion (modo "rescue")

En `src/scripts/generar_video_prediccion.py` lineas 543-562, el modo
`--grooming-source rescue` aplica:

```python
elif grooming_source == "rescue":
    probs_rf = np.asarray(probs_groom, dtype=float)
    rescue_mask = (
        (probs_rf >= float(lstm_rescue_rf_threshold))    # default 0.22
        & (probs_rf < float(grooming_confirm_threshold)) # default 0.41
        & (probs_lstm >= float(lstm_rescue_threshold))   # default 0.11
    )
    confident_mask = (
        (probs_rf < float(grooming_confirm_threshold))
        & (probs_lstm >= float(lstm_confident_threshold)) # default 0.50
    )
    elevate_mask = rescue_mask | confident_mask
    probs_groom[elevate_mask] = np.maximum(probs_groom[elevate_mask], confirm_threshold)
```

**Lógica narrativa**: si el RF esta titubeando (entre 0.22-0.41) Y la
LSTM confirma (>= 0.11), elevar a Grooming. Tambien, si la LSTM esta muy
segura (>= 0.50) sin importar RF, elevar.

Esta lógica se introdujo el 2026-05-04 cuando el usuario observo que la
LSTM detectaba pero RF no lo cruzaba al threshold.

### 2.6 Smoothing y eventos

**Smoothing**: rolling mean centrado de 15 frames (`BEHAVIOR_SMOOTHING_FRAMES=15`).

**Threshold operativo Grooming**: 0.41 (`GROOMING_CONFIRM_THRESHOLD`).
**Threshold operativo Thigmotaxis**: 0.30 (`THIGMO_CONFIRM_THRESHOLD`).

**Duración minima evento**: 0.5 s (15 frames @ 30 fps). Eventos mas
cortos se descartan.

### 2.7 Render multimodal

**Script**: `src/scripts/generar_video_prediccion.py`
**Inputs requeridos**:
- `--video`: MP4 original
- `--features`: CSV de features SimBA
- `--model_thigmo`, `--model_grooming`: paths a .sav
- `--output`: nombre del MP4 final
- `--zonas_file`: JSON de ROIs
- `--lstm-grooming-csv`: CSV LSTM (opcional)
- `--grooming-source`: `rf`, `lstm`, `ensemble`, o `rescue`

**Outputs**:
- `{output}.mp4`: video con overlays multimodal
- `{output}_GROOMING_TIMELOG.csv`: eventos Grooming con timestamps
- `{output}_THIGMOTAXIS_TIMELOG.csv`: eventos Thigmotaxis
- `{output}_trajectory.csv`: posicion frame a frame con zona

### 2.8 Pipeline orquestador (one-shot)

**Script**: `src/scripts/run_behavior_pipeline.py --backend yolo --video <path>`

Encadena todos los pasos. Reusa outputs frescos si existen (no recomputa
si los timestamps son OK). Ideal para procesar videos nuevos.

## 3. Scripts auxiliares importantes

### validación blind real (LOO)

| Script | Funcion |
|---|---|
| `src/scripts/leave_one_out_grooming.py` | LOO solo Grooming, retrenando RF Grooming sin held-out |
| `src/scripts/leave_one_out_both.py` | LOO ambos clasificadores SimBA |
| `src/scripts/loo_full_bsoid.py` | LOO completo: SimBA + B-SOiD retrenados, eval triple (SimBA/B-SOiD/Ensemble) |

Todos usan lock file `.leaveoneout.lock` para evitar conflictos.

### B-SOiD experimental

| Script | Funcion |
|---|---|
| `src/scripts/bsoid_extract_features.py` | 51 features ego-centricas desde bridge CSV |
| `src/scripts/bsoid_train.py` | UMAP + HDBSCAN + RF auxiliar |
| `src/scripts/bsoid_evaluate.py` | Compara SimBA / B-SOiD / Ensemble en un video |

### Otros

| Script | Funcion |
|---|---|
| `src/scripts/compute_periodic_features.py` | Features espectrales (FFT, autocorr). NO usadas — SimBA las filtra. |
| `src/scripts/build_yolo_simba_project.py` | Crea proyecto SimBA YOLO desde cero |

## 4. configuración (src/config.py)

Constantes globales del proyecto:

```python
SIMBA_YOLO_BASE                    # proyecto SimBA YOLO
SIMBA_YOLO_PROJECT_DIR             # subfolder project_folder
SIMBA_YOLO_GENERATED_MODELS_DIR    # generated_models/
GROOMING_MODEL_YOLO                # Grooming.sav path
THIGMOTAXIS_MODEL_YOLO             # Thigmotaxis.sav path
```

`run_behavior_pipeline.py` selecciona modelos automaticamente segun `--backend yolo`.

## 5. Entornos Python

El proyecto tiene 2 venvs por compatibilidad:

| venv | Python | Para que |
|---|---|---|
| `venv_310` | 3.10 | SimBA training (compatible con keras 2 y sklearn antigua) |
| `venv_311` | 3.11 | YOLO Pose, scripts modernos, B-SOiD |

Comandos tipicos:
```bash
./venv_310/Scripts/python.exe src/scripts/retrain_simba_models.py --yolo
./venv_311/Scripts/python.exe src/scripts/yolo_pose_to_csv.py --video <path>
./venv_311/Scripts/python.exe src/scripts/generar_video_prediccion.py ...
./venv_311/Scripts/python.exe src/scripts/loo_full_bsoid.py --video <stem>
```

## 6. Estructura de directorios

```
TT_Ratones_2026/
  ├── data/
  │   ├── bsoid_features/                # 51 features ego-centricas (28 csv)
  │   ├── bsoid_models/                  # artifacts B-SOiD
  │   ├── models/lstm_grooming_yolo/     # LSTM (legacy)
  │   └── simba_projects/grooming_thigmotaxis_yolo/
  │       ├── models/generated_models/   # RF combo + backups
  │       └── project_folder/
  │           ├── project_config.ini     # config combo
  │           ├── csv/
  │           │   ├── targets_inserted/  # 26 videos etiquetados
  │           │   ├── features_extracted/# 28 videos con features SimBA
  │           │   └── input_csv/         # bridge YOLO -> SimBA format
  │           └── videos/                # videos para SimBA
  ├── keypoints_yolo/{stem}/             # YOLO outputs por video
  ├── resultados_yolo/{stem}/            # outputs finales por video
  ├── runs/pose/yolo11s_pose_raton_v4/   # YOLO modelo
  ├── src/
  │   ├── config.py
  │   ├── analysis_logic.py              # detectar_thigmotaxis, checar_zona
  │   └── scripts/                       # todos los scripts del pipeline
  ├── reportes/                          # documentacion
  ├── logs/                              # logs de ejecución
  ├── venv_310/, venv_311/               # entornos python
  └── pages/                             # interfaz Streamlit (UI)
```

## 7. código critico de leer en este orden

Si queres entender el sistema (humano o IA cold start), lee en este
orden:

1. `src/config.py` — paths globales
2. `src/scripts/run_behavior_pipeline.py` — orquestador principal
3. `src/scripts/generar_video_prediccion.py` — render multimodal final
   (lógica de rescue, smoothing, etc.)
4. `src/scripts/retrain_simba_models.py` — como se entrenan los RF
5. `src/scripts/loo_full_bsoid.py` — como se válida blind real

Eso da una vision completa en ~30 min de lectura.

## 8. Como procesar un video nuevo (deployment)

```bash
cd c:/Users/chavi/.gemini/antigravity/scratch/TT_Ratones_2026

# Pipeline completo (incluye YOLO, features, LSTM, render)
./venv_311/Scripts/python.exe src/scripts/run_behavior_pipeline.py \
  --backend yolo \
  --video videos_data/MI_VIDEO.mp4
```

O paso a paso:

```bash
# 1. YOLO pose
./venv_311/Scripts/python.exe src/scripts/yolo_pose_to_csv.py \
  --video videos_data/MI_VIDEO.mp4 \
  --output keypoints_yolo/MI_VIDEO/MI_VIDEO_yolo_pose.csv \
  --video-out keypoints_yolo/MI_VIDEO/MI_VIDEO_yolo_keypoints.mp4

# 2. Features SimBA (asume que ya hay un bridge_MI_VIDEO.csv)
# (Se hace automaticamente cuando corres el pipeline o desde la UI)

# 3. LSTM (si keras 2 funciona)
./venv_311/Scripts/python.exe src/scripts/infer_grooming_lstm.py \
  --features data/simba_projects/.../features_extracted/MI_VIDEO.csv \
  --output resultados_yolo/MI_VIDEO/MI_VIDEO_grooming_lstm.csv

# 4. Render multimodal
./venv_311/Scripts/python.exe src/scripts/generar_video_prediccion.py \
  --video data/simba_projects/.../videos/MI_VIDEO.mp4 \
  --features data/simba_projects/.../features_extracted/MI_VIDEO.csv \
  --model_thigmo data/simba_projects/.../Thigmotaxis.sav \
  --model_grooming data/simba_projects/.../Grooming.sav \
  --output resultados_yolo/MI_VIDEO/MI_VIDEO_final.mp4 \
  --zonas_file logs/analysis/zonas_activas.json \
  --grooming-source rescue \
  --lstm-grooming-csv resultados_yolo/MI_VIDEO/MI_VIDEO_grooming_lstm.csv
```

## 9. Como validar blind un video etiquetado (LOO)

```bash
# Asume que el video YA esta en targets_inserted y tiene features
./venv_311/Scripts/python.exe src/scripts/loo_full_bsoid.py --video MI_VIDEO

# El script:
#  1. Hace backup de Grooming.sav, Thigmotaxis.sav, target CSV
#  2. Saca el target de targets_inserted
#  3. Reentrena ambos RF SimBA sin el video (~12 min)
#  4. Reentrena B-SOiD sin el video (~3 min)
#  5. Predice sobre el video held-out
#  6. Reporta métricas SimBA / B-SOiD / Ensemble
#  7. Restaura todo (target + 2 modelos originales)
#  Tiempo total: ~15 min
```
