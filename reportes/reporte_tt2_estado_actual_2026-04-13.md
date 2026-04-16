# Reporte TT2 - Estado Actual del Proyecto

Fecha: 2026-04-13  
Proyecto: `TT_Ratones_2026`  
Estado del documento: borrador tecnico inicial para TT2

---

## 1. Proposito de este documento

Este reporte resume el estado real del proyecto al inicio de TT2 con base en:

- el ultimo contexto operativo completo (`reportes/contexto_operativo_streamlit_pipeline_2026-03-25.md`),
- la estructura actual del repositorio,
- el codigo activo de la app en Streamlit,
- los scripts del pipeline DLC + YOLO + SimBA,
- los artefactos locales de entrenamiento YOLO y logs recientes.

La idea no es repetir el reporte anterior, sino actualizarlo con tres objetivos:

1. dejar claro que partes del sistema ya estan operativas,
2. estimar el avance real del proyecto con criterio tecnico,
3. abrir formalmente la nueva fase de trabajo orientada a `YOLO26 Pose` como posible reemplazo de DeepLabCut u (opción adicional) en extraccion de keypoints.

---

## 2. Resumen ejecutivo

El proyecto ya no esta en una fase de "prueba de concepto" aislada. La app principal ya implementa un flujo funcional de trabajo para un experimento EPM:

`Login -> Ingesta -> Keypoints -> Configuracion de Zonas -> Analisis Final -> Resultados`

En su version operativa actual, el pipeline real sigue siendo:

`Video -> DeepLabCut SuperAnimal -> filtro bbox con YOLO detector -> bridge a SimBA -> features -> inferencia conductual -> video multimodal -> persistencia en BD -> dashboard`

Sin embargo, el cuello de botella principal ya cambio. El problema dominante ya no es "integrar piezas", sino:

- el tiempo excesivo de extraccion de pose con DeepLabCut,
- la necesidad de reducir latencia por video,
- y la conveniencia de migrar hacia un nuevo pipeline basado en `YOLO26 Pose`.

La fase actual del equipo, segun el estado del codigo y lo reportado por el usuario, es:

- adopcion de `YOLO26 Pose` como candidato principal,
- etiquetado del dataset en formato YOLO,
- evaluacion de un pipeline alterno para keypoints,
- y preparacion de una posible transicion tecnologica fuera de DLC.

---

## 3. Hallazgos principales del estado actual

### 3.1. Lo que ya esta funcional

- La app de Streamlit ya esta organizada como producto usable y no solo como demo.
- La extraccion de keypoints en `pages/02_Keypoints.py` ya corre en segundo plano, con logs persistentes y recuperacion de estado.
- El runner central `src/scripts/run_behavior_pipeline.py` ya unifica DLC, bbox, bridge SimBA y video final.
- La configuracion de zonas ya sincroniza las 6 paredes canonicas a SimBA.
- El analisis final ya persiste resultados y `trajectory_path` en base de datos.
- La vista de resultados ya consume datos reales y ya genera metricas y heatmap.

### 3.2. Lo que sigue dependiendo de DLC

La ruta activa de keypoints aun esta conectada a `DeepLabCut SuperAnimal`.

Evidencia directa en el codigo:

- `pages/02_Keypoints.py` muestra la opcion `YOLO Pose (Experimental)`, pero advierte que la ruta operativa actual sigue conectada a DLC.
- `src/scripts/run_behavior_pipeline.py` lanza `run_superanimal.py` como primera etapa del pipeline.
- `run_superanimal.py` y el resto del flujo esperan salidas DLC (`.h5` y `.csv`) para continuar con bbox y SimBA.

### 3.3. Lo que ya existe de YOLO en el repo

El repositorio si contiene trabajo real con YOLO, pero hoy esta orientado principalmente a deteccion/tracking, no a pose operativa:

- `src/scripts/entrenar_yolo_local.py` entrena un detector YOLO local.
- `src/scripts/solo_yolo_tracker.py` implementa tracking puro con YOLO.
- `src/scripts/apply_dlc_bbox_constraint.py` usa YOLO como restriccion espacial para limpiar keypoints de DLC.
- `src/scripts/generar_video_prediccion.py` usa un modelo YOLO tracker para trayectoria y apoyo visual.
- Existen artefactos de entrenamiento en `YOLO_Ratones_Resultados/entrenamiento_roedores/`.

Importante: en el codigo activo no existe aun un pipeline `YOLO26 Pose` de reemplazo completo para la pagina 02. Lo que si existe es:

- una opcion experimental visible en la UI,
- rastros de una rama previa en `pages/_archive/03_Analisis_IA_LEGACY.py`,
- y la infraestructura conceptual para introducir un backend alterno de pose.

