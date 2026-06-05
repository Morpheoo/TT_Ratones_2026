# Pilar 3: Plan de mejoras pendientes

Fecha: 2026-05-05
Contexto: F1 promedio Grooming blind = 0.45, Thigmotaxis = 0.58. Objetivo
deployable es F1 >= 0.85 promedio. Ver pilar 1 para métricas. Ver pilar 2
para detalles tecnicos.

---

## 1. Diagnostico raiz del problema

**El proyecto tiene 26 videos etiquetados. La literatura cientifica
recomienda 40-60 minimo para Grooming**. Estamos 30-50% debajo del minimo.

Sintoma: el RF aprende patrones especificos por animal mas que la firma
transversal del comportamiento. Resultado: F1 varia entre 0.00 y 0.99
segun el animal en LOO blind.

**Solución definitiva**: etiquetar 14-30 videos mas (cuando esten
disponibles).

**Solución intermedia (este plan)**: exprimir lo que tenemos con tecnicas
de ensemble, augmentation y modelos complementarios. Objetivo realista
con 26 videos: F1 ~0.70-0.80.

## 2. Las 5 mejoras priorizadas

| # | Mejora | Esfuerzo | Ganancia esperada F1 Grooming | Pre-requisitos |
|---:|---|---|---:|---|
| 1 | **Ensemble condicional** | 30 min | +0.10 - 0.15 | B-SOiD ya entrenado ✅ |
| 2 | **Mirror augmentation** (52 videos efectivos) | 60 min | +0.10 - 0.15 | nada |
| 3 | **Reentrenar LSTM con 26 videos** | 60 min | +0.05 - 0.10 | resolver compatibilidad keras 2 |
| 4 | **Bagging multi-semilla SimBA** | 90 min | +0.03 - 0.05 | nada |
| 5 | **Calibracion threshold por video** | 30 min | +0.02 - 0.05 | nada |

**Combinadas, proyeccion F1 Grooming blind: 0.45 → 0.70 - 0.80** (no
estrictamente aditivas; hay solapamiento en el efecto).

## 3. Mejora #1: Ensemble condicional

### 3.1 Justificacion

Los datos de los 13 LOO con full B-SOiD muestran patron claro:

- Cuando SimBA Grooming F1 < 0.30: ensemble OR rescata (+0.20 - 0.80 pp)
- Cuando SimBA Grooming F1 > 0.70: ensemble OR HIERE (-0.10 - 0.32 pp)

Si tuvieramos un oraculo que escogiera el mejor entre SimBA solo y
ensemble por video, el promedio seria F1 = 0.62 (vs 0.56 ensemble OR
siempre, vs 0.45 SimBA solo).

### 3.2 Regla propuesta

Sin ground truth en deployment, aproximamos el oraculo con un detector
de catastrofe SimBA:

```
PARA CADA VIDEO:
  predicciones_simba = SimBA RF predict_proba(features)
  count_pos_simba = sum(predicciones_simba >= 0.41)

  SI count_pos_simba >= UMBRAL_MINIMO (e.g., 100 frames = 3.3 s):
    USAR SOLO SimBA  (modelo confiado en si mismo)
  ELSE:
    activar B-SOiD prediction
    USAR (SimBA RF >= 0.41) OR (B-SOiD motif P_grooming >= 0.5)
```

Threshold UMBRAL_MINIMO sugerido: 100 frames. Tunear con datos.

### 3.3 Implementacion

Archivo a modificar: `src/scripts/generar_video_prediccion.py`

1. Agregar nuevo `--grooming-source ensemble_conditional`
2. Cargar artefactos B-SOiD desde `data/bsoid_models/bsoid_artifacts_all26_fine.pkl`
3. En la rama `ensemble_conditional`:
   - Predecir con SimBA RF (código actual)
   - Contar positivos
   - Si > umbral: continuar como `rf` source
   - Si <= umbral: predecir B-SOiD (cargar features ego-centricas, RF auxiliar predice motivo, mapear a P_grooming) y aplicar OR
4. Agregar CLI args `--bsoid-artifacts`, `--ensemble-min-pos-frames`

Tambien actualizar `src/scripts/run_behavior_pipeline.py` para pasar
estos args.

### 3.4 Validación

Re-correr `loo_full_bsoid.py` modificado para que evalue tambien la
estrategia `ensemble_conditional`. Comparar promedios contra los 13 LOO
existentes.

