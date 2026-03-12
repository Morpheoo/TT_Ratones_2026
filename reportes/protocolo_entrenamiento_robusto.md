# Protocolo de Entrenamiento Robusto (Basado en Goodwin et al. 2024)

Este documento detalla el procedimiento actualizado paramitigar el *Jitter* (vibración de coordenadas causante de falsos positivos) y el *Sobreajuste Ambiental* (incapacidad de generalizar entre distintos entornos), siguiendo las directrices del paper de SimBA.

## 1. Problema Diagnosticado en Pruebas Iniciales
*   **Falsos Positivos por Jitter:** Al reducir la resolución del video (para acelerar la inferencia en DeepLabCut), la red neuronal generó coordenadas inestables. SimBA interpretó esta inestabilidad micrométrica como comportamientos genuinos (*Grooming* / *Thigmotaxis*).
*   **Sobreajuste Ambiental:** El modelo fue entrenado exclusivamente en un entorno oscuro (`prueba_real_2min`). Al intentar aplicarlo a un entorno azul (`R5B20`), falló la detección.

## 2. Metodología de Corrección (Paso a Paso)

### Fase A: Creación del "Dataset Híbrido" (Multi-Entorno)
Para asegurar que el clasificador generalice correctamente, el entrenamiento debe realizarse utilizando muestras representativas de distintos escenarios.
1.  **Extracción de Clips Representativos:** Se han recortado fragmentos de 40 segundos de tres entornos distintos:
    *   Entorno 1 (Caja Oscura): `C1-R1_clip.mp4`
    *   Entorno 2 (Laberinto Azul Open): `DZP-R1_clip.mp4`
    *   Entorno 3 (Laberinto Azul Variado): `R5B20_01mar24_clip.mp4`
2.  **Inferencia Rápida (GPU):** Estos clips cortos se procesaron con DeepLabCut (usando resolución nativa/escalada según necesidad) en el entorno `venv_310`, minimizando el tiempo de cómputo (estimado 1.5 hrs en total para los 3 clips combinados).

### Fase B: Importación y Tratamiento Anti-Jitter en SimBA
Al importar los archivos `.csv` generados por DeepLabCut hacia SimBA, es **crítico** aplicar los siguientes filtros en el módulo de "Import Tracking Data" para eliminar la vibración espuria:
1.  **Interpolación:** Activar `Linear Interpolation` para rellenar los huecos donde el modelo perdió la posición temporalmente.
2.  **Suavizado (Smoothing):** Activar `Savitzky-Golay Smoothing` (o filtro Gaussiano). El paper sugiere que esto mitiga la vibración cuadro a cuadro, evitando que los estimadores (Random Forest) lo interpreten como micro-movimientos de acicalamiento.
3.  **Corrección de Outliers:** Activar `Location Outliers` y `Movement Outliers` usando los defaults de SimBA, esto evita saltos cuánticos de las partes del cuerpo.

### Fase C: Etiquetado Manual Multi-Contexto
Una vez creadas las *Features* sobre los datos ya suavizados y estabilizados:
1.  Se utilizará el módulo *Label Behavior* en SimBA para recorrer el dataset híbrido.
2.  El etiquetado se realizará de forma equitativa a través de los diversos entornos, asegurando que el modelo aprenda a identificar "Tigmotaxis" independiente del color de la pared o la iluminación del fondo. 

## 3. Resultado Esperado en Base al Paper
Al aplicar este filtro y utilizando un dataset heterogéneo (Híbrido) obtendremos un clasificador **resistente a la resolución baja** (por el alisado de las curvas de tracking) y universalmente adaptable a tus 9 clips del experimento.