### 3.4. Evidencia del cuello de botella actual

La lentitud de DLC no es solo percepcion; esta respaldada por artefactos locales:

- `reportes/tiempos_dlc.md` reporta alrededor de `4h 20m` para un video de `5 min` en 720p con RTX 5070 Ti Laptop GPU.
- `logs/keypoints/keypoints_extract.process.json` muestra una corrida completada para `R6YB15_01mar24.mp4` con duracion efectiva de `03:19:10` para un rango de `311 s`.

Esto justifica plenamente abrir TT2 con un frente fuerte de optimizacion de pose.

### 3.5. Datos confirmados del nuevo dataset YOLO Pose

Con la informacion proporcionada por el equipo, el dataset actual de pose queda descrito de forma preliminar asi:

- alrededor de `857 imagenes` bien anotadas,
- aproximadamente `5 videos` fuente,
- `1 escenario` experimental principal,
- `8 keypoints` por pose,
- y `6 jobs` de etiquetado visibles en la plataforma de anotacion.

Tambien se confirmo una linea de interes cientifico especifica:

- se esta evaluando dar mayor enfasis a `grooming`,
- porque sus micro-posturas podrian contener informacion conductual interesante,
- y podrian influir positivamente en el entrenamiento si quedan bien representadas en el dataset.

Esto es valioso para TT2 porque ya no solo hay una idea de migracion a YOLO Pose, sino un dataset real en construccion para soportarla.

---

## 4. Estimacion de avance del proyecto

Esta estimacion es tecnica y orientativa. No sustituye una medicion institucional formal. Se calcula ponderando el estado funcional del software, la robustez del pipeline y el nivel de validacion cientifica pendiente.

| Componente | Peso | Avance estimado | Comentario |
| --- | ---: | ---: | --- |
| App Streamlit y flujo UX | 20% | 85% | La navegacion y el flujo principal ya existen y son utilizables. |
| Pipeline operativo DLC + bbox + SimBA + resultados | 30% | 80% | Ya corre de punta a punta, pero sigue atado a DLC y necesita refinamiento. |
| Persistencia, BD y trazabilidad | 10% | 75% | Ya hay guardado de experimentos, ROIs, resultados y trayectorias. |
| Robustez, testing y mantenibilidad | 10% | 55% | Hay pruebas, pero se concentran en auth/DB/logica base; falta cobertura del pipeline. |
| Validacion cientifica de modelos y umbrales | 20% | 45% | Aqui sigue una parte critica del trabajo pendiente. |
| Migracion a YOLO26 Pose | 10% | 15% | Ya hay dataset, direccion confirmada y ruta objetivo definida, pero aun no hay integracion operativa. |

### Avance global estimado

**Avance tecnico global estimado: 67%**

Interpretacion:

- El sistema principal ya esta bastante construido.
- El proyecto no esta trabado en interfaz ni en integracion basica.
- La parte mas importante pendiente para TT2 es consolidar velocidad, validez cientifica y una nueva ruta de pose.

---

## 5. Arquitectura actual del sistema

### 5.1. Capa de aplicacion

La interfaz principal vive en Streamlit y esta distribuida entre:

- `Home.py`
- `pages/00_Login.py`
- `pages/01_Ingesta_de_Video.py`
- `pages/02_Keypoints.py`
- `pages/03_Configuracion_Zonas.py`
- `pages/04_Analisis_Final.py`
- `pages/05_Resultados_y_Estadisticas.py`
- `pages/98_Perfil.py`
- `pages/99_Admin_Panel.py`

### 5.2. Capa de logica y soporte

El nucleo tecnico vive principalmente en `src/`:

- configuracion central: `src/config.py`
- persistencia de sesion: `src/session_utils.py`
- splash y componentes UI: `src/ui_components.py`
- autenticacion y correo: `src/auth.py`, `src/email_utils.py`
- logica conductual base: `src/analysis_logic.py`
- sincronizacion ROI con SimBA: `src/simba_roi_bridge.py`
- capa de BD: `src/db/`

### 5.3. Capa de ejecucion del pipeline

Los scripts mas importantes del flujo actual son:

- `src/scripts/run_behavior_pipeline.py`
- `src/scripts/run_superanimal.py`
- `src/scripts/apply_dlc_bbox_constraint.py`
- `src/scripts/compute_simba_features.py`
- `src/scripts/generar_video_prediccion.py`
- `src/scripts/run_with_live_log.py`
- `src/scripts/render_dlc_keypoints_video.py`

### 5.4. Tamano actual del codigo activo inspeccionado

Conteo rapido del repositorio activo:

- `pages/`: 9 archivos, 5230 lineas
- `src/`: 82 archivos, 10752 lineas
- `tests/`: 7 archivos, 387 lineas