**Criterio de éxito**: F1 promedio Grooming blind >= 0.60 (vs 0.56
ensemble siempre).

## 4. Mejora #2: Mirror augmentation

### 4.1 Justificacion

Validamos en 2026-05-04 con test de espejo que el modelo NO tiene bias
direccional fuerte (mirror cambia detecciones <2%). Esto significa que
los ratones se acicalan/hacen thigmotaxis con kinetica simetrica
respecto al eje X. Podemos generar datos sinteticos espejeando.

**Dataset efectivo: 26 → 52 videos** (acercando al minimo recomendado de
40-60 para Grooming).

Es una técnica estandar en computer vision (data augmentation).

### 4.2 Procedimiento

Para cada video en training:

1. Leer pose YOLO (`bridge_{stem}.csv`).
2. Aplicar transformaciones de espejo:
   - `x' = 1280 - x` (flip horizontal en imagen 1280x720)
   - **Swap left ↔ right** en pares simetricos:
     - `Ear_left ↔ Ear_right`
     - `Lat_left ↔ Lat_right`
     - (NO swap `Nose`, `Center`, `Tail_base`, `Tail_end` — son axiales)
3. Recomputar features SimBA con la pose espejada.
4. Las etiquetas humanas (Grooming, Thigmotaxis) se mantienen identicas.
5. Guardar como nuevo video sintetico: `{stem}_MIRROR`.

### 4.3 Implementacion

Nuevo script: `src/scripts/mirror_augmentation.py`

1. Para cada `bridge_{stem}.csv`:
   - Aplicar flip y swap
   - Guardar como `bridge_{stem}_MIRROR.csv`
2. Recomputar features SimBA → `features_extracted/{stem}_MIRROR.csv`
3. Copiar target CSV → `targets_inserted/{stem}_MIRROR.csv`
4. Actualizar `video_info.csv` de SimBA con los nuevos nombres
5. Reentrenar RF Grooming + Thigmotaxis con 52 videos (combo config)

### 4.4 Riesgos

- Si la camara tiene asimetria sistematica (montaje no perfectamente
  simetrico), el mirror introduce ruido. Verificación: revisar que
  zonas_activas.json sea simetrica respecto a x=640.
- El B-SOiD requiere reentreno tambien (las features ego-centricas
  cambian).

### 4.5 Validación

LOO blind sobre los videos originales (no sobre los espejos), con el
modelo entrenado en 52 videos. Comparar F1 promedio vs el actual (0.45
SimBA solo, 0.56 ensemble).

**Criterio de éxito**: F1 promedio Grooming blind sube al menos +0.10
respecto a usar solo 26 videos.

## 5. Mejora #3: Reentrenar LSTM con 26 videos

### 5.1 Justificacion

LSTM actual esta entrenada con 11 videos (de cuando empezo el proyecto).
Con 26 videos disponibles, deberia mejorar en videos donde el RF se
queda corto.

### 5.2 Pre-requisito: arreglar compatibilidad keras

LSTM esta en formato `.keras` HDF5 antiguo. keras 3 no lo carga
directamente. Soluciones:
- Instalar keras 2 en un venv separado y usar ese para inferencia
- Re-entrenar el modelo desde cero con keras 3 (mas limpio)

### 5.3 Procedimiento

1. Buscar `src/scripts/train_grooming_lstm.py` (o equivalente — en el
   repo seguro existe). Revisar su CLI.
2. Asegurar que recibe el feature set actual (242 features SimBA).
3. Ejecutar entrenamiento con los 26 videos:
   - Train/val split estratificado
   - Hyperparameters: similares al modelo actual, pero con mas epochs
     porque hay mas datos
4. Guardar nuevo modelo en formato compatible con keras 3
   (formato `.keras` zip o HDF5 explicito).
5. Actualizar `data/models/lstm_grooming_yolo/grooming_lstm.keras` y
   metadata.json (best_threshold, etc.).

### 5.4 Validación

LOO blind sobre los mismos 13 videos validados anteriormente. Comparar
F1 con la regla `rescue` modificada (RF + LSTM nueva).

**Criterio de éxito**: F1 promedio Grooming blind sube +0.05 respecto a
RF solo. Idealmente sube +0.10.

## 6. Mejora #4: Bagging multi-semilla SimBA

### 6.1 Justificacion

El RF actual usa un solo random_state. Con dataset pequeno (26 videos)
hay mucha varianza segun que subset de frames toca cada arbol. Bagging =
entrenar 5-10 RFs con seeds diferentes y promediar predicciones.

