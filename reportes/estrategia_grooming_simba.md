# Plan de Acción: Detección de Grooming en SimBA (Generado por IA)

¡Hola! Basado en el excelente contexto del proyecto de tesis que has proporcionado, la infraestructura que ya tienen (YOLO para zonas + Tracking robusto, DLC para postura, SimBA para Thigmotaxis) es muy sólida y defendible.  

Introducir "Grooming" (aseo) requiere un enfoque muy particular, principalmente porque desde una vista superior (Top-Down) típica en un EPM, las patas delanteras a menudo quedan ocluidas bajo el cuerpo, y el ligero *jitter* de estimación de postura puede confundirse fácilmente con el movimiento vibratorio del grooming.

A continuación, presento la estrategia científica y técnica detallada para implementar esto en el pipeline existente, ideal como entregable para documentar en la tesis o aplicar como próximos pasos:

---

## 1. Diseño de la Estrategia de Implementación en SimBA
La estrategia asume que el Grooming es un comportamiento de **baja movilidad global**, **alta compactación corporal** y **alta oscilación local** en la zona anterior del cuerpo. Dependiendo del robustez de los puntos extraídos en la cabeza del ratón, SimBA analizará las variaciones espaciales en ventanas cortas de tiempo (features dinámicas). 

No es necesario volver a utilizar YOLO, ya que los recuentos de fotogramas, zonas e identificación espacial ya están cubiertos. SimBA exclusivamente procesará cinemática 2D en base al output filtrado de DLC.

## 2. Keypoints Indispensables (desde SuperAnimal/DLC)
Para la tesis, enfócate en garantizar que tu modelo de estimación posicional mantenga estos puntos estables:
*   **Nose (Nariz):** Crítico. El movimiento oscilador local de la nariz representa el 80% de la varianza en el grooming visto desde arriba.
*   **Center / Spine (Centro del cuerpo):** Para confirmar que la movilidad global es cercana a cero.
*   **Tail base (Inicio de la cola):** Crítico para establecer la longitud de la postura.
*   *(Si tus modelos los tienen, son de oro)* **Left / Right Front Paws (Patas Delanteras):** Si el output de SuperAnimal extrae patas, la proximidad de estas hacia la nariz es la variable predictora más exacta de Grooming.

## 3. Features Sugeridas para el Feature Engineering
En SimBA, las *features* de geometría básica y derivadas temporales son clave. Sugiero enfocarse en:
*   **Body Length (Distancia Nariz - Base de la Cola):** Durante el grooming, el ratón se sienta y se encorva, reduciendo dramáticamente esta distancia comparado con cuando está explorando.
*   **Nose-to-Center Speed vs Center Speed:** La velocidad de la nariz respecto al centro será alta (por frotarse la cara), pero la velocidad de desplazamiento del centro será nula.
*   **Hull Area / Eccentricity (Si SimBA lo permite):** El polígono formado por los puntos será casi circular durante el grooming, mientras que será muy alargado durante Thigmotaxis o exploración.
*   **Body Angle Variance:** Rotaciones pequeñas y repetitivas de la cabeza en intervalos de ~0.2 a 0.5 segundos.

## 4. Flujo de Trabajo: Entrenamiento y Validación
Para asegurar que tu tesis sea robustamente defendible estadísticamente:

**Fase A: Pre-procesamiento Crítico (Anti-Jitter)**
*   Dado que reconoces que DLC tiene "temblor" (jitter) en los bordes o áreas oscuras, **debes filtrar los CSVs** de coordenadas ANTES de meterlos a SimBA o generar features. Si el ratón está quieto y el Tracker tiembla, SimBA creerá que está haciendo Grooming.
*   *Recomendación:* Implementar un filtro `Savitzky-Golay` de ventana corta sobre las coordenadas originales. Mantiene la forma del movimiento de alta frecuencia pero suaviza el ruido aleatorio del píxel.

**Fase B: Anotación Específica**
*   **Definición estricta:** Anota fotogramas como grooming *solo* cuando ves claramente el patrón de "lavar cara/cuerpo". Excluye rascados singulares o sacudidas rápidas (shaking). 
*   Usa al menos 3 a 5 "bouts" (episodios) largos por video para el entrenamiento, abarcando ratones distintos y diferentes brazos del laberinto, para evitar el sesgo por iluminación.

**Fase C: Entrenamiento del RF**
*   Entrenar un clasificador *Random Forest*. Configura los hiperparámetros de SimBA: ~2000 estimadores. 
*   **Minimum Bout Length:** Establecer en 0.5 segundos o superior (el ratón apenas hace groomings menores a medio segundo; esto evita falsos positivos rápidos).
*   **Threshold (Umbral):** Puedes partir de `0.35` al igual que el Thigmotaxis, o subirlo a `0.45` si ves que la respiración fuerte estando estático se clasifica falsamente.

**Fase D: Validación Cruzada Ciega (Crucial para Tesis)**
*   Retén el ~20% de tus clips grabados fuera del modelo por completo.
*   Comparar métricas en matriz de confusión: Precision (¿qué tanto de lo que el modelo dijo que era grooming realmente lo era?), Recall y F1-Score contra tu Ground Truth (humano). Muestra las curvas ROC-AUC como validación en tu reporte.

## 5. Estructura de Scripts Auxiliares Recomendada
Para integrar sin romper el pipeline orquestador limpio que ya desarrollaron (`generar_video_prediccion.py`), sugiero estos scripts pequeños modulares:

1.  `scripts/01_filter_dlc_jitter.py`
    *   *Propósito:* Toma los `CSV` crudos, aplica el pasabajos (Sav-Gol) a las columnas de coordenadas (`x`, `y`) filtrando según el nivel de confianza (likelihood) del keypoint. Emite el CSV procesado que se usará para feature engineering.
2.  `scripts/02_extract_grooming_features.py` (O la UI de SimBA).
3.  `generar_video_prediccion.py` (Actualización)
    *   *Modificación:* Añadir la lectura simultánea del clasificador RF de Grooming.
    *   *Modificador en HUD:* Crear variables acumuladores para el tiempo del Grooming en la sección *Superior Derecha* del video (y en el TIMELOG).

## 6. Mantenimiento de la Compatibilidad
*   YOLOv11 seguirá haciendo su excelente trabajo marcando el sujeto en las 5 zonas.
*   El modelo Thigmotaxis y Grooming **corren en paralelo**, utilizando el mismo CSV procesado de features. Simplemente cargas el modelo `.sav` de Random Forest de Grooming, le pasas las features y obtienes una columna `prob_grooming`.
*   Esto mantiene tu sistema intacto, ordenado y simplemente expande sus capacidades modulares justificando métricas precisas.
