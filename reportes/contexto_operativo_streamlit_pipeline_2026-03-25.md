# Contexto Operativo Streamlit + DLC + SimBA + Resultados

Fecha: 2026-03-25  
Proyecto: `TT_Ratones_2026`  
Objetivo de este documento: dejar contexto completo para otra IA o para una futura sesión, evitando pérdida de continuidad por desconexiones, reinicios de Streamlit, cambios de pestaña o estados intermedios no persistidos.

---

## 1. Estado general al 25 de marzo de 2026

Se logró un avance importante: el flujo real de la app ya funciona de punta a punta.

La cadena operativa actual es:

`Ingesta -> Keypoints -> Configuración de Zonas -> Análisis Final -> Resultados y Estadísticas`

Y el pipeline técnico real quedó así:

`Video / clip recortado -> DLC SuperAnimal -> filtro YOLO BBox Constraint -> bridge a SimBA -> features -> video multimodal final -> persistencia en BD -> dashboard`

Lo más importante:

- ya se puede correr un video real completo,
- ya se generan keypoints y pose filtrada,
- ya se importa el video y la pose al proyecto activo de SimBA,
- ya se pueden sincronizar automáticamente las 6 paredes como ROIs de SimBA,
- ya se genera el video final multimodal,
- ya se guarda `trajectory_path` en la base de datos,
- y ya existe una pantalla funcional de resultados con métricas y gráficas reales.

No se pidió seguir moviendo diseño visual. El diseño quedó suficientemente bien. Lo que sigue es afinación científica y robustez.

---

## 2. Rutas y activos clave

### Proyecto base

- Raíz del repo: `C:\Users\chavi\.gemini\antigravity\scratch\TT_Ratones_2026`

### Proyecto SimBA activo

- Base SimBA: `data/simba_projects/New folder/thigmotaxis_optimizado`
- Proyecto SimBA real: `data/simba_projects/New folder/thigmotaxis_optimizado/project_folder`

### Modelos activos

La app quedó apuntando a `generated_models` como fuente principal:

- `data/simba_projects/New folder/thigmotaxis_optimizado/models/generated_models/Grooming.sav`
- `data/simba_projects/New folder/thigmotaxis_optimizado/models/generated_models/Thigmotaxis.sav`

Importante: la app hoy usa esos nombres fijos. No escoge “el archivo más nuevo por timestamp”; escoge esos nombres canónicos. Si se entrena un modelo nuevo con otro nombre, hay que renombrarlo o actualizar `src/config.py`.

### Entornos Python

- `venv_310`: se usa para DeepLabCut / TensorFlow / parte del flujo DLC.
- `venv_311`: se usa para Streamlit, YOLO, bbox filtering, renderer final y utilidades modernas.

### Persistencia de sesión y logs

- Estado de sesión persistido: `.streamlit_session.json`
- Logs de keypoints: `logs/keypoints/`
- Logs de análisis final: `logs/analysis/`

### Logos / splash

- Logo principal del splash: `assets/logos/logo_ria_desktop.png`
- Fondo del splash: `#f6f4f5`

---

## 3. Qué se cambió por módulo

## 3.1. Splash screen y navegación

Se centralizó y corrigió el comportamiento del splash.

### Qué quedó resuelto

- el splash se muestra en todos los módulos principales,
- usa el logo oficial,
- tiene barra de progreso,
- el fondo quedó en `#f6f4f5`,
- y si ocurre un error real durante la carga, el splash se limpia y se muestra el error en pantalla.

Esto fue importante porque antes el splash podía “tapar” el error real y confundir.

### Dónde vive

- `src/ui_components.py`

### Punto clave para otra IA

No volver a implementar splash por página de forma manual. Ya existe un controlador central con:

- `run_page_splash(...)`
- `load_resource_with_splash(...)`

Además ya contempla limpieza del overlay en caso de excepción.

---

## 3.2. Ingesta de Video

### Objetivo

