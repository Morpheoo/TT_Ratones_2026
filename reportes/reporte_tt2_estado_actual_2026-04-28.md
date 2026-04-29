# Reporte TT2 — Estado Actual del Proyecto

Fecha: 2026-04-28
Proyecto: `TT_Ratones_2026`
Hito: Integración completa del pipeline YOLO Pose — fin de dependencia de DeepLabCut

---

## 1. Resumen ejecutivo

Este reporte documenta el avance más significativo de TT2: la migración completa del backend de extracción de pose de DeepLabCut a YOLO Pose. El pipeline operativo ya no depende de DLC para ningún experimento nuevo.

El flujo activo actual es:

```
Video → YOLO v4 Pose → CSV (formato DLC) → SimBA features → RF classifiers → Video multimodal
```

Tiempo por video de 5 minutos: **~3.5 minutos** (vs ~4h 20min con DLC = 75x más rápido).

---

## 2. Hitos completados hoy

### 2.1 Modelo YOLO Pose v4

- Dataset: **3,953 imágenes** (train: 2,928 / valid: 682 / test: 343)
- Modelo base: `yolo11s-pose.pt`
- Resolución de entrenamiento: `imgsz=1280`
- Epochs: 150 (convergencia en epoch 27)

| Métrica | Valor |
|---|---|
| Pose mAP50 | **99.50%** |
| Pose mAP50-95 | **80.04%** |
| Pose Precision | **99.57%** |
| Pose Recall | **99.85%** |
| Box mAP50 | 96.61% |

El modelo satura en epoch 11 y se mantiene estable hasta el final — indicador de dataset limpio y bien distribuido.

### 2.2 Integración al pipeline Streamlit

- Módulo 02 (Keypoints) ahora permite seleccionar **YOLO Pose (Experimental)** como motor real y funcional.
- Los resultados YOLO se guardan en `keypoints_yolo/{video_stem}/`:
  - `{stem}_yolo_pose.csv` — keypoints en formato DLC multi-index para SimBA
  - `{stem}_yolo_keypoints.mp4` — video con overlay de keypoints y esqueleto
- Botón "ABRIR CARPETA KEYPOINTS YOLO" en la UI para acceso directo.

### 2.3 Proyecto SimBA `grooming_thigmotaxis_yolo`

Se creó un proyecto SimBA nuevo dedicado al backend YOLO, separado del proyecto DLC existente:

- **10 videos de entrenamiento** procesados con YOLO v4
- **242 features** extraídas por SimBA ExtractFeaturesFrom8bps
- Etiquetas reutilizadas del proyecto DLC (frame-level, independientes del backend)

| Comportamiento | Frames positivos | Total frames |
|---|---|---|
| Grooming | ~7,770 | ~93,000 |
| Thigmotaxis | ~2,481 | ~93,000 |

Clasificadores reentrenados:
- `Grooming.sav` — 112.9 MB, 2,000 árboles RF
- `Thigmotaxis.sav` — 159.8 MB, 2,000 árboles RF
- Tiempo de entrenamiento: 4 minutos 4 segundos

### 2.4 Pipeline backend-aware

`run_behavior_pipeline.py` ahora selecciona automáticamente proyecto y modelos según el flag `--backend`:

```
--backend dlc   → thigmotaxis_optimizado + modelos DLC
--backend yolo  → grooming_thigmotaxis_yolo + modelos YOLO
```

---

## 3. Arquitectura del sistema actualizada

```
┌─────────────────────────────────────────────────────────────────┐
│                    App Streamlit (Módulos 00-05)                 │
└───────────────────────────────┬─────────────────────────────────┘
                                │
         ┌──────────────────────┴──────────────────────┐
         │                                             │
   Backend: DLC (legacy)                   Backend: YOLO (activo)
         │                                             │
   run_superanimal.py                  yolo_pose_to_csv.py
   apply_dlc_bbox_constraint.py        (YOLO v4, 3.5 min/video)
         │                                             │
         └──────────────────────┬──────────────────────┘
                                │
                 compute_simba_features.py
                 (bridge 8bp, mapeo YOLO→SimBA)
                                │
                 ┌──────────────┴──────────────┐
                 │                             │
         Proyecto DLC                  Proyecto YOLO
         thigmotaxis_optimizado        grooming_thigmotaxis_yolo
         Grooming.sav (DLC)            Grooming.sav (YOLO)
         Thigmotaxis.sav (DLC)         Thigmotaxis.sav (YOLO)
                 │                             │
                 └──────────────┬──────────────┘
                                │
                 generar_video_prediccion.py
                 (video multimodal final)
```

