# Contexto del Proyecto: Sistema de Seguimiento y Análisis de Comportamiento en Ratones (Laberinto en Cruz Elevado - EPM)

Este documento resume el progreso, la arquitectura y los modelos implementados en nuestro proyecto de tesis para automatizar el análisis conductual de roedores. Este contexto es ideal para solicitar métricas de evaluación o nuevos enfoques analíticos.

## 🎯 Objetivo General
Desarrollar un sistema de visión computacional robusto para rastrear la posición de ratones (principalmente albinos) en un Laberinto en Cruz Elevado (EPM) azul, cuantificar el tiempo que pasan en cada brazo y clasificar comportamientos complejos como **Thigmotaxis** (implementado) y **Grooming/Aseo** (próximo objetivo).

## 🧠 Modelos y Tecnologías Implementadas

### 1. YOLOv11 (Tracker Espacial Exclusivo)
*   **Rol:** Seguimiento visual del ratón (centro de masa) para calcular el tiempo exacto en cada zona del laberinto.
*   **Entrenamiento:** Entrenado localmente en una GPU RTX con un dataset propio (*RoedoresV3*) de **2,265 imágenes** anotadas, diseñado para superar el *domain shift* (pelaje blanco sobre el laberinto azul y sombras profundas en brazos cerrados).
*   **Métricas Obtenidas:**
    *   **Precision (P):** 99.5%
    *   **Recall (R):** 98.7%
    *   **mAP50:** 99.4%
*   **Resultado:** Rastreo perfecto (sin saltos ni *jitters* severos), superando los problemas previos donde el modelo confundía el fondo con el sujeto.

### 2. DeepLabCut / SuperAnimal (Pose Estimation)
*   **Rol:** Extracción de coordenadas anatómicas críticas (nariz, orejas, centro, base de la cola, extremidades).
*   **Estado Actual:** Funcional, extrayendo los `.csv` base.
*   **Área de Mejora:** Aún presenta ligero temblor (*jitter*) en posiciones complejas (e.g., bordes de los brazos cerrados). Una de las metas inmediatas es aplicar filtros de suavizado avanzados (como Savitzky-Golay mejorado) o afinar las inferencias de pose.

### 3. SimBA - Simple Behavioral Analysis (Random Forest)
*   **Rol:** Clasificación binaria (o probabilística) de comportamiento basada en la cinemática o geometría extraída por DLC.
*   **Estado Actual:** Modelo de **Thigmotaxis** entrenado y funcional, prediciendo con un umbral dinámico ajustado a 0.35 para confirmación.

## ⚙️ Arquitectura del Pipeline (`generar_video_prediccion.py`)
Hemos construido un script orquestador en Python + OpenCV que integra todos los modelos y renderiza un video de prueba de alta calidad. Sus características clave son:

1.  **Selector Interactivo de ROIs (Regiones de Interés):** Al iniciar, el investigador dibuja a mano con el mouse 5 recuadros (Brazo Norte - Abierto, Sur - Abierto, Este - Cerrado, Oeste - Cerrado y Centro). Cuenta con control de color categórico y opción de deshacer. Esto provee precisión paramétrica perfecta por cada video.
2.  **Split HUD (Head-Up Display) de Nivel Científico:**
    *   **Cuadrante Superior Derecho:** Barra de probabilidad, eventos detectados (Thigmotaxis) y tiempos acumulados del comportamiento.
    *   **Cuadrante Inferior Derecho:** Cronómetros exactos del tiempo que el ratón pasa en cada brazo del laberinto.
    *   **Diseño:** Opacidad del fondo del HUD al 90%, y opacidad del texto al 100% para evitar distracciones en el video pero mantener legibilidad absoluta de los datos.
3.  **Tracker Camaleónico:** Dibuja un punto sobre el ratón cuyo color depende del área física en la que se encuentre: Rosa Coral (Brazos Abiertos), Cyan (Brazos Cerrados) o Naranja (Centro).
4.  **Bitácora CSV Automática:** Exporta un archivo `*_TIMELOG.csv` con todos los *timestamps* de los comportamientos registrados en el video (segundo exacto de inicio, fin y duración).

## 🚀 Siguientes Pasos y Progreso Actual
1.  **Detección de Grooming (Aseo):** 
    *   *Progreso:* Actualizamos el proyecto en SimBA para incluir a "Grooming" como segunda conducta a clasificar. Actualmente estamos en la etapa estricta de anotación manual ("Label Behavior") sobre el dataset de entrenamiento, utilizando atajos de rango continuo para demarcar *bouts* (episodios) consistentes.
    *   *Siguiente Paso:* Realizar el *feature extraction* haciendo hincapié en la oscilación local compacta frente a la inmovilidad global, y entrenar el clasificador Random Forest (RF).
2.  **Optimización de Pose (DLC / SuperAnimal):** 
    *   *Hallazgo (El Problema):* Observamos que los cambios bruscos de iluminación exterior y las sombras profundas (ej. cuando la persona se acerca a la pista) provocan colapsos transitorios (teletransportaciones de *keypoints*) en las inferencias de SuperAnimal.
    *   *Estrategias de Robustez Propuestas:* 
        1.  **Fine-tuning (Transfer Learning):** Refinar los pesos de SuperAnimal anotando apenas ~100-150 frames quirúrgicos en los que existe sombra severa constante (no entrenar desde cero).
        2.  **Active Learning:** Usar la función `extract_outlier_frames` de DLC para detectar automáticamente los saltos estadísticos, corregirlos a mano y afinar el modelo focalizadamente en los fallos persistentes.
        3.  **Filtrado Cinemático Matemático (Enfoque Tesis Actual):** Aplicar interpolación y filtros estadísticos (como Savitzky-Golay) directo sobre los `.csv` antes de introducirlos a SimBA. El modelo corregirá la trayectoria asumiendo que los "teletransportes imposibles" de puntos clave son falsos positivos, delegando al Random Forest de SimBA el trabajo de mitigar la varianza en la clasificación.

***
*Nota para la IA Analista:* Utiliza este contexto para proponernos estrategias rápidas en Python para implementar los filtros cinemáticos (Savitzky-Golay o interpolaciones de outliers) sobre los archivos `.csv` de DLC. Queremos limpiar los saltos transitorios de pose ocasionados por el *domain shift* antes de pasar el dataset a nuestro Random Forest en SimBA.