Permitir carga de video y recorte temporal antes del resto del pipeline.

### Estado actual

En la práctica el flujo quedó orientado a:

- cargar el video,
- definir tiempo de inicio,
- definir tiempo de fin,
- permitir casos como “video dura 05:11 pero analizar solo hasta 05:00”,
- activar el registro y dejarlo listo para `Keypoints`.

### Punto importante

La duración del video se calcula con OpenCV, no con una dependencia más frágil.

### Dónde vive

- `pages/01_Ingesta_de_Video.py`

---

## 3.3. Keypoints

Este fue uno de los cambios estructurales más importantes.

### Antes

La pantalla estaba cerca de maqueta:

- parecía lanzar la extracción,
- pero no necesariamente ejecutaba el pipeline real,
- no mostraba progreso útil,
- cambiar de pestaña rompía la visibilidad de logs,
- y cancelar era poco confiable.

### Ahora

La pantalla `Keypoints` ya dispara una corrida operacional real.

### Flujo real actual en Keypoints

`DLC -> filtro bbox -> bridge a SimBA`

En este módulo no se renderiza el video multimodal final completo. Eso quedó reservado para `Análisis Final`.

### Cambios clave

1. Se lanzó la extracción en segundo plano.
2. Se agregó un wrapper de logs en consola del sistema.
3. Se agregó recuperación de estado si el usuario cambia de pestaña y regresa.
4. Se agregó cancelación real del árbol de procesos.
5. Se agregó progreso visible por etapas y heartbeats.
6. Se dejó claro que el HUD de este módulo es un overlay de control de calidad, no el HUD conductual final.

### Cómo funciona técnicamente

`pages/02_Keypoints.py` construye un comando que termina llamando:

- `src/scripts/run_behavior_pipeline.py --skip-final-video`

Eso significa:

- sí corre DLC,
- sí aplica bbox constraint,
- sí hace bridge de pose a SimBA y genera features,
- pero se detiene antes del video multimodal final.

### Wrapper de logs

Se agregó:

- `src/scripts/run_with_live_log.py`

Este wrapper:

- abre una consola nueva en Windows,
- hace `tee` de stdout/stderr a consola + archivo de log,
- deja visible el avance incluso si Streamlit se re-renderiza,
- y soporta cancelación.

### Cancelación

Se agregaron botones en UI para:

- detener extracción,
- abrir la última consola de logs.

La cancelación ya no depende de `Ctrl+C` en la terminal principal. Se usa terminación del árbol de procesos.

### Persistencia / reconexión

Aunque el usuario cambie de pestaña:

- el proceso sigue corriendo,
- los logs siguen escribiéndose,
- y al volver a `Keypoints` la UI reconstruye el estado desde los artefactos persistidos en `logs/keypoints`.

### Batch size

La recomendación operativa quedó así:

- máximo UI: `32`
- recomendado estable: `16`
- intermedio razonable: `24`

El cap de 32 se dejó para no castigar demasiado la GPU.

### Hallazgo importante de hardware

En la RTX 5070 Ti Laptop GPU hay advertencias de compatibilidad de binarios CUDA / TensorFlow / PyTorch.  
Eso provoca:

- detección correcta de GPU,
- pero a veces JIT de kernels,
- con pausas largas al inicio que pueden parecer “congelamiento”.

No siempre es un error; muchas veces es costo del entorno.

### Dónde vive

- `pages/02_Keypoints.py`
- `src/scripts/run_with_live_log.py`
- `src/scripts/run_superanimal.py`
- `src/scripts/run_behavior_pipeline.py`
- `src/scripts/render_dlc_keypoints_video.py`

---

## 3.4. Configuración de Zonas

### Objetivo funcional

Separar dos conceptos:

1. las 6 paredes canónicas que SimBA necesita como ROIs de thigmotaxis,
2. las demás zonas de interés que el HUD final usa para tiempos espaciales.

### Decisión importante de diseño de datos

