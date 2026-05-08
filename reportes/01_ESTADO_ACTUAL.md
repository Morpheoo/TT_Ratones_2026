# Pilar 1: Estado actual del proyecto TT_Ratones_2026

Fecha del corte: 2026-05-05
Mantenedor: usuario + asistentes (Claude, Codex)

Este reporte resume QUE TENEMOS Y COMO FUNCIONA ahora mismo. Para
entender como funciona internamente el pipeline ver pilar 2
(`02_PIPELINE_TECNICO.md`). Para saber que viene despues ver pilar 3
(`03_PLAN_MEJORAS.md`).

---

## 1. Objetivo del proyecto

Sistema de deteccion automatica de comportamientos en ratones (laberinto
en cruz, EPM):

- **Grooming**: el raton se acicala (lava cara, cuerpo, etc.).
- **Thigmotaxis**: el raton hace contacto con la pared.
- Tracking de **trayectoria** por zonas (Brazos Abiertos, Brazos Cerrados, Centro).

Output deseado: video multimodal con detector visual en tiempo real,
timelogs CSV de eventos, trayectoria CSV por zona.

## 2. Pipeline operativo (resumen)

```
Video MP4
    -> YOLO Pose v4 (3.5 min)            : keypoints_yolo/{stem}/{stem}_yolo_pose.csv
    -> Bridge SimBA-friendly             : keypoints_yolo/{stem}/bridge_{stem}.csv
    -> SimBA features extraction         : data/simba_projects/grooming_thigmotaxis_yolo/.../features_extracted/{stem}.csv
    -> RF Grooming (combo, 269 MB) + RF Thigmotaxis (combo, 286 MB)
    -> LSTM Grooming rescue (modo "rescue")
    -> Smoothing 15 frames + thresholds operativos
    -> Video multimodal + timelogs + trayectoria
```

Detalles en pilar 2.

## 3. Modelos productivos al 2026-05-05

### 3.1 Modelo YOLO Pose

| Atributo | Valor |
|---|---|
| Path | `runs/pose/yolo11s_pose_raton_v4/weights/best.pt` |
| Dataset | `dataset_yolo_v4/` (3,953 imgs) |
| Pose mAP50 | 99.50% |
| Velocidad | ~3.5 min por video (vs 4h+ con DLC) |
| Status | ACTIVO, validado |

### 3.2 Modelos SimBA RF (configuracion "combo")

| Atributo | Grooming.sav | Thigmotaxis.sav |
|---|---|---|
| Tamano | 268.8 MB | 286.0 MB |
| Generado | 2026-05-05 00:04 | 2026-05-05 02:02 |
| n_estimators | 2000 | 2000 |
| min_samples_leaf | **10** | **10** |
| class_weight | **balanced** | **balanced** |
| under_sample | None | None |
| n_features | 242 | 242 |
| Videos training | 26 | 26 |

Configuracion combo en `data/simba_projects/grooming_thigmotaxis_yolo/project_folder/project_config.ini`,
seccion `[create ensemble settings]`. Esta config fue el fix critico que
saco al modelo del overfitting por animal.

### 3.3 LSTM Grooming (estado)

| Atributo | Valor |
|---|---|
| Path | `data/models/lstm_grooming_yolo/grooming_lstm.keras` |
| Videos training originales | 11 (de cuando se entreno por primera vez) |
| Status | DESACTUALIZADA — hay 26 videos disponibles ahora |
| Compatibilidad | Roto en keras 3 (`File not found .keras zip`); funciona con keras 2 |
| Uso actual en pipeline | Modo `rescue` cuando RF esta entre umbrales |
| Plan | Reentrenar con 26 videos (pendiente, ver pilar 3) |

### 3.4 B-SOiD (experimental)

