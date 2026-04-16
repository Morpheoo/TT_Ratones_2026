# Inventario de Codigo TT2

Fecha: 2026-04-13  
Objetivo: documentar la base tecnica activa del repositorio para apoyar el reporte TT2

---

## 1. Alcance de esta lectura

Este inventario cubre el codigo activo mas relevante del proyecto:

- app principal en Streamlit,
- modulos de `src/`,
- scripts de pipeline,
- pruebas disponibles,
- y artefactos relacionados con YOLO, DLC y SimBA.

Quedan fuera del foco principal:

- `venv`, `venv_310`, `venv_311`
- carpeta duplicada `TT_Ratones_2026-main`
- reportes historicos y archivos binarios

---

## 2. Estructura general

### Raiz

- `Home.py`: dashboard principal y acceso a modulos.
- `README.md`: descripcion general, hoy parcialmente desactualizada.
- `schema.sql`: esquema base de PostgreSQL.
- `docker-compose.yml`: servicios de base de datos.
- `ui_theme.py`: tema visual transversal.
- `run_app.py`, `start_services.py`, `launcher.bat`: arranque local.

### Carpetas tecnicas principales

- `pages/`: interfaz Streamlit por modulo.
- `src/`: logica principal del sistema.
- `src/scripts/`: runners, puentes y utilerias del pipeline.
- `src/db/`: conexion y persistencia.
- `tests/`: pruebas unitarias / integracion ligera.
- `reportes/`: documentacion tecnica y academica.

---

## 3. Paginas Streamlit

### `Home.py`

Responsabilidad:

- tablero principal del sistema,
- chequeos de Docker, base de datos y GPU,
- navegacion hacia los modulos.

Notas:

- muestra el estado del sistema en tarjetas KPI,
- todavia contiene texto viejo que describe `Analisis Final` como `YOLO + LSTM`.

### `pages/00_Login.py`

Responsabilidad:

- login y registro,
- carga inicial de sesion,
- acceso controlado por rol.

Dependencias principales:

- `src/auth.py`
- `src/session_utils.py`
- `src/ui_components.py`

### `pages/01_Ingesta_de_Video.py`

Responsabilidad:

- carga del video experimental,
- seleccion de rango temporal,
- persistencia del contexto del experimento.

Salidas de sesion relevantes:

- `ruta_video_actual`
- `inicio_recorte`
- `fin_recorte`
- `id_raton_actual`
- `treatment`

### `pages/02_Keypoints.py`

Responsabilidad:

- lanzar la extraccion de keypoints,
- monitorear logs,
- renderizar vista previa de overlay,
- sincronizar resultados intermedios a la sesion.

Puntos clave:

- hoy la ruta operativa esta conectada a `DeepLabCut SuperAnimal`,
- la opcion `YOLO Pose (Experimental)` ya existe en UI pero no esta integrada al flujo real,
- el proceso se lanza en segundo plano con recuperacion de estado.

Scripts vinculados:

- `src/scripts/run_behavior_pipeline.py`
- `src/scripts/run_with_live_log.py`
- `src/scripts/render_dlc_keypoints_video.py`

### `pages/03_Configuracion_Zonas.py`

Responsabilidad:

- dibujo de zonas y paredes del laberinto,
- persistencia de zonas en sesion y base de datos,
- sincronizacion de 6 paredes canonicas hacia SimBA.

Dependencias principales:

- `src/simba_roi_bridge.py`
- `src/db/experiment_history.py`

### `pages/04_Analisis_Final.py`

Responsabilidad:

- correr el pipeline completo,
- recolectar outputs,
- resumir trayectoria,
- persistir resultados a base de datos.

Puntos clave:

- reutiliza artefactos ya existentes cuando puede,
- inserta o reemplaza resultados en `analysis_results`,
- agrega `trajectory_path` en runtime si hace falta.

### `pages/05_Resultados_y_Estadisticas.py`

Responsabilidad:

- leer historial de experimentos,
- mostrar KPIs y comparativas,
- cargar trayectoria,
- generar heatmap y visualizaciones.

Puntos clave:

- consulta datos reales de BD,
- tiene fallback a datos de sesion actual,
- hoy es una vista funcional, pero aun no conecta export PDF/Excel.

### `pages/98_Perfil.py`

Responsabilidad:

- visualizacion y gestion del perfil del usuario.

### `pages/99_Admin_Panel.py`

Responsabilidad:

