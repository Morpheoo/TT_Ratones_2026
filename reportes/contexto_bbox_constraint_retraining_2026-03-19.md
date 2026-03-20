# Contexto de Avance: Pipeline EPM con DLC + YOLO BBox Constraint + SimBA

Fecha: 2026-03-19  
Proyecto: `TT_Ratones_2026`

## Resumen ejecutivo

El proyecto mejoró de forma importante. Antes, el pipeline producía resultados pobres principalmente porque la pose de DeepLabCut era inestable: varios keypoints se salían del cuerpo del ratón y eso contaminaba las features de SimBA.

Ahora el flujo ya:

1. corre DLC sin downscale,
2. aplica un filtro personalizado guiado por YOLO,
3. genera una pose corregida para SimBA,
4. usa 6 paredes canónicas como ROIs de thigmotaxis,
5. reentrenó modelos en `models/generated_models`,
6. y da resultados cualitativamente mejores en videos nuevos.

La mejora cualitativa se puede resumir así:

- antes: `malo`
- ahora: `decente`

Todavía no está “listo” ni “perfecto”. Siguen apareciendo falsos positivos y algunos bouts reales de grooming no se detectan. Pero la mejora estructural es real.

## Estado actual del pipeline

### Flujo operativo

`Video original o clip recortado -> DLC full-res -> YOLO BBox Constraint -> pose corregida -> compute_simba_features.py -> SimBA -> video multimodal final`

### Downscale

El pipeline nuevo ya no usa downscale cuando el análisis se lanza desde cero.

Eso significa:

- el recorte temporal sigue existiendo,
- pero el clip se conserva a resolución original,
- y DLC ya no trabaja sobre una versión reducida del video.

## Filtro principal de pose

### Qué filtro estamos usando

No estamos usando Savitzky-Golay como filtro principal.

Estamos usando un filtro personalizado basado en YOLO, implementado en:

- [apply_dlc_bbox_constraint.py](c:/Users/chavi/.gemini/antigravity/scratch/TT_Ratones_2026/src/scripts/apply_dlc_bbox_constraint.py)

### Idea central

DeepLabCut estima keypoints frame a frame, pero algunos puntos pueden teletransportarse o caer en posiciones anatómicamente imposibles. Para evitar que SimBA reciba esa señal corrupta, el pipeline usa una detección independiente del ratón con YOLO como restricción espacial fuerte.

### Lógica del filtro

Para cada frame:

1. YOLO detecta al ratón y genera un `bounding box`.
2. Ese bbox se expande con un margen.
3. Cada keypoint DLC se valida contra esa región.
4. Si cae fuera, se invalida.
5. La pose se interpola.
6. Luego se hace una segunda pasada:
   - recheck contra bbox,
   - límite de salto por keypoint,
   - límite radial respecto al centro corporal.
7. Si algo sigue anatómicamente absurdo, se hace un `snap` final al último punto válido o al centro corporal.

### Diferencia contra Savitzky-Golay

Savitzky-Golay sirve para suavizar una señal temporal, pero no sabe si un punto:

- salió del cuerpo,
- saltó a una región imposible,
- o cambió de lugar de forma anatómicamente absurda.

Nuestro filtro no sólo suaviza. Primero decide qué puntos son físicamente imposibles y luego reconstruye la pose usando restricciones espaciales guiadas por YOLO.

### Explicación corta para otra IA

> Este proyecto usa un post-proceso personalizado para DeepLabCut basado en YOLO. En cada frame, YOLO detecta al ratón mediante un bounding box. Cualquier keypoint DLC fuera de esa región expandida por un margen se invalida. Después, la pose se reconstruye con interpolación lineal y una segunda pasada de consistencia espacial que limita saltos entre frames y distancia al centro corporal. Finalmente, si persisten outliers, se reasignan al último punto válido o al centro estimado del cuerpo. Este filtro reemplaza el rol de un suavizado genérico tipo Savitzky-Golay, porque no sólo suaviza la trayectoria, sino que impone restricciones anatómicas guiadas por la detección visual del animal.

## Integración con Streamlit

### Keypoints

Archivo:

- [02_Keypoints.py](c:/Users/chavi/.gemini/antigravity/scratch/TT_Ratones_2026/pages/02_Keypoints.py)

La UI ahora:

- deja claro que el flujo nuevo ya no usa downscale,
- muestra el overlay DLC clásico,
- muestra también el video filtrado `*_bbox_constraint.mp4`,
- y reporta la ruta exacta del MP4 filtrado y de la pose corregida.

### Configuración de zonas

Archivo:

- [03_Configuracion_Zonas.py](c:/Users/chavi/.gemini/antigravity/scratch/TT_Ratones_2026/pages/03_Configuracion_Zonas.py)

La capa de zonas quedó separada así:

- para SimBA y thigmotaxis:
  - `Pared 1`
  - `Pared 2`
  - `Pared 3`
  - `Pared 4`
  - `Pared 5`
  - `Pared 6`
- para visualización/YOLO/conteo por brazos:
  - `Brazo Abierto 1`
  - `Brazo Abierto 2`
  - `Brazo Cerrado 1`
  - `Brazo Cerrado 2`
  - `Centro`

En SimBA se conservan sólo las 6 paredes como ROIs canónicas para no saturar el proyecto.

## Integración con SimBA

Archivos importantes:

- [full_pipeline.py](c:/Users/chavi/.gemini/antigravity/scratch/TT_Ratones_2026/src/scripts/full_pipeline.py)
- [compute_simba_features.py](c:/Users/chavi/.gemini/antigravity/scratch/TT_Ratones_2026/src/scripts/compute_simba_features.py)

Flujo real:

