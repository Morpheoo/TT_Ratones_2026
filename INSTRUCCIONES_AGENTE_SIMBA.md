# 🚀 Pipeline Final de Entrenamiento Masivo para Tigmotaxis (Split Train/Test)

¡Hola Chavi! He preparado todo el terreno según las directrices metodológicas para un modelo verdaderamente robusto de Machine Learning.

**Estrategia de Datos (5 Train / 2 Test):**
Me parece una estrategia perfecta, agregando los videos que mencionas la validación será brutal. Aquí está la versión definitiva de los sets:

**Entrenamiento (Para `Label Behavior` en SimBA):**
1. `C1-R1.mov`
2. `C2-R1.mov`
3. `C56-R1.mov`
4. `C7-R1.mov`
5. `R5DZ_01mar24.mp4` (El extra elegido para enseñar la conducta)

**Prueba / Validación Ciega (Predicción y Video OpenCV con `generar_video_prediccion.py`):**
1. `DZP-R1.mov` (El que está ejecutándose actualmente)
2. `R5B20_01mar24.mp4` (El extra elegido de forma ciega)

## 🎯 Acciones Ejecutadas por el Agente:
1. **Inferencia Masiva en GPU:** He dejado ejecutándose en segundo plano (corriendo en la RTX 5070 Ti) el pipeline de **DeepLabCut** (*SuperAnimal TopViewMouse*) sobre los videos de 5 minutos `DZP-R1.mov` y `C1-R1.mov`.
2. **Refactorización Profesional de Scripts:**
   - Hice paramétrico el script `produccion_tigmotaxis.py` (ahora acepta argumentos `--h5_file` por terminal) para que fácilmente apliques el Anti-Jitter/Savitzky-Golay a los nuevos archivos H5 una vez terminen de procesarse.
   - Refactoricé el renderizador `generar_video_prediccion.py`, el cual ahora es una herramienta de despliegue dinámico. Se le pasa el `--video`, `--features` y `--output` asegurando que el  **HUD impecable estilo SimBA** siga luciendo perfecto para cualquier duración clínica.
3. **Generación de Reportes Nivel Paper:** Localicé el PDF de SimBA (*Nilsson et al.*), extraje sus bases, y redacté un reporte profesional en \LaTeX (\`reportes/reporte_tigmotaxis_simba.tex\`) justificando la inclusión de secuencias de 5 minutos para dominar la detección de micro-expresiones con Random Forest. 

## 🧠 Siguientes Pasos (Acción Requerida - Etiquetado Humano)

Como el modelo masivo requiere que tú (**el experto humano**) valides las nuevas secuencias, aquí está tu *To-Do list* una vez que termine la Inferencia DLC:

### Paso 1: Eliminar Jitter de la Inferencia (Savitzky-Golay)
Cuando la consola termine de extraer posturas y te arroje los `.h5` nuevos en la carpeta `dataset_tt\`, deberás ejecutar para cada uno en tu entorno virtual:

```bash
venv_311\Scripts\python.exe src\scripts\produccion_tigmotaxis.py --h5_file dataset_tt\DZP-R1DLC...h5
```
Esto planchará los marcadores mitigando el jitter (el parpadeo erróneo de hocico y orejas) y lo pondrá como `csv` limpio dentro del proyecto SimBA listo para que lo lea.

### Paso 2: Dibujar ROIs de Interés Manualmente (GUI de SimBA) 🔥 MUY IMPORTANTE
Tienes toda la razón, si no dibujamos las paredes, la thigmotaxis no existe. 
1. Abre de nuevo el GUI de SimBA (`venv_311\Scripts\simba`).
2. Ve a la pestaña **[Region of Interest]** > **[Draw ROIs]**.
3. Selecciona tus recuadros o polígonos alrededor del **Centro** de la arena de experimentación y a lo largo de las **Paredes**. Hazlo para cada video C1, C2, DZP, etc.
4. El objetivo es que la IA entienda el mundo físico simulado de la caja usando SimBA.

### Paso 3: Calculo Automático de todas las Cinemáticas y Features 
Una vez que en el paso previo dibujes y **guardes** tus ROIs, he dejado un script CLI que se encarga de extraer la cinemática de los puntos e integrar tus ROIs automáticamente:
```bash
venv_311\Scripts\python.exe src\scripts\automatizar_simba.py --config "data\simba_projects\New folder\thigmotaxis_optimizado\project_folder\project_config.ini"
```
¡Esto hará el trabajo sucio en minutos y arrojará los features finales listos!

### Paso 4: ¡Tu turno de Etiquetado! (Label Behavior)
1. En SimBA, ve a **Label Behavior**. Aquí es donde enseñarás el "nuevo oro" a la IA etiquetando los momentos exactos de tigmotaxis a lo largo de los 5 minutos.
2. Terminado el etiquetado, entra a **Train Machine Model** y vuelve a entrenar el *Random Forest* pisando el archivo modelo anterior (`Thigmotaxis.sav`).

### Paso 4: Validar Visualmente con el Nuevo HUD
Una vez el clasificador esté re-entrenado, renderiza la belleza de su predicción:
```bash
venv_311\Scripts\python.exe src\scripts\generar_video_prediccion.py --video dataset_tt\DZP-R1.mov --features "data\simba_projects\New folder\thigmotaxis_optimizado\project_folder\csv\features_extracted\DZP-R1.csv" --output dataset_tt\DZP_R1_FINAL_PREDICT.mp4
```

¡Es todo tuyo, doc! El modelo robusto v2.0 va a quedar brutal.