Esto da una base aproximada de **16369 lineas de Python activas** entre interfaz, logica y pruebas.

---

## 6. Estado actual de la documentacion vs estado real del codigo

Durante la revision aparecieron varias discrepancias importantes entre documentos viejos y el estado real del sistema.

### 6.1. Elementos ya desactualizados

- `Home.py` todavia describe `Analisis Final` como "YOLO + LSTM", pero el pipeline actual real depende de DLC + SimBA + renderer multimodal.
- `reportes/pipeline_TT2026.html` habla de exportacion PDF/Excel y clustering K-Means, pero eso no esta conectado actualmente en la pagina de resultados.
- `src/reporting.py` ya existe para PDF, pero no esta integrado al flujo principal actual.
- `schema.sql` no incluye originalmente `trajectory_path`; las paginas 04 y 05 hacen `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` en runtime.

### 6.2. Interpretacion

La arquitectura del sistema avanzo mas rapido que parte de su documentacion estatica. Por eso TT2 necesita una nueva capa documental que refleje:

- el pipeline real vigente,
- las dependencias verdaderas,
- y la transicion planeada a YOLO26 Pose.

---

## 7. Fase actual: transicion de DLC a YOLO26 Pose

La fase presente del proyecto puede describirse asi:

### Fase operativa actual

- El pipeline funcional usa DLC para pose.
- YOLO se usa como soporte de bbox/tracking, no como pose backend principal.
- SimBA sigue siendo el motor de features y clasificacion conductual.

### Fase de investigacion en curso

- Se esta etiquetando dataset en formato YOLO.
- Se adopta `YOLO26 Pose` como candidato principal para la nueva etapa.
- Se quiere construir un pipeline alterno mas rapido para reemplazar la extraccion lenta de DLC.

### Decisiones ya confirmadas

1. La ruta objetivo principal sera:
   - `YOLO26 Pose -> bridge a SimBA`

2. El dataset actual de pose se esta construyendo con:
   - `857 imagenes`
   - `5 videos` aproximados
   - `1 escenario`
   - `8 keypoints`

3. Existe interes explicito en reforzar la representacion de `grooming`.
   - Esto es cientificamente razonable porque el grooming depende de micro-posturas y cambios finos de configuracion corporal.

### Recomendacion tecnica sobre el modelo

Para este proyecto, `YOLO26 Pose` si es una muy buena decision como linea principal de TT2, por cuatro razones:

1. En la interfaz de entrenamiento aparece como la opcion mas reciente de Ultralytics.
2. El repositorio actual ya usa `ultralytics`, asi que la integracion tecnica seria mas natural que adoptar una ruta muy distinta.
3. El objetivo principal de TT2 no es solo precision absoluta, sino bajar tiempos de inferencia frente a DLC.
4. Mantener una arquitectura cercana al ecosistema ya usado en el proyecto reduce friccion de integracion.

Sin embargo, para el reporte conviene expresarlo asi:

- `YOLO26 Pose` sera el **candidato principal**,
- y `YOLO11 Pose` puede conservarse como **baseline comparativa** de velocidad/estabilidad.

Esto es mejor que afirmar desde ahora que YOLO26 es "el mejor" en terminos absolutos sin benchmark interno.

### Conclusiones de esta transicion

1. TT2 ya no deberia presentarse solo como "continuacion de DLC".
2. TT2 deberia documentar una nueva linea experimental: `Pipeline YOLO26 Pose`.
3. El objetivo no es solo acelerar inferencia, sino verificar si las nuevas poses siguen siendo utiles para analisis conductual posterior.
4. La ruta `YOLO26 Pose -> bridge a SimBA` es la mejor opcion inicial porque reutiliza la mitad aguas abajo del sistema ya validado.

---

## 8. Posibles mejoras priorizadas

### 8.1. Mejoras de arquitectura

1. Crear una interfaz formal de backends de pose.
   - Idea: que `pages/02_Keypoints.py` y `run_behavior_pipeline.py` puedan trabajar con `DLCBackend` y `YOLO26PoseBackend`.

2. Separar el pipeline en etapas mas modulares.
   - Hoy `run_behavior_pipeline.py` ya ordena bien el flujo, pero aun concentra demasiada responsabilidad.

3. Centralizar thresholds y parametros cientificos.
   - Hoy hay umbrales repartidos entre `simba_inference.py`, `generar_video_prediccion.py` y logica de resultados.

### 8.2. Mejoras cientificas

1. Definir un benchmark formal DLC vs YOLO26 Pose.
   - tiempo por video
   - fps efectivo
   - estabilidad de keypoints
   - impacto en features
   - impacto en deteccion de grooming y thigmotaxis