Reduce overfitting a particularidades del split de training y suaviza
la sensibilidad a animales especificos.

### 6.2 Procedimiento

1. Modificar `retrain_simba_models.py` para aceptar `--n-models 5` que
   genera 5 RF independientes con random_state distinto.
2. Guardar como `Grooming_seed01.sav`, `Grooming_seed02.sav`, ..., 
   `Grooming_seed05.sav`.
3. En `generar_video_prediccion.py`, modificar la carga del modelo para
   aceptar lista de modelos. Predecir con cada uno y promediar.
4. Costo: 5x el tamano en disco (5 x 269 MB = 1.35 GB). Aceptable.

### 6.3 Validación

LOO blind con bagging activado. Esperamos varianza reducida entre
videos (menos catastrofes F1=0).

**Criterio de éxito**: maxima diferencia F1 entre videos blind se reduce
en al menos 30%. Por ejemplo, si actual rango es [0.00, 0.99], con
bagging deberia ser [0.30, 0.95].

## 7. Mejora #5: Calibracion threshold por video

### 7.1 Justificacion

Threshold operativo fijo 0.41 puede no ser optimo para todos los
videos. Calibracion dinámica basada en la distribucion de probabilidades
predichas.

### 7.2 Procedimiento

Al predecir un video:
1. Computar histograma de predicciones SimBA.
2. Si la distribucion esta sesgada hacia probabilidades bajas (ej. 99%
   de frames con prob<0.2), bajar threshold operativo a 0.30.
3. Si esta sesgada alta (>5% de frames con prob>0.6), subir a 0.50.

Esto es heuristico. Puede integrarse con la mejora #1 (ensemble
condicional).

### 7.3 Validación

LOO blind con calibracion. Comparar F1.

**Criterio de éxito**: F1 promedio +0.02 - 0.05.

## 8. Orden recomendado de ejecución

```
[1] Ensemble condicional         → milestone: F1 0.45 → 0.55-0.60
[2] Mirror augmentation          → milestone: F1 0.55 → 0.65-0.70
[3] LSTM reentreno               → milestone: F1 0.65 → 0.70-0.75
[4] Bagging                      → milestone: F1 0.70 → 0.72-0.78
[5] Calibracion threshold        → milestone: F1 +0.02-0.05 final
```

Después de cada paso, hacer LOO blind sobre los 13 videos. Si un paso
no aporta, revisar antes de seguir.

## 9. Checkpoint cada paso

Después de implementar cada mejora, generar reporte:
- `reportes/checkpoint_M{n}_{nombre}_{fecha}.md`
- Incluir tabla LOO completa
- Comparar con baseline anterior
- Decidir continuar o revisar

## 10. Lo que NO esta en el plan (descartado)

- **Switching a Keypoint-MoSeq**: requeriria reescribir buena parte del
  pipeline. Complejidad no justificable con ganancia incierta dado
  problema raiz (datos limitados).
- **Subclasificacion B-SOiD de tipos de grooming** (paw/face vs head vs
  body): bonita pero no critica. Hacer después si las mejoras 1-5 dan
  el F1 deployable.
- **Features periodicas custom** (FFT, autocorr): SimBA las filtra
  silenciosamente. No vale la pena pelearse con SimBA — hay que
  parchear su pipeline o usar otro framework. Las features ego-centricas
  ya capturan la firma temporal via ventanas y velocidades.

## 11. solución definitiva (cuando haya recursos)

**Etiquetar 14-30 videos mas** llevaria el dataset a 40-60, en el rango
recomendado por la literatura para Grooming. Esto NO se puede hacer
ahora (usuario sin acceso a mas videos), pero deberia ser la prioridad
absoluta cuando recursos lo permitan.

Con 50+ videos etiquetados, el RF probablemente alcanzaria F1 blind 0.85+
sin necesidad de B-SOiD u otros tricks. La mayoria de las mejoras
listadas aqui se vuelven innecesarias.

## 12. Referencias

- Plan original que llevo a este: `plan_mejora_grooming_segmentacion_motivos_2026-05-04.md` (sera borrado)
- Datos LOO blind base: ver pilar 1, seccion 5
- B-SOiD paper: https://www.nature.com/articles/s41467-021-25420-x
- Keypoint-MoSeq: https://www.nature.com/articles/s41592-024-02318-2
- SimBA validation: https://www.nature.com/articles/s41386-022-01473-4