Solo las 6 paredes se sincronizan a SimBA como ROIs canónicas.

Las demás zonas:

- `Brazo Abierto 1`
- `Brazo Abierto 2`
- `Brazo Cerrado 1`
- `Brazo Cerrado 2`
- `Centro`

se conservan para el análisis final y para el HUD multimodal.

### Qué quedó implementado

- las paredes ahora se dibujan en color naranja,
- las zonas quedan normalizadas a resolución real del video,
- al guardar, la configuración se persiste en sesión,
- y además se sincronizan automáticamente las 6 paredes a SimBA.

### Mensaje esperado

La UI muestra confirmación explícita cuando las 6 paredes se importan correctamente a SimBA.

### Integración con SimBA

Se usa:

- `src/simba_roi_bridge.py`

y específicamente la sincronización:

- solo de las 6 paredes,
- con alias canónicos `pared1` a `pared6`,
- hacia `ROI_definitions.h5`.

### Hallazgo operativo importante

Si SimBA ya estaba abierto cuando se escribieron las ROIs nuevas, puede no reflejar el cambio de inmediato.  
En ese caso suele hacer falta:

- cerrar SimBA,
- reabrir el proyecto.

### Dónde vive

- `pages/03_Configuracion_Zonas.py`
- `src/simba_roi_bridge.py`

---

## 3.5. Análisis Final

Este módulo corre el pipeline completo.

### Flujo actual

`DLC -> filtro bbox -> features SimBA -> modelos conductuales -> video multimodal final`

### Comportamiento deseado

El módulo:

- reutiliza outputs ya existentes si siguen vigentes,
- usa las zonas guardadas,
- usa las 6 paredes como referencia física para thigmotaxis,
- usa los modelos activos de `generated_models`,
- genera el video multimodal final,
- y luego guarda resumen del experimento en PostgreSQL.

### Persistencia a BD

Se guarda en `analysis_results`:

- `time_open_arms`
- `time_closed_arms`
- `time_center`
- `grooming_duration`
- `thigmotaxis_duration`
- `trajectory_path`

### Punto importante

Se agregó explícitamente:

- `ALTER TABLE analysis_results ADD COLUMN IF NOT EXISTS trajectory_path TEXT`

Esto se hace para que el dashboard posterior pueda reconstruir gráficas reales sin depender sólo de la sesión viva.

### Dónde vive

- `pages/04_Analisis_Final.py`
- `src/scripts/run_behavior_pipeline.py`
- `src/scripts/generar_video_prediccion.py`

---

## 3.6. Resultados y Estadísticas

Este módulo fue rehecho para dejar de ser “demo” y consumir datos reales.

### Problemas que tenía

1. Se rompía con error `'accent'`.
2. La UI estaba usando un color inexistente del tema.
3. La lógica de resultados era muy básica.
4. Había una colisión de nombres de columnas en una gráfica:
   - `Grooming`
   - `Thigmotaxis`
   repetidos dos veces.

### Qué se corrigió

- se eliminó la dependencia de `colors['accent']`,
- se rehízo la consulta de `analysis_results`,
- se toma el último resultado por experimento,
- se resuelve `trajectory_path`,
- se agregó fallback a la trayectoria actual de sesión si la BD aún no tiene suficiente información,
- se corrigió la serie temporal conductual para no duplicar nombres de columnas,
- se estilizaron las gráficas con una línea más coherente con IPN,
- y se agregó un mapa de calor generado con OpenCV a partir de la trayectoria.

### Qué muestra hoy

- total en brazos abiertos,
- total en brazos cerrados,
- total en centro,
- grooming acumulado,
- thigmotaxis acumulado,
- comparativa entre experimentos,
- tiempo por zona,
- serie temporal conductual acumulada,
- mapa de calor de permanencia.

### Dónde vive

- `pages/05_Resultados_y_Estadisticas.py`

---

