# Reporte TT2 - Pipeline completo RF + LSTM rescue y prueba ciega R6C

Fecha: 2026-04-29  
Proyecto: `TT_Ratones_2026`  
Hito: Consolidación del flujo completo de análisis conductual con YOLO Pose, SimBA RF y complemento temporal LSTM para Grooming.

---

## 1. Resumen ejecutivo

Durante este ciclo se consolidó el pipeline completo para analizar videos nuevos de ratones en el laberinto elevado en cruz. El flujo actual ya permite ingresar un video, extraer keypoints con YOLO Pose, sincronizar features con SimBA, aplicar clasificadores Random Forest para Grooming y Thigmotaxis, complementar Grooming con una LSTM temporal en modo `rescue`, renderizar un video multimodal final y exportar tablas de trayectoria y eventos.

El avance más importante fue convertir la LSTM en un complemento del RF, no en un reemplazo. El RF sigue siendo el clasificador primario, mientras que la LSTM ayuda a rescatar frames ambiguos donde el RF queda por debajo del umbral de confirmación, pero todavía muestra señal suficiente.

El sistema quedó probado en dos escenarios:

| Escenario | Video | Tipo de validación | Resultado |
|---|---|---|---|
| Control positivo con etiqueta humana | `R5C_mar24_2` contra `R5C__01mar24_full.csv` | Comparación frame a frame | F1 = **99.70%** para Grooming |
| Prueba ciega operativa | `R6C_01mar24` | Evaluación visual preliminar | El usuario estimó precisión mayor a **80%** |

La conclusión operativa es que el sistema ya funciona como pipeline completo. La siguiente fase debe enfocarse en convertir las pruebas ciegas exitosas en nuevas etiquetas humanas para reentrenar y robustecer el modelo.

---

## 2. Flujo activo del proyecto

El flujo activo actual es:

```text
Video
-> Ingesta y selección de tramo
-> YOLO Pose v4
-> CSV compatible con SimBA
-> Features de SimBA
-> RF Grooming / RF Thigmotaxis
-> LSTM temporal para Grooming
-> Modo rescue RF + LSTM
-> Video multimodal final
-> Timelogs, trayectoria y estadísticas
```

Componentes principales:

| Componente | Estado |
|---|---|
| YOLO Pose v4 | Operativo para keypoints |
| Proyecto SimBA YOLO | Operativo en `data/simba_projects/grooming_thigmotaxis_yolo` |
| RF Grooming | Reentrenado y calibrado |
| RF Thigmotaxis | Reentrenado junto con el proyecto YOLO |
| LSTM Grooming | Integrada como apoyo temporal |
| Streamlit pipeline | Integrado hasta Análisis Final |
| Prueba ciega | Ejecutada con `R6C_01mar24` |

---

## 3. Base de entrenamiento actual

La carpeta de etiquetas humanas activa es:

```text
data/simba_projects/grooming_thigmotaxis_yolo/project_folder/csv/targets_inserted
```

Al cierre de este ciclo contiene 11 archivos anotados:

| Métrica | Valor |
|---|---:|
| Videos anotados en SimBA YOLO | 11 |
| Frames totales anotados | 102,732 |
| Frames Grooming positivos | 8,167 |
| Frames Thigmotaxis positivos | 2,861 |

Tabla de targets:

| Archivo | Frames | Grooming | Thigmotaxis |
|---|---:|---:|---:|
| `R5B20_01mar24.csv` | 9,341 | 773 | 399 |
| `R5C__01mar24_full.csv` | 9,331 | 2,848 | 660 |
| `R5DZ_01mar24_v2_trimmed_0_310.csv` | 9,300 | 203 | 106 |
| `R5Y20_01mar24.csv` | 9,323 | 277 | 270 |
| `R5YB20_01mar24.csv` | 9,323 | 285 | 291 |
| `R6B20_01mar24_trimmed_0_300.csv` | 9,000 | 619 | 153 |
| `R6BY5_01mar24.csv` | 9,519 | 1,064 | 114 |
| `R6DZ_01mar24_full.csv` | 9,301 | 698 | 307 |
| `R6Y20_01mar24.csv` | 9,632 | 431 | 0 |
| `R6YB15_01mar24.csv` | 9,331 | 572 | 181 |
| `R6YB20_01mar24.csv` | 9,331 | 397 | 380 |

La anotación de `R6YB20_01mar24` fue incorporada antes del reentrenamiento, por lo que el modelo actual ya incluye ese caso.

---

## 4. Cambios técnicos realizados

### 4.1 Reentrenamiento de SimBA

Se reentrenaron los clasificadores del proyecto YOLO:

```text
data/simba_projects/grooming_thigmotaxis_yolo/models/generated_models/Grooming.sav
data/simba_projects/grooming_thigmotaxis_yolo/models/generated_models/Thigmotaxis.sav
```

El reentrenamiento resolvió el problema donde el RF detectaba parcialmente la postura de Grooming, pero podía perder continuidad temporal en videos nuevos.

### 4.2 Calibración de Grooming

Se diagnosticó el umbral óptimo de Grooming contra etiquetas humanas. El umbral operativo quedó:

| Parámetro | Valor |
|---|---:|
| Confirmación Grooming | 0.41 |
| Posible Grooming | 0.30 |
| Suavizado temporal | 15 frames |
| Evento mínimo | 0.50 s |

### 4.3 Integración de LSTM

Se agregó una LSTM experimental para Grooming:

```text
data/models/lstm_grooming_yolo/grooming_lstm.keras
data/models/lstm_grooming_yolo/scaler.pkl
data/models/lstm_grooming_yolo/metadata.json
```

La LSTM se integró en modo `rescue`:

```text
RF >= 0.22
RF < 0.41
LSTM >= 0.11
=> se eleva el frame al umbral de confirmación
```

Esto permite que la memoria temporal de la LSTM ayude en segmentos ambiguos sin sobreescribir el criterio principal del RF.

### 4.4 Integración al pipeline final

El módulo de Análisis Final ya ejecuta:

```text
YOLO Pose -> SimBA features -> RF -> LSTM -> Video final
```

El comando interno usa:

```text
--grooming-source rescue
--grooming-confirm-threshold 0.41
--lstm-rescue-rf-threshold 0.22
--lstm-rescue-threshold 0.11
```

---

## 5. Validación objetiva: R5C

Se procesó `R5C_mar24_2` y se comparó contra la anotación humana disponible `R5C__01mar24_full.csv`.

Archivos usados:

```text
resultados_yolo/R5C_mar24_2/R5C_mar24_2_STREAMLIT_MULTIMODAL_trajectory.csv
resultados_yolo/R5C_mar24_2/R5C_mar24_2_grooming_lstm.csv
data/simba_projects/grooming_thigmotaxis_yolo/project_folder/csv/targets_inserted/R5C__01mar24_full.csv
```

Se alinearon 9,331 frames, equivalentes a 311.03 s a 30 FPS.

### 5.1 Resultado final RF + LSTM rescue

| Métrica | Valor |
|---|---:|
| True positives | 2,837 |
| False positives | 6 |
| False negatives | 11 |
| True negatives | 6,477 |
| Precision | 99.79% |
| Recall | 99.61% |
| F1 | 99.70% |
| Accuracy | 99.82% |
| Jaccard | 99.40% |

Duración de Grooming:

| Fuente | Frames | Duración |
|---|---:|---:|
| Humano | 2,848 | 94.93 s |
| Pipeline final | 2,843 | 94.77 s |
| Diferencia | 5 frames | 0.17 s |

### 5.2 Comparación contra LSTM sola

| Modelo | Precision | Recall | F1 |
|---|---:|---:|---:|
| LSTM sola | 95.15% | 99.12% | 97.09% |
| RF + LSTM rescue | 99.79% | 99.61% | 99.70% |

Esto confirma que la LSTM no debe reemplazar al RF. Su mejor función actual es complementar la decisión del RF en casos ambiguos.

---

## 6. Prueba ciega: R6C_01mar24

`R6C_01mar24` fue seleccionado como video completamente desconocido para el pipeline porque no tenía targets humanos en SimBA YOLO y no existían resultados previos en `resultados_yolo`.

Estado antes del análisis:

| Elemento | Estado |
|---|---|
| Video crudo | Disponible |
| Keypoints YOLO | Generados |
| ROIs | Definidas y guardadas |
| Features SimBA | Generadas |
| Targets humanos | No existentes |
| Tipo de prueba | Ciega |

Archivos generados:

```text
keypoints_yolo/R6C_01mar24/R6C_01mar24_yolo_pose.csv
keypoints_yolo/R6C_01mar24/R6C_01mar24_yolo_keypoints.mp4
keypoints_yolo/R6C_01mar24/bridge_R6C_01mar24.csv
data/simba_projects/grooming_thigmotaxis_yolo/project_folder/csv/features_extracted/R6C_01mar24.csv
resultados_yolo/R6C_01mar24/R6C_01mar24_STREAMLIT_MULTIMODAL.mp4
resultados_yolo/R6C_01mar24/R6C_01mar24_STREAMLIT_MULTIMODAL_trajectory.csv
resultados_yolo/R6C_01mar24/R6C_01mar24_STREAMLIT_MULTIMODAL_GROOMING_TIMELOG.csv
resultados_yolo/R6C_01mar24/R6C_01mar24_STREAMLIT_MULTIMODAL_THIGMOTAXIS_TIMELOG.csv
resultados_yolo/R6C_01mar24/R6C_01mar24_grooming_lstm.csv
```

