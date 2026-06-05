# Documentación del Plan de Reentrenamiento SimBA (2026-02-16)

## 📌 Objetivo
Desarrollar un modelo de clasificación de comportamiento robusto para ratones (específicamente **Grooming** y **Thignotaxis**) que funcione eficazmente en múltiples entornos experimentales. 

El modelo original mostró:
- **Alta sensibilidad (falsos positivos)** en videos de baja resolución (9.1% grooming).
- **Baja sensibilidad (muy conservador)** en videos de alta resolución (0.7% grooming).

## 🚀 Estrategia de Reentrenamiento (Dataset Híbrido)

### 1. Composición del Dataset de Entrenamiento (4 Videos)
Para capturar mejor la variabilidad, utilizaremos un conjunto de datos que mezcla el entorno experimental "Nuevo" con el "Antiguo".

| Video | Entorno | Resolución de Tracking | Estado |
| :--- | :--- | :--- | :--- |
| `R5B20_01mar24.mp4` | **Nuevo** (EPM) | **Full Resolution** (1280x720) | ✅ Listo (Tracking generado) |
| `C1-R1.mov` | **Antiguo** | **Optimized/Fast** (Downscaled 50%) | 🔄 Procesando (Tracking Rápido) |
| `C2-R1.mov` | **Antiguo** | **Optimized/Fast** (Downscaled 50%) | 🔄 Procesando (Tracking Rápido) |
| `C7-R1.mov` | **Antiguo** | **Optimized/Fast** (Downscaled 50%) | 🔄 Procesando (Tracking Rápido) |

> **Nota Técnica:** Se utilizan datos de tracking "Optimizados" (50% resolución) para los videos antiguos porque entrenar un clasificador Random Forest depende más de los *patrones de movimiento* y velocidades relativas que de la precisión de píxel absoluta. Esto ahorra ~10 horas de procesamiento. Los videos nuevos se procesan en Full Resolution para máxima precisión en la inferencia final.

### 2. Flujo de Trabajo Actual
1.  **Generación de Tracking (En curso):**
    -   Script `process_dataset_training.py` está ejecutando DeepLabCut en modo rápido (`downscale_factor=0.5`) para los 3 videos antiguos.
    -   Tiempo estimado: ~45 mins por video.

2.  **Importación a SimBA:**
    -   Una vez generados los archivos de tracking (`.csv`, `.h5`) y los videos correspondientes, se importarán al proyecto SimBA (`SimBA_EPM_Analysis`).

3.  **Etiquetado Manual (Próximo Paso):**
    -   El usuario abrirá la GUI de SimBA y etiquetará manualmente segmentos de comportamiento (Grooming/Thigmotaxis) en estos 4 videos.
    -   Esto proveerá la "verdad terreno" (Ground Truth) para el entrenamiento.

4.  **Entrenamiento del Modelo:**
    -   Se entrenará un nuevo clasificador Random Forest con los datos combinados de los 4 videos.
    -   validación cruzada (Cross-Validation) para asegurar generalización.

5.  **Validación Final:**
    -   Se correrá el nuevo modelo sobre el video `R5B20_01mar24_full` (procesado en alta resolución) para verificar la precisión y reducción de falsos positivos.

## 🛠️ Detalles Técnicos y Optimizaciones
-   **DeepLabCut:** Modelo `superanimal_topviewmouse`.
-   **Aceleración GPU:** `ptxas` habilitado para NVIDIA RTX 5070 Ti (Compute Capability 12.0).
-   **SimBA:** Random Forest Classifier (n_estimators=2000).
-   **Post-Procesamiento:** Umbrales de confianza ajustados (Thigmotaxis: 0.35, Grooming: 0.5) y duración mínima de eventos (100ms).

---
*Este documento sirve como registro del plan de pruebas y configuración actual para referencia futura o auditoría por otros agentes.*