2. Establecer una verdad terreno minima para pose y comportamiento.
   - No basta con que YOLO26 Pose sea rapido; debe sostener o mejorar la calidad del analisis final.

3. Evaluar si SimBA seguira siendo la capa conductual final.
   - Si YOLO26 Pose entrega keypoints distintos o esquema distinto de bodyparts, hay que definir si:
   - se adapta el bridge actual a SimBA,
   - o se entrena un clasificador nuevo fuera de SimBA.

4. Abrir una linea especifica para `grooming`.
   - Para thigmotaxis, `8 keypoints` pueden ser suficientes en un escenario controlado.
   - Para grooming, las micro-posturas podrian requerir keypoints mas informativos o una seleccion muy fina de frames de entrenamiento.
   - Conviene validar pronto si el esquema actual de `8 keypoints` captura de forma suficiente la senal relevante para grooming.

### 8.3. Mejoras de mantenibilidad

1. Refactorizar los archivos mas grandes:
   - `src/scripts/apply_dlc_bbox_constraint.py`
   - `pages/02_Keypoints.py`
   - `pages/04_Analisis_Final.py`
   - `src/scripts/compute_simba_features.py`
   - `src/scripts/generar_video_prediccion.py`

2. Mover cambios de esquema a migraciones reales.
   - Evitar que la app altere tablas en runtime como parte del flujo normal.

3. Actualizar documentacion institucional.
   - README
   - Home
   - pipeline HTML
   - manuales de testing

### 8.4. Mejoras de calidad y pruebas

1. Agregar pruebas de integracion del pipeline.
2. Agregar pruebas sobre ROIs, bridge de pose y persistencia de resultados.
3. Agregar una corrida corta de smoke test con un clip pequeno y expected outputs.

---

## 9. Riesgos actuales

### Riesgo 1: dependencia fuerte en DLC

Aunque el pipeline funciona, el costo temporal de DLC afecta:

- iteracion experimental,
- pruebas comparativas,
- retraining,
- y escalamiento a lotes mayores.

### Riesgo 2: deriva documental

Hay partes del repo que describen un sistema ligeramente distinto al que realmente corre. Esto puede afectar TT2 si no se corrige pronto.

### Riesgo 3: acoplamiento fuerte

La cadena actual depende de que el formato de pose salga con estructura DLC para que todo lo demas funcione sin adaptaciones.

### Riesgo 4: validacion cientifica incompleta

La infraestructura ya esta madura, pero la calidad cientifica de los modelos sigue necesitando ajuste fino.

### Riesgo 5: sobreajuste por escenario unico

El dataset actual parece concentrarse en:

- un solo escenario,
- pocos videos fuente,
- y una distribucion todavia limitada de poses.

Eso puede ayudar a obtener buen rendimiento local, pero tambien puede producir sobreajuste si luego cambian:

- iluminacion,
- posicion de camara,
- escala,
- o variaciones sutiles entre animales.

---

## 10. Recomendacion para TT2

La narrativa tecnica de TT2 deberia organizarse en dos bloques:

### Bloque A. Sistema ya consolidado

- app multipagina en Streamlit,
- pipeline operativo validado,
- persistencia de resultados,
- bridge con SimBA,
- resultados visuales y dashboard.

### Bloque B. Nueva linea de investigacion

- limitaciones operativas de DLC,
- necesidad de acelerar extraccion de pose,
- etiquetado actual en YOLO,
- diseno de un nuevo pipeline basado en `YOLO26 Pose`,
- comparativa futura entre ambos enfoques.

En otras palabras: TT2 debe presentar al proyecto no solo como "software funcional", sino como un sistema que entra a una segunda etapa de optimizacion y modernizacion del backend de pose.

---

## 11. Proximos pasos sugeridos

1. Formalizar el nombre del nuevo frente experimental.
   - usar `YOLO26 Pose` como nombre principal en TT2,
   - y conservar `YOLO11 Pose` como baseline interna de comparacion.

2. Documentar el estado del dataset YOLO.
   - `857 imagenes`
   - `5 videos` aproximados
   - `1 escenario`
   - `8 keypoints`
   - enfasis experimental en `grooming`

3. Definir la ruta de integracion:
   - `YOLO26 Pose -> bridge a SimBA` como ruta principal de bajo riesgo
   - y evaluar mas adelante si conviene `YOLO Pose -> nuevo clasificador conductual`

4. Actualizar el reporte con metricas de entrenamiento y benchmarking en cuanto existan.

---

## 12. Nota final

El hallazgo mas importante para abrir TT2 es este:

**el proyecto ya tiene una columna vertebral funcional.**  
Lo que falta no es empezar el sistema, sino mejorar su velocidad, su robustez cientifica y su siguiente generacion de pose estimation.

Eso cambia por completo el tono del reporte TT2.