| Atributo | Valor |
|---|---|
| Path | `data/bsoid_models/bsoid_artifacts_all26_fine.pkl` |
| Configuracion | UMAP 3D, HDBSCAN min_cluster=0.1% (242 frames) |
| Motivos descubiertos | 165 (10+ "puros" de Grooming con P>0.95) |
| Status | Validado en LOO; mejora F1 Grooming en videos donde SimBA falla |
| Integracion al pipeline | NO INTEGRADA AUN — pendiente ensemble condicional |

## 4. Datos etiquetados

| Categoria | Valor |
|---|---|
| Videos en `targets_inserted/` | 26 |
| Frames totales etiquetados | 243,253 |
| Frames Grooming positivos | 20,757 (8.5%) |
| Frames Thigmotaxis positivos | 7,478 (3.1%) |
| Sesiones experimentales | 01mar24, 02mar24 |

### Recomendacion literatura vs realidad

| Comportamiento | Minimo recomendado | Optimo | Tenemos |
|---|---:|---:|---:|
| Thigmotaxis (binario simple) | 15-20 | 30-40 | **26** ✅ |
| Grooming (multiples subtipos) | 40-60 | 80-120 | **26** ⚠️ |

Estamos por debajo del minimo recomendado para Grooming. Esta es la causa
matematica de la varianza alta entre videos en LOO (F1 entre 0.00 y 0.99).

## 5. Validacion blind real (resumen)

Validacion via leave-one-out (sacar video del training, reentrenar,
evaluar sobre el video held-out). 13 videos validados con SimBA + B-SOiD,
7 mas con SimBA solo. Total 20 mediciones blind.

### 5.1 Grooming: 13 videos con full LOO + B-SOiD

| Video | SimBA F1 | B-SOiD F1 | Ensemble OR F1 |
|---|---:|---:|---:|
| R5DZ | 0.10 | 0.39 | 0.33 |
| R5Y20 | 0.99 | 0.14 | 0.79 |
| R5YB20 | 0.99 | 0.14 | 0.80 |
| R6B20 | 0.00 | **0.82** | 0.80 |
| R6C | 0.91 | 0.06 | 0.59 |
| R6DZ | 0.00 | 0.20 | 0.20 |
| R6YB15 | 0.01 | 0.29 | 0.26 |
| R6YB20 | 0.22 | 0.23 | 0.32 |
| R7B20 | 0.92 | 0.69 | 0.82 |
| R7Y20 | 0.22 | 0.30 | 0.43 |
| R7YB20 | 0.00 | **0.43** | 0.41 |
| R7YB5 | 0.77 | 0.56 | 0.78 |
| R8C | 0.68 | 0.65 | 0.77 |
| **PROMEDIO** | **0.45** | **0.38** | **0.56** |

### 5.2 Thigmotaxis: 13 videos con full LOO

| Video | SimBA F1 | B-SOiD F1 |
|---|---:|---:|
| R5DZ | 0.60 | 0.32 |
| R5Y20 | 0.66 | — |
| R5YB20 | 0.75 | — |
| R6B20 | 0.73 | — |
| R6C | 0.50 | — |
| R6DZ | 0.53 | 0.32 |
| R6YB15 | 0.53 | — |
| R6YB20 | 0.68 | — |
| R7B20 | 0.08 | — |
| R7Y20 | 0.77 | 0.37 |
| R7YB20 | 0.75 | 0.60 |
| R7YB5 | 0.21 | 0.26 |
| R8C | 0.75 | 0.56 |
| **PROMEDIO** | **0.58** | — |

### 5.3 Patrones clave observados

1. **Grooming SimBA tiene varianza ENORME** (F1 0.00 a 0.99). Algunos
   animales generalizan bien, otros no.

2. **Cuando SimBA Grooming "cae al piso" (F1<0.3), B-SOiD suele rescatar**:
   - R6B20: SimBA 0.00 → B-SOiD 0.82 ✅
   - R7YB20: SimBA 0.00 → B-SOiD 0.43 ✅
   - R6DZ: SimBA 0.00 → B-SOiD 0.20 ✅