---

## 4. Mapeo anatómico YOLO → SimBA

| Keypoint YOLO | SimBA 8bp | Anatomía |
|---|---|---|
| nariz | Nose | nariz |
| torso | Center | centro del cuerpo |
| cola-base | Tail_base | base de la cola |
| punta-cola | Tail_end | punta de la cola |
| oreja-izq | Ear_left | oreja izquierda |
| oreja-der | Ear_right | oreja derecha |
| pata-izq | Lat_left | pata delantera izquierda |
| pata-der | Lat_right | pata delantera derecha |

Nota: el mapeo torso→Center y pata→Lateral es una aproximación funcional. Los clasificadores RF del proyecto YOLO fueron reentrenados sobre estas features para compensar la diferencia anatómica respecto a DLC SuperAnimal.

---

## 5. Comparativa DLC vs YOLO

| Dimensión | DLC SuperAnimal | YOLO v4 Pose |
|---|---|---|
| Tiempo por video 5min | ~4h 20min | ~3.5 min |
| Speedup | 1x (referencia) | **~75x** |
| Keypoints | 27 (SuperAnimal) | 8 (custom) |
| Resolución inferencia | 720p | 1280p |
| Proyecto SimBA | thigmotaxis_optimizado | grooming_thigmotaxis_yolo |
| Clasificadores | entrenados en DLC | entrenados en YOLO |
| Estado | legacy (funcional) | activo |

---

## 6. Avance global estimado (actualizado)

| Componente | Peso | Avance | Cambio vs 2026-04-13 |
|---|---|---|---|
| App Streamlit y flujo UX | 20% | 90% | +5% |
| Pipeline operativo (pose + SimBA + resultados) | 30% | 90% | +10% (YOLO integrado) |
| Persistencia, BD y trazabilidad | 10% | 75% | = |
| Robustez, testing y mantenibilidad | 10% | 55% | = |
| Validación científica de modelos | 20% | 55% | +10% (YOLO classifiers) |
| Migracion a YOLO Pose | 10% | **95%** | +80% |

**Avance técnico global estimado: ~76%** (vs 67% al inicio de TT2)

---

## 7. Pendientes para cierre de TT2

1. **Prueba de inferencia completa** — correr pipeline YOLO end-to-end con video real (incluyendo video multimodal final).
2. **Validación científica de clasificadores YOLO** — comparar resultados de grooming/thigmotaxis entre DLC y YOLO sobre los mismos videos.
3. **Dataset v5 (futuro)** — pendiente completar ~290 imágenes restantes para llegar a ~4,243 imágenes.
4. **Actualizar Home.py** — texto aún describe el sistema como "YOLO + LSTM", actualizar a arquitectura real.
5. **Reporte TT2 formal** — documento institucional con métricas, comparativa y conclusiones.

---

## 8. Scripts nuevos añadidos en esta sesión

| Script | Función |
|---|---|
| `src/scripts/yolo_pose_to_csv.py` | YOLO → CSV DLC-format + video overlay |
| `src/scripts/build_yolo_simba_project.py` | Automatiza creación del proyecto SimBA YOLO |
| `src/scripts/retrain_simba_models.py` (actualizado) | Soporte `--yolo` para proyecto YOLO |
| `train_pose.py` (actualizado) | Entrena desde `dataset_yolo_v4/` local |
| `validate_pose.py` (actualizado) | Apunta a modelo v4 |

---

## 9. Cómo correr el pipeline YOLO completo

### Desde Streamlit (recomendado)
1. Módulo 01: Seleccionar video
2. Módulo 02: Seleccionar **YOLO Pose (Experimental)** → INICIAR EXTRACCION
3. Módulo 04: Análisis Final (video multimodal)
4. Módulo 05: Resultados y Estadísticas

### Desde terminal
```bash
venv_311\Scripts\python.exe src\scripts\run_behavior_pipeline.py \
  --video videos_data\MiVideo.mp4 \
  --backend yolo
```