## 4. Persistencia, reconexiones y recuperación tras desconexiones

Este punto es crucial.

## 4.1. Persistencia de `st.session_state`

Se usa:

- `src/session_utils.py`

El archivo `.streamlit_session.json` guarda, entre otras, estas claves críticas:

- login / usuario / rol
- `ruta_video_actual`
- `inicio_recorte`
- `fin_recorte`
- `zonas_configuradas`
- `dlc_batch_size`
- `dlc_device_opt`
- `ultimo_video_analizado`
- `ultimo_pose_file`
- `ultimo_pose_filtrado`
- `ultimo_bbox_video`
- `ultimo_feature_file`
- `ultimo_multimodal_video`
- `ultimo_trajectory_file`
- `ultimo_grooming_timelog`
- `ultimo_thigmotaxis_timelog`
- `analysis_db_notice`

### Consecuencia

Si Streamlit se rerunea o el usuario cambia de módulo, mucho del contexto se puede reconstruir.

## 4.2. Reconexión de Keypoints

La extracción pesada ya no depende de que la pestaña siga abierta.

Queda viva mediante:

- procesos en segundo plano,
- log persistente en `logs/keypoints`,
- wrapper dedicado,
- y estado restaurable al regresar al módulo.

## 4.3. Reconexión de Análisis Final

El análisis final no se hizo en segundo plano separado como `Keypoints`, pero:

- sí guarda outputs,
- sí persiste resumen a BD,
- sí guarda `trajectory_path`,
- y la UI puede reconstruir salidas una vez que se completa.

## 4.4. Splash y errores

El splash ahora se cancela si hay excepción real.  
Esto evita que el usuario se quede “ciego” sin ver el error verdadero.

## 4.5. Regla práctica de recuperación para otra IA

Si una sesión futura llega “desconectada”:

1. revisar `.streamlit_session.json`
2. revisar `logs/keypoints/`
3. revisar `logs/analysis/`
4. revisar `videos_data/`
5. revisar `project_folder/csv/features_extracted/`
6. revisar `project_folder/logs/measures/ROI_definitions.h5`

Con eso casi siempre se puede reconstruir el estado sin repetir todo el pipeline.

---

## 5. Ejecución real validada sobre R6B20

Se hizo una prueba de fuego con:

- video base: `R6B20_01mar24.mp4`
- rango activo: `00:00 -> 05:00`

### Artefactos generados / validados

#### DLC / clip

- `videos_data/R6B20_01mar24_trimmed_0_300.mp4`
- `videos_data/R6B20_01mar24_trimmed_0_300DLC_snapshot-200000.h5`

#### Filtro bbox

- `videos_data/R6B20_01mar24_trimmed_0_300_bbox_constrained.csv`
- `videos_data/R6B20_01mar24_trimmed_0_300_bbox_constrained.h5`
- `videos_data/R6B20_01mar24_trimmed_0_300_bbox_constraint.mp4`

#### SimBA

- video dentro del proyecto SimBA
- pose en `input_csv`
- pose en `outlier_corrected_movement_location`
- features en `features_extracted`

#### ROI walls en SimBA

Se confirmó que `R6B20_01mar24_trimmed_0_300` ya tiene:

- `pared1`
- `pared2`
- `pared3`
- `pared4`
- `pared5`
- `pared6`

en `ROI_definitions.h5`.

#### Video final multimodal

- `videos_data/R6B20_01mar24_trimmed_0_300_STREAMLIT_MULTIMODAL.mp4`
- `videos_data/R6B20_01mar24_trimmed_0_300_STREAMLIT_MULTIMODAL_trajectory.csv`

### Métricas registradas observadas

Ya quedaron valores reales en BD para ese experimento:

- brazos abiertos: ~`237.6s`
- brazos cerrados: ~`48.9s`
- grooming: ~`31.3s`
- thigmotaxis: ~`1.1s`

Estas cifras son útiles como prueba de que el pipeline ya está operando realmente.

