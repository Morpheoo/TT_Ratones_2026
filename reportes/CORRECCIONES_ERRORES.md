# Registro de Correcciones y Optimizaciones
## TT Ratones 2026 | Errores Solventados en el Setup

Este reporte recopila las fallas detectadas y corregidas durante la inicialización y prueba del sistema, para que puedas replicar estas soluciones en tu computadora principal o en el repositorio definitivo.

---

## 1. Error: Falta de Configuración de Puntos de Interés (SimBA)
### 🔴 Síntoma
Durante la fase de extracción de características de SimBA (`SIMBA_FEATURES`), el pipeline falló arrojando el siguiente error:
```text
SIMBA NO FILES FOUND ERROR: ...\project_folder\logs\measures\pose_configs\bp_names\project_bp_names.csv is not a valid file path
```

### 🔍 Causa
El repositorio clonado por defecto no incluye el archivo `project_bp_names.csv` dentro de la carpeta del proyecto de SimBA. SimBA utiliza este archivo para validar la correspondencia entre los puntos detectados (YOLO) y el modelo de clasificación.

### 🛠️ Solución
Se creó el archivo en la ruta correspondiente:
`data/simba_projects/grooming_thigmotaxis_yolo/project_folder/logs/measures/pose_configs/bp_names/project_bp_names.csv`

Con el listado exacto de los 8 keypoints de YOLO (uno por línea):
```text
nariz
torso
cola-base
oreja-izq
oreja-der
pata-izq
pata-der
punta-cola
```

---

## 2. Error: NameError por Caracteres Acentuados
### 🔴 Síntoma
Al abrir el módulo de configuración de zonas, la página web de Streamlit falló mostrando el siguiente mensaje:
```text
NameError: name 'operación' is not defined
File "pages/03_Configuracion_Zonas.py", line 405, in <module>
    drawing_mode = "transform" if "Mover" in operación else ("line" if "Muro" in tipo_zona else "rect")
```

### 🔍 Causa
En la línea 388, el control de la interfaz (un botón de tipo radio) define la variable como `operacion` (sin acento). En la línea 405, se intentó validar usando la palabra `operación` (con acento). En Python, los acentos cambian por completo la identidad de la variable.

### 🛠️ Solución
En `pages/03_Configuracion_Zonas.py` (Línea 405), se modificó:
* **Antes**: `in operación`
* **Ahora**: `in operacion`

---

## 3. Error: Dependencia Faltante `pytables`
### 🔴 Síntoma
Al intentar guardar las zonas de interés dibujadas y sincronizarlas con el archivo `.h5` de SimBA, se obtuvo la siguiente excepción:
```text
ImportError: Missing optional dependency 'pytables'. Use pip or conda to install pytables.
File "pages/03_Configuracion_Zonas.py", line 240, in _sync_wall_rois_to_simba
    roi_sync_result = sync_streamlit_rois_to_simba(...)
```

### 🔍 Causa
Pandas utiliza la biblioteca `tables` (PyTables) para leer y escribir en almacenamiento estructurado HDF5 (`.h5`), el formato en el que SimBA guarda sus definiciones de zonas. Esta librería no estaba listada en los requisitos de instalación del entorno virtual Python 3.11.

### 🛠️ Solución
1. Se instaló la dependencia en el entorno activo ejecutando:
   ```bash
   venv_311\Scripts\python.exe -m pip install tables
   ```