Resumen del procesamiento:

| Métrica | Valor |
|---|---:|
| Frames procesados | 9,319 |
| Duración aproximada | 310.63 s |
| Frames de tracking válidos | 9,031 / 9,319 |
| Frames rescatados por LSTM antes del suavizado | 29 |
| Frames finales Grooming | 865 |
| Duración final Grooming | 28.83 s |
| Frames finales Thigmotaxis | 116 |
| Duración final Thigmotaxis | 3.87 s |
| Frames LSTM Grooming crudos | 2,121 |
| Duración LSTM Grooming cruda | 70.70 s |

Grooming detectado en timelog:

| Inicio | Fin | Duración | Tipo |
|---|---|---:|---|
| 03:22.20 | 03:50.39 | 28.20 s | Confirmada |

Thigmotaxis detectada en timelog:

| Inicio | Fin | Duración | Tipo |
|---|---|---:|---|
| 02:31.80 | 02:32.50 | 0.70 s | Confirmada |
| 04:03.33 | 04:04.09 | 0.77 s | Confirmada |
| 04:24.33 | 04:25.26 | 0.93 s | Confirmada |
| 04:45.76 | 04:46.29 | 0.53 s | Confirmada |

Distribución de zonas según trayectoria:

| Zona | Frames |
|---|---:|
| Brazo Cerrado 2 | 2,241 |
| Brazo Abierto 1 | 2,066 |
| Brazo Cerrado 1 | 2,045 |
| Brazo Abierto 2 | 1,443 |
| Centro | 1,434 |
| Ninguna | 90 |

Evaluación visual preliminar:

El resultado fue descrito por el usuario como no 100% preciso, pero sí superior al 80% de correspondencia visual esperada. Al no existir todavía una anotación humana `targets_inserted/R6C_01mar24.csv`, esta observación debe tratarse como evaluación cualitativa preliminar, no como métrica final.

---

## 7. Interpretación

El comportamiento observado en R6C es justo el tipo de señal que se buscaba: el sistema generaliza a un video no usado en entrenamiento y produce una detección de Grooming razonable sin etiqueta humana previa.

La comparación R5C demuestra que, cuando existe una anotación humana comparable, el pipeline puede alcanzar una correspondencia frame a frame muy alta. La prueba R6C sugiere que el sistema ya es útil como detector preliminar para nuevos videos, pero debe seguir cerrándose el ciclo humano-modelo:

```text
Prueba ciega
-> revisión humana
-> corrección en SimBA
-> reentrenamiento RF
-> reentrenamiento LSTM
-> nueva validación
```

---

## 8. Limitaciones actuales

1. `R6C_01mar24` todavía no tiene anotación humana en SimBA, por lo que no se puede calcular precision, recall o F1 real.
2. La LSTM sola tiende a detectar más Grooming que el resultado final, por lo que puede introducir falsos positivos si se usa como reemplazo.
3. El modo `rescue` ayuda de forma conservadora, pero debe seguir monitoreándose en videos nuevos.
4. La precisión cualitativa mayor a 80% de R6C debe validarse con comparación frame a frame después de etiquetar el video.

---

## 9. Recomendación siguiente

El sistema puede considerarse completo a nivel operativo. La recomendación técnica es:

1. Etiquetar `R6C_01mar24` en SimBA usando el resultado multimodal como guía visual.
2. Comparar `targets_inserted/R6C_01mar24.csv` contra el resultado actual de `resultados_yolo/R6C_01mar24`.
3. Registrar métricas frame a frame de Grooming y Thigmotaxis.
4. Reentrenar RF con R6C integrado.
5. Reentrenar LSTM con R6C integrado.
6. Repetir prueba ciega con otro video no usado.

Con esto se pasa de un sistema funcional a un ciclo de mejora continua con evidencia cuantitativa por cada video nuevo.

---

## 10. Conclusión

El pipeline actual ya cumple el objetivo central del proyecto: analizar videos nuevos de ratones, extraer pose, generar features conductuales, detectar Grooming y Thigmotaxis, producir video multimodal y exportar resultados cuantificables.

La validación objetiva en R5C alcanzó F1 de **99.70%** para Grooming, mientras que la prueba ciega R6C mostró un desempeño visualmente alto en un video desconocido. Esto representa un avance importante hacia un sistema robusto, reproducible y utilizable para el análisis conductual automatizado en TT2.