---

## 6. Hallazgos científicos / comportamiento actual de los modelos

Aunque el flujo técnico funciona, el comportamiento científico todavía necesita afinación.

### Hallazgo actual del usuario y validación visual

- `Grooming` está generando demasiados falsos positivos.
- `Thigmotaxis` está subdetectando episodios reales.

### Interpretación

El problema actual principal ya no es “el pipeline no corre”.  
Ahora el problema principal es:

- calibración del modelo,
- thresholds,
- quizá set de entrenamiento,
- quizá relación entre paredes dibujadas, YOLO tracking y lectura de features conductuales.

### Conclusión importante

La etapa de infraestructura quedó suficientemente avanzada como para pasar a fase de refinamiento científico.

---

## 7. Qué no debería tocar otra IA sin motivo

1. No rehacer diseño visual principal.
   - El usuario ya indicó que el diseño está bien.

2. No volver a separar manualmente el flujo fuera de `run_behavior_pipeline.py`.
   - Ese runner ya quedó como columna vertebral del pipeline.

3. No revertir el esquema de ROIs.
   - SimBA recibe sólo las 6 paredes.
   - Las demás zonas son para HUD / tiempos espaciales / módulo final.

4. No volver a usar modelos viejos de `validations` como fuente principal.
   - La prioridad correcta hoy es `generated_models`.

5. No romper persistencia de:
   - `.streamlit_session.json`
   - `trajectory_path`
   - logs de keypoints
   - logs de analysis

---

## 8. Qué debería hacer otra IA si retoma mañana

### Si el objetivo es robustez de producto

Revisar:

- recuperación de procesos si Streamlit muere mientras `Keypoints` sigue vivo,
- posible background también para `Análisis Final`,
- validaciones más explícitas de outputs generados,
- reuso inteligente de artefactos ya existentes.

### Si el objetivo es calidad científica

Revisar:

- umbrales de `Grooming`,
- umbrales de `Thigmotaxis`,
- videos de validación con ground truth,
- si el tracking YOLO del punto central está representando bien el contacto con pared,
- y si conviene recalibrar o reentrenar nuevamente los modelos SimBA.

### Si el objetivo es dashboard / resultados

Ya hay base sólida. Los siguientes pasos razonables serían:

- agregar exportación PDF o CSV institucional,
- agregar curvas por tiempo más refinadas,
- agregar overlays de eventos confirmados,
- y quizá superponer el mapa de calor OpenCV sobre un frame base del laberinto.

---

## 9. Resumen ultra corto para otra IA

Si sólo se puede leer una sección, leer esta.

### Pipeline actual correcto

`Ingesta -> Keypoints (DLC + bbox + SimBA bridge) -> Zonas (6 paredes a SimBA) -> Analisis Final (video multimodal + DB) -> Resultados`

### Fuentes de verdad

- modelos activos: `generated_models/Grooming.sav` y `generated_models/Thigmotaxis.sav`
- SimBA activo: `data/simba_projects/New folder/thigmotaxis_optimizado/project_folder`
- estado persistido: `.streamlit_session.json`
- logs: `logs/keypoints`, `logs/analysis`

### Lo ya probado

- R6B20 procesado de 0 a 300 s
- DLC real funcionando
- bbox constraint funcionando
- bridge a SimBA funcionando
- 6 paredes ya sincronizadas a SimBA
- video final generado
- trayectoria generada
- resultados cargando en dashboard

### Lo pendiente real

- bajar falsos positivos de grooming
- subir sensibilidad útil de thigmotaxis
- seguir afinando detalles, no rehacer la arquitectura

---

## 10. Nota final

El gran cambio de estado del proyecto es este:

Antes el trabajo estaba atascado principalmente en integración, continuidad y reconexión del flujo.  
Ahora el flujo ya corre. El cuello de botella principal se movió a afinación de modelos, thresholds y lectura científica del resultado.

Eso es una muy buena señal.