- gestion administrativa de usuarios,
- operaciones de administracion interna.

---

## 4. Modulos centrales en `src/`

### `src/config.py`

Responsabilidad:

- rutas canonicas del proyecto,
- rutas de modelos DLC, YOLO y SimBA,
- deteccion de FFmpeg.

Puntos clave:

- define `SIMBA_BASE`, `SIMBA_PROJECT_DIR`,
- fija `Grooming.sav` y `Thigmotaxis.sav` en `generated_models`,
- define `YOLO_MODEL`.

### `src/session_utils.py`

Responsabilidad:

- guardar y recuperar `.streamlit_session.json`.

Valor tecnico:

- permite recuperar estado entre paginas y reruns.

### `src/ui_components.py`

Responsabilidad:

- splash screens,
- carga visual de recursos,
- helpers reutilizables para pages.

### `src/auth.py`

Responsabilidad:

- hashing y login,
- validaciones de acceso,
- soporte de roles.

### `src/email_utils.py`

Responsabilidad:

- envio de correos para verificacion u operaciones de cuenta.

### `src/analysis_logic.py`

Responsabilidad:

- logica geometrica y heuristica para:
- normalizacion de zonas,
- deteccion de zona actual,
- grooming heuristico,
- thigmotaxis geometrica basada en lineas o bordes.

Importancia:

- es la capa mas explicita de interpretacion conductual basica del lado Python puro.

### `src/simba_roi_bridge.py`

Responsabilidad:

- sincronizar videos y ROIs de Streamlit hacia un proyecto SimBA,
- mapear zonas del usuario a aliases `pared1` ... `pared6`,
- reconstruir `ROI_definitions.h5`.

### `src/video_context_banner.py`

Responsabilidad:

- banner contextual del video activo en paginas del pipeline.

### `src/zone_templates.py`

Responsabilidad:

- cargar templates de zonas.

### `src/reporting.py`

Responsabilidad:

- generacion PDF con `FPDF`.

Estado:

- existe, pero no esta conectado al flujo principal actual de resultados.

### `src/security_logger.py`

Responsabilidad:

- logging de eventos de seguridad.

---

## 5. Capa de base de datos

### `src/db/connection.py`

Responsabilidad:

- crear engine SQLAlchemy,
- probar conexion,
- inicializar esquema desde `schema.sql`.

Punto importante:

- usa `@st.cache_resource` para no recrear engine continuamente.

### `src/db/experiment_history.py`

Responsabilidad:

- resolver o crear experimento por video,
- guardar ROIs en `roi_configurations`,
- recuperar historial con zonas.

Valor tecnico:

- conecta la UI de zonas con una persistencia reutilizable.

### `src/db/migrations/`

Contenido:

- scripts para extender el esquema con columnas como `trajectory_path`, verificacion, auditoria, etc.

Observacion:

- parte de la evolucion del esquema se apoya todavia en `ALTER TABLE` ejecutados desde paginas de la app.

---

## 6. Scripts mas importantes del pipeline

### `src/scripts/run_behavior_pipeline.py`

Responsabilidad:

- orquestador principal del pipeline actual.

Etapas:

1. DLC
2. filtro bbox
3. bridge/features SimBA
4. video multimodal final

Valor:

- hoy es la columna vertebral del flujo operativo.

### `src/scripts/run_superanimal.py`

Responsabilidad:

- ejecutar DeepLabCut SuperAnimal,
- recortar video si aplica,
- localizar salidas de pose.

### `src/scripts/apply_dlc_bbox_constraint.py`

Responsabilidad:

- usar YOLO detector para corregir keypoints DLC,
- invalidar outliers,
- reconstruir pose,
- renderizar video de validacion bbox.

Estado:

- es uno de los archivos mas grandes y delicados del proyecto.

### `src/scripts/compute_simba_features.py`

Responsabilidad:

- transformar pose de entrada al bridge de 8 body parts para SimBA,
- sincronizar video y ROIs,
- correr extractores nativos de SimBA,
- completar columnas requeridas.

### `src/scripts/generar_video_prediccion.py`

Responsabilidad:

- render multimodal final,
- trayectoria,
- lectura de modelos conductuales,
- overlays de eventos y tiempos.

Observacion:

- usa `yolo_tracker.pt` como apoyo para tracking visual/trajectory.

### `src/scripts/run_with_live_log.py`

Responsabilidad:

- wrapper de ejecucion con consola viva y escritura dual de logs.

### `src/scripts/render_dlc_keypoints_video.py`

Responsabilidad:

- crear overlay de inspeccion de keypoints DLC.

---

## 7. Scripts de entrenamiento, inferencia y mantenimiento

### Entrenamiento / inferencia SimBA

- `src/scripts/simba_train.py`: entrenamiento de clasificadores RF.
- `src/scripts/train_single_simba_classifier.py`: entrenamiento individual.
- `src/scripts/simba_inference.py`: inferencia batch con modelos activos.
- `src/scripts/run_inference_only.py`: corrida solo de inferencia final.

### Preparacion de datasets y retraining

- `src/scripts/rebuild_filtered_training_targets.py`
- `src/scripts/process_dataset_training.py`
- `src/scripts/create_hybrid_clips.py`
- `src/scripts/import_hybrid_simba.py`
- `src/scripts/import_r5.py`
- `src/scripts/prune_simba_project.py`

### Utilerias de video y render

- `src/scripts/reencode_video.py`
- `src/scripts/trim_video_2min.py`
- `src/scripts/trim_test_video.py`
- `src/scripts/render_video.py`
- `src/scripts/simba_render_video.py`

### Diagnostico y soporte tecnico

- `src/scripts/verify_gpu.py`
- `src/scripts/benchmark_gpu.py`
- `src/scripts/check_resolution.py`
- `src/scripts/check_probs.py`
- `src/scripts/check_annotations.py`
- `src/scripts/debug_csv.py`
- `src/scripts/repair_keras.py`
- `src/scripts/restore_missing_simba_rois.py`

---

## 8. Trabajo relacionado con YOLO

### Codigo activo relacionado

- `src/scripts/entrenar_yolo_local.py`
- `src/scripts/solo_yolo_tracker.py`
- `src/scripts/apply_dlc_bbox_constraint.py`
- `src/scripts/generar_video_prediccion.py`

### Artefactos presentes

- `YOLO_Ratones_Resultados/entrenamiento_roedores/weights/best.pt`
- `YOLO_Ratones_Resultados/entrenamiento_roedores/results.csv`
- `YOLO_Ratones_Resultados/entrenamiento_roedores/args.yaml`

### Lectura tecnica actual

- el repo muestra un detector/tracker YOLO ya entrenado,
- pero no muestra aun una integracion operativa equivalente a `YOLO Pose` en la pagina principal de keypoints,
- aunque si hay indicios de una linea experimental previa en `pages/_archive/03_Analisis_IA_LEGACY.py`.

---

## 9. Pruebas disponibles

### Pruebas unitarias / integracion ligera

- `tests/test_analysis_logic.py`
- `tests/test_auth_logic.py`
- `tests/test_db_integration.py`
- `tests/test_email_mock.py`
- `tests/test_security_fixes.py`
- `tests/test_security_logger.py`

### Pruebas y diagnosticos operativos

- `quick_diag.py`
- `test_docker_setup.py`
- `test_interactive.py`
- `run_tests.bat`

### Observacion

Las pruebas cubren principalmente:

- auth,
- seguridad,
- DB,
- logica base de analisis.

Faltan pruebas fuertes sobre:

- `run_behavior_pipeline.py`
- bbox constraint
- bridge SimBA
- resultados visuales
- persistencia end-to-end

---

## 10. Hotspots de complejidad

Los archivos activos mas grandes y propensos a necesitar refactorizacion son:

- `src/scripts/apply_dlc_bbox_constraint.py`
- `pages/02_Keypoints.py`
- `pages/04_Analisis_Final.py`
- `src/scripts/compute_simba_features.py`
- `src/scripts/generar_video_prediccion.py`
- `src/simba_roi_bridge.py`

Interpretacion:

- aqui vive buena parte del valor tecnico del proyecto,
- pero tambien buena parte de su deuda de mantenibilidad.

---

## 11. Conclusiones del inventario

1. El proyecto ya tiene una base de software amplia y funcional.
2. La arquitectura actual esta claramente construida alrededor de DLC + YOLO bbox + SimBA.
3. La nueva fase `YOLO Pose` todavia no esta integrada como backend formal, pero ya tiene espacio conceptual y tecnico para entrar.
4. El siguiente paso documental correcto es enlazar este inventario con un apendice TT2 por modulo y, despues, con un benchmark comparativo DLC vs YOLO Pose.
