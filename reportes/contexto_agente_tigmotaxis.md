# Contexto y Plan de Acción: Modelo Robusto de Tigmotaxis v2.0 (Videos 5 Minutos)

Este documento sirve como puente de memoria para la próxima sesión de IA (Agente) para continuar con el desarrollo del Trabajo Terminal **TT_Ratones_2026**.

## 1. Resumen de lo Logrado Hasta Ahora
Logramos crear un clasificador *Random Forest* inicial (`Thigmotaxis.sav`) en SimBA que detecta medianamente exitosamente el comportamiento de tigmotaxis (ansiedad/bordear paredes) en roedores. 

**Metodología exitosa desarrollada:**
*   **Mitigación de Jitter (Vibración):** Los puntos de DeepLabCut (H5) presentaban mucho *jitter*. Se programó un pipeline (`produccion_tigmotaxis.py`) que interpola bajas probabilidades ($p < 0.1$) y aplica un filtro espacial **Savitzky-Golay** a los marcadores críticos (hocico, orejas, centro, costados, base de la cola). Esto erradicó los falsos positivos.
*   **Set Híbrido + ROIs:** Se fusionaron clips de diferentes iluminaciones y reflejos (C1-R1, DZP-R1, R5B20) y se usó *Append ROI* explícito en SimBA para darle conciencia espacial a la inteligencia artificial.
*   **Validación:** Se probó ciegamente en un video de 2 minutos sin tigmotaxis (`R5DZ_01mar24_2min.mp4`) dando exactamente 0.00 segundos de detecciones falsas.
*   **HUD Profesional (Visualización):** Se programó un renderizador en OpenCV (`generar_video_prediccion.py`) que en lugar de umbrales rígidos, usa `predict_proba` con un umbral ajustable (ej. 18%). Crea un cuadro / HUD elegante estilo SimBA (gris semi-transparente) en la esquina derecha que muestra: Tiempo Acumulado, Barra de Progreso de Probabilidad, % de Certeza en tiempo real, y avisos de color intuitivos. 

## 2. El Problema Actual a Resolver ("El Cuello de Botella")
El modelo detectó falsos negativos ante picos muy sutiles de la conducta (certezas del 30% en fotogramas de tigmotaxis leve), porque fue entrenado solo con *Clips de 40 segundos* (~1200 frames). Necesitamos que el modelo cuente con "experiencia masiva".

## 3. Plan de Acción para la IA Entrante
El objetivo principal es entrenar y reportar un modelo definitivo usando videos masivos de 5 minutos ($\sim$9000 fotogramas). 

**Pasos mandatarios para el Agente:**
1.  **Inferencia Masiva GPU:** Ejecutar DeepLabCut (*SuperAnimal TopViewMouse*) aprovechando la RTX 5070 Ti local sobre los videos completos (ej. `DZP-R1.mov`, `C1-R1.mov`). 
2.  **Pipeline de Preprocesado:** Pasar obligatoriamente los resultados por el script Anti-Jitter/Savitzky-Golay localizado en el proyecto para "planchar" las curvas antes de SimBA.
3.  **Etiquetado Humano (Pausa):** Preparar los entornos en SimBA para que el Usuario (Chavi) pueda etiquetar a mano e instruir las conductas verdaderas de tigmotaxis a lo largo de los 5 minutos.
4.  **Generación de Reportes Nivel Paper:** 
    *   Revisar o recordar los lineamientos de los papers oficiales de SimBA (Nilsson et al.) y generar de forma proactiva métricas (Matriz de Confusión, Precisión, Error OOB).
    *   Generar los reportes finales en `.tex` o Markdown con terminología altamente profesional, justificando la adición de videos de 5 min.
5.  **Refinamiento del Video (HUD):** Asegurar que cuando se haga el *predict* del modelo final, el script del *HUD* siga luciendo impecable, manteniendo la barra visual con porcentaje y acumulación de tiempo en la esquina superior derecha para todas las presentaciones clínicas.

## Notas Técnicas Locales
*   **Rutas clave:** Todo se trabaja en `C:\Users\chavi\.gemini\antigravity\scratch\TT_Ratones_2026\`.
*   **Manejo de Python:** Dos entornos virtuales: `venv_310` (Para DeepLabCut nativo GPU, requiere tricks de OS en Windows para detectar DLLs de CUDA) y `venv_311` (Para Streamlit, SimBA y análisis genérico).
*   ¡Tratar al usuario como un analista y científico! Todo texto y reporte generado debe mantener extrema rigurosidad científica, citando el contexto de validación biológica y *Machine Learning*.
