# Reporte de Pruebas: Aceleración GPU, Integración DeepLabCut/SimBA y Evaluación de Modelos

**Proyecto:** TT_Ratones_2026
**Hardware Registrado:** NVIDIA GeForce RTX 5070 Ti Laptop GPU

## 1. Resumen Ejecutivo
Se logró exitosamente la integración y aceleración por GPU para la extracción de poses espaciales con DeepLabCut y la clasificación de comportamientos con SimBA. Se optimizaron los tiempos de procesamiento de ~6.0 s/it a ~1.63 s/it. 

Sin embargo, **al entrenar y evaluar los modelos en videos con nuevos entornos (Laberinto Azul vs. Caja Oscura) y con resoluciones alteradas, los resultados iniciales no fueron los esperados**. Se observaron problemas de generalización al cambiar el montaje experimental, así como falsos positivos sistemáticos en el comportamiento debido a fluctuaciones en las coordenadas (*jitter* en resoluciones bajas), lo que obligó a reajustar los modelos y afinar los umbrales de detección.

---

## 2. Configuración de Entornos y Aceleración GPU
- **Entorno GPU Dedicado (`venv_310`):** Dado que TensorFlow 2.10 (requerido para soporte nativo de GPU en Windows) necesita Python 3.10 o inferior, se separó la ejecución del análisis del entorno principal (`venv_311`).
- **Librerías Clave:** Python 3.10.11, TensorFlow 2.10.0 (habilitado vía *legacy headers*), PyTorch 2.7.1+cu118 y librerías NVIDIA para CUDA 11.x.
- **Integración con Streamlit:** La aplicación se mantiene en el entorno principal, pero se ha modificado `pages/03_Analisis_IA.py` para levantar un subproceso (`run_superanimal.py`) con inyección automática de rutas dinámicas a las librerías NVIDIA.
- **Rendimiento Logrado:** 
  - La tarjeta gráfica RTX 5070 Ti fue detectada correctamente por ambas librerías.
  - El tiempo de extracción mejoró radicalmente de **6.0 segundos** (operación CPU) a **1.63 segundos** por iteración en GPU.

---

## 3. Entrenamiento Inicial de Modelos (SimBA)
Se automatizó el pipeline de extracción de datos (proyecto `SimBA_EPM_Analysis`) usando el video base `prueba_real_2min.mp4`. Las características espaciales de movimiento y distancias se utilizaron para crear dos clasificadores de tipo *Random Forest* (2000 estimadores):
- **Grooming.sav** (27 MB) — entrenado con 179 frames etiquetados (5% del video).
- **Thigmotaxis.sav** (46 MB) — entrenado con 383 frames etiquetados (10.6% del video).

---

## 4. Análisis de Video Completo (R5B20_01mar24.mp4 - 5 mins)
Aquí es donde se presentaron los problemas con las expectativas del modelo entrenado.

### 4.1. Desafío 1: El Cambio de Entorno experimental
El video de 5 minutos introdujo un cambio sustancial: el animal fue evaluado en un **Laberinto Azul** en lugar de la **Caja Oscura** original.
- **Impacto:** El modelo original arrojó **0 detecciones** de comportamiento.
- **Mitigación:** Se extrajeron cuadros representativos del clip de prueba y se reentrenó el modelo en SimBA para que lograra identificar los comportamientos bajo la nueva condición de iluminación y espacio, obteniendo resultados iniciales coherentes evaluados en un set corto de 2 min.

### 4.2. Desafío 2: Velocidad vs. Precisión (Problema de Jitter)
Debido a que el video de 5 minutos (~9341 frames) tardaba un estimado de 8 horas, se intentó una optimización bajando la resolución (reducción a 640x360, es decir 50%). Sumado a la corrección del ejecutable `ptxas.exe` para optimizar kernels CUDA (subiendo la velocidad de 0.3 it/s a 3.3 it/s), esto redujo el tiempo total a ~45 minutos. **No obstante, se sacrificó enormemente la precisión.**

**Comparativa del Comportamiento (Benchmarks):**

| Métrica | Ejecución Optimizada (Escalada 50%) | Ejecución Full Res. (Alta Calidad) | Reajuste Full Res. Final |
|---|---|---|---|
| **Duración** | ~48 minutos (🚀 Rápida) | ~3h 56 minutos (🐢 Lenta) | ~4 horas (reuso de tracking DLC) |
| **Resolución** | 640x360 | 1280x720 | 1280x720 |
| **Umbral (Threshold)** | 0.3 | 0.5 (Original) | 0.35 (Thigmotaxis) / 0.5 (Grooming) |
| **Detección: Grooming** | **9.1%** (848 frames) - Falso ↑ | 0.7% (69 frames) | 0.8% (71 frames) |
| **Detección: Thigmo** | **0.2%** (19 frames) - Falso ↑ | 0.0% (0 frames) | 0.4% (35 frames) |

**Explicación del Fallo (Lo que no esperábamos):**
La "Ejecución Optimizada" generó tasas de detección artificialmente altas que no coincidían con la realidad. Al reducir la resolución, los puntos clave (marcadores visuales) en DeepLabCut vibraban constantemente (*coordinate jitter*). El modelo de Random Forest en SimBA malinterpretó esa inestabilidad micrométrica como movimiento legítimo de acicalamiento (Grooming), disparando falsos positivos masivos. Además, un umbral general de 0.5 en alta resolución invisibilizó comportamientos sutiles como la tigmotaxis.

---

## 5. Pruebas de Validación: Video R5DZ_01mar24.mp4
Conociendo las limitaciones de la compresión, se procedió a validar el pipeline completo corriendo un nuevo video a resolución normal (cortado a 2 minutos, omitiendo los 30s iniciales).
- **Extracción:** Se ejecutó con soporte GPU sin incidentes.
- **Inferencia:** Evaluado con los modelos reentrenados y umbrales corregidos.
- **Resultados:** Grooming: 1.7% (63 frames, ~2.1s). Thigmotaxis: 0 frames.
- **En conclusión:** Los niveles de actividad detectados son congruentes con el comportamiento del individuo, centrándose más en exploración del centro del laberinto, y demostrando que la sensibilidad hiperactiva de los modelos fue efectivamente suprimida.

---

## 6. Conclusiones y Diagnóstico Técnico
1. **El Hardware funciona.** El entorno doble (`venv_311` manejando la app y `venv_310` asumiendo la carga matricial) fue un éxito rotundo.
2. **La baja de resolución no es viable.** Intentar procesar videos a escalas del 50% degrada críticamente la certeza del *pipeline*; el "Jitter" resultante destruye la utilidad predictiva del random forest. **Asumiremos los tiempos prolongados de DeepLabCut (3 - 5 horas por 5 min)** a favor de una calidad limpia.
3. **El sobreajuste (Overfitting) ambiental.** El modelo sufre cuando se desplaza al ratón a un recinto totalmente nuevo. Si el proyecto va a combinar ratones de cajas abiertas y laberintos oscuros, será imperativo crear un solo *dataset* de entrenamiento híbrido en SimBA que contenga ejemplos etiquetados de ambos mundos para robustecer a los modelos.