1. DLC genera la pose.
2. `apply_dlc_bbox_constraint.py` produce la pose corregida.
3. Se genera un CSV corregido para el bridge.
4. `compute_simba_features.py` construye el bridge 8bp.
5. Ese bridge entra automáticamente a:
   - `project_folder/csv/input_csv`
   - `project_folder/csv/outlier_corrected_movement_location`
6. Luego SimBA genera:
   - `project_folder/csv/features_extracted/<video>.csv`

No hay que importar manualmente el CSV filtrado en el pipeline actual. El bridge lo hace automáticamente.

## Rebuild del set supervisado

Archivo:

- [rebuild_filtered_training_targets.py](c:/Users/chavi/.gemini/antigravity/scratch/TT_Ratones_2026/src/scripts/rebuild_filtered_training_targets.py)

Objetivo:

- rehacer la pose de videos etiquetados con el filtro bbox,
- regenerar las features de SimBA,
- reconstruir `targets_inserted`,
- conservar las etiquetas históricas de `Grooming` y `Thigmotaxis`.

Se ejecutó sobre 6 videos etiquetados:

- `C1-R1`
- `C2-R1`
- `C56-R1`
- `C7-R1`
- `DZP-R1`
- `R5B20_01mar24`

También se generó un backup de los `targets_inserted` previos.

## Entrenamiento de modelos

### Grooming

Sí existe un nuevo modelo generado en:

- [Grooming.sav](c:/Users/chavi/.gemini/antigravity/scratch/TT_Ratones_2026/data/simba_projects/New%20folder/thigmotaxis_optimizado/models/generated_models/Grooming.sav)

### Thigmotaxis

Al principio parecía que el reentrenamiento no había dejado un `.sav` nuevo. Después se lanzó correctamente el entrenamiento single-model y se confirmó:

- [Thigmotaxis.sav](c:/Users/chavi/.gemini/antigravity/scratch/TT_Ratones_2026/data/simba_projects/New%20folder/thigmotaxis_optimizado/models/generated_models/Thigmotaxis.sav)

con fecha del día `2026-03-19`.

También quedaron sus archivos de evaluación en:

- `models/generated_models/model_evaluations/Thigmotaxis_meta.csv`
- `models/generated_models/model_evaluations/Thigmotaxis_pr_curve.csv`
- `models/generated_models/model_evaluations/Thigmotaxis_feature_importance_log.csv`

## Cambio importante en Análisis Final

Archivos actualizados:

- [04_Analisis_Final.py](c:/Users/chavi/.gemini/antigravity/scratch/TT_Ratones_2026/pages/04_Analisis_Final.py)
- [generar_video_prediccion.py](c:/Users/chavi/.gemini/antigravity/scratch/TT_Ratones_2026/src/scripts/generar_video_prediccion.py)

Antes, `Análisis Final` seguía agarrando modelos viejos de:

- `models/validations`

Ahora la lógica correcta es:

1. preferir:
   - `models/generated_models/Grooming.sav`
   - `models/generated_models/Thigmotaxis.sav`
2. usar `models/validations` sólo como fallback

Esto era crucial, porque si no la app seguía evaluando videos nuevos con modelos viejos aunque SimBA ya hubiera reentrenado otros más recientes.

## Estado cualitativo actual

### Lo bueno

- Las predicciones mejoraron bastante.
- `Thigmotaxis` ya reacciona mejor cuando el ratón está cerca de las paredes.
- El pipeline completo ya no se rompe por falta de features o rutas incorrectas.
- Los videos nuevos se pueden procesar con pose filtrada, zonas y SimBA de punta a punta.

### Lo que sigue mal

- Siguen existiendo falsos positivos.
- `Grooming` sigue siendo la parte más débil.
- Algunos bouts reales no se detectan completos.
- En algunos casos se activa grooming en momentos raros o poco plausibles.

La lectura correcta no es que el sistema esté resuelto, sino que ahora sí estamos viendo errores “de modelo/dataset” y no errores “estructurales del pipeline”.

## Videos nuevos

Se empezaron a probar videos nuevos más limpios y con escenario fijo, por ejemplo:

- `R5C_01mar24.mp4`
- `R6DZ_01mar24.mp4`
- `R6B20_01mar24.mp4`
- `R6YB20_01mar24.mp4`

`R5C` ya se usó como prueba de fuego. La conclusión fue:

- el resultado todavía está lejos de ser excelente,
- pero ya es suficientemente decente como para justificar anotación supervisada adicional.

## Recomendación técnica actual

La mejor siguiente inversión no es reinventar el pipeline, sino:

1. seguir anotando videos nuevos limpios,
2. meter casos como `R5C_01mar24` al aprendizaje supervisado,
3. reentrenar periódicamente con ese dataset expandido,
4. seguir usando el video `*_bbox_constraint.mp4` como control de calidad de pose.

## Opinión técnica

El avance es importante de verdad.

Antes el proyecto tenía una base inestable: aunque SimBA, YOLO o Streamlit estuvieran “bien”, la pose estaba contaminada y todo lo de arriba se volvía engañoso. Ahora ya existe un pipeline coherente:

- pose full-resolution,
- restricción anatómica guiada por YOLO,
- 6 paredes limpias en SimBA,
- modelos recientes en `generated_models`,
- y una mejora visible en videos nuevos.

Todavía falta mejorar mucho, sobre todo con más supervisión y más videos buenos, pero la dirección actual sí es la correcta.

## Próximos pasos sugeridos

1. Anotar supervisadamente `R5C_01mar24`.
2. Validar los otros videos nuevos limpios.
3. Seguir creciendo el set etiquetado.
4. Hacer que `Resultados y Estadísticas` muestre el video final guardado en la base.
5. Cuando el flujo esté más estable, formalizar un documento de pipeline final “cerrado”.