3. **Cuando SimBA Grooming es fuerte (F1>0.7), B-SOiD HIERE el ensemble**:
   - R5Y20: SimBA 0.99 → Ensemble 0.79 ❌
   - R6C: SimBA 0.91 → Ensemble 0.59 ❌

4. **Thigmotaxis: SimBA es claramente mejor**. B-SOiD sobre-predice
   masivamente (precision 0.13-0.40). Thigmotaxis es de baja complejidad
   y SimBA con 26 videos ya esta bien.

5. **Promedio actual blind real**:
   - Grooming SimBA solo: F1 = 0.45 (debajo del umbral deployable de 0.85)
   - Grooming Ensemble OR: F1 = 0.56 (mejor pero aun insuficiente)
   - Thigmotaxis SimBA: F1 = 0.58

## 6. Lecciones aprendidas en este proyecto

1. **F1 interno de SimBA (split random) sobreestima dramaticamente**: el
   F1 = 0.998 reportado por SimBA con split random era leakage. F1 blind
   real es 0.45 promedio.

2. **El primer instinto de "datos corruptos" o "modelo degradado" suele
   ser equivocado**: lo que parecia ser etiquetas faltantes (R7DZ, R8DZ
   con thigmotaxis = 0) eran etiquetas correctas. Lo que parecia ser
   degradacion del modelo eran cambios de threshold mal interpretados
   (0.41 era el umbral de discriminacion, no el F1).

3. **Regularizacion > features adicionales**: el cambio que mas movio la
   aguja fue cambiar 3 hiperparametros del RF (`min_leaf=10`,
   `class_weight=balanced`, `under_sample=None`). Las features periodicas
   computadas no aportaron nada (SimBA las filtro silenciosamente).

4. **B-SOiD como ensemble es valioso pero condicional**: ayuda solo cuando
   SimBA falla. Cuando SimBA es fuerte, B-SOiD agrega FPs.

5. **El usuario tiene mejor intuicion que las metricas internas para
   detectar problemas reales**: la observacion del usuario sobre R7YB20
   (`el modelo queria detectar grooming pero no se animaba`) llevo
   directamente al diagnostico de regularizacion.

## 7. Limitaciones reconocidas

1. **Dataset tamano**: 26 videos para Grooming esta debajo del minimo
   recomendado de 40-60 por la literatura (B-SOiD paper, SimBA validation).

2. **LSTM desactualizada**: sigue entrenada con 11 videos.

3. **B-SOiD no integrado al pipeline operativo**: solo experimental hasta
   que se implemente ensemble condicional.

4. **Etiquetas humanas son de un solo observador**: no hay validacion
   inter-observador.

5. **Variabilidad por animal**: el modelo aprende patrones especificos
   por animal mas que la firma transversal del comportamiento.

## 8. Archivos productivos clave

```
runs/pose/yolo11s_pose_raton_v4/weights/best.pt         # YOLO pose v4
data/models/lstm_grooming_yolo/grooming_lstm.keras       # LSTM (legacy 11 videos)
data/simba_projects/grooming_thigmotaxis_yolo/
    models/generated_models/
        Grooming.sav                                    # RF combo 269 MB
        Thigmotaxis.sav                                 # RF combo 286 MB
    project_folder/
        project_config.ini                              # config combo aplicada
        csv/
            targets_inserted/                           # 26 videos etiquetados
            features_extracted/                         # 28 videos con features SimBA
data/bsoid_features/                                    # 28 videos con features ego-centricas (51 cols)
data/bsoid_models/bsoid_artifacts_all26_fine.pkl        # B-SOiD pipeline entrenado
```

## 9. Reportes vivos en este folder

- `01_ESTADO_ACTUAL.md` (este) — estado y metricas actuales
- `02_PIPELINE_TECNICO.md` — como funciona el pipeline end-to-end
- `03_PLAN_MEJORAS.md` — que sigue (5 mejoras priorizadas)
- `SETUP_COLABORADOR.md` — setup del entorno para nuevos colaboradores