2. Se agregó la dependencia al archivo de instalación de prerrequisitos [requirements_venv311.txt](file:///c:/Users/Usuario/.gemini/antigravity-ide/scratch/TT_Ratones_2026/requirements_venv311.txt) para automatizarla en el futuro:
   ```text
   tables==3.11.1
   ```

---

## 4. Optimización: Reutilización de Keypoints en Fallas
### 💡 Descripción
La extracción de keypoints con YOLO Pose por CPU tarda aproximadamente **1 hora y 45 minutos** para videos de 5 minutos. Si el pipeline falla en etapas posteriores (como la base de datos o SimBA) y el usuario vuelve a dar clic al botón de la interfaz, el programa original sobrescribía el CSV y repetía toda la extracción desde cero.

### 🛠️ Solución
Se modificó la lógica en [run_behavior_pipeline.py](file:///c:/Users/Usuario/.gemini/antigravity-ide/scratch/TT_Ratones_2026/src/scripts/run_behavior_pipeline.py) (Líneas 306-312) para validar la existencia del archivo de salida de keypoints antes de lanzar la inferencia pesada:

```python
    # Evitar re-procesar si ya existe el CSV de YOLO Pose
    if output_csv.exists() and output_csv.stat().st_size > 100000:
        log(f"[INFO] Reusing existing YOLO Pose CSV: {output_csv}")
        log(f"[OUTPUT] ANALYZED_VIDEO={video_path.resolve()}")
        log(f"[OUTPUT] FILTERED_CSV={output_csv.resolve()}")
        log(f"[OUTPUT] YOLO_KEYPOINTS_VIDEO={output_video.resolve()}")
        return video_path.resolve(), output_csv.resolve(), output_video.resolve()
```
Esto permite que el pipeline salte de inmediato a los pasos finales en caso de cualquier re-ejecución, ahorrando horas de tiempo de cómputo en CPU.

---

## 5. Error: Mismatch de Body Parts en Extractor de ROIs (SimBA)
### 🔴 Síntoma
El pipeline falla en la etapa `SIMBA_FEATURES` con el siguiente error:
```text
SIMBA BODY_PART COLUMN NOT FOUND ERROR: The body-part Center is not a valid body-part in the SimBA project. Options: ['nariz', 'torso', 'cola-base', 'oreja-izq', 'oreja-der', 'pata-izq', 'pata-der', 'punta-cola']
```

### 🔍 Causa
El extractor de ROIs de SimBA (`ROIFeatureCreator`) está configurado para calcular distancias a zonas usando la parte del cuerpo `"Center"`. Sin embargo, el proyecto de SimBA se inicializó con los 8 puntos anatómicos definidos en español (donde `"Center"` se denomina `"torso"`). Al validar los nombres contra la configuración del proyecto, SimBA arroja un error crítico.

### 🛠️ Solución
Se modificó `src/scripts/compute_simba_features.py` para:
1. **Inyección temporal**: Antes de ejecutar `ROIFeatureCreator`, se cargan los datos de la pose del animal y se duplican las columnas de `Center` (`Center_x`, `Center_y`, `Center_p`) bajo el nombre `torso` (`torso_x`, `torso_y`, `torso_p`) en el archivo temporal de pose.
2. **Cálculo con `torso`**: Se invoca a `ROIFeatureCreator` con la opción `body_parts=["torso"]` para que realice los cálculos sin arrojar error.
3. **Limpieza y Re-mapeo**:
   - Se restaura el CSV de pose original para no alterar el archivo.
   - En el archivo final de características (`features_extracted`), se renombran todas las columnas que contienen la palabra `torso` de vuelta a `Center` (ej. `pared1 Animal_1 torso distance` pasa a ser `pared1 Animal_1 Center distance`) para que concuerden con lo esperado por los clasificadores de comportamiento y la base de datos downstream.

---

## 6. Error: Métricas en 0.0 y Estado Pendiente en Módulo de Resultados
### 🔴 Síntoma
En el Módulo 05 ("Resultados y estadísticas"), el experimento aparece listado pero con todos los tiempos en `0.0` y el estado en `Pendiente`, a pesar de que la consola del pipeline reportó una ejecución exitosa.

### 🔍 Causa
El flujo de inserción de resultados en la base de datos local está acoplado al Módulo 04 ("Análisis final"). Cuando el proceso en segundo plano termina:
1. La UI de Streamlit monitorea el archivo `analysis_pipeline.process.json` y los logs.
2. Debido a un criterio de éxito obsoleto en `pages/04_Analisis_Final.py` (buscaba `[PASO] COMPLETADO` el cual nunca es emitido por el script), la interfaz catalogó el proceso internamente con estado `error`.
3. Esto bloqueó la sincronización de salidas (`_sync_analysis_outputs`) y la llamada a `persist_summary_to_db()`.
4. En consecuencia, la tabla `analysis_results` de PostgreSQL quedó vacía (0 filas), provocando que al consultar el historial en el Módulo 05 se mostraran valores en `0.0` y estado `Pendiente`.

### 🛠️ Solución
1. **Corrección de la UI**: Se modificó `pages/04_Analisis_Final.py` (Línea 301) para que reconozca la terminación exitosa nativa del wrapper: `[WRAPPER] Child exit code: 0` y la cancelación de proceso `[STEP] CANCELLED`.
2. **Importación Directa**: Se creó y ejecutó un script utilitario en la consola (`import_results.py`) que leyó el CSV de trayectoria final (`R5B20_01mar24_Cafeína_50mg_STREAMLIT_MULTIMODAL_trajectory.csv`), calculó los tiempos netos por zona/conducta e inyectó los resultados directamente en la base de datos PostgreSQL en el registro del experimento correspondientes.
3. **Proceso Completado**: Se actualizó el estado a `completed` en la base de datos y en `analysis_pipeline.process.json` para reflejar el éxito del experimento.

---

## 7. Comportamiento: No se envían correos OTP (Modo DEV / Consola)
### 🔴 Síntoma
Al registrar un usuario o solicitar el restablecimiento de contraseña, el correo electrónico con el código de verificación de 6 dígitos nunca llega. Al rellenar códigos genéricos, se muestra "Código incorrecto".

### 🔍 Causa
El archivo `.env` tiene configurados los correos y contraseñas SMTP con placeholders por defecto (`your_email@gmail.com` y `your_app_password`). 
Al detectar esto, el sistema se ejecuta en **Modo de Desarrollo (DEV)** e imprime el código de verificación directamente en la consola/terminal donde corre el servidor de Streamlit, omitiendo el envío de correos reales.

### 🛠️ Solución
1. **Uso inmediato**: Puedes ingresar el código activo actual que recuperamos de la base de datos para `hportocarreror1700@alumno.ipn.mx`, el cual es **`235130`**.
2. **Configuración real**: Para que se envíen correos reales en el futuro, debes configurar una cuenta de Gmail remitente en el archivo `.env`:
   - `GMAIL_SENDER_EMAIL`: Tu correo remitente de Gmail.
   - `GMAIL_APP_PASSWORD`: Contraseña de aplicación de 16 caracteres generada desde tu cuenta de Google.



